"""Deterministic Markdown views over validated domain records."""

from __future__ import annotations

from collections.abc import Sequence

from ets4.domain.schemas import (
    EditorPanelDesign,
    FinalEditorDecision,
    RefereeReport,
    ReviewRequirementSelection,
    RunWarning,
)


def _table_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _single_paragraph(value: str) -> str:
    return " ".join(value.split())


def _warning_lines(warnings: Sequence[RunWarning]) -> list[str]:
    lines: list[str] = []
    for warning in warnings:
        lines.extend([f"> **Warning:** {warning.message}", ""])
    return lines


def render_review_requirements(selection: ReviewRequirementSelection) -> str:
    lines = [
        "# Initial editor review requirements",
        "",
        (
            "> ETS4 is experimental decision support. It complements, and does not replace, "
            "human peer review."
        ),
        "",
    ]
    if selection.discarded_requirement_ids:
        lines.extend(
            [
                (
                    "> **Warning:** The initial editor identified "
                    f"{selection.identified_count} review requirements. ETS4 retained the "
                    f"first {len(selection.retained_requirements)} and excluded the rest from "
                    "panel design and later stages."
                ),
                "",
            ]
        )
    lines.extend(["## Retained review requirements", ""])
    for requirement in selection.retained_requirements:
        lines.extend(
            [
                f"### {requirement.requirement_id}: {requirement.component_or_claim}",
                "",
                requirement.review_scope,
                "",
            ]
        )
    return "\n".join(lines)


def render_initial_editor(
    panel: EditorPanelDesign, warnings: Sequence[RunWarning] = ()
) -> str:
    lines = [
        "# Initial editor and targeted panel design",
        "",
        (
            "> ETS4 is experimental decision support. It complements, and does not replace, "
            "human peer review."
        ),
        "",
    ]
    lines.extend(_warning_lines(warnings))
    lines.extend(["## Manuscript review map", ""])
    for requirement in panel.manuscript_review_map:
        lines.extend(
            [
                f"### {requirement.requirement_id}: {requirement.component_or_claim}",
                "",
                requirement.review_scope,
                "",
            ]
        )
    lines.extend(["## Referee panel", ""])
    for profile in panel.referee_profiles:
        lines.extend(
            [
                f"### {profile.referee_id}: {profile.functional_slot}",
                "",
                f"- Orientation: {profile.research_orientation}",
                f"- Primary expertise: {profile.primary_expertise}",
                f"- Specialist topics: {', '.join(profile.specialist_topics)}",
                f"- Audit mandate: {profile.primary_audit_mandate}",
                f"- Unique contribution: {profile.unique_contribution}",
                f"- Not principal authority for: {', '.join(profile.non_authority_areas)}",
                "",
            ]
        )
    headers = ["Dimension", *[profile.referee_id for profile in panel.referee_profiles]]
    lines.extend(
        [
            "## Planned coverage matrix",
            "",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
    )
    for row in panel.planned_coverage_matrix:
        coverage = row.coverage_by_referee()
        values = [row.manuscript_dimension, *[coverage[item].value for item in headers[1:]]]
        lines.append("| " + " | ".join(_table_cell(item) for item in values) + " |")
    lines.extend(
        [
            "",
            "## Panel assessment",
            "",
            "- Remaining expertise gaps: "
            + ("; ".join(panel.panel_assessment.remaining_expertise_gaps) or "None identified"),
            "- Unavoidable redundancy: "
            + ("; ".join(panel.panel_assessment.unavoidable_redundancy) or "None identified"),
            f"- Generic replacement cost: {panel.panel_assessment.generic_replacement_cost}",
            "",
        ]
    )
    return "\n".join(lines)


def render_referee(report: RefereeReport) -> str:
    answers = report.harmonized_answers
    question_rows = [
        ("Clear and relevant forecasting contribution", answers.forecasting_contribution.value),
        ("Appropriately positioned in literature", answers.literature_positioning.value),
        ("Methodology, data, and design scientifically sound", answers.scientific_soundness.value),
        ("Forecasting evaluation credible and fair", answers.forecasting_evaluation.value),
        ("Results support conclusions", answers.conclusions_supported.value),
        ("Limitations adequately discussed", answers.limitations_discussed.value),
        (
            "Presentation and replication documentation sufficient",
            answers.presentation_and_replication.value,
        ),
    ]
    lines = [
        f"# Independent referee report: {report.referee_id}",
        "",
        (
            "> ETS4 is experimental decision support. This artificial report does not "
            "replace human peer review."
        ),
        "",
        f"**Recommendation:** {report.recommendation.value}",
        "",
        "## Brief neutral summary and contribution",
        "",
        report.neutral_summary_and_contribution,
        "",
        "## Overall assessment",
        "",
        report.overall_assessment,
        "",
        "## Major comments",
        "",
    ]
    for index, comment in enumerate(report.major_comments, start=1):
        lines.extend([f"{index}. {_single_paragraph(comment.comment)}", ""])
    lines.extend(["## Minor comments", ""])
    lines.extend([f"- {item}" for item in report.minor_comments] or ["- None"])
    lines.extend(
        [
            "",
            "## Harmonized questions",
            "",
            "| Question | Answer |",
            "| --- | --- |",
            *[f"| {_table_cell(question)} | {answer} |" for question, answer in question_rows],
            "",
            "## Confidential comments to the editor",
            "",
            report.confidential_comments_to_editor,
            "",
            "- Ethical or integrity concerns: "
            + ("Yes" if report.ethical_or_integrity_concerns else "No"),
            "",
        ]
    )
    return "\n".join(lines)


def render_final_editor(
    decision: FinalEditorDecision, warnings: Sequence[RunWarning] = ()
) -> str:
    lines = [
        "# Final editor synthesis and recommendation",
        "",
        (
            "> ETS4 is experimental decision support. The recommendation requires "
            "independent human judgment."
        ),
        "",
    ]
    lines.extend(_warning_lines(warnings))
    lines.extend(
        [
            f"**Final recommendation:** {decision.final_recommendation.value}",
            "",
            "## Summary",
            "",
            decision.neutral_manuscript_summary,
            "",
            "## Overall assessment",
            "",
            decision.overall_assessment,
            "",
            "## Referee comments",
            "",
        ]
    )
    for index, issue in enumerate(decision.issue_based_synthesis, start=1):
        lines.extend([f"{index}. {_single_paragraph(issue.comment)}", ""])
    lines.extend(
        [
            "## Recommendation",
            "",
            decision.recommendation_justification,
            "",
            "## Appendix: planned versus realized referee coverage",
            "",
        ]
    )
    referee_ids = [cell.referee_id for cell in decision.coverage_appendix.rows[0].referee_coverage]
    headers = ["Manuscript dimension", *referee_ids, "Panel assessment"]
    lines.extend(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
    )
    for row in decision.coverage_appendix.rows:
        coverage = row.coverage_by_referee()
        cells = [
            row.manuscript_dimension,
            *[coverage[referee_id].notation for referee_id in referee_ids],
            row.panel_assessment,
        ]
        lines.append("| " + " | ".join(_table_cell(cell) for cell in cells) + " |")
    lines.extend(
        [
            "",
            "- Covered as planned: "
            + ("; ".join(decision.coverage_appendix.dimensions_covered_as_planned) or "None"),
            "- Under-covered: "
            + ("; ".join(decision.coverage_appendix.under_covered_dimensions) or "None"),
            "- Substantial unplanned contributions: "
            + ("; ".join(decision.coverage_appendix.substantial_unplanned_contributions) or "None"),
            "- Excessive overlap: "
            + ("; ".join(decision.coverage_appendix.excessive_overlap) or "None"),
            "- Functional differentiation: "
            + decision.coverage_appendix.functional_differentiation_assessment,
            "",
        ]
    )
    return "\n".join(lines)
