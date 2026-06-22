from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .collect import collect_rss_source
from .config import load_config
from .documents import process_document_for_paper, refresh_evidence_from_stored_pages
from .evaluate import (
    BenchmarkValidationResult,
    EvaluationMismatch,
    EvaluationResult,
    create_benchmark_subset,
    create_benchmark_template,
    evaluate_run,
    validate_benchmark_file,
)
from .export import export_run
from .export.writer import ExportWriteError
from .manifest import create_manifest
from .models import get_model_provider
from .ops.archive import create_archive_bundle
from .ops.replay import replay_baseline_run
from .ops.retry import retry_call
from .ops.usage import record_fake_usage
from .review.workflow import run_panel_review_for_paper, selected_review_targets
from .selection import select_full_review_candidates, select_publication_candidates
from .store.db import (
    connect,
    init_db,
    insert_run_event,
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

    collect_parser = subparsers.add_parser(
        "collect",
        help="Collect candidates from configured sources.",
    )
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

    refresh_evidence_parser = subparsers.add_parser(
        "refresh-evidence",
        help="Rebuild evidence items from stored extracted document pages.",
    )
    refresh_evidence_parser.add_argument(
        "--run-id",
        help="Refresh successful documents extracted for one run.",
    )
    refresh_evidence_parser.add_argument(
        "--paper-id",
        help="Refresh successful documents for one paper.",
    )
    refresh_evidence_parser.set_defaults(func=cmd_refresh_evidence)

    review_parser = subparsers.add_parser(
        "review",
        help="Run evidence-grounded independent reviewer reports and handling-editor memo.",
    )
    _add_manifest_args(review_parser)
    review_parser.add_argument(
        "--paper-id",
        help="Review one paper instead of all selected papers.",
    )
    review_parser.set_defaults(func=cmd_review)

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate a completed run against labeled benchmark JSON.",
    )
    _add_manifest_args(evaluate_parser)
    evaluate_parser.add_argument(
        "--labels",
        required=True,
        help="Path to benchmark label JSON.",
    )
    evaluate_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full metric JSON.",
    )
    evaluate_parser.add_argument(
        "--errors",
        action="store_true",
        help="Print per-paper mismatches between accepted labels and system outputs.",
    )
    evaluate_parser.set_defaults(func=cmd_evaluate)

    replay_parser = subparsers.add_parser(
        "replay-baseline",
        help="Replay triage/review for an existing run's papers using the current provider.",
    )
    replay_parser.add_argument("--source-run-id", required=True)
    replay_parser.add_argument(
        "--issue-date",
        help="Issue date for the replay run. Defaults to the source run issue date.",
    )
    replay_parser.add_argument(
        "--labels",
        help="Optional benchmark labels to evaluate the replay run immediately.",
    )
    replay_parser.add_argument(
        "--errors",
        action="store_true",
        help="When --labels is provided, print grouped and per-paper evaluation errors.",
    )
    replay_parser.add_argument(
        "--json",
        action="store_true",
        help="When --labels is provided, print full evaluation metric JSON.",
    )
    replay_parser.set_defaults(func=cmd_replay_baseline)

    benchmark_parser = subparsers.add_parser(
        "benchmark-template",
        help="Create a human-labeling benchmark template from a completed run.",
    )
    benchmark_parser.add_argument("--run-id", required=True)
    benchmark_parser.add_argument(
        "--output",
        help="Path to write benchmark template JSON. Defaults to exports/benchmarks/<run-id>.json.",
    )
    benchmark_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of triaged papers to include.",
    )
    benchmark_parser.add_argument(
        "--include-untriaged",
        action="store_true",
        help="Append untriaged collected papers for false-negative labeling.",
    )
    benchmark_parser.set_defaults(func=cmd_benchmark_template)

    benchmark_status_parser = subparsers.add_parser(
        "benchmark-status",
        help="Validate benchmark JSON and report draft or incomplete labels.",
    )
    benchmark_status_parser.add_argument(
        "--labels",
        required=True,
        help="Path to benchmark label or template JSON.",
    )
    benchmark_status_parser.add_argument(
        "--subset-output",
        help="Optional path to write a smaller copied subset for human editing.",
    )
    benchmark_status_parser.add_argument(
        "--subset-size",
        type=int,
        default=6,
        help="Number of papers to include when --subset-output is used.",
    )
    benchmark_status_parser.add_argument(
        "--paper-id",
        action="append",
        default=[],
        help="Paper id to force into the subset. May be passed more than once.",
    )
    benchmark_status_parser.set_defaults(func=cmd_benchmark_status)

    export_parser = subparsers.add_parser(
        "export",
        help="Export draft Markdown and internal notes for human review.",
    )
    _add_manifest_args(export_parser)
    export_parser.add_argument(
        "--output-dir",
        default="exports",
        help="Directory where generated export artifacts are written.",
    )
    export_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing human-edited export files.",
    )
    export_parser.set_defaults(func=cmd_export)

    archive_parser = subparsers.add_parser(
        "archive",
        help="Create a reproducible archive bundle for a run.",
    )
    archive_parser.add_argument("--run-id", required=True)
    archive_parser.add_argument("--archive-dir", default="exports/archives")
    archive_parser.set_defaults(func=cmd_archive)

    scheduled_parser = subparsers.add_parser(
        "run-scheduled",
        help="Run the scheduled draft pipeline without publishing.",
    )
    _add_manifest_args(scheduled_parser)
    scheduled_parser.add_argument("--output-dir", default="exports")
    scheduled_parser.add_argument("--archive-dir", default="exports/archives")
    scheduled_parser.add_argument("--skip-collect", action="store_true")
    scheduled_parser.add_argument("--skip-extract", action="store_true")
    scheduled_parser.add_argument("--force-export", action="store_true")
    scheduled_parser.set_defaults(func=cmd_run_scheduled)
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
        insert_run_event(
            conn,
            run_id=run_id,
            stage="collect",
            status="started",
            message="Collect started",
        )
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
                candidates = retry_call(lambda source=source: collect_rss_source(source))
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
                insert_run_event(
                    conn,
                    run_id=run_id,
                    stage="collect",
                    status="error",
                    message=str(exc),
                    metadata={"source_id": source.id},
                )
        insert_run_event(
            conn,
            run_id=run_id,
            stage="collect",
            status="ok",
            message=f"Collected {collected} candidates",
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
        insert_run_event(
            conn,
            run_id=run_id,
            stage="triage",
            status="started",
            message="Triage started",
        )
        rows = conn.execute(
            """
            SELECT
                papers.id,
                papers.title,
                papers.abstract,
                COALESCE(sources.name, '') AS source_name
            FROM papers
            LEFT JOIN sources ON sources.id = papers.source_id
            WHERE papers.status = 'candidate'
            ORDER BY papers.created_at ASC
            LIMIT ?
            """,
            (config.issue.max_candidates_to_triage,),
        ).fetchall()
        for row in rows:
            input_text = f"{row['title']}\n{row['abstract']}\n{row['source_name']}"
            result = retry_call(
                lambda row=row: provider.triage(row["title"], row["abstract"], row["source_name"])
            )
            record_fake_usage(
                conn,
                run_id=run_id,
                stage="triage",
                provider=provider.name,
                model=config.model_policy.triage_model,
                input_text=input_text,
                output_text=json.dumps(result.__dict__, sort_keys=True),
                metadata={"paper_id": row["id"]},
            )
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
            next_status = (
                "shortlisted" if result.decision == "assign_reviewers" else result.decision
            )
            conn.execute(
                "UPDATE papers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (next_status, row["id"]),
            )
            reviewed += 1
        selection = select_full_review_candidates(conn, run_id=run_id, config=config)
        insert_run_event(
            conn,
            run_id=run_id,
            stage="triage",
            status="ok",
            message=f"Triaged {reviewed} candidates",
        )
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
        insert_run_event(
            conn,
            run_id=run_id,
            stage="extract",
            status="started",
            message="Extraction started",
        )
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
        insert_run_event(
            conn,
            run_id=run_id,
            stage="extract",
            status="error" if errors else "ok",
            message=f"Processed {processed} documents with {errors} errors",
        )
    print(f"Run manifest: {run_id}")
    print(f"Processed documents: {processed}")
    print(f"Document errors: {errors}")
    return 1 if errors else 0


def cmd_refresh_evidence(args: argparse.Namespace) -> int:
    if not args.run_id and not args.paper_id:
        raise SystemExit("refresh-evidence requires --run-id or --paper-id")
    with connect(args.db) as conn:
        init_db(conn)
        if args.run_id and not run_exists(conn, args.run_id):
            raise SystemExit(f"Run manifest not found: {args.run_id}")
        result = refresh_evidence_from_stored_pages(
            conn,
            run_id=args.run_id,
            paper_id=args.paper_id,
        )
    print(f"Run manifest: {args.run_id or 'n/a'}")
    print(f"Paper id: {args.paper_id or 'all'}")
    print(f"Refreshed documents: {result.document_count}")
    print(f"Evidence items: {result.evidence_count}")
    print(f"Skipped documents: {result.skipped_count}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    provider = get_model_provider(config.model_policy.provider)
    reviewed = 0
    errors = 0
    with connect(args.db) as conn:
        init_db(conn)
        run_id = _ensure_run_manifest(conn, config, args)
        insert_run_event(
            conn,
            run_id=run_id,
            stage="review",
            status="started",
            message="Review started",
        )
        targets = selected_review_targets(conn, run_id=run_id, paper_id=args.paper_id)
        for paper_id in targets:
            result = run_panel_review_for_paper(
                conn,
                paper_id=paper_id,
                run_id=run_id,
                provider=provider,
                model_name=config.model_policy.review_model,
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
        insert_run_event(
            conn,
            run_id=run_id,
            stage="review",
            status="error" if errors else "ok",
            message=f"Panel-reviewed {reviewed} papers with {errors} errors",
        )
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
    with connect(args.db) as conn:
        init_db(conn)
        if not args.run_id:
            raise SystemExit("evaluate requires --run-id for a completed run")
        if not run_exists(conn, args.run_id):
            raise SystemExit(f"Run manifest not found: {args.run_id}")
        run_id = args.run_id
        result = evaluate_run(conn, run_id=run_id, labels_path=args.labels)
    if args.json:
        print(json.dumps(result.metrics, indent=2, sort_keys=True))
    else:
        _print_evaluation_result(result, include_errors=args.errors)
    return 0


def cmd_replay_baseline(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    provider = get_model_provider(config.model_policy.provider)
    issue_date = date.fromisoformat(args.issue_date) if args.issue_date else None
    with connect(args.db) as conn:
        init_db(conn)
        try:
            replay = replay_baseline_run(
                conn,
                config=config,
                source_run_id=args.source_run_id,
                provider=provider,
                issue_date=issue_date,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        evaluation = (
            evaluate_run(conn, run_id=replay.replay_run_id, labels_path=args.labels)
            if args.labels
            else None
        )

    if args.json and evaluation:
        print(json.dumps(evaluation.metrics, indent=2, sort_keys=True))
        return 0
    print(f"Source run: {replay.source_run_id}")
    print(f"Replay run: {replay.replay_run_id}")
    print(f"Triaged papers: {replay.triaged_count}")
    print(
        "Selected for full review: "
        f"{replay.full_review_selected_count}/{replay.full_review_candidate_count} "
        "eligible candidates"
    )
    print(f"Panel-reviewed papers: {replay.reviewed_count}")
    print(f"Review errors: {replay.review_error_count}")
    print(f"Selected for deep-dive draft: {replay.deep_dive_selected_count}")
    print(f"Selected for short mention: {replay.short_mention_selected_count}")
    if evaluation:
        _print_evaluation_result(evaluation, include_errors=args.errors)
    return 0


def cmd_benchmark_template(args: argparse.Namespace) -> int:
    output = args.output or f"exports/benchmarks/{args.run_id}.benchmark-template.json"
    with connect(args.db) as conn:
        init_db(conn)
        if not run_exists(conn, args.run_id):
            raise SystemExit(f"Run manifest not found: {args.run_id}")
        try:
            result = create_benchmark_template(
                conn,
                run_id=args.run_id,
                output_path=output,
                limit=args.limit,
                include_untriaged=args.include_untriaged,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    print(f"Run manifest: {result.run_id}")
    print(f"Benchmark template: {result.path}")
    print(f"Papers: {result.paper_count}")
    print(f"Accepted labels: {result.accepted_count}")
    return 0


def cmd_benchmark_status(args: argparse.Namespace) -> int:
    try:
        result = validate_benchmark_file(args.labels)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read benchmark JSON: {exc}") from exc

    _print_benchmark_validation(result)
    if args.subset_output:
        try:
            subset = create_benchmark_subset(
                args.labels,
                args.subset_output,
                size=args.subset_size,
                paper_ids=tuple(args.paper_id),
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"Subset written: {subset.path}")
        print(f"Subset papers: {subset.paper_count}")
        print(f"Subset paper ids: {', '.join(subset.paper_ids)}")
    return 1 if result.error_count else 0


def cmd_export(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        init_db(conn)
        if not args.run_id:
            raise SystemExit("export requires --run-id for a reviewed run")
        if not run_exists(conn, args.run_id):
            raise SystemExit(f"Run manifest not found: {args.run_id}")
        insert_run_event(
            conn,
            run_id=args.run_id,
            stage="export",
            status="started",
            message="Export started",
        )
        try:
            result = export_run(
                conn,
                run_id=args.run_id,
                output_dir=args.output_dir,
                force=args.force,
            )
        except ExportWriteError as exc:
            insert_run_event(
                conn,
                run_id=args.run_id,
                stage="export",
                status="error",
                message=str(exc),
            )
            conn.commit()
            raise SystemExit(str(exc)) from exc
        insert_run_event(
            conn,
            run_id=args.run_id,
            stage="export",
            status="ok",
            message=f"Exported {result.artifact_count} artifacts",
        )
        conn.commit()
    print(f"Run manifest: {result.run_id}")
    print(f"Export directory: {result.output_dir}")
    print(f"Selected records exported: {result.selected_count}")
    for artifact in result.artifacts:
        print(f"{artifact.artifact_type}: {artifact.path}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        init_db(conn)
        if not run_exists(conn, args.run_id):
            raise SystemExit(f"Run manifest not found: {args.run_id}")
        insert_run_event(
            conn,
            run_id=args.run_id,
            stage="archive",
            status="started",
            message="Archive started",
        )
        result = create_archive_bundle(conn, run_id=args.run_id, archive_dir=args.archive_dir)
        insert_run_event(
            conn,
            run_id=args.run_id,
            stage="archive",
            status="ok",
            message=f"Created archive with {result.file_count} files",
            metadata={"path": str(result.path)},
        )
        conn.commit()
    print(f"Run manifest: {result.run_id}")
    print(f"Archive: {result.path}")
    print(f"Files archived: {result.file_count}")
    return 0


def cmd_run_scheduled(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    provider = get_model_provider(config.model_policy.provider)
    with connect(args.db) as conn:
        init_db(conn)
        run_id = _scheduled_run_id(conn, config, args)
        insert_run_event(
            conn,
            run_id=run_id,
            stage="scheduled",
            status="started",
            message="Scheduled draft run started",
        )
        collected = 0
        if not args.skip_collect:
            collected = _scheduled_collect(conn, config=config, run_id=run_id)
        reviewed = _scheduled_triage(conn, config=config, run_id=run_id, provider=provider)
        selection = select_full_review_candidates(conn, run_id=run_id, config=config)
        extracted, extraction_errors = (0, 0)
        if not args.skip_extract:
            extracted, extraction_errors = _scheduled_extract(conn, run_id=run_id)
        panel_reviewed, review_errors = _scheduled_review(
            conn,
            config=config,
            run_id=run_id,
            provider=provider,
        )
        publication_selection = select_publication_candidates(conn, run_id=run_id, config=config)
        export_result = export_run(
            conn,
            run_id=run_id,
            output_dir=args.output_dir,
            force=args.force_export,
        )
        archive_result = create_archive_bundle(conn, run_id=run_id, archive_dir=args.archive_dir)
        status = "error" if extraction_errors or review_errors else "ok"
        insert_run_event(
            conn,
            run_id=run_id,
            stage="scheduled",
            status=status,
            message="Scheduled draft run finished",
            metadata={
                "collected": collected,
                "triaged": reviewed,
                "selected_full_review": selection.selected_count,
                "extracted": extracted,
                "extraction_errors": extraction_errors,
                "panel_reviewed": panel_reviewed,
                "review_errors": review_errors,
                "deep_dive_drafts": publication_selection.deep_dive_selected_count,
                "short_mentions": publication_selection.short_mention_selected_count,
                "export_dir": str(export_result.output_dir),
                "archive": str(archive_result.path),
            },
        )
        conn.commit()
    print(f"Run manifest: {run_id}")
    print(f"Collected candidates: {collected}")
    print(f"Triaged candidates: {reviewed}")
    print(f"Selected for full review: {selection.selected_count}")
    print(f"Extracted documents: {extracted}; errors={extraction_errors}")
    print(f"Panel-reviewed papers: {panel_reviewed}; errors={review_errors}")
    print(f"Selected deep-dive drafts: {publication_selection.deep_dive_selected_count}")
    print(f"Selected short mentions: {publication_selection.short_mention_selected_count}")
    print(f"Export directory: {export_result.output_dir}")
    print(f"Archive: {archive_result.path}")
    return 1 if status == "error" else 0


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


def _scheduled_run_id(conn, config, args) -> str:
    if args.run_id:
        if not run_exists(conn, args.run_id):
            raise SystemExit(f"Run manifest not found: {args.run_id}")
        return args.run_id
    manifest = create_manifest(
        config=config,
        issue_date=date.fromisoformat(args.issue_date),
        automation_mode="scheduled-draft",
    )
    insert_manifest(conn, manifest)
    return manifest.run_id


def _scheduled_collect(conn, *, config, run_id: str) -> int:
    collected = 0
    insert_run_event(
        conn,
        run_id=run_id,
        stage="collect",
        status="started",
        message="Collect started",
    )
    for source in config.sources:
        upsert_source(conn, source)
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
            candidates = retry_call(lambda source=source: collect_rss_source(source))
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
    insert_run_event(
        conn,
        run_id=run_id,
        stage="collect",
        status="ok",
        message=f"Collected {collected} candidates",
    )
    conn.commit()
    return collected


def _scheduled_triage(conn, *, config, run_id: str, provider) -> int:
    reviewed = 0
    insert_run_event(
        conn,
        run_id=run_id,
        stage="triage",
        status="started",
        message="Triage started",
    )
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
        result = retry_call(
            lambda row=row: provider.triage(row["title"], row["abstract"], row["source_name"])
        )
        record_fake_usage(
            conn,
            run_id=run_id,
            stage="triage",
            provider=provider.name,
            model=config.model_policy.triage_model,
            input_text=f"{row['title']}\n{row['abstract']}\n{row['source_name']}",
            output_text=json.dumps(result.__dict__, sort_keys=True),
            metadata={"paper_id": row["id"]},
        )
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
    insert_run_event(
        conn,
        run_id=run_id,
        stage="triage",
        status="ok",
        message=f"Triaged {reviewed} candidates",
    )
    conn.commit()
    return reviewed


def _scheduled_extract(conn, *, run_id: str) -> tuple[int, int]:
    processed = 0
    errors = 0
    insert_run_event(
        conn,
        run_id=run_id,
        stage="extract",
        status="started",
        message="Extraction started",
    )
    for paper_id, source_uri in _extract_targets(conn, run_id=run_id, paper_id=None, source=None):
        result = process_document_for_paper(
            conn,
            paper_id=paper_id,
            source_uri=source_uri,
            run_id=run_id,
        )
        processed += 1
        if result.status != "ok":
            errors += 1
    insert_run_event(
        conn,
        run_id=run_id,
        stage="extract",
        status="error" if errors else "ok",
        message=f"Processed {processed} documents with {errors} errors",
    )
    conn.commit()
    return processed, errors


def _scheduled_review(conn, *, config, run_id: str, provider) -> tuple[int, int]:
    reviewed = 0
    errors = 0
    insert_run_event(
        conn,
        run_id=run_id,
        stage="review",
        status="started",
        message="Review started",
    )
    for paper_id in selected_review_targets(conn, run_id=run_id):
        result = run_panel_review_for_paper(
            conn,
            paper_id=paper_id,
            run_id=run_id,
            provider=provider,
            model_name=config.model_policy.review_model,
        )
        reviewed += 1
        if result.status != "ok":
            errors += 1
    insert_run_event(
        conn,
        run_id=run_id,
        stage="review",
        status="error" if errors else "ok",
        message=f"Panel-reviewed {reviewed} papers with {errors} errors",
    )
    conn.commit()
    return reviewed, errors


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


def _format_metric(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def _print_evaluation_result(result: EvaluationResult, *, include_errors: bool) -> None:
    triage = result.metrics["triage"]
    evidence = result.metrics["evidence"]
    review = result.metrics["review"]
    selection = result.metrics["selection"]
    rubric = result.metrics.get("rubric", {})
    print(f"Run manifest: {result.run_id}")
    print(f"Evaluation run: {result.evaluation_run_id}")
    print(f"Benchmark: {result.benchmark_version}")
    print(f"Labeled papers: {result.metrics['labeled_papers']}")
    print(f"Triage decision accuracy: {_format_metric(triage['decision_accuracy'])}")
    print(f"Full-review selected precision: {_format_metric(triage['selected_precision'])}")
    print(f"Relevant-paper recall: {_format_metric(triage['relevant_recall'])}")
    print(
        "Hard-negative false-positive rate: "
        f"{_format_metric(triage['hard_negative_false_positive_rate'])}"
    )
    print(
        "Evidence required-kind coverage: "
        f"{_format_metric(evidence['required_kind_coverage'])}"
    )
    print(f"Reviewer citation coverage: {_format_metric(review['citation_coverage'])}")
    print(f"Invalid citation rate: {_format_metric(review['invalid_citation_rate'])}")
    print(
        "Editorial decision accuracy: "
        f"{_format_metric(review['editorial_decision_accuracy'])}"
    )
    print(f"Deep-dive selection accuracy: {_format_metric(selection['deep_dive_accuracy'])}")
    print(
        "Publication-track accuracy: "
        f"{_format_metric(rubric.get('publication_track_accuracy'))}"
    )
    if include_errors:
        _print_evaluation_error_summary(result.metrics["error_summary"])
        _print_evaluation_mismatches(result.mismatches)


def _print_evaluation_mismatches(mismatches: tuple[EvaluationMismatch, ...]) -> None:
    print(f"Mismatches: {len(mismatches)}")
    if not mismatches:
        return
    current_paper_id: str | None = None
    for mismatch in mismatches:
        if mismatch.paper_id != current_paper_id:
            current_paper_id = mismatch.paper_id
            title = mismatch.title or "(title unavailable)"
            print(f"- {title} [{mismatch.paper_id}]")
        print(
            "  "
            f"{mismatch.field}: human={_format_report_value(mismatch.human_label)}; "
            f"system={_format_report_value(mismatch.system_output)}; "
            f"type={mismatch.failure_type}; "
            f"{mismatch.reason}"
        )


def _print_evaluation_error_summary(summary: dict[str, object]) -> None:
    print("Error summary:")
    print(f"- impacted papers: {summary['paper_count']}")
    print(f"- total mismatches: {summary['mismatch_count']}")
    by_failure_type = summary.get("by_failure_type") or {}
    if by_failure_type:
        print("- failure types:")
        for name, count in by_failure_type.items():
            print(f"  {name}: {count}")
    missing_kinds = summary.get("missing_required_evidence_kinds") or {}
    if missing_kinds:
        print("- missing evidence kinds:")
        for name, count in missing_kinds.items():
            print(f"  {name}: {count}")
    recommendations = summary.get("recommendations") or ()
    if recommendations:
        print("- recommended next actions:")
        for recommendation in recommendations:
            print(f"  {recommendation}")


def _format_report_value(value: object) -> str:
    if value is None:
        return "missing"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


def _print_benchmark_validation(result: BenchmarkValidationResult) -> None:
    print(f"Benchmark: {result.version}")
    print(f"Path: {result.path}")
    print(f"Papers: {result.paper_count}")
    print(f"Accepted labels: {result.accepted_count}")
    print(f"Draft/not accepted labels: {result.not_accepted_count}")
    print(f"Incomplete labels: {result.incomplete_count}")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")
    print(f"Ready for ets4 evaluate: {'yes' if result.ready_for_evaluation else 'no'}")
    for error in result.top_level_errors:
        print(f"Top-level error: {error}")
    if result.duplicate_paper_ids:
        print(f"Duplicate paper ids: {', '.join(result.duplicate_paper_ids)}")

    problem_statuses = [
        status
        for status in result.paper_statuses
        if not status.is_accepted or status.is_incomplete or status.warnings
    ]
    if not problem_statuses:
        return
    print("Draft, incomplete, or warning labels:")
    for status in problem_statuses:
        details = []
        if status.label_status not in {None, "accepted"}:
            details.append(f"status={status.label_status or 'missing'}")
        if status.missing_fields:
            details.append(f"missing={','.join(status.missing_fields)}")
        if status.invalid_fields:
            details.append(f"invalid={','.join(status.invalid_fields)}")
        if status.warnings:
            details.append(f"warnings={','.join(status.warnings)}")
        print(f"- {status.paper_id}: {'; '.join(details)}")


if __name__ == "__main__":
    raise SystemExit(main())
