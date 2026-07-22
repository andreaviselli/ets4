"""Deterministic Markdown views over validated domain records."""

from __future__ import annotations

from ets4.domain.schemas import EditorPanelDesign, FinalEditorDecision, RefereeReport

PANEL_STATUS_LABELS = {
    "consensus": "Consensus finding",
    "specialist": "Specialist contribution",
    "disagreement": "Disagreement",
}
VALIDITY_LABELS = {
    "supported": "Supported",
    "partly_supported": "Partly supported",
    "not_supported": "Not supported",
    "unresolved": "Unresolved",
}
CORRECTABILITY_LABELS = {
    "yes": "Fixable",
    "no": "Not fixable",
    "uncertain": "Uncertain fixability",
}


def _table_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_initial_editor(panel: EditorPanelDesign) -> str:
    lines = [
        "# Initial editor and targeted panel design",
        "",
        (
            "> ETS4 is experimental decision support. It complements, and does not replace, "
            "human peer review."
        ),
        "",
        "## Manuscript review map",
        "",
    ]
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
        lines.extend(
            [
                f"### {index}. {comment.title}",
                "",
                f"Concern: {comment.concern}",
                "",
                f"Affected claim or component: {comment.affected_claim_or_component}",
                "",
                comment.reasoning,
                "",
                "Locations: " + (", ".join(comment.manuscript_locations) or "Not specified"),
                "",
            ]
        )
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
            f"- Reviewer confidence: {report.reviewer_confidence.value}",
            "- Ethical or integrity concerns: "
            + ("Yes" if report.ethical_or_integrity_concerns else "No"),
            "",
        ]
    )
    return "\n".join(lines)


def render_final_editor(decision: FinalEditorDecision) -> str:
    lines = [
        "# Final editor synthesis and recommendation",
        "",
        (
            "> ETS4 is experimental decision support. The recommendation requires "
            "independent human judgment."
        ),
        "",
        f"**Final recommendation:** {decision.final_recommendation.value}",
        "",
        "## Neutral manuscript summary",
        "",
        decision.neutral_manuscript_summary,
        "",
        "## Overall assessment",
        "",
        decision.overall_assessment,
        "",
        "## Issue-based synthesis",
        "",
    ]
    for index, issue in enumerate(decision.issue_based_synthesis, start=1):
        metadata = " · ".join(
            [
                PANEL_STATUS_LABELS[issue.panel_status.value],
                VALIDITY_LABELS[issue.validity.value],
                issue.severity.value.title(),
                f"{issue.centrality.value.title()} centrality",
                CORRECTABILITY_LABELS[issue.correctability.value],
            ]
        )
        lines.extend(
            [
                f"### {index}. {issue.issue}",
                "",
                f"**Where it applies:** {issue.claim_or_component_affected}",
                "",
                f"**What is missing:** {issue.what_is_missing}",
                "",
                f"**Why it matters:** {issue.why_it_matters}",
                "",
                f"**What needs to change:** {issue.what_needs_to_change}",
                "",
                f"**Editor's view:** {issue.adjudication}",
                "",
                f"*{metadata}*",
                "",
            ]
        )

    def add_list(title: str, values: list[str]) -> None:
        lines.extend([f"## {title}", ""])
        lines.extend([f"- {value}" for value in values] or ["- None"])
        lines.append("")

    add_list("Principal strengths", decision.principal_strengths)
    add_list("Decision-determining issues", decision.decision_determining_issues)
    add_list("Essential revisions", decision.essential_revisions)
    add_list(
        "Desirable but non-essential improvements",
        decision.desirable_nonessential_improvements,
    )
    lines.extend(
        [
            "## Recommendation justification",
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
