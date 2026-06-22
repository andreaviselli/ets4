from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .validate import BenchmarkValidationResult


@dataclass(frozen=True)
class GateCheck:
    name: str
    passed: bool
    observed: object
    required: str
    severity: str
    reason: str


@dataclass(frozen=True)
class ProviderGateResult:
    status: str
    ready: bool
    failed_count: int
    checks: tuple[GateCheck, ...]


DEFAULT_PROVIDER_GATE_THRESHOLDS = {
    "min_labeled_papers": 100,
    "min_full_review_examples": 20,
    "min_hard_negative_examples": 1,
    "min_directly_relevant_examples": 1,
    "min_selected_precision": 0.8,
    "min_relevant_recall": 0.8,
    "max_hard_negative_false_positive_rate": 0.0,
    "min_required_evidence_coverage": 0.95,
    "max_invalid_citation_rate": 0.0,
    "max_hidden_disagreement_count": 0,
    "min_editorial_decision_accuracy": 0.8,
    "min_publication_track_accuracy": 0.8,
}


def assess_provider_gate(
    *,
    metrics: dict[str, Any],
    item_results: tuple[dict[str, Any], ...],
    benchmark_validation: BenchmarkValidationResult,
) -> ProviderGateResult:
    thresholds = DEFAULT_PROVIDER_GATE_THRESHOLDS
    triage = metrics.get("triage", {})
    evidence = metrics.get("evidence", {})
    review = metrics.get("review", {})
    rubric = metrics.get("rubric", {})
    checks = [
        _check_equal(
            name="benchmark_validation_errors",
            observed=benchmark_validation.error_count,
            expected=0,
            reason="Benchmark JSON must be structurally valid.",
        ),
        _check_equal(
            name="benchmark_incomplete_labels",
            observed=benchmark_validation.incomplete_count,
            expected=0,
            reason="Provider comparison requires complete accepted labels.",
        ),
        _check_equal(
            name="benchmark_warning_count",
            observed=benchmark_validation.warning_count,
            expected=0,
            reason="Resolve mixed accepted-label axes before provider adoption.",
        ),
        _check_min(
            name="labeled_papers",
            observed=int(metrics.get("labeled_papers") or 0),
            minimum=int(thresholds["min_labeled_papers"]),
            reason="Pilot gate requires a representative triage benchmark.",
        ),
        _check_min(
            name="full_review_examples",
            observed=_full_review_example_count(item_results),
            minimum=int(thresholds["min_full_review_examples"]),
            reason="Pilot gate requires enough full-review examples to judge review quality.",
        ),
        _check_min(
            name="hard_negative_examples",
            observed=sum(1 for item in item_results if item["label"].get("hard_negative")),
            minimum=int(thresholds["min_hard_negative_examples"]),
            reason="Benchmark must include explicit hard negatives.",
        ),
        _check_min(
            name="directly_relevant_examples",
            observed=sum(
                1 for item in item_results if item["label"].get("relevance_label") == "directly_relevant"
            ),
            minimum=int(thresholds["min_directly_relevant_examples"]),
            reason="Benchmark must include directly relevant papers.",
        ),
        _check_min(
            name="selected_precision",
            observed=triage.get("selected_precision"),
            minimum=float(thresholds["min_selected_precision"]),
            reason="Full-review selection must preserve precision before provider adoption.",
        ),
        _check_min(
            name="relevant_recall",
            observed=triage.get("relevant_recall"),
            minimum=float(thresholds["min_relevant_recall"]),
            reason="Full-review selection must avoid missing relevant papers.",
        ),
        _check_max(
            name="hard_negative_false_positive_rate",
            observed=triage.get("hard_negative_false_positive_rate"),
            maximum=float(thresholds["max_hard_negative_false_positive_rate"]),
            reason="Hard-negative false positives must remain zero.",
        ),
        _check_min(
            name="required_evidence_coverage",
            observed=evidence.get("required_kind_coverage"),
            minimum=float(thresholds["min_required_evidence_coverage"]),
            reason="Required evidence kinds must be covered before provider comparison.",
        ),
        _check_max(
            name="invalid_citation_rate",
            observed=review.get("invalid_citation_rate"),
            maximum=float(thresholds["max_invalid_citation_rate"]),
            reason="Reviewer citations must resolve to stored evidence items.",
        ),
        _check_max(
            name="hidden_disagreement_count",
            observed=review.get("hidden_disagreement_count"),
            maximum=int(thresholds["max_hidden_disagreement_count"]),
            reason="Handling-editor memos must not hide reviewer disagreement.",
        ),
        _check_min(
            name="editorial_decision_accuracy",
            observed=review.get("editorial_decision_accuracy"),
            minimum=float(thresholds["min_editorial_decision_accuracy"]),
            reason="Editorial decisions need acceptable agreement with labels.",
        ),
        _check_min(
            name="publication_track_accuracy",
            observed=rubric.get("publication_track_accuracy"),
            minimum=float(thresholds["min_publication_track_accuracy"]),
            reason="Publication-track routing must be calibrated before provider adoption.",
        ),
    ]
    failed_count = sum(1 for check in checks if not check.passed)
    return ProviderGateResult(
        status="ready" if failed_count == 0 else "not_ready",
        ready=failed_count == 0,
        failed_count=failed_count,
        checks=tuple(checks),
    )


def provider_gate_dict(result: ProviderGateResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "ready": result.ready,
        "failed_count": result.failed_count,
        "checks": [
            {
                "name": check.name,
                "passed": check.passed,
                "observed": check.observed,
                "required": check.required,
                "severity": check.severity,
                "reason": check.reason,
            }
            for check in result.checks
        ],
    }


def _full_review_example_count(item_results: tuple[dict[str, Any], ...]) -> int:
    return sum(
        1
        for item in item_results
        if item["label"].get("expected_triage_decision") in {"assign_reviewers", "borderline"}
        or item["label"].get("expected_editorial_decision") not in {None, "reject"}
    )


def _check_equal(*, name: str, observed: object, expected: object, reason: str) -> GateCheck:
    return GateCheck(
        name=name,
        passed=observed == expected,
        observed=observed,
        required=f"== {expected}",
        severity="blocker",
        reason=reason,
    )


def _check_min(*, name: str, observed: object, minimum: float | int, reason: str) -> GateCheck:
    return GateCheck(
        name=name,
        passed=_number_or_none(observed) is not None and _number_or_none(observed) >= minimum,
        observed=observed,
        required=f">= {minimum:g}",
        severity="blocker",
        reason=reason,
    )


def _check_max(*, name: str, observed: object, maximum: float | int, reason: str) -> GateCheck:
    return GateCheck(
        name=name,
        passed=_number_or_none(observed) is not None and _number_or_none(observed) <= maximum,
        observed=observed,
        required=f"<= {maximum:g}",
        severity="blocker",
        reason=reason,
    )


def _number_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
