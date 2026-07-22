"""Validated structured outputs and durable workflow records."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CoverageLevel(str, Enum):
    PRIMARY = "P"
    SECONDARY = "S"
    BLANK = "Blank"


class RefereeRecommendation(str, Enum):
    ACCEPT = "Accept"
    MINOR_REVISION = "Minor revision"
    MAJOR_REVISION = "Major revision"
    REJECT = "Reject"


class FinalRecommendation(str, Enum):
    ACCEPT = "Accept"
    MINOR_REVISION = "Minor revision"
    MAJOR_REVISION = "Major revision"
    REJECT_AND_RESUBMIT = "Reject and resubmit"
    REJECT = "Reject"


class HarmonizedAnswer(str, Enum):
    YES = "Yes"
    MOSTLY = "Mostly"
    PARTLY = "Partly"
    NO = "No"
    NOT_APPLICABLE = "Not applicable"


class ReviewerConfidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ManuscriptRequirement(StrictModel):
    requirement_id: Annotated[str, Field(pattern=r"^requirement-[1-8]$")]
    component_or_claim: Annotated[str, Field(min_length=3)]
    review_scope: Annotated[str, Field(min_length=10)]
    central_claim: bool


class RefereeProfile(StrictModel):
    referee_id: Annotated[str, Field(pattern=r"^referee-[1-9][0-9]*$")]
    functional_slot: Annotated[str, Field(min_length=3)]
    research_orientation: Annotated[str, Field(min_length=3)]
    primary_expertise: Annotated[str, Field(min_length=3)]
    specialist_topics: Annotated[list[str], Field(min_length=3, max_length=5)]
    primary_audit_mandate: Annotated[str, Field(min_length=10)]
    unique_contribution: Annotated[str, Field(min_length=10)]
    non_authority_areas: Annotated[list[str], Field(min_length=1)]


class PlannedCoverageCell(StrictModel):
    referee_id: Annotated[str, Field(pattern=r"^referee-[1-9][0-9]*$")]
    level: CoverageLevel


class PlannedCoverageRow(StrictModel):
    requirement_id: str
    manuscript_dimension: Annotated[str, Field(min_length=3)]
    coverage: Annotated[list[PlannedCoverageCell], Field(min_length=1, max_length=12)]

    @model_validator(mode="after")
    def validate_unique_referees(self) -> PlannedCoverageRow:
        referee_ids = [cell.referee_id for cell in self.coverage]
        if len(referee_ids) != len(set(referee_ids)):
            raise ValueError("coverage cells must contain unique referee identifiers")
        return self

    def coverage_by_referee(self) -> dict[str, CoverageLevel]:
        return {cell.referee_id: cell.level for cell in self.coverage}


class PanelAssessment(StrictModel):
    remaining_expertise_gaps: list[str]
    unavoidable_redundancy: list[str]
    generic_replacement_cost: Annotated[str, Field(min_length=10)]


class EditorPanelDesign(StrictModel):
    manuscript_review_map: Annotated[list[ManuscriptRequirement], Field(min_length=5, max_length=8)]
    requested_referee_count: Annotated[int, Field(ge=1, le=12)]
    referee_profiles: Annotated[list[RefereeProfile], Field(min_length=1, max_length=12)]
    planned_coverage_matrix: Annotated[list[PlannedCoverageRow], Field(min_length=5, max_length=8)]
    panel_assessment: PanelAssessment

    @model_validator(mode="after")
    def validate_panel_design(self) -> EditorPanelDesign:
        if len(self.referee_profiles) != self.requested_referee_count:
            raise ValueError("referee profile count must equal requested_referee_count")

        expected_referees = {
            f"referee-{index}" for index in range(1, self.requested_referee_count + 1)
        }
        actual_referees = {profile.referee_id for profile in self.referee_profiles}
        if actual_referees != expected_referees:
            raise ValueError("referee identifiers must be contiguous from referee-1")

        requirements = {item.requirement_id: item for item in self.manuscript_review_map}
        if len(requirements) != len(self.manuscript_review_map):
            raise ValueError("manuscript requirement identifiers must be unique")
        matrix_requirements = {row.requirement_id for row in self.planned_coverage_matrix}
        if matrix_requirements != set(requirements):
            raise ValueError("coverage matrix rows must exactly match the manuscript review map")

        for row in self.planned_coverage_matrix:
            coverage = row.coverage_by_referee()
            if set(coverage) != expected_referees:
                raise ValueError("every coverage row must contain every requested referee")
            primary_count = sum(level == CoverageLevel.PRIMARY for level in coverage.values())
            if primary_count == 0:
                raise ValueError("every manuscript requirement must have at least one P")
            if primary_count > 2 and not requirements[row.requirement_id].central_claim:
                raise ValueError(
                    "non-central requirements may not have more than two P assignments"
                )
        return self


class HarmonizedAnswers(StrictModel):
    forecasting_contribution: HarmonizedAnswer
    literature_positioning: HarmonizedAnswer
    scientific_soundness: HarmonizedAnswer
    forecasting_evaluation: HarmonizedAnswer
    conclusions_supported: HarmonizedAnswer
    limitations_discussed: HarmonizedAnswer
    presentation_and_replication: HarmonizedAnswer


class RefereeComment(StrictModel):
    title: Annotated[str, Field(min_length=3)]
    concern: Annotated[str, Field(min_length=10)]
    affected_claim_or_component: Annotated[str, Field(min_length=3)]
    reasoning: Annotated[str, Field(min_length=10)]
    manuscript_locations: list[str]


class RefereeReport(StrictModel):
    referee_id: Annotated[str, Field(pattern=r"^referee-[1-9][0-9]*$")]
    recommendation: RefereeRecommendation
    harmonized_answers: HarmonizedAnswers
    neutral_summary_and_contribution: Annotated[str, Field(min_length=20)]
    overall_assessment: Annotated[str, Field(min_length=20)]
    major_comments: Annotated[list[RefereeComment], Field(min_length=1, max_length=8)]
    minor_comments: Annotated[list[str], Field(max_length=8)]
    confidential_comments_to_editor: Annotated[str, Field(min_length=5)]
    reviewer_confidence: ReviewerConfidence
    ethical_or_integrity_concerns: bool


class FindingStatus(str, Enum):
    CONSENSUS = "consensus"
    SPECIALIST = "specialist"
    DISAGREEMENT = "disagreement"


class ValidityAssessment(str, Enum):
    SUPPORTED = "supported"
    PARTLY_SUPPORTED = "partly_supported"
    NOT_SUPPORTED = "not_supported"
    UNRESOLVED = "unresolved"


class Centrality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class Correctability(str, Enum):
    YES = "yes"
    NO = "no"
    UNCERTAIN = "uncertain"


class RefereeReasoning(StrictModel):
    referee_id: str
    reasoning: Annotated[str, Field(min_length=5)]


class SynthesizedIssue(StrictModel):
    issue: Annotated[str, Field(min_length=5)]
    claim_or_component_affected: Annotated[str, Field(min_length=3)]
    what_is_missing: Annotated[str, Field(min_length=10)]
    why_it_matters: Annotated[str, Field(min_length=10)]
    what_needs_to_change: Annotated[str, Field(min_length=5)]
    panel_status: FindingStatus
    referee_reasoning: Annotated[list[RefereeReasoning], Field(min_length=1)]
    validity: ValidityAssessment
    centrality: Centrality
    severity: Severity
    correctability: Correctability
    adjudication: Annotated[str, Field(min_length=5)]


class PanelFinding(StrictModel):
    finding: Annotated[str, Field(min_length=5)]
    referee_ids: Annotated[list[str], Field(min_length=1)]
    editorial_assessment: Annotated[str, Field(min_length=5)]


class Disagreement(StrictModel):
    issue: Annotated[str, Field(min_length=5)]
    positions: Annotated[list[RefereeReasoning], Field(min_length=2)]
    adjudication: Annotated[str, Field(min_length=5)]
    unresolved: bool


class PlannedActualCell(StrictModel):
    referee_id: Annotated[str, Field(pattern=r"^referee-[1-9][0-9]*$")]
    planned: CoverageLevel
    actual: CoverageLevel

    @property
    def notation(self) -> str:
        return f"{self.planned.value}→{self.actual.value}"


class RealizedCoverageRow(StrictModel):
    requirement_id: str
    manuscript_dimension: Annotated[str, Field(min_length=3)]
    referee_coverage: Annotated[list[PlannedActualCell], Field(min_length=1, max_length=12)]
    panel_assessment: Annotated[str, Field(min_length=3)]

    @model_validator(mode="after")
    def validate_unique_referees(self) -> RealizedCoverageRow:
        referee_ids = [cell.referee_id for cell in self.referee_coverage]
        if len(referee_ids) != len(set(referee_ids)):
            raise ValueError("realized coverage cells must contain unique referee identifiers")
        return self

    def coverage_by_referee(self) -> dict[str, PlannedActualCell]:
        return {cell.referee_id: cell for cell in self.referee_coverage}


class CoverageAppendix(StrictModel):
    rows: Annotated[list[RealizedCoverageRow], Field(min_length=5, max_length=8)]
    dimensions_covered_as_planned: list[str]
    under_covered_dimensions: list[str]
    substantial_unplanned_contributions: list[str]
    excessive_overlap: list[str]
    functional_differentiation_assessment: Annotated[str, Field(min_length=10)]


class FinalEditorDecision(StrictModel):
    neutral_manuscript_summary: Annotated[str, Field(min_length=20)]
    overall_assessment: Annotated[str, Field(min_length=20)]
    issue_based_synthesis: Annotated[list[SynthesizedIssue], Field(min_length=1, max_length=12)]
    consensus_findings: list[PanelFinding]
    specialist_contributions: list[PanelFinding]
    disagreements_and_adjudications: list[Disagreement]
    principal_strengths: Annotated[list[str], Field(min_length=1)]
    decision_determining_issues: Annotated[list[str], Field(min_length=1)]
    essential_revisions: list[str]
    desirable_nonessential_improvements: list[str]
    final_recommendation: FinalRecommendation
    recommendation_justification: Annotated[str, Field(min_length=20)]
    coverage_appendix: CoverageAppendix


def structured_output_schema_hashes() -> dict[str, str]:
    """Hash provider-facing schemas so resume cannot silently cross schema revisions."""

    models: dict[str, type[BaseModel]] = {
        "initial_editor": EditorPanelDesign,
        "referee": RefereeReport,
        "final_editor": FinalEditorDecision,
    }
    return {
        stage: hashlib.sha256(
            json.dumps(model.model_json_schema(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        for stage, model in models.items()
    }


class WorkflowState(str, Enum):
    MANUSCRIPT_RECEIVED = "manuscript_received"
    MANUSCRIPT_NORMALIZED = "manuscript_normalized"
    INITIAL_EDITOR_COMPLETED = "initial_editor_completed"
    REFEREE_JOBS_CREATED = "referee_jobs_created"
    REFEREES_IN_PROGRESS = "referee_reports_in_progress"
    REFEREES_COMPLETED = "referee_reports_completed"
    FINAL_EDITOR_COMPLETED = "final_editor_completed"
    OUTPUTS_RENDERED = "outputs_rendered"
    COMPLETED = "completed"
    AWAITING_RETRY = "awaiting_retry"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageRecord(StrictModel):
    status: StageStatus = StageStatus.PENDING
    attempts: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    error_details: dict[str, str | int | None] = Field(default_factory=dict)
    artifact_checksums: dict[str, str] = Field(default_factory=dict)
    provider_response_id: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class RunManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    input_fingerprint: str
    manuscript_sha256: str
    manuscript_source: str
    created_at: datetime
    updated_at: datetime
    configuration: dict[str, Any]
    prompt_versions: dict[str, str]
    output_schema_hashes: dict[str, str] = Field(default_factory=dict)
    provider_runtime: dict[str, str] = Field(default_factory=dict)
    workflow_state: WorkflowState
    stages: dict[str, StageRecord]
    completed_stages: list[str] = Field(default_factory=list)
    failed_stages: list[str] = Field(default_factory=list)
    cancellation_requested: bool = False
