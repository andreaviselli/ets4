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
            "reason": mismatch.reason,
        }
        for mismatch in evaluation_mismatches(items)
    ]


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
        reason="Triage decision differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="category",
        human_label=label.get("expected_category"),
        system_output=triage.get("category_hint"),
        reason="Triage category differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="editorial_decision",
        human_label=label.get("expected_editorial_decision"),
        system_output=editorial.get("decision"),
        reason="Handling-editor decision differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="deep_dive_selection",
        human_label=label.get("expected_deep_dive"),
        system_output=selection.get("selected_deep_dive"),
        reason="Deep-dive selection differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="short_mention_selection",
        human_label=label.get("expected_short_mention"),
        system_output=selection.get("selected_short_mention"),
        reason="Short-mention selection differs from accepted label.",
    )
    _append_value_mismatch(
        mismatches,
        paper_id=paper_id,
        title=title,
        field="publication_track",
        human_label=label.get("publication_track"),
        system_output=editorial.get("publication_track"),
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
            reason=reason,
        )
    )
