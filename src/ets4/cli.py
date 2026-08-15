"""Terminal interface for complete targeted manuscript reviews."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ets4.config import (
    ConfigurationError,
    ReviewSettings,
    load_settings,
    validate_provider_environment,
)
from ets4.domain.schemas import WorkflowState
from ets4.ingestion.pdf import ManuscriptIngestionError
from ets4.limits import MAX_REVIEW_REQUIREMENTS
from ets4.providers.factory import build_provider, provider_descriptions
from ets4.providers.mock import MockProvider
from ets4.storage.run_store import RunStore, RunStoreError, redact_secrets
from ets4.workflow.engine import ReviewWorkflow, WorkflowError


def _common_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-dir", type=Path, help="root directory containing isolated runs")
    parser.add_argument("--provider", choices=("mock", "openai"), help="model provider")
    parser.add_argument("--model", help="global provider model identifier")
    parser.add_argument("--initial-editor-model", help="optional Stage 1 model override")
    parser.add_argument("--referee-model", help="optional Stage 2 model override")
    parser.add_argument("--final-editor-model", help="optional Stage 3 model override")
    parser.add_argument("--config", type=Path, help="local ETS4 TOML configuration")


def _review_requirement_count(value: str) -> int | str:
    if value.strip().lower() == "auto":
        return "auto"
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use 'auto' or a positive integer") from exc
    if not 1 <= count <= MAX_REVIEW_REQUIREMENTS:
        raise argparse.ArgumentTypeError(
            f"review requirements must be between 1 and {MAX_REVIEW_REQUIREMENTS}"
        )
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ets4",
        description="Targeted multi-agent academic review for economic time-series forecasting.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    review = subparsers.add_parser("review", help="run all three stages on a PDF or manuscript URL")
    review.add_argument(
        "source", help="local PDF path or direct/narrowly resolvable manuscript URL"
    )
    _common_run_options(review)
    review.add_argument("--referees", type=int, dest="referee_count", help="requested panel size")
    review.add_argument(
        "--review-requirements",
        type=_review_requirement_count,
        dest="review_requirement_count",
        metavar="COUNT|auto",
        help=(
            "exact number of Stage 1 review requirements, or auto for no number guidance "
            f"(exact maximum: {MAX_REVIEW_REQUIREMENTS})"
        ),
    )
    review.add_argument("--max-referees", type=int, help="cost-control ceiling (hard maximum: 12)")
    review.add_argument("--max-concurrency", type=int, help="maximum simultaneous referee calls")
    review.add_argument(
        "--retain-raw-responses",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="retain confidential raw provider responses under logs/raw",
    )

    resume = subparsers.add_parser("resume", help="resume only incomplete or failed stages")
    resume.add_argument("run_id")
    resume.add_argument("--output-dir", type=Path, default=Path("runs"))

    status = subparsers.add_parser("status", help="inspect durable workflow state")
    status.add_argument("run_id")
    status.add_argument("--output-dir", type=Path, default=Path("runs"))
    status.add_argument("--json", action="store_true", dest="as_json")

    cancel = subparsers.add_parser("cancel", help="mark an incomplete run as cancelled")
    cancel.add_argument("run_id")
    cancel.add_argument("--output-dir", type=Path, default=Path("runs"))

    validate = subparsers.add_parser(
        "validate-config", help="validate configuration and credentials"
    )
    _common_run_options(validate)
    validate.add_argument("--referees", type=int, dest="referee_count")
    validate.add_argument(
        "--review-requirements",
        type=_review_requirement_count,
        dest="review_requirement_count",
        metavar="COUNT|auto",
    )

    subparsers.add_parser("providers", help="list implemented provider capabilities")
    return parser


def _cli_overrides(arguments: argparse.Namespace) -> dict[str, Any]:
    names = {
        "output_dir",
        "provider",
        "model",
        "initial_editor_model",
        "referee_model",
        "final_editor_model",
        "referee_count",
        "review_requirement_count",
        "max_referees",
        "max_concurrency",
        "retain_raw_responses",
    }
    return {name: getattr(arguments, name, None) for name in names}


def _status_code(state: WorkflowState) -> int:
    return 0 if state == WorkflowState.COMPLETED else 2


def _progress(message: str) -> None:
    print(f"[ets4] {message}", file=sys.stderr)


def _settings_for_existing_run(output_dir: Path, run_id: str) -> tuple[ReviewSettings, RunStore]:
    store = RunStore(output_dir)
    manifest = store.load_manifest(run_id)
    settings = ReviewSettings.model_validate(manifest.configuration).model_copy(
        update={"output_dir": output_dir}
    )
    return settings, store


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "providers":
            print(json.dumps(provider_descriptions(), indent=2))
            return 0

        if arguments.command == "status":
            manifest = RunStore(arguments.output_dir).load_manifest(arguments.run_id)
            payload = {
                "run_id": manifest.run_id,
                "input_fingerprint": manifest.input_fingerprint,
                "workflow_state": manifest.workflow_state.value,
                "completed_stages": manifest.completed_stages,
                "failed_stages": manifest.failed_stages,
                "warnings": [warning.model_dump(mode="json") for warning in manifest.warnings],
                "stages": {
                    name: {
                        "status": record.status.value,
                        "attempts": record.attempts,
                        "error": record.error,
                        "error_details": record.error_details,
                    }
                    for name, record in manifest.stages.items()
                },
            }
            if arguments.as_json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(f"Run: {manifest.run_id}")
                print(f"State: {manifest.workflow_state.value}")
                print("Completed: " + (", ".join(manifest.completed_stages) or "none"))
                print("Failed: " + (", ".join(manifest.failed_stages) or "none"))
                for warning in manifest.warnings:
                    print(f"Warning: {warning.message}")
                for stage in manifest.failed_stages:
                    record = manifest.stages[stage]
                    print(f"Failure {stage}: {record.error or 'unknown error'}")
                    for key in ("status", "code", "parameter", "request_id"):
                        value = record.error_details.get(key)
                        if value is not None:
                            print(f"  {key}: {value}")
            return _status_code(manifest.workflow_state)

        if arguments.command == "cancel":
            settings, store = _settings_for_existing_run(arguments.output_dir, arguments.run_id)
            workflow = ReviewWorkflow(settings, MockProvider(), store=store, progress=_progress)
            manifest = workflow.cancel(arguments.run_id)
            print(manifest.run_id)
            return 0

        if arguments.command == "resume":
            settings, store = _settings_for_existing_run(arguments.output_dir, arguments.run_id)
            validate_provider_environment(settings)
            workflow = ReviewWorkflow(
                settings, build_provider(settings), store=store, progress=_progress
            )
            manifest = workflow.resume(arguments.run_id)
            print(manifest.run_id)
            return _status_code(manifest.workflow_state)

        settings = load_settings(arguments.config, _cli_overrides(arguments))
        validate_provider_environment(settings)
        if arguments.command == "validate-config":
            print(json.dumps(settings.manifest_dict(), indent=2, sort_keys=True))
            return 0

        if arguments.command == "review":
            provider = build_provider(settings)
            workflow = ReviewWorkflow(settings, provider, progress=_progress)
            manifest = workflow.start(arguments.source)
            print(manifest.run_id)
            return _status_code(manifest.workflow_state)
    except (
        ConfigurationError,
        ManuscriptIngestionError,
        RunStoreError,
        WorkflowError,
        ValueError,
    ) as exc:
        print(f"ets4: {redact_secrets(str(exc))}", file=sys.stderr)
        return 1

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
