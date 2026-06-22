from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationMismatch:
    paper_id: str
    title: str | None
    field: str
    human_label: Any
    system_output: Any
    failure_type: str
    reason: str


def evaluation_mismatches(items: tuple[dict[str, Any], ...]) -> tuple[EvaluationMismatch, ...]:
    mismatches: list[EvaluationMismatch] = []
    for item in items:
        mismatches.extend(_paper_mismatches(item))
    return tuple(mismatches)


def mismatch_dicts(items: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    return [
        {
            "paper_id": mismatch.paper_id,
            "title": mismatch.title,
            "field": mismatch.field,
            "human_label": mismatch.human_label,
            "system_output": mismatch.system_output,
            "failure_type": mismatch.failure_type,
            "reason": mismatch.reason,
        }
        for mismatch in evaluation_mismatches(items)
    ]


def error_summary_dict(items: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    mismatches = evaluation_mismatches(items)
    missing_kinds: dict[str, int] = {}
    for item in items:
        for kind in item["evidence"].get("missing_required_kinds") or ():
            key = str(kind)
            missing_kinds[key] = missing_kinds.get(key, 0) + 1

    return {
        "mismatch_count": len(mismatches),
        "paper_count": len({mismatch.paper_id for mismatch in mismatches}),
        "by_field": _count_by(mismatches, "field"),
        "by_failure_type": _count_by(mismatches, "failure_type"),
        "missing_required_evidence_kinds": dict(sorted(missing_kinds.items())),
        "recommendations": _recommendations(mismatches, missing_kinds),
    }


def _paper_mismatches(item: dict[str, Any]) -> list[EvaluationMismatch]:
    paper_id = str(item["paper_id"])
    title = item.get("title")
    title = str(title) if title is not None else None
    label = item["label"]
    triage = item["triage"]
    selection = item["selection"]
    evidence = item["evidence"]
    editorial = item["editorial"]
    mismatches: list[EvaluationMismatch] = []

    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="triage_decision",
        human_label=label.get("expected_triage_decision"),
        system_output=triage.get("decision"),
        failure_type=_triage_failure_type(
            label.get("expected_triage_decision"),
            triage.get("decision"),
        ),
        reason="Triage decision differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="category",
        human_label=label.get("expected_category"),
        system_output=triage.get("category_hint"),
        failure_type=_category_failure_type(
            label.get("expected_category"),
            triage.get("category_hint"),
        ),
        reason="Triage category differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="editorial_decision",
        human_label=label.get("expected_editorial_decision"),
        system_output=editorial.get("decision"),
        failure_type=_editorial_failure_type(
            label.get("expected_editorial_decision"),
            editorial.get("decision"),
        ),
        reason="Handling-editor decision differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="deep_dive_selection",
        human_label=label.get("expected_deep_dive"),
        system_output=selection.get("selected_deep_dive"),
        failure_type=_selection_failure_type(
            expected=label.get("expected_deep_dive"),
            actual=selection.get("selected_deep_dive"),
            positive_type="deep_dive_underselection",
            negative_type="deep_dive_overselection",
        ),
        reason="Deep-dive selection differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="short_mention_selection",
        human_label=label.get("expected_short_mention"),
        system_output=selection.get("selected_short_mention"),
        failure_type=_selection_failure_type(
            expected=label.get("expected_short_mention"),
            actual=selection.get("selected_short_mention"),
            positive_type="short_mention_underselection",
            negative_type="short_mention_overselection",
        ),
        reason="Short-mention selection differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="publication_track",
        human_label=label.get("publication_track"),
        system_output=editorial.get("publication_track"),
        failure_type=_publication_track_failure_type(
            label.get("publication_track"),
            editorial.get("publication_track"),
        ),
        reason="Derived publication track differs from accepted label.",
    )

    missing_required_kinds = evidence.get("missing_required_kinds") or []
    if missing_required_kinds:
        mismatches.append(
            EvaluationMismatch(
                paper_id=paper_id,
                title=title,
                field="required_evidence",
                human_label=label.get("required_evidence_kinds") or [],
                system_output=evidence.get("evidence_kinds") or [],
                failure_type="evidence_kind_gap",
                reason="Missing required evidence kinds: "
                f"{', '.join(str(kind) for kind in missing_required_kinds)}.",
            )
        )

    return mismatches


def _append_value_mismatch(
    mismatches: list[EvaluationMismatch],
    *,
    paper_id: str,
    title: str | None,
    field: str,
    human_label: Any,
    system_output: Any,
    failure_type: str,
    reason: str,
) -> None:
    if human_label is None:
        return
    if human_label == system_output:
        return
    mismatches.append(
        EvaluationMismatch(
            paper_id=paper_id,
            title=title,
            field=field,
            human_label=human_label,
            system_output=system_output,
            failure_type=failure_type,
            reason=reason,
        )
    )


def _triage_failure_type(human_label: Any, system_output: Any) -> str:
    if system_output is None:
        return "missing_triage_output"
    if human_label in {"reject", "borderline"} and system_output == "assign_reviewers":
        return "triage_overpromotion"
    if human_label == "assign_reviewers" and system_output in {"reject", "borderline"}:
        return "triage_underpromotion"
    return "triage_decision_mismatch"


def _category_failure_type(human_label: Any, system_output: Any) -> str:
    if system_output is None:
        return "missing_triage_output"
    if human_label in {"not_relevant", "paper_of_interest"} and system_output == "directly_relevant":
        return "scope_overclassification"
    if human_label == "directly_relevant" and system_output in {"paper_of_interest", "not_relevant"}:
        return "scope_underclassification"
    return "category_mismatch"


def _editorial_failure_type(human_label: Any, system_output: Any) -> str:
    if system_output is None:
        return "missing_review_output"
    if system_output == "full_deep_dive" and human_label != "full_deep_dive":
        return "editorial_overpromotion"
    if human_label == "full_deep_dive" and system_output != "full_deep_dive":
        return "editorial_underpromotion"
    return "editorial_decision_mismatch"


def _selection_failure_type(
    *,
    expected: Any,
    actual: Any,
    positive_type: str,
    negative_type: str,
) -> str:
    if expected is True and actual is False:
        return positive_type
    if expected is False and actual is True:
        return negative_type
    return "selection_mismatch"


def _publication_track_failure_type(human_label: Any, system_output: Any) -> str:
    if system_output is None:
        return "missing_review_output"
    if system_output == "deep_dive" and human_label != "deep_dive":
        return "publication_track_overpromotion"
    if human_label == "reject" and system_output != "reject":
        return "publication_track_false_positive"
    if human_label == "deep_dive" and system_output != "deep_dive":
        return "publication_track_underpromotion"
    return "publication_track_mismatch"


def _count_by(mismatches: tuple[EvaluationMismatch, ...], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for mismatch in mismatches:
        key = str(getattr(mismatch, field_name))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _recommendations(
    mismatches: tuple[EvaluationMismatch, ...],
    missing_kinds: dict[str, int],
) -> list[str]:
    counts = _count_by(mismatches, "failure_type")
    recommendations: list[str] = []
    if counts.get("triage_overpromotion") or counts.get("scope_overclassification"):
        recommendations.append(
            "Tighten desk-screening scope for practitioner/applied economic forecasting."
        )
    if counts.get("editorial_overpromotion") or counts.get("publication_track_overpromotion"):
        recommendations.append(
            "Make handling-editor and publication-track gates more conservative before provider work."
        )
    if counts.get("deep_dive_overselection"):
        recommendations.append(
            "Review deep-dive ranking penalties for applied value, evidence quality, and track fit."
        )
    if counts.get("missing_review_output"):
        recommendations.append(
            "Inspect skipped or failed reviews before interpreting editorial accuracy."
        )
    if counts.get("evidence_kind_gap"):
        top_kinds = ", ".join(kind for kind, _ in sorted(missing_kinds.items()))
        recommendations.append(f"Improve evidence extraction or kind mapping for: {top_kinds}.")
    if not recommendations and mismatches:
        recommendations.append("Inspect residual mismatches manually before changing providers.")
    return recommendations
