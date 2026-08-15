"""Deterministic no-cost provider for tests and local workflow inspection."""

from __future__ import annotations

import threading
from typing import Any

from ets4.domain.schemas import (
    Centrality,
    Correctability,
    CoverageAppendix,
    CoverageLevel,
    EditorPanelDesign,
    FinalEditorDecision,
    FinalRecommendation,
    FindingStatus,
    HarmonizedAnswer,
    HarmonizedAnswers,
    ManuscriptRequirement,
    PanelAssessment,
    PanelFinding,
    PlannedActualCell,
    PlannedCoverageCell,
    PlannedCoverageRow,
    RealizedCoverageRow,
    RefereeComment,
    RefereeProfile,
    RefereeReasoning,
    RefereeRecommendation,
    RefereeReport,
    ReviewerConfidence,
    ReviewRequirementDiscovery,
    Severity,
    SynthesizedIssue,
    ValidityAssessment,
)
from ets4.ingestion.models import ManuscriptPackage
from ets4.providers.base import (
    Provider,
    ProviderCapabilities,
    ProviderError,
    ProviderResult,
    StageRequest,
    StructuredModel,
)


class MockProvider(Provider):
    """Produce schema-valid deterministic artifacts without pretending to judge quality."""

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="mock",
            structured_outputs=True,
            native_pdf_input=True,
            paginated_text_fallback=True,
            supports_reasoning_effort=False,
            supports_store_control=False,
        )

    @property
    def calls(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._calls)

    def preflight(self, manuscript: ManuscriptPackage) -> None:
        if not manuscript.pages:
            raise ProviderError("mock provider requires a complete normalized manuscript")

    def generate(self, request: StageRequest[StructuredModel]) -> ProviderResult[StructuredModel]:
        with self._lock:
            self._calls.append(
                {
                    "stage": request.stage,
                    "agent_id": request.agent_id,
                    "prompt": request.prompt,
                    "supplemental_context": request.supplemental_context,
                    "metadata": request.metadata,
                    "manuscript_sha256": request.manuscript.metadata.sha256,
                }
            )

        if request.response_model is ReviewRequirementDiscovery:
            output: Any = self._requirements(request)
        elif request.response_model is EditorPanelDesign:
            output = self._panel(request)
        elif request.response_model is RefereeReport:
            output = self._referee(request)
        elif request.response_model is FinalEditorDecision:
            output = self._final(request)
        else:
            raise ProviderError(f"mock provider does not support {request.response_model.__name__}")

        parsed = request.response_model.model_validate(output.model_dump(mode="json"))
        raw = parsed.model_dump(mode="json")
        return ProviderResult(
            parsed=parsed,
            raw_response=raw,
            response_id=f"mock-{request.agent_id}",
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )

    @staticmethod
    def _requirements_for_count(count: int) -> list[ManuscriptRequirement]:
        base_names = [
            "Central forecasting claim",
            "Methodological design",
            "Forecast evaluation and inference",
            "Data and empirical application",
            "Interpretation, limitations, and reproducibility",
        ]
        requirement_names = [
            *base_names,
            *[
                f"Additional manuscript-specific review dimension {index}"
                for index in range(len(base_names) + 1, count + 1)
            ],
        ][:count]
        return [
            ManuscriptRequirement(
                requirement_id=f"requirement-{index}",
                component_or_claim=name,
                review_scope=(
                    f"Evaluate the manuscript's {name.lower()} as a broad review dimension."
                ),
                central_claim=index == 1,
            )
            for index, name in enumerate(requirement_names, start=1)
        ]

    @classmethod
    def _requirements(cls, request: StageRequest[Any]) -> ReviewRequirementDiscovery:
        configured_count = request.metadata.get("review_requirement_count")
        count = int(configured_count) if configured_count is not None else 5
        return ReviewRequirementDiscovery(
            manuscript_review_map=cls._requirements_for_count(count)
        )

    @classmethod
    def _panel(cls, request: StageRequest[Any]) -> EditorPanelDesign:
        count = int(request.metadata["referee_count"])
        supplied_requirements = request.supplemental_context.get("review_requirements")
        requirements = (
            [ManuscriptRequirement.model_validate(item) for item in supplied_requirements]
            if supplied_requirements is not None
            else cls._requirements_for_count(5)
        )
        profiles = [
            RefereeProfile(
                referee_id=f"referee-{index}",
                functional_slot=f"Functional specialist {index}",
                research_orientation="Economic forecasting researcher",
                primary_expertise=f"Forecasting review dimension {index}",
                specialist_topics=[
                    "forecast design",
                    "empirical validation",
                    "economic interpretation",
                ],
                primary_audit_mandate=(
                    f"Provide sustained examination of assigned broad manuscript dimension {index}."
                ),
                unique_contribution=f"Adds functional perspective {index} to the fixed panel.",
                non_authority_areas=["Unassigned specialist dimensions"],
            )
            for index in range(1, count + 1)
        ]
        matrix = []
        for index, requirement in enumerate(requirements):
            primary = (index % count) + 1
            coverage = [
                PlannedCoverageCell(
                    referee_id=f"referee-{referee_index}",
                    level=(
                        CoverageLevel.PRIMARY
                        if referee_index == primary
                        else CoverageLevel.SECONDARY
                        if count > 1 and referee_index == (primary % count) + 1
                        else CoverageLevel.BLANK
                    ),
                )
                for referee_index in range(1, count + 1)
            ]
            matrix.append(
                PlannedCoverageRow(
                    requirement_id=requirement.requirement_id,
                    manuscript_dimension=requirement.component_or_claim,
                    coverage=coverage,
                )
            )
        return EditorPanelDesign(
            manuscript_review_map=requirements,
            requested_referee_count=count,
            referee_profiles=profiles,
            planned_coverage_matrix=matrix,
            panel_assessment=PanelAssessment(
                remaining_expertise_gaps=[],
                unavoidable_redundancy=["Central validity receives limited shared attention."],
                generic_replacement_cost=(
                    "A generic replacement would remove one explicitly assigned "
                    "functional perspective."
                ),
            ),
        )

    @staticmethod
    def _referee(request: StageRequest[Any]) -> RefereeReport:
        return RefereeReport(
            referee_id=request.agent_id,
            recommendation=RefereeRecommendation.MAJOR_REVISION,
            harmonized_answers=HarmonizedAnswers(
                forecasting_contribution=HarmonizedAnswer.MOSTLY,
                literature_positioning=HarmonizedAnswer.MOSTLY,
                scientific_soundness=HarmonizedAnswer.PARTLY,
                forecasting_evaluation=HarmonizedAnswer.PARTLY,
                conclusions_supported=HarmonizedAnswer.PARTLY,
                limitations_discussed=HarmonizedAnswer.PARTLY,
                presentation_and_replication=HarmonizedAnswer.MOSTLY,
            ),
            neutral_summary_and_contribution=(
                "Synthetic mock report confirming that the complete manuscript "
                "reached this isolated call."
            ),
            overall_assessment=(
                "The mock provider makes no substantive quality claim and exists "
                "for workflow validation."
            ),
            major_comments=[
                RefereeComment(
                    comment=(
                        "A live specialist must evaluate the assigned manuscript dimension. "
                        "For example, this deterministic fixture can confirm that the PDF "
                        "reached the referee call, but it cannot judge whether a forecast "
                        "comparison supports the paper's claims."
                    ),
                    manuscript_locations=["Complete manuscript"],
                )
            ],
            minor_comments=[],
            confidential_comments_to_editor="Use this output only to test ETS4 orchestration.",
            reviewer_confidence=ReviewerConfidence.LOW,
            ethical_or_integrity_concerns=False,
        )

    @staticmethod
    def _final(request: StageRequest[Any]) -> FinalEditorDecision:
        panel = EditorPanelDesign.model_validate(request.supplemental_context["initial_editor"])
        reports = [
            RefereeReport.model_validate(item)
            for item in request.supplemental_context["referee_reports"]
        ]
        first_report = reports[0]
        coverage_rows = [
            RealizedCoverageRow(
                requirement_id=row.requirement_id,
                manuscript_dimension=row.manuscript_dimension,
                referee_coverage=[
                    PlannedActualCell(
                        referee_id=cell.referee_id,
                        planned=cell.level,
                        actual=cell.level,
                    )
                    for cell in row.coverage
                ],
                panel_assessment="Mock output records realized coverage as matching the plan.",
            )
            for row in panel.planned_coverage_matrix
        ]
        return FinalEditorDecision(
            neutral_manuscript_summary=(
                "Synthetic final-editor output demonstrating complete fixed-panel "
                "artifact assembly."
            ),
            overall_assessment=(
                "This deterministic result validates orchestration and is not a substantive review."
            ),
            issue_based_synthesis=[
                SynthesizedIssue(
                    comment=(
                        "The entire manuscript still needs substantive specialist review because "
                        "the mock output checks only the workflow. A deterministic fixture cannot "
                        "establish manuscript quality, so a real editorial use would require a run "
                        "with a capable configured provider. The workflow is functioning, but this "
                        "synthetic comment is not an editorial judgment."
                    ),
                    panel_status=FindingStatus.SPECIALIST,
                    referee_reasoning=[
                        RefereeReasoning(
                            referee_id=first_report.referee_id,
                            reasoning=first_report.major_comments[0].comment,
                        )
                    ],
                    validity=ValidityAssessment.SUPPORTED,
                    centrality=Centrality.HIGH,
                    severity=Severity.MAJOR,
                    correctability=Correctability.YES,
                )
            ],
            consensus_findings=[],
            specialist_contributions=[
                PanelFinding(
                    finding="The mock provider confirms isolated artifact flow only.",
                    referee_ids=[first_report.referee_id],
                    editorial_assessment=(
                        "This is an orchestration diagnostic, not a manuscript judgment."
                    ),
                )
            ],
            disagreements_and_adjudications=[],
            final_recommendation=FinalRecommendation.MAJOR_REVISION,
            recommendation_justification=(
                "The mock recommendation is deterministic test data and must not be "
                "used editorially."
            ),
            coverage_appendix=CoverageAppendix(
                rows=coverage_rows,
                dimensions_covered_as_planned=[row.manuscript_dimension for row in coverage_rows],
                under_covered_dimensions=[],
                substantial_unplanned_contributions=[],
                excessive_overlap=[],
                functional_differentiation_assessment=(
                    "The mock run preserved the planned functional assignments for "
                    "workflow testing."
                ),
            ),
        )
