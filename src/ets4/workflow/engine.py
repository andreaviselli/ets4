"""Explicit editor -> independent referees -> final editor state machine."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import BaseModel

from ets4.config import ReviewSettings
from ets4.domain.schemas import (
    EditorPanelDesign,
    FinalEditorDecision,
    RefereeReport,
    RunManifest,
    StageRecord,
    StageStatus,
    WorkflowState,
    structured_output_schema_hashes,
)
from ets4.ingestion.models import ManuscriptPackage
from ets4.ingestion.pdf import ManuscriptIngestor
from ets4.prompts.renderer import PromptRepository
from ets4.providers.base import Provider, ProviderError, ProviderResult, StageRequest
from ets4.rendering.markdown import render_final_editor, render_initial_editor, render_referee
from ets4.storage.run_store import RunStore, redact_secrets

ProgressCallback = Callable[[str], None]
ArtifactModel = TypeVar("ArtifactModel", bound=BaseModel)


class WorkflowError(RuntimeError):
    """Raised when durable workflow invariants would otherwise be violated."""


@dataclass(frozen=True, slots=True)
class CallOutcome:
    result: ProviderResult[Any]
    attempts: int
    invalid_raw_responses: tuple[Any, ...]


class StageExecutionError(WorkflowError):
    def __init__(
        self,
        message: str,
        *,
        attempts: int,
        invalid_raw_responses: tuple[Any, ...] = (),
        error_details: dict[str, str | int | None] | None = None,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.invalid_raw_responses = invalid_raw_responses
        self.error_details = error_details or {}


class ReviewWorkflow:
    """Application-controlled stage ordering with isolated fan-out and durable fan-in."""

    def __init__(
        self,
        settings: ReviewSettings,
        provider: Provider,
        *,
        prompts: PromptRepository | None = None,
        ingestor: ManuscriptIngestor | None = None,
        store: RunStore | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.prompts = prompts or PromptRepository()
        self.ingestor = ingestor or ManuscriptIngestor(settings)
        self.store = store or RunStore(settings.output_dir)
        self.progress = progress or (lambda _message: None)

    def start(self, source: str) -> RunManifest:
        self.progress("Normalizing the complete manuscript")
        manuscript = self.ingestor.ingest(source)
        self.provider.preflight(manuscript)

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        prompt_versions = self.prompts.versions()
        output_schema_hashes = structured_output_schema_hashes()
        provider_runtime = self.provider.runtime_metadata
        fingerprint = self._fingerprint(
            manuscript, prompt_versions, output_schema_hashes, provider_runtime
        )
        now = datetime.now(UTC)
        stages = {
            "initial-editor": StageRecord(),
            **{
                f"referee-{index}": StageRecord()
                for index in range(1, self.settings.referee_count + 1)
            },
            "final-editor": StageRecord(),
            "render": StageRecord(),
        }
        manifest = RunManifest(
            run_id=run_id,
            input_fingerprint=fingerprint,
            manuscript_sha256=manuscript.metadata.sha256,
            manuscript_source=manuscript.metadata.source,
            created_at=now,
            updated_at=now,
            configuration=self.settings.manifest_dict(),
            prompt_versions=prompt_versions,
            output_schema_hashes=output_schema_hashes,
            provider_runtime=provider_runtime,
            workflow_state=WorkflowState.MANUSCRIPT_RECEIVED,
            stages=stages,
        )
        self.store.create(run_id)
        self.store.write_manuscript(run_id, manuscript)
        manifest.workflow_state = WorkflowState.MANUSCRIPT_NORMALIZED
        self._save(manifest, "manuscript_normalized")
        self.progress(f"Run created: {run_id}")
        return self._execute(manifest, manuscript)

    def resume(self, run_id: str) -> RunManifest:
        manifest = self.store.load_manifest(run_id)
        self._validate_resume_configuration(manifest)
        if manifest.prompt_versions != self.prompts.versions():
            raise WorkflowError(
                "run prompt versions are not available in this checkout; refusing prompt drift"
            )
        if manifest.output_schema_hashes != structured_output_schema_hashes():
            raise WorkflowError(
                "run structured-output schema provenance differs from this checkout; "
                "start a new run"
            )
        if manifest.provider_runtime != self.provider.runtime_metadata:
            raise WorkflowError(
                "run provider runtime provenance differs from this environment; start a new run"
            )
        if manifest.workflow_state == WorkflowState.COMPLETED:
            return manifest
        if manifest.workflow_state == WorkflowState.CANCELLED:
            raise WorkflowError("cancelled runs cannot be resumed")
        manifest.cancellation_requested = False
        manuscript = self.store.load_manuscript(run_id)
        self.provider.preflight(manuscript)
        self.progress(f"Resuming run: {run_id}")
        return self._execute(manifest, manuscript)

    def cancel(self, run_id: str) -> RunManifest:
        manifest = self.store.load_manifest(run_id)
        if manifest.workflow_state == WorkflowState.COMPLETED:
            raise WorkflowError("completed runs cannot be cancelled")
        manifest.cancellation_requested = True
        manifest.workflow_state = WorkflowState.CANCELLED
        for record in manifest.stages.values():
            if record.status in {StageStatus.PENDING, StageStatus.IN_PROGRESS}:
                record.status = StageStatus.CANCELLED
        self._save(manifest, "run_cancelled")
        return manifest

    def _execute(self, manifest: RunManifest, manuscript: ManuscriptPackage) -> RunManifest:
        if self._cancel_if_requested(manifest):
            return manifest

        panel = self._recover_or_run_initial_editor(manifest, manuscript)
        if panel is None:
            return manifest
        if self._cancel_if_requested(manifest):
            return manifest

        reports = self._recover_or_run_referees(manifest, manuscript, panel)
        if reports is None:
            return manifest
        if self._cancel_if_requested(manifest):
            return manifest

        decision = self._recover_or_run_final_editor(manifest, manuscript, panel, reports)
        if decision is None:
            return manifest

        if self._cancel_if_requested(manifest):
            return manifest
        self._render_completion_artifacts(manifest, panel, reports, decision)
        return manifest

    def _recover_or_run_initial_editor(
        self, manifest: RunManifest, manuscript: ManuscriptPackage
    ) -> EditorPanelDesign | None:
        stage = "initial-editor"
        recovered = self._recover_json_artifact(
            manifest, stage, "initial-editor.json", EditorPanelDesign
        )
        if recovered is not None:
            return recovered

        self.progress("Stage 1/3: designing the targeted referee panel")
        record = manifest.stages[stage]
        record.status = StageStatus.IN_PROGRESS
        record.started_at = datetime.now(UTC)
        record.error = None
        record.error_details = {}
        self._save(manifest, "stage_started", stage=stage)
        request = StageRequest(
            stage="initial_editor",
            agent_id="initial-editor",
            model=self.settings.model_for_stage("initial_editor"),
            prompt=self.prompts.render_initial_editor(self.settings.referee_count),
            manuscript=manuscript,
            response_model=EditorPanelDesign,
            metadata={"referee_count": self.settings.referee_count},
        )
        try:
            outcome = self._call_with_bounds(request)
            panel = EditorPanelDesign.model_validate(outcome.result.parsed)
            if panel.requested_referee_count != self.settings.referee_count:
                raise StageExecutionError(
                    "initial editor returned the wrong referee count",
                    attempts=outcome.attempts,
                    invalid_raw_responses=outcome.invalid_raw_responses,
                )
            self._write_stage_artifacts(
                manifest,
                stage,
                "initial-editor",
                panel,
                render_initial_editor(panel),
                outcome,
            )
            manifest.workflow_state = WorkflowState.INITIAL_EDITOR_COMPLETED
            self._save(manifest, "stage_completed", stage=stage)
            return panel
        except StageExecutionError as exc:
            self._fail_stage(manifest, stage, exc)
            return None

    def _recover_or_run_referees(
        self,
        manifest: RunManifest,
        manuscript: ManuscriptPackage,
        panel: EditorPanelDesign,
    ) -> list[RefereeReport] | None:
        reports: dict[str, RefereeReport] = {}
        for profile in panel.referee_profiles:
            recovered = self._recover_json_artifact(
                manifest,
                profile.referee_id,
                f"{profile.referee_id}.json",
                RefereeReport,
            )
            if recovered is not None:
                if recovered.referee_id != profile.referee_id:
                    raise WorkflowError("stored referee report identifier is inconsistent")
                reports[profile.referee_id] = recovered

        pending_profiles = [
            profile for profile in panel.referee_profiles if profile.referee_id not in reports
        ]
        if pending_profiles:
            manifest.workflow_state = WorkflowState.REFEREE_JOBS_CREATED
            self._save(manifest, "referee_jobs_created", count=len(pending_profiles))
            self.progress(
                f"Stage 2/3: running {len(pending_profiles)} independent referee execution(s)"
            )
            for profile in pending_profiles:
                record = manifest.stages[profile.referee_id]
                record.status = StageStatus.IN_PROGRESS
                record.started_at = datetime.now(UTC)
                record.error = None
                record.error_details = {}
            manifest.workflow_state = WorkflowState.REFEREES_IN_PROGRESS
            self._save(manifest, "referee_reports_started", count=len(pending_profiles))

            futures: dict[Future[CallOutcome], str] = {}
            with ThreadPoolExecutor(
                max_workers=min(self.settings.max_concurrency, len(pending_profiles)),
                thread_name_prefix="ets4-referee",
            ) as executor:
                for profile in pending_profiles:
                    request = StageRequest(
                        stage="referee",
                        agent_id=profile.referee_id,
                        model=self.settings.model_for_stage("referee"),
                        prompt=self.prompts.render_referee(profile),
                        manuscript=manuscript,
                        response_model=RefereeReport,
                        supplemental_context={},
                        metadata={"functional_slot": profile.functional_slot},
                    )
                    futures[executor.submit(self._call_with_bounds, request)] = profile.referee_id

                for future in as_completed(futures):
                    referee_id = futures[future]
                    try:
                        outcome = future.result()
                        report = RefereeReport.model_validate(outcome.result.parsed)
                        if report.referee_id != referee_id:
                            raise StageExecutionError(
                                "referee report identifier does not match its isolated job",
                                attempts=outcome.attempts,
                                invalid_raw_responses=outcome.invalid_raw_responses,
                            )
                        self._write_stage_artifacts(
                            manifest,
                            referee_id,
                            referee_id,
                            report,
                            render_referee(report),
                            outcome,
                        )
                        reports[referee_id] = report
                        self._save(manifest, "stage_completed", stage=referee_id)
                    except StageExecutionError as exc:
                        self._record_stage_failure(manifest, referee_id, exc)
                        self._save(manifest, "stage_failed", stage=referee_id)

        expected_ids = {profile.referee_id for profile in panel.referee_profiles}
        if set(reports) != expected_ids:
            manifest.workflow_state = WorkflowState.AWAITING_RETRY
            manifest.failed_stages = sorted(
                stage
                for stage in expected_ids
                if manifest.stages[stage].status == StageStatus.FAILED
            )
            self._save(
                manifest,
                "referee_fan_in_blocked",
                missing=sorted(expected_ids - set(reports)),
            )
            self.progress("Final editor blocked: one or more referee reports require retry")
            return None

        manifest.workflow_state = WorkflowState.REFEREES_COMPLETED
        self._save(manifest, "referee_reports_completed", count=len(reports))
        return [reports[f"referee-{index}"] for index in range(1, len(reports) + 1)]

    def _recover_or_run_final_editor(
        self,
        manifest: RunManifest,
        manuscript: ManuscriptPackage,
        panel: EditorPanelDesign,
        reports: list[RefereeReport],
    ) -> FinalEditorDecision | None:
        stage = "final-editor"
        recovered = self._recover_json_artifact(
            manifest, stage, "final-editor.json", FinalEditorDecision
        )
        if recovered is not None:
            self._validate_final_coverage(panel, recovered)
            return recovered

        if len(reports) != self.settings.referee_count:
            raise WorkflowError("final editor cannot run without every configured report")
        self.progress("Stage 3/3: synthesizing the fixed panel and editorial recommendation")
        record = manifest.stages[stage]
        record.status = StageStatus.IN_PROGRESS
        record.started_at = datetime.now(UTC)
        record.error = None
        record.error_details = {}
        self._save(manifest, "stage_started", stage=stage)
        request = StageRequest(
            stage="final_editor",
            agent_id="final-editor",
            model=self.settings.model_for_stage("final_editor"),
            prompt=self.prompts.render_final_editor(self.settings.referee_count),
            manuscript=manuscript,
            response_model=FinalEditorDecision,
            supplemental_context={
                "initial_editor": panel.model_dump(mode="json"),
                "referee_reports": [report.model_dump(mode="json") for report in reports],
            },
            metadata={"referee_count": self.settings.referee_count},
        )
        try:
            outcome = self._call_with_bounds(request)
            decision = FinalEditorDecision.model_validate(outcome.result.parsed)
            self._validate_final_coverage(panel, decision)
            self._write_stage_artifacts(
                manifest,
                stage,
                "final-editor",
                decision,
                render_final_editor(decision),
                outcome,
            )
            manifest.workflow_state = WorkflowState.FINAL_EDITOR_COMPLETED
            self._save(manifest, "stage_completed", stage=stage)
            return decision
        except (StageExecutionError, WorkflowError) as exc:
            wrapped = (
                exc
                if isinstance(exc, StageExecutionError)
                else StageExecutionError(str(exc), attempts=max(1, record.attempts))
            )
            self._fail_stage(manifest, stage, wrapped)
            return None

    def _render_completion_artifacts(
        self,
        manifest: RunManifest,
        panel: EditorPanelDesign,
        reports: list[RefereeReport],
        decision: FinalEditorDecision,
    ) -> None:
        stage = "render"
        record = manifest.stages[stage]
        if record.status != StageStatus.COMPLETED:
            record.status = StageStatus.IN_PROGRESS
            record.started_at = datetime.now(UTC)
            checksums = {
                "initial-editor.md": self.store.write_text(
                    manifest.run_id, "initial-editor.md", render_initial_editor(panel)
                ),
                "final-editor.md": self.store.write_text(
                    manifest.run_id, "final-editor.md", render_final_editor(decision)
                ),
            }
            for report in reports:
                filename = f"{report.referee_id}.md"
                checksums[filename] = self.store.write_text(
                    manifest.run_id, filename, render_referee(report)
                )
            usage = {
                stage_name: stage_record.usage
                for stage_name, stage_record in manifest.stages.items()
                if stage_record.usage
            }
            checksums["usage.json"] = self.store.write_json(manifest.run_id, "usage.json", usage)
            record.artifact_checksums = checksums
            record.status = StageStatus.COMPLETED
            record.completed_at = datetime.now(UTC)
            manifest.workflow_state = WorkflowState.OUTPUTS_RENDERED
            self._mark_completed(manifest, stage)
            self._save(manifest, "outputs_rendered")

        manifest.workflow_state = WorkflowState.COMPLETED
        manifest.failed_stages = []
        self._save(manifest, "run_completed")
        self.progress(f"Review completed: {self.store.run_dir(manifest.run_id)}")

    def _call_with_bounds(self, request: StageRequest[Any]) -> CallOutcome:
        attempts = 0
        retry_count = 0
        repair_count = 0
        invalid_raw: list[Any] = []
        prompt = request.prompt
        while True:
            attempts += 1
            current_request = StageRequest(
                stage=request.stage,
                agent_id=request.agent_id,
                model=request.model,
                prompt=prompt,
                manuscript=request.manuscript,
                response_model=request.response_model,
                supplemental_context=request.supplemental_context,
                metadata=request.metadata,
            )
            try:
                result = self.provider.generate(current_request)
                return CallOutcome(
                    result=result,
                    attempts=attempts,
                    invalid_raw_responses=tuple(invalid_raw),
                )
            except ProviderError as exc:
                if exc.raw_response is not None:
                    invalid_raw.append(exc.raw_response)
                if (
                    exc.raw_response is not None
                    and repair_count < self.settings.max_repair_attempts
                ):
                    repair_count += 1
                    prompt = (
                        request.prompt
                        + "\n\nOUTPUT REPAIR\nThe previous response did not validate. "
                        "Return the complete "
                        "structured output again and conform exactly to the supplied schema."
                    )
                    continue
                if exc.retryable and retry_count < self.settings.max_provider_retries:
                    retry_count += 1
                    continue
                raise StageExecutionError(
                    redact_secrets(str(exc)),
                    attempts=attempts,
                    invalid_raw_responses=tuple(invalid_raw),
                    error_details=exc.details,
                ) from exc
            except Exception as exc:
                raise StageExecutionError(
                    f"unexpected provider failure: {exc.__class__.__name__}",
                    attempts=attempts,
                    invalid_raw_responses=tuple(invalid_raw),
                ) from exc

    def _recover_json_artifact(
        self,
        manifest: RunManifest,
        stage: str,
        filename: str,
        model: type[ArtifactModel],
    ) -> ArtifactModel | None:
        record = manifest.stages[stage]
        if record.status == StageStatus.COMPLETED or self.store.artifact_exists(
            manifest.run_id, filename
        ):
            try:
                recovered = model.model_validate(self.store.read_json(manifest.run_id, filename))
            except (ValueError, RuntimeError) as exc:
                raise WorkflowError(f"completed stage artifact is invalid: {filename}") from exc
            record.status = StageStatus.COMPLETED
            record.error = None
            record.error_details = {}
            self._mark_completed(manifest, stage)
            return recovered
        return None

    def _write_stage_artifacts(
        self,
        manifest: RunManifest,
        stage: str,
        basename: str,
        parsed: BaseModel,
        markdown: str,
        outcome: CallOutcome,
    ) -> None:
        checksums = {
            f"{basename}.json": self.store.write_json(
                manifest.run_id, f"{basename}.json", parsed.model_dump(mode="json")
            ),
            f"{basename}.md": self.store.write_text(manifest.run_id, f"{basename}.md", markdown),
        }
        self._write_raw_responses(manifest.run_id, stage, outcome)
        record = manifest.stages[stage]
        record.status = StageStatus.COMPLETED
        record.attempts += outcome.attempts
        record.completed_at = datetime.now(UTC)
        record.error = None
        record.error_details = {}
        record.artifact_checksums = checksums
        record.provider_response_id = outcome.result.response_id
        record.usage = outcome.result.usage
        self._mark_completed(manifest, stage)
        if stage in manifest.failed_stages:
            manifest.failed_stages.remove(stage)

    def _write_raw_responses(self, run_id: str, stage: str, outcome: CallOutcome) -> None:
        if not self.settings.retain_raw_responses:
            return
        for index, raw in enumerate(outcome.invalid_raw_responses, start=1):
            self.store.write_json(run_id, f"logs/raw/{stage}-invalid-{index}.json", raw)
        self.store.write_json(
            run_id,
            f"logs/raw/{stage}-response.json",
            outcome.result.raw_response,
        )

    def _record_stage_failure(
        self, manifest: RunManifest, stage: str, exc: StageExecutionError
    ) -> None:
        record = manifest.stages[stage]
        record.status = StageStatus.FAILED
        record.attempts += exc.attempts
        record.completed_at = datetime.now(UTC)
        record.error = redact_secrets(str(exc))
        record.error_details = {
            key: redact_secrets(value) if isinstance(value, str) else value
            for key, value in exc.error_details.items()
        }
        if stage not in manifest.failed_stages:
            manifest.failed_stages.append(stage)
        if self.settings.retain_raw_responses:
            for index, raw in enumerate(exc.invalid_raw_responses, start=1):
                self.store.write_json(
                    manifest.run_id,
                    f"logs/raw/{stage}-failed-{record.attempts}-{index}.json",
                    raw,
                )

    def _fail_stage(self, manifest: RunManifest, stage: str, exc: StageExecutionError) -> None:
        self._record_stage_failure(manifest, stage, exc)
        manifest.workflow_state = WorkflowState.AWAITING_RETRY
        self._save(
            manifest,
            "stage_failed",
            stage=stage,
            error=record_error(manifest, stage),
            error_details=manifest.stages[stage].error_details,
        )
        self.progress(f"Stage requires retry: {stage}")

    @staticmethod
    def _validate_final_coverage(panel: EditorPanelDesign, decision: FinalEditorDecision) -> None:
        planned_rows = {row.requirement_id: row for row in panel.planned_coverage_matrix}
        actual_rows = {row.requirement_id: row for row in decision.coverage_appendix.rows}
        if set(planned_rows) != set(actual_rows):
            raise WorkflowError("final coverage appendix must include every planned dimension")
        expected_referees = {profile.referee_id for profile in panel.referee_profiles}
        for requirement_id, planned in planned_rows.items():
            realized = actual_rows[requirement_id]
            planned_coverage = planned.coverage_by_referee()
            realized_coverage = realized.coverage_by_referee()
            if set(realized_coverage) != expected_referees:
                raise WorkflowError("final coverage row must include every referee")
            for referee_id, planned_level in planned_coverage.items():
                if realized_coverage[referee_id].planned != planned_level:
                    raise WorkflowError("final editor changed an original planned coverage cell")

    def _fingerprint(
        self,
        manuscript: ManuscriptPackage,
        prompt_versions: dict[str, str],
        output_schema_hashes: dict[str, str],
        provider_runtime: dict[str, str],
    ) -> str:
        settings = self.settings.manifest_dict()
        settings.pop("output_dir", None)
        settings.pop("retain_raw_responses", None)
        payload = {
            "manuscript_sha256": manuscript.metadata.sha256,
            "prompt_versions": prompt_versions,
            "output_schema_hashes": output_schema_hashes,
            "provider_runtime": provider_runtime,
            "settings": settings,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(serialized).hexdigest()

    def _validate_resume_configuration(self, manifest: RunManifest) -> None:
        stored = ReviewSettings.model_validate(manifest.configuration).manifest_dict()
        current = self.settings.manifest_dict()
        for key in {"output_dir", "retain_raw_responses"}:
            stored.pop(key, None)
            current.pop(key, None)
        if stored != current:
            raise WorkflowError("resume configuration differs from the recorded run manifest")

    def _cancel_if_requested(self, manifest: RunManifest) -> bool:
        if self.store.exists(manifest.run_id):
            persisted = self.store.load_manifest(manifest.run_id)
            manifest.cancellation_requested = (
                manifest.cancellation_requested or persisted.cancellation_requested
            )
        if not manifest.cancellation_requested:
            return False
        manifest.workflow_state = WorkflowState.CANCELLED
        for record in manifest.stages.values():
            if record.status in {StageStatus.PENDING, StageStatus.IN_PROGRESS}:
                record.status = StageStatus.CANCELLED
        self._save(manifest, "run_cancelled")
        return True

    def _mark_completed(self, manifest: RunManifest, stage: str) -> None:
        if stage not in manifest.completed_stages:
            manifest.completed_stages.append(stage)

    def _save(self, manifest: RunManifest, event: str, **fields: Any) -> None:
        if self.store.exists(manifest.run_id):
            persisted = self.store.load_manifest(manifest.run_id)
            if persisted.cancellation_requested:
                manifest.cancellation_requested = True
                manifest.workflow_state = WorkflowState.CANCELLED
        manifest.updated_at = datetime.now(UTC)
        self.store.write_manifest(manifest)
        self.store.append_event(
            manifest.run_id, event, workflow_state=manifest.workflow_state.value, **fields
        )


def record_error(manifest: RunManifest, stage: str) -> str | None:
    return manifest.stages[stage].error
