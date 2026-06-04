from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .collect import collect_rss_source
from .config import load_config
from .documents import process_document_for_paper
from .manifest import create_manifest
from .models import get_model_provider
from .review.workflow import run_panel_review_for_paper, selected_review_targets
from .selection import select_full_review_candidates, select_publication_candidates
from .store.db import (
    connect,
    init_db,
    insert_source_event,
    insert_manifest,
    run_exists,
    upsert_paper,
    upsert_source,
)

DEFAULT_CONFIG = Path("config/feeds.example.toml")
DEFAULT_DB = Path("data/ets4.sqlite")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ets4")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to TOML config.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to SQLite database.")
    subparsers = parser.add_subparsers(required=True)

    init_parser = subparsers.add_parser("init-db", help="Initialize the SQLite database.")
    init_parser.set_defaults(func=cmd_init_db)

    manifest_parser = subparsers.add_parser("manifest", help="Create and store a run manifest.")
    _add_manifest_args(manifest_parser)
    manifest_parser.set_defaults(func=cmd_manifest)

    collect_parser = subparsers.add_parser("collect", help="Collect candidates from configured sources.")
    _add_manifest_args(collect_parser)
    collect_parser.add_argument("--dry-run", action="store_true", help="Register sources only.")
    collect_parser.set_defaults(func=cmd_collect)

    triage_parser = subparsers.add_parser("triage", help="Run fake-provider triage for candidates.")
    _add_manifest_args(triage_parser)
    triage_parser.set_defaults(func=cmd_triage)

    select_parser = subparsers.add_parser(
        "select",
        help="Select full-review candidates under the issue paper budget.",
    )
    _add_manifest_args(select_parser)
    select_parser.set_defaults(func=cmd_select)

    extract_parser = subparsers.add_parser(
        "extract",
        help="Retrieve documents and extract page text/evidence items.",
    )
    _add_manifest_args(extract_parser)
    extract_parser.add_argument("--paper-id", help="Paper id to extract evidence for.")
    extract_parser.add_argument("--source", help="Document URL or local path.")
    extract_parser.set_defaults(func=cmd_extract)

    review_parser = subparsers.add_parser(
        "review",
        help="Run evidence-grounded independent reviewer reports and handling-editor memo.",
    )
    _add_manifest_args(review_parser)
    review_parser.add_argument("--paper-id", help="Review one paper instead of all selected papers.")
    review_parser.set_defaults(func=cmd_review)

    evaluate_parser = subparsers.add_parser("evaluate", help="Placeholder for evaluation harness.")
    evaluate_parser.set_defaults(func=cmd_evaluate)

    export_parser = subparsers.add_parser("export", help="Placeholder for draft export.")
    export_parser.set_defaults(func=cmd_export)
    return parser


def _add_manifest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--issue-date", default=date.today().isoformat())
    parser.add_argument("--run-id", help="Continue an existing run manifest.")
    parser.add_argument(
        "--automation-mode",
        choices=("manual", "scheduled-draft", "evaluation"),
        default="manual",
    )


def cmd_init_db(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        init_db(conn)
    print(f"Initialized database: {args.db}")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    manifest = create_manifest(
        config=config,
        issue_date=date.fromisoformat(args.issue_date),
        automation_mode=args.automation_mode,
    )
    with connect(args.db) as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
    print(manifest.run_id)
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    collected = 0
    with connect(args.db) as conn:
        init_db(conn)
        run_id = _ensure_run_manifest(conn, config, args)
        for source in config.sources:
            upsert_source(conn, source)
            if args.dry_run:
                continue
            if source.type != "rss":
                insert_source_event(
                    conn,
                    source_id=source.id,
                    run_id=run_id,
                    status="skipped",
                    message=f"Unsupported source type: {source.type}",
                )
                continue
            try:
                candidates = collect_rss_source(source)
                for candidate in candidates:
                    upsert_paper(
                        conn,
                        paper_id=candidate.paper_id,
                        title=candidate.title,
                        canonical_url=candidate.canonical_url,
                        abstract=candidate.abstract,
                        authors=candidate.authors,
                        source_id=candidate.source_id,
                        published_date=candidate.published_date,
                        doi=candidate.doi,
                        arxiv_id=candidate.arxiv_id,
                    )
                collected += len(candidates)
                insert_source_event(
                    conn,
                    source_id=source.id,
                    run_id=run_id,
                    status="ok",
                    message=f"Collected {len(candidates)} candidates",
                    candidate_count=len(candidates),
                )
            except Exception as exc:
                insert_source_event(
                    conn,
                    source_id=source.id,
                    run_id=run_id,
                    status="error",
                    message=str(exc),
                )
        conn.commit()
    print(f"Run manifest: {run_id}")
    print(f"Registered sources: {len(config.sources)}")
    print(f"Collected candidates: {collected}")
    return 0


def cmd_triage(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    provider = get_model_provider(config.model_policy.provider)
    reviewed = 0
    with connect(args.db) as conn:
        init_db(conn)
        run_id = _ensure_run_manifest(conn, config, args)
        rows = conn.execute(
            """
            SELECT papers.id, papers.title, papers.abstract, COALESCE(sources.name, '') AS source_name
            FROM papers
            LEFT JOIN sources ON sources.id = papers.source_id
            WHERE papers.status = 'candidate'
            ORDER BY papers.created_at ASC
            LIMIT ?
            """,
            (config.issue.max_candidates_to_triage,),
        ).fetchall()
        for row in rows:
            result = provider.triage(row["title"], row["abstract"], row["source_name"])
            conn.execute(
                """
                INSERT OR REPLACE INTO triage_reviews (
                    paper_id, run_id, provider, decision, category_hint,
                    forecasting_signal, economic_signal, score, confidence, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    run_id,
                    provider.name,
                    result.decision,
                    result.category_hint,
                    result.forecasting_signal,
                    result.economic_signal,
                    result.score,
                    result.confidence,
                    result.reason,
                ),
            )
            next_status = "shortlisted" if result.decision == "assign_reviewers" else result.decision
            conn.execute(
                "UPDATE papers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (next_status, row["id"]),
            )
            reviewed += 1
        selection = select_full_review_candidates(conn, run_id=run_id, config=config)
        conn.commit()
    print(f"Run manifest: {run_id}")
    print(f"Triaged candidates: {reviewed}")
    print(
        "Selected for full review: "
        f"{selection.selected_count}/{selection.candidate_count} eligible candidates"
    )
    return 0


def cmd_select(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    with connect(args.db) as conn:
        init_db(conn)
        run_id = _ensure_run_manifest(conn, config, args)
        selection = select_full_review_candidates(conn, run_id=run_id, config=config)
    print(f"Run manifest: {run_id}")
    print(
        "Selected for full review: "
        f"{selection.selected_count}/{selection.candidate_count} eligible candidates"
    )
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    processed = 0
    errors = 0
    with connect(args.db) as conn:
        init_db(conn)
        run_id = _ensure_run_manifest(conn, config, args)
        targets = _extract_targets(conn, run_id=run_id, paper_id=args.paper_id, source=args.source)
        for paper_id, source_uri in targets:
            result = process_document_for_paper(
                conn,
                paper_id=paper_id,
                source_uri=source_uri,
                run_id=run_id,
            )
            processed += 1
            if result.status != "ok":
                errors += 1
            print(
                f"{paper_id}: {result.status}; pages={result.page_count}; "
                f"evidence={result.evidence_count}; source={source_uri}"
            )
    print(f"Run manifest: {run_id}")
    print(f"Processed documents: {processed}")
    print(f"Document errors: {errors}")
    return 1 if errors else 0


def cmd_review(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    provider = get_model_provider(config.model_policy.provider)
    reviewed = 0
    errors = 0
    with connect(args.db) as conn:
        init_db(conn)
        run_id = _ensure_run_manifest(conn, config, args)
        targets = selected_review_targets(conn, run_id=run_id, paper_id=args.paper_id)
        for paper_id in targets:
            result = run_panel_review_for_paper(
                conn,
                paper_id=paper_id,
                run_id=run_id,
                provider=provider,
            )
            reviewed += 1
            if result.status != "ok":
                errors += 1
            decision = result.decision or "none"
            score = "n/a" if result.deep_dive_score is None else f"{result.deep_dive_score:.3f}"
            print(
                f"{paper_id}: {result.status}; reviewers={result.reviewer_count}; "
                f"decision={decision}; deep_dive_score={score}"
            )
        publication_selection = select_publication_candidates(conn, run_id=run_id, config=config)
    print(f"Run manifest: {run_id}")
    print(f"Panel-reviewed papers: {reviewed}")
    print(
        "Selected for deep-dive draft: "
        f"{publication_selection.deep_dive_selected_count}/"
        f"{publication_selection.candidate_count} reviewed candidates"
    )
    print(f"Selected for short mention: {publication_selection.short_mention_selected_count}")
    print(f"Review errors: {errors}")
    return 1 if errors else 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    print("Evaluation harness is not implemented yet. Next phase: labeled fixtures + metrics.")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    print("Draft export is not implemented yet. Next phase: Markdown + internal notes.")
    return 0


def _ensure_run_manifest(conn, config, args) -> str:
    if args.run_id:
        if not run_exists(conn, args.run_id):
            raise SystemExit(f"Run manifest not found: {args.run_id}")
        return args.run_id

    manifest = create_manifest(
        config=config,
        issue_date=date.fromisoformat(args.issue_date),
        automation_mode=args.automation_mode,
    )
    insert_manifest(conn, manifest)
    return manifest.run_id


def _extract_targets(
    conn,
    *,
    run_id: str,
    paper_id: str | None,
    source: str | None,
) -> list[tuple[str, str]]:
    if paper_id and source:
        return [(paper_id, source)]
    if paper_id or source:
        raise SystemExit("--paper-id and --source must be provided together")
    rows = conn.execute(
        """
        SELECT papers.id, papers.canonical_url
        FROM candidate_selections
        JOIN papers ON papers.id = candidate_selections.paper_id
        WHERE candidate_selections.run_id = ?
          AND candidate_selections.selection_stage = 'full_review'
        ORDER BY candidate_selections.rank ASC
        """,
        (run_id,),
    ).fetchall()
    return [(row["id"], row["canonical_url"]) for row in rows]


if __name__ == "__main__":
    raise SystemExit(main())
