from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .collect import collect_rss_source
from .config import load_config
from .manifest import create_manifest
from .models import get_model_provider
from .store.db import (
    connect,
    init_db,
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

    review_parser = subparsers.add_parser("review", help="Placeholder for full panel review.")
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
                conn.execute(
                    """
                    INSERT INTO source_events(source_id, run_id, status, message)
                    VALUES (?, ?, ?, ?)
                    """,
                    (source.id, run_id, "skipped", f"Unsupported source type: {source.type}"),
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
                    )
                collected += len(candidates)
                conn.execute(
                    """
                    INSERT INTO source_events(source_id, run_id, status, message)
                    VALUES (?, ?, ?, ?)
                    """,
                    (source.id, run_id, "ok", f"Collected {len(candidates)} candidates"),
                )
            except Exception as exc:
                conn.execute(
                    """
                    INSERT INTO source_events(source_id, run_id, status, message)
                    VALUES (?, ?, ?, ?)
                    """,
                    (source.id, run_id, "error", str(exc)),
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
        conn.commit()
    print(f"Run manifest: {run_id}")
    print(f"Triaged candidates: {reviewed}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    print("Full panel review is not implemented yet. Next phase: evidence dossier + reviewers.")
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
