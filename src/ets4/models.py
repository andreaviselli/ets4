from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TriageResult:
    decision: str
    category_hint: str
    forecasting_signal: str
    economic_signal: str
    score: float
    confidence: float
    reason: str


@dataclass(frozen=True)
class ReviewerReportResult:
    role: str
    recommendation: str
    score: float
    confidence: float
    summary: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    required_evidence: tuple[str, ...]
    evidence_item_ids: tuple[int, ...]
    questions_for_editor: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "recommendation": self.recommendation,
            "score": self.score,
            "confidence": self.confidence,
            "summary": self.summary,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "required_evidence": list(self.required_evidence),
            "evidence_item_ids": list(self.evidence_item_ids),
            "questions_for_editor": list(self.questions_for_editor),
        }


@dataclass(frozen=True)
class EditorialDecisionResult:
    decision: str
    deep_dive_score: float
    confidence: float
    rationale: str
    majority_view: str
    minority_view: str
    evidence_item_ids: tuple[int, ...]
    questions_for_human: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "deep_dive_score": self.deep_dive_score,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "majority_view": self.majority_view,
            "minority_view": self.minority_view,
            "evidence_item_ids": list(self.evidence_item_ids),
            "questions_for_human": list(self.questions_for_human),
        }


class ModelProvider(Protocol):
    name: str

    def triage(self, title: str, abstract: str, source_name: str = "") -> TriageResult:
        """Return a deterministic triage result for a paper."""

    def review(self, role: str, dossier: dict[str, Any]) -> ReviewerReportResult:
        """Return an independent structured reviewer report for a paper dossier."""

    def handling_editor(
        self,
        dossier: dict[str, Any],
        reports: list[dict[str, Any]],
    ) -> EditorialDecisionResult:
        """Return the handling-editor reconciliation memo for reviewer reports."""


class FakeModelProvider:
    """Deterministic provider used for offline development and tests."""

    name = "fake"

    forecasting_terms = (
        "forecast",
        "forecasting",
        "predict",
        "prediction",
        "predictive",
        "nowcast",
        "nowcasting",
        "scenario",
        "scenarios",
        "stress-test",
        "stress testing",
        "time series",
        "probabilistic",
    )
    economic_terms = (
        "economic",
        "economy",
        "macroeconomic",
        "inflation",
        "gdp",
        "monetary",
        "policy",
        "central bank",
        "federal reserve",
        "reserves",
        "demand",
        "supply",
        "business",
        "employment",
        "labor",
        "prices",
        "scenario",
    )
    adjacent_economic_terms = (
        "commodity",
        "commodities",
        "electricity",
        "energy",
        "gas",
        "oil",
    )
    financial_method_terms = (
        "asset",
        "equity",
        "equities",
        "finance",
        "financial",
        "garch",
        "market",
        "portfolio",
        "trading",
        "value at risk",
        "expected shortfall",
        "volatility",
    )
    finance_reject_terms = (
        "equity market",
        "equity markets",
        "expected shortfall",
        "trading",
        "value at risk",
    )
    hard_negative_terms = (
        "causal inference",
        "treatment effect",
        "structural var",
        "variance decomposition",
    )
    role_evidence_kinds = {
        "relevance": ("method", "dataset", "metric"),
        "methods": ("method", "metric", "baseline", "limitation"),
        "evidence": ("dataset", "metric", "baseline", "limitation", "code"),
        "practitioner": ("dataset", "metric", "code", "limitation"),
        "transferability": ("dataset", "limitation", "method"),
    }

    def triage(self, title: str, abstract: str, source_name: str = "") -> TriageResult:
        text = f"{title} {abstract} {source_name}".lower()
        has_forecasting = _contains_any_term(text, self.forecasting_terms)
        has_economic = _contains_any_term(text, self.economic_terms)
        has_adjacent_economic = _contains_any_term(text, self.adjacent_economic_terms)
        has_financial_method = _contains_any_term(text, self.financial_method_terms)
        has_finance_reject = _contains_any_term(text, self.finance_reject_terms)
        has_hard_negative = _contains_any_term(text, self.hard_negative_terms)

        if has_hard_negative and not has_forecasting:
            return TriageResult(
                decision="reject",
                category_hint="not_relevant",
                forecasting_signal="absent",
                economic_signal="explicit" if has_economic else "absent",
                score=2.0,
                confidence=0.85,
                reason="Detected a hard-negative topic without an explicit forecasting signal.",
            )

        if has_finance_reject and not has_economic:
            return TriageResult(
                decision="reject",
                category_hint="not_relevant",
                forecasting_signal="explicit" if has_forecasting else "absent",
                economic_signal="absent",
                score=3.0,
                confidence=0.7,
                reason=(
                    "Detected a finance/trading risk topic without enough applied economic "
                    "forecasting fit for the default product."
                ),
            )

        if has_forecasting and has_economic:
            return TriageResult(
                decision="assign_reviewers",
                category_hint="directly_relevant",
                forecasting_signal="explicit",
                economic_signal="explicit",
                score=8.0,
                confidence=0.75,
                reason="Detected explicit forecasting and economic signals.",
            )

        if has_forecasting and (has_financial_method or has_adjacent_economic):
            return TriageResult(
                decision="borderline",
                category_hint="paper_of_interest",
                forecasting_signal="explicit",
                economic_signal="implied",
                score=5.8,
                confidence=0.55,
                reason=(
                    "Detected a forecasting signal in financial/time-series methods, "
                    "but applied economic forecasting fit is not explicit."
                ),
            )

        if has_forecasting:
            return TriageResult(
                decision="borderline",
                category_hint="paper_of_interest",
                forecasting_signal="explicit",
                economic_signal="absent",
                score=6.5,
                confidence=0.55,
                reason="Detected forecasting signal but no clear economic signal.",
            )

        return TriageResult(
            decision="reject",
            category_hint="not_relevant",
            forecasting_signal="absent",
            economic_signal="explicit" if has_economic else "absent",
            score=1.5,
            confidence=0.8,
            reason="No forecasting signal detected.",
        )

    def review(self, role: str, dossier: dict[str, Any]) -> ReviewerReportResult:
        evidence_items = list(dossier.get("evidence_items", []))
        evidence_by_kind = _count_evidence_by_kind(evidence_items)
        relevant_kinds = self.role_evidence_kinds.get(role, ())
        cited = tuple(
            int(item["id"])
            for item in evidence_items
            if str(item.get("kind")) in relevant_kinds
        )[:6]
        coverage = len({kind for kind in relevant_kinds if evidence_by_kind.get(kind, 0)})
        score = min(8.5, 3.0 + coverage * 1.2 + min(len(cited), 4) * 0.35)
        missing = tuple(kind for kind in relevant_kinds if evidence_by_kind.get(kind, 0) == 0)
        confidence = 0.35 + min(len(cited), 6) * 0.08
        recommendation = _review_recommendation(score, missing)

        title = str(dossier.get("paper", {}).get("title", "paper"))
        strengths = (
            f"{role} review found {coverage}/{len(relevant_kinds)} expected evidence types.",
        )
        weaknesses = (
            (f"Missing evidence types: {', '.join(missing)}.",) if missing else ()
        )
        questions = (
            ("Can the missing evidence be verified in the full text?",) if missing else ()
        )
        return ReviewerReportResult(
            role=role,
            recommendation=recommendation,
            score=round(score, 3),
            confidence=round(min(confidence, 0.9), 3),
            summary=f"Fake {role} reviewer assessed '{title}' using cited evidence items.",
            strengths=strengths,
            weaknesses=weaknesses,
            required_evidence=tuple(relevant_kinds),
            evidence_item_ids=cited,
            questions_for_editor=questions,
        )

    def handling_editor(
        self,
        dossier: dict[str, Any],
        reports: list[dict[str, Any]],
    ) -> EditorialDecisionResult:
        if not reports:
            return EditorialDecisionResult(
                decision="needs_human_adjudication",
                deep_dive_score=0.0,
                confidence=0.0,
                rationale="No reviewer reports are available.",
                majority_view="No panel view.",
                minority_view="No minority view.",
                evidence_item_ids=(),
                questions_for_human=("Assign reviewers before making an editorial decision.",),
            )

        scores = [float(report["score"]) for report in reports]
        avg_score = sum(scores) / len(scores)
        disagreement = max(scores) - min(scores)
        all_evidence_ids = sorted(
            {
                int(evidence_id)
                for report in reports
                for evidence_id in report.get("evidence_item_ids", [])
            }
        )
        weak_reports = [
            report["role"]
            for report in reports
            if report["recommendation"] in {"needs_editor", "reject"}
        ]
        evidence_count = int(dossier.get("evidence_count", len(dossier.get("evidence_items", []))))
        adjusted_score = avg_score
        if evidence_count < 4:
            adjusted_score -= 1.0
        if disagreement >= 2.5:
            adjusted_score -= 0.75
        if weak_reports:
            adjusted_score -= 0.5
        paper = dossier.get("paper", {})
        paper_text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        has_forecasting = _contains_any_term(paper_text, self.forecasting_terms)
        has_economic = _contains_any_term(paper_text, self.economic_terms)
        has_adjacent_economic = _contains_any_term(paper_text, self.adjacent_economic_terms)
        has_financial_method = _contains_any_term(paper_text, self.financial_method_terms)
        track_fit = _track_fit(
            has_forecasting=has_forecasting,
            has_economic=has_economic,
            has_adjacent_economic=has_adjacent_economic,
            has_financial_method=has_financial_method,
        )

        if disagreement >= 3.0 or len(weak_reports) >= 2:
            decision = "needs_human_adjudication"
        elif adjusted_score >= 7.0 and evidence_count >= 5 and track_fit == "deep_dive":
            decision = "full_deep_dive"
        elif adjusted_score >= 5.8 and track_fit in {"deep_dive", "applied_note"}:
            decision = "short_mention"
        elif adjusted_score >= 4.5 or track_fit == "methods_watch":
            decision = "watchlist"
        else:
            decision = "reject"

        questions = []
        if evidence_count < 4:
            questions.append("Evidence coverage is thin; verify the full text before publication.")
        if disagreement >= 2.5:
            questions.append("Reviewer disagreement is material; inspect minority concerns.")
        if weak_reports:
            questions.append(f"Resolve weak reviewer reports: {', '.join(weak_reports)}.")
        if track_fit != "deep_dive":
            questions.append(
                "Applied forecasting fit is limited; verify publication track before drafting."
            )

        return EditorialDecisionResult(
            decision=decision,
            deep_dive_score=round(max(0.0, adjusted_score), 3),
            confidence=round(
                max(0.2, min(0.85, 0.55 + evidence_count * 0.03 - disagreement * 0.05)),
                3,
            ),
            rationale=(
                f"Handling editor reconciled {len(reports)} independent reports with "
                f"average score {avg_score:.2f} and disagreement {disagreement:.2f}."
            ),
            majority_view=_majority_view(reports),
            minority_view=_minority_view(reports),
            evidence_item_ids=tuple(all_evidence_ids[:10]),
            questions_for_human=tuple(questions),
        )


def _count_evidence_by_kind(evidence_items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evidence_items:
        kind = str(item.get("kind", "unknown"))
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _review_recommendation(score: float, missing: tuple[str, ...]) -> str:
    if len(missing) >= 2:
        return "needs_editor"
    if score >= 7.0:
        return "support_deep_dive"
    if score >= 5.8:
        return "support_short_mention"
    if score >= 4.5:
        return "watchlist"
    return "reject"


def _track_fit(
    *,
    has_forecasting: bool,
    has_economic: bool,
    has_adjacent_economic: bool,
    has_financial_method: bool,
) -> str:
    if has_forecasting and has_economic:
        return "deep_dive"
    if has_economic:
        return "applied_note"
    if has_forecasting and (has_financial_method or has_adjacent_economic):
        return "methods_watch"
    return "reject"


def _contains_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(_contains_term(text, term) for term in terms)


def _contains_term(text: str, term: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9]){re.escape(term.lower())}(?![A-Za-z0-9])"
    return re.search(pattern, text) is not None


def _majority_view(reports: list[dict[str, Any]]) -> str:
    recommendations: dict[str, int] = {}
    for report in reports:
        recommendation = str(report["recommendation"])
        recommendations[recommendation] = recommendations.get(recommendation, 0) + 1
    top = sorted(recommendations.items(), key=lambda item: (-item[1], item[0]))[0]
    return f"{top[1]} reviewer(s) recommended {top[0]}."


def _minority_view(reports: list[dict[str, Any]]) -> str:
    recommendations = {str(report["recommendation"]) for report in reports}
    if len(recommendations) <= 1:
        return "No material minority recommendation."
    return "Minority recommendations: " + ", ".join(sorted(recommendations))


def get_model_provider(name: str) -> ModelProvider:
    if name == "fake":
        return FakeModelProvider()
    raise ValueError(f"Unknown model provider: {name}")
