from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_RELEVANCE_LABELS = {
    "directly_relevant",
    "paper_of_interest",
    "not_relevant",
    "borderline",
}
VALID_TRIAGE_DECISIONS = {"assign_reviewers", "borderline", "reject"}
VALID_EDITORIAL_DECISIONS = {
    "full_deep_dive",
    "short_mention",
    "watchlist",
    "needs_human_adjudication",
    "reject",
}


@dataclass(frozen=True)
class PaperLabel:
    paper_id: str
    relevance_label: str
    expected_category: str | None = None
    expected_triage_decision: str | None = None
    expected_editorial_decision: str | None = None
    expected_deep_dive: bool | None = None
    expected_short_mention: bool | None = None
    required_evidence_kinds: tuple[str, ...] = ()
    hard_negative: bool = False
    high_value: bool = False

    @property
    def is_relevant(self) -> bool:
        return self.relevance_label in {"directly_relevant", "paper_of_interest", "borderline"}


@dataclass(frozen=True)
class Benchmark:
    version: str
    labels: tuple[PaperLabel, ...]


def load_benchmark(path: str | Path) -> Benchmark:
    labels_path = Path(path)
    with labels_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    version = str(raw.get("version") or labels_path.stem)
    labels = tuple(_load_label(item) for item in raw.get("papers", ()))
    if not labels:
        raise ValueError("Benchmark must contain at least one paper label")
    _validate_unique_paper_ids(labels)
    return Benchmark(version=version, labels=labels)


def _load_label(raw: dict[str, Any]) -> PaperLabel:
    paper_id = str(raw["paper_id"])
    label_status = _optional_str(raw.get("label_status"))
    if label_status and label_status != "accepted":
        raise ValueError(
            f"Paper label for {paper_id} has label_status={label_status!r}; "
            "set label_status to 'accepted' after human review before evaluation"
        )
    relevance_label = str(raw["relevance_label"])
    if relevance_label not in VALID_RELEVANCE_LABELS:
        raise ValueError(f"Invalid relevance label for {paper_id}: {relevance_label}")
    expected_category = _optional_str(raw.get("expected_category"))
    if expected_category and expected_category not in VALID_RELEVANCE_LABELS - {"borderline"}:
        raise ValueError(f"Invalid expected category for {paper_id}: {expected_category}")
    expected_triage_decision = _optional_str(raw.get("expected_triage_decision"))
    if expected_triage_decision and expected_triage_decision not in VALID_TRIAGE_DECISIONS:
        raise ValueError(
            f"Invalid expected triage decision for {paper_id}: {expected_triage_decision}"
        )
    expected_editorial_decision = _optional_str(raw.get("expected_editorial_decision"))
    if expected_editorial_decision and expected_editorial_decision not in VALID_EDITORIAL_DECISIONS:
        raise ValueError(
            f"Invalid expected editorial decision for {paper_id}: {expected_editorial_decision}"
        )
    return PaperLabel(
        paper_id=paper_id,
        relevance_label=relevance_label,
        expected_category=expected_category,
        expected_triage_decision=expected_triage_decision,
        expected_editorial_decision=expected_editorial_decision,
        expected_deep_dive=_optional_bool(raw.get("expected_deep_dive")),
        expected_short_mention=_optional_bool(raw.get("expected_short_mention")),
        required_evidence_kinds=tuple(str(kind) for kind in raw.get("required_evidence_kinds", ())),
        hard_negative=bool(raw.get("hard_negative", False)),
        high_value=bool(raw.get("high_value", False)),
    )


def _validate_unique_paper_ids(labels: tuple[PaperLabel, ...]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for label in labels:
        if label.paper_id in seen:
            duplicates.add(label.paper_id)
        seen.add(label.paper_id)
    if duplicates:
        raise ValueError(f"Duplicate paper labels: {', '.join(sorted(duplicates))}")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)
