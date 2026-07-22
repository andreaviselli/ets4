from __future__ import annotations

from pathlib import Path

from ets4.cli import main
from ets4.config import ReviewSettings
from ets4.providers.base import ProviderError, StageRequest
from ets4.providers.mock import MockProvider
from ets4.workflow.engine import ReviewWorkflow


class DetailedInitialFailureProvider(MockProvider):
    def generate(self, request: StageRequest):
        if request.stage == "initial_editor":
            raise ProviderError(
                "Invalid response format schema",
                retryable=False,
                details={
                    "provider": "openai",
                    "exception_type": "BadRequestError",
                    "message": "Invalid response format schema",
                    "code": "invalid_json_schema",
                    "parameter": "text.format.schema",
                    "status": 400,
                    "request_id": "req_status_123",
                },
            )
        return super().generate(request)


def test_cli_review_status_and_provider_listing(
    manuscript_path: Path, tmp_path: Path, capsys
) -> None:
    runs = tmp_path / "runs"
    exit_code = main(
        [
            "review",
            str(manuscript_path),
            "--provider",
            "mock",
            "--referees",
            "2",
            "--output-dir",
            str(runs),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    run_id = captured.out.strip()
    assert run_id.startswith("run-")
    assert "Stage 1/3" in captured.err
    assert main(["status", run_id, "--output-dir", str(runs)]) == 0
    status = capsys.readouterr().out
    assert "State: completed" in status
    assert main(["providers"]) == 0
    assert '"openai"' in capsys.readouterr().out


def test_cli_does_not_offer_api_key_flag() -> None:
    exit_code = main(["providers"])
    assert exit_code == 0


def test_status_shows_sanitized_provider_failure_details(
    manuscript_path: Path, tmp_path: Path, capsys
) -> None:
    runs = tmp_path / "runs"
    settings = ReviewSettings(
        referee_count=1,
        output_dir=runs,
        max_provider_retries=0,
        max_repair_attempts=0,
    )
    failed = ReviewWorkflow(settings, DetailedInitialFailureProvider()).start(str(manuscript_path))

    assert main(["status", failed.run_id, "--output-dir", str(runs)]) == 2
    output = capsys.readouterr().out
    assert "Failure initial-editor: Invalid response format schema" in output
    assert "status: 400" in output
    assert "code: invalid_json_schema" in output
    assert "parameter: text.format.schema" in output
    assert "request_id: req_status_123" in output

    events = (runs / failed.run_id / "logs" / "events.jsonl").read_text()
    assert '"parameter": "text.format.schema"' in events
    assert '"request_id": "req_status_123"' in events
