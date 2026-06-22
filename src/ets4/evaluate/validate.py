from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .labels import (
    VALID_APPLICATION_TYPES,
    VALID_AUDIENCE_FITS,
    VALID_ECONOMIC_RELEVANCE,
    VALID_EDITORIAL_DECISIONS,
    VALID_FORECASTING_CONTRIBUTIONS,
    VALID_PUBLICATION_TRACKS,
    VALID_RELEVANCE_LABELS,
    VALID_SOCIAL_HOOK_POTENTIAL,
    VALID_TRIAGE_DECISIONS,
)

MINIMUM_LABEL_FIELDS = (
    "relevance_label",
    "audience_fit",
    "application_type",
    "economic_relevance",
    "forecasting_contribution",
    "publication_track",
    "expected_triage_decision",
    "expected_deep_dive",
    "expected_short_mention",
    "required_evidence_kinds",
    "hard_negative",
    "high_value",
)
RECOMMENDED_LABEL_FIELDS = (
    "expected_category",
    "expected_editorial_decision",
    "social_hook_potential",
)


@dataclass(frozen=True)
class PaperLabelStatus:
    paper_id: str
    title: str | None
    label_status: str | None
    missing_fields: tuple[str, ...]
    invalid_fields: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    @property
    def is_accepted(self) -> bool:
        return self.label_status in {None, "accepted"}

    @property
    def is_incomplete(self) -> bool:
        return bool(self.missing_fields or self.invalid_fields)


@dataclass(frozen=True)
class BenchmarkValidationResult:
    path: Path
    version: str
    paper_count: int
    accepted_count: int
    not_accepted_count: int
    incomplete_count: int
    error_count: int
    warning_count: int
    paper_statuses: tuple[PaperLabelStatus, ...]
    top_level_errors: tuple[str, ...] = ()
    duplicate_paper_ids: tuple[str, ...] = ()

    @property
    def ready_for_evaluation(self) -> bool:
        return (
            self.paper_count > 0
            and self.accepted_count == self.paper_count
            and self.incomplete_count == 0
            and self.error_count == 0
        )


@dataclass(frozen=True)
class BenchmarkSubsetResult:
    path: Path
    paper_count: int
    paper_ids: tuple[str, ...]


def validate_benchmark_file(path: str | Path) -> BenchmarkValidationResult:
    labels_path = Path(path)
    raw = _load_json(labels_path)
    top_errors: list[str] = []
    if not isinstance(raw, dict):
        return BenchmarkValidationResult(
            path=labels_path,
            version=labels_path.stem,
            paper_count=0,
            accepted_count=0,
            not_accepted_count=0,
            incomplete_count=0,
            error_count=1,
            warning_count=0,
            paper_statuses=(),
            top_level_errors=("Benchmark JSON must be an object",),
        )

    version = str(raw.get("version") or labels_path.stem)
    papers = raw.get("papers")
    if not isinstance(papers, list):
        return BenchmarkValidationResult(
            path=labels_path,
            version=version,
            paper_count=0,
            accepted_count=0,
            not_accepted_count=0,
            incomplete_count=0,
            error_count=1,
            warning_count=0,
            paper_statuses=(),
            top_level_errors=("Benchmark JSON must contain a papers list",),
        )
    if not papers:
        top_errors.append("Benchmark must contain at least one paper label")

    statuses: list[PaperLabelStatus] = []
    seen: set[str] = set()
    duplicates: set[str] = set()
    structural_errors = 0
    for index, paper in enumerate(papers, start=1):
        if not isinstance(paper, dict):
            structural_errors += 1
            statuses.append(
                PaperLabelStatus(
                    paper_id=f"<paper-{index}>",
                    title=None,
                    label_status=None,
                    missing_fields=("paper_id",),
                    invalid_fields=("paper",),
                    warnings=(),
                )
            )
            continue
        status = _paper_label_status(paper, index=index)
        if status.paper_id in seen:
            duplicates.add(status.paper_id)
        seen.add(status.paper_id)
        statuses.append(status)

    duplicate_tuple = tuple(sorted(duplicates))
    error_count = (
        len(top_errors)
        + structural_errors
        + len(duplicate_tuple)
        + sum(len(status.invalid_fields) for status in statuses)
    )
    accepted_count = sum(1 for status in statuses if status.is_accepted)
    incomplete_count = sum(1 for status in statuses if status.is_incomplete)
    warning_count = sum(len(status.warnings) for status in statuses)
    return BenchmarkValidationResult(
        path=labels_path,
        version=version,
        paper_count=len(papers),
        accepted_count=accepted_count,
        not_accepted_count=len(papers) - accepted_count,
        incomplete_count=incomplete_count,
        error_count=error_count,
        warning_count=warning_count,
        paper_statuses=tuple(statuses),
        top_level_errors=tuple(top_errors),
        duplicate_paper_ids=duplicate_tuple,
    )


def create_benchmark_subset(
    input_path: str | Path,
    output_path: str | Path,
    *,
    size: int = 6,
    paper_ids: tuple[str, ...] = (),
) -> BenchmarkSubsetResult:
    if size <= 0 and not paper_ids:
        raise ValueError("Subset size must be positive unless paper ids are provided")

    source_path = Path(input_path)
    payload = _load_json(source_path)
    if not isinstance(payload, dict):
        raise ValueError("Benchmark JSON must be an object")
    papers = payload.get("papers")
    if not isinstance(papers, list):
        raise ValueError("Benchmark JSON must contain a papers list")
    if not papers:
        raise ValueError("Benchmark must contain at least one paper label")

    selected = _select_subset_papers(papers, size=size, paper_ids=paper_ids)
    if not selected:
        raise ValueError("No matching papers found for subset")

    subset_payload = copy.deepcopy(payload)
    source_version = str(payload.get("version") or source_path.stem)
    subset_payload["version"] = f"{source_version}-subset"
    subset_payload["labeling_status"] = "draft_subset"
    subset_payload["source_benchmark_version"] = source_version
    subset_payload["papers"] = selected
    instructions = subset_payload.setdefault("instructions", {})
    if isinstance(instructions, dict):
        instructions["subset"] = (
            "This file copies existing paper records for human editing. It does not "
            "fill labels or mark labels accepted."
        )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(subset_payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return BenchmarkSubsetResult(
        path=path,
        paper_count=len(selected),
        paper_ids=tuple(str(paper.get("paper_id", "")) for paper in selected),
    )


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _paper_label_status(paper: dict[str, Any], *, index: int) -> PaperLabelStatus:
    paper_id_value = paper.get("paper_id")
    paper_id = str(paper_id_value) if paper_id_value else f"<paper-{index}>"
    missing = _missing_fields(paper)
    invalid = _invalid_fields(paper)
    warnings = _label_warnings(paper)
    if not paper_id_value:
        missing = (*missing, "paper_id")
    return PaperLabelStatus(
        paper_id=paper_id,
        title=_optional_string(paper.get("title")),
        label_status=_optional_string(paper.get("label_status")),
        missing_fields=tuple(sorted(set(missing))),
        invalid_fields=tuple(sorted(set(invalid))),
        warnings=tuple(sorted(set(warnings))),
    )


def _missing_fields(paper: dict[str, Any]) -> tuple[str, ...]:
    missing: list[str] = []
    for field in (*MINIMUM_LABEL_FIELDS, *_recommended_fields(paper)):
        if field not in paper or paper[field] is None or paper[field] == "":
            missing.append(field)
    return tuple(missing)


def _recommended_fields(paper: dict[str, Any]) -> tuple[str, ...]:
    editorial_context = _context_value(paper, "editorial")
    if isinstance(editorial_context, dict) and editorial_context.get("decision") is not None:
        return RECOMMENDED_LABEL_FIELDS
    return ("expected_category",)


def _invalid_fields(paper: dict[str, Any]) -> tuple[str, ...]:
    invalid: list[str] = []
    relevance = paper.get("relevance_label")
    if relevance is not None and relevance not in VALID_RELEVANCE_LABELS:
        invalid.append("relevance_label")
    expected_category = paper.get("expected_category")
    if expected_category is not None and expected_category not in (
        VALID_RELEVANCE_LABELS - {"borderline"}
    ):
        invalid.append("expected_category")
    _append_invalid_choice(
        invalid,
        paper=paper,
        field="audience_fit",
        valid_values=VALID_AUDIENCE_FITS,
    )
    _append_invalid_choice(
        invalid,
        paper=paper,
        field="application_type",
        valid_values=VALID_APPLICATION_TYPES,
    )
    _append_invalid_choice(
        invalid,
        paper=paper,
        field="economic_relevance",
        valid_values=VALID_ECONOMIC_RELEVANCE,
    )
    _append_invalid_choice(
        invalid,
        paper=paper,
        field="forecasting_contribution",
        valid_values=VALID_FORECASTING_CONTRIBUTIONS,
    )
    _append_invalid_choice(
        invalid,
        paper=paper,
        field="publication_track",
        valid_values=VALID_PUBLICATION_TRACKS,
    )
    _append_invalid_choice(
        invalid,
        paper=paper,
        field="social_hook_potential",
        valid_values=VALID_SOCIAL_HOOK_POTENTIAL,
    )
    triage_decision = paper.get("expected_triage_decision")
    if triage_decision is not None and triage_decision not in VALID_TRIAGE_DECISIONS:
        invalid.append("expected_triage_decision")
    editorial_decision = paper.get("expected_editorial_decision")
    if editorial_decision is not None and editorial_decision not in VALID_EDITORIAL_DECISIONS:
        invalid.append("expected_editorial_decision")
    for field in ("expected_deep_dive", "expected_short_mention", "hard_negative", "high_value"):
        if field in paper and paper[field] is not None and not isinstance(paper[field], bool):
            invalid.append(field)
    evidence_kinds = paper.get("required_evidence_kinds")
    if evidence_kinds is not None and not _string_list(evidence_kinds):
        invalid.append("required_evidence_kinds")
    return tuple(invalid)


def _label_warnings(paper: dict[str, Any]) -> tuple[str, ...]:
    warnings: list[str] = []
    expected_triage = paper.get("expected_triage_decision")
    expected_category = paper.get("expected_category")
    expected_editorial = paper.get("expected_editorial_decision")
    expected_deep_dive = paper.get("expected_deep_dive")
    expected_short_mention = paper.get("expected_short_mention")
    publication_track = paper.get("publication_track")

    if expected_triage == "reject" and expected_category in {"directly_relevant", "paper_of_interest"}:
        warnings.append("reject_triage_with_positive_category")

    if expected_editorial == "full_deep_dive":
        if expected_deep_dive is False:
            warnings.append("full_deep_dive_without_deep_dive_selection")
        if expected_short_mention is True:
            warnings.append("full_deep_dive_with_short_mention_selection")
        if publication_track not in {None, "deep_dive"}:
            warnings.append("full_deep_dive_with_non_deep_dive_track")
    elif expected_editorial == "short_mention":
        if expected_deep_dive is True:
            warnings.append("short_mention_with_deep_dive_selection")
        if expected_short_mention is False:
            warnings.append("short_mention_without_short_mention_selection")
        if publication_track not in {None, "applied_note"}:
            warnings.append("short_mention_with_non_applied_note_track")
    elif expected_editorial in {"watchlist", "needs_human_adjudication", "reject"}:
        if expected_deep_dive is True:
            warnings.append(f"{expected_editorial}_with_deep_dive_selection")
        if expected_short_mention is True:
            warnings.append(f"{expected_editorial}_with_short_mention_selection")

    if publication_track == "deep_dive" and expected_deep_dive is False:
        warnings.append("deep_dive_track_without_deep_dive_selection")
    if publication_track == "applied_note" and expected_short_mention is False:
        warnings.append("applied_note_track_without_short_mention_selection")
    if publication_track in {"methods_watch", "reject"}:
        if expected_deep_dive is True:
            warnings.append(f"{publication_track}_track_with_deep_dive_selection")
        if expected_short_mention is True:
            warnings.append(f"{publication_track}_track_with_short_mention_selection")

    return tuple(warnings)


def _append_invalid_choice(
    invalid: list[str],
    *,
    paper: dict[str, Any],
    field: str,
    valid_values: set[str],
) -> None:
    value = paper.get(field)
    if value is not None and value not in valid_values:
        invalid.append(field)


def _context_value(paper: dict[str, Any], key: str) -> Any:
    context = paper.get("system_context")
    if not isinstance(context, dict):
        return None
    return context.get(key)


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _select_subset_papers(
    papers: list[Any],
    *,
    size: int,
    paper_ids: tuple[str, ...],
) -> list[dict[str, Any]]:
    valid_papers = [paper for paper in papers if isinstance(paper, dict)]
    selected: list[dict[str, Any]] = []
    for paper_id in paper_ids:
        match = next((paper for paper in valid_papers if str(paper.get("paper_id")) == paper_id), None)
        if match is not None:
            _append_unique(selected, match)

    if len(selected) >= size > 0:
        return copy.deepcopy(selected[:size])

    selectors = (
        _is_deep_dive,
        _is_short_mention,
        _is_full_review_only,
        _has_document_failure,
        _is_triage_reject,
        _has_no_evidence,
    )
    target_size = max(size, len(selected))
    for selector in selectors:
        if len(selected) >= target_size:
            return copy.deepcopy(selected)
        match = next((paper for paper in valid_papers if selector(paper)), None)
        if match is not None:
            _append_unique(selected, match)

    for selector in selectors:
        for paper in valid_papers:
            if len(selected) >= target_size:
                return copy.deepcopy(selected)
            if selector(paper):
                _append_unique(selected, paper)
    for paper in valid_papers:
        if len(selected) >= target_size:
            break
        _append_unique(selected, paper)
    return copy.deepcopy(selected)


def _append_unique(selected: list[dict[str, Any]], paper: dict[str, Any]) -> None:
    paper_id = str(paper.get("paper_id"))
    if paper_id and all(str(item.get("paper_id")) != paper_id for item in selected):
        selected.append(paper)


def _is_deep_dive(paper: dict[str, Any]) -> bool:
    return "deep_dive_draft" in _selection_context(paper)


def _is_short_mention(paper: dict[str, Any]) -> bool:
    return "short_mention" in _selection_context(paper)


def _is_full_review_only(paper: dict[str, Any]) -> bool:
    selections = _selection_context(paper)
    return "full_review" in selections and "deep_dive_draft" not in selections


def _has_document_failure(paper: dict[str, Any]) -> bool:
    document = _context_value(paper, "document")
    return isinstance(document, dict) and document.get("status") not in {None, "ok"}


def _is_triage_reject(paper: dict[str, Any]) -> bool:
    triage = _context_value(paper, "triage")
    return isinstance(triage, dict) and triage.get("decision") == "reject"


def _has_no_evidence(paper: dict[str, Any]) -> bool:
    evidence = _context_value(paper, "evidence")
    return isinstance(evidence, dict) and int(evidence.get("count") or 0) == 0


def _selection_context(paper: dict[str, Any]) -> dict[str, Any]:
    selections = _context_value(paper, "selection")
    return selections if isinstance(selections, dict) else {}
