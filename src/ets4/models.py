from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
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
    publication_track: str
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
            "publication_track": self.publication_track,
            "deep_dive_score": self.deep_dive_score,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "majority_view": self.majority_view,
            "minority_view": self.minority_view,
            "evidence_item_ids": list(self.evidence_item_ids),
            "questions_for_human": list(self.questions_for_human),
        }


@dataclass(frozen=True)
class ModelCallUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


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

    def last_usage(self) -> ModelCallUsage | None:
        """Return usage metadata for the most recent provider call, if available."""


class FakeModelProvider:
    """Deterministic provider used for offline development and tests."""

    name = "fake"

    forecasting_terms = (
        "forecast",
        "forecasts",
        "forecasting",
        "predict",
        "predicts",
        "prediction",
        "predictions",
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
        "portfolio",
        "trading",
        "value at risk",
        "expected shortfall",
        "volatility",
    )
    applied_note_terms = (
        "alternative scenario",
        "alternative scenarios",
        "evaluation",
        "historical",
        "interpretation",
        "retrospective",
    )
    applied_method_terms = (
        "arma",
        "bayesian",
        "compositional",
        "dirichlet",
        "intervention",
        "structural break",
        "structural breaks",
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

    def last_usage(self) -> ModelCallUsage | None:
        return None

    def triage(self, title: str, abstract: str, source_name: str = "") -> TriageResult:
        text = f"{title} {abstract} {source_name}".lower()
        has_forecasting = _contains_any_term(text, self.forecasting_terms)
        has_economic = _contains_any_term(text, self.economic_terms)
        has_adjacent_economic = _contains_any_term(text, self.adjacent_economic_terms)
        has_financial_method = _contains_any_term(text, self.financial_method_terms)
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
                publication_track="reject",
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
            paper_text=paper_text,
            has_forecasting=has_forecasting,
            has_economic=has_economic,
            has_adjacent_economic=has_adjacent_economic,
            has_financial_method=has_financial_method,
            applied_note_terms=self.applied_note_terms,
            applied_method_terms=self.applied_method_terms,
        )

        if disagreement >= 3.0 or len(weak_reports) >= 2:
            decision = "needs_human_adjudication"
        elif (
            track_fit in {"methods_watch", "reject"}
            and has_financial_method
            and adjusted_score >= 6.5
            and evidence_count >= 5
        ):
            decision = "needs_human_adjudication"
        elif adjusted_score >= 7.0 and evidence_count >= 5 and track_fit in {
            "deep_dive",
            "applied_method",
        }:
            decision = "full_deep_dive"
        elif adjusted_score >= 5.8 and track_fit in {"deep_dive", "applied_note", "applied_method"}:
            decision = "short_mention"
        elif adjusted_score >= 4.5 or track_fit == "methods_watch":
            decision = "watchlist"
        else:
            decision = "reject"
        publication_track = _publication_track_for_decision(
            decision=decision,
            track_fit=track_fit,
        )

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
            publication_track=publication_track,
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


class OpenAIModelProvider:
    """OpenAI-backed provider using structured Responses API JSON outputs."""

    name = "openai"
    default_model = "gpt-5.5"

    def __init__(
        self,
        *,
        triage_model: str | None = None,
        review_model: str | None = None,
        prompt_version: str = "dev",
        client: Any | None = None,
    ) -> None:
        self.triage_model = _usable_model_name(triage_model, self.default_model)
        self.review_model = _usable_model_name(review_model, self.triage_model)
        self.prompt_version = prompt_version
        self._client = client
        self._last_usage: ModelCallUsage | None = None

    def last_usage(self) -> ModelCallUsage | None:
        return self._last_usage

    def triage(self, title: str, abstract: str, source_name: str = "") -> TriageResult:
        payload = {
            "title": title,
            "abstract": abstract,
            "source_name": source_name,
            "product": "practitioner/applied economic forecasting digest",
        }
        result = self._request_json(
            model=self.triage_model,
            schema_name="ets4_triage",
            schema=_triage_schema(),
            system_prompt=_triage_system_prompt(),
            user_payload=payload,
        )
        return TriageResult(
            decision=str(result["decision"]),
            category_hint=str(result["category_hint"]),
            forecasting_signal=str(result["forecasting_signal"]),
            economic_signal=str(result["economic_signal"]),
            score=float(result["score"]),
            confidence=float(result["confidence"]),
            reason=str(result["reason"]),
        )

    def review(self, role: str, dossier: dict[str, Any]) -> ReviewerReportResult:
        payload = {
            "role": role,
            "dossier": _compact_dossier(dossier),
            "product": "practitioner/applied economic forecasting digest",
        }
        result = self._request_json(
            model=self.review_model,
            schema_name="ets4_reviewer_report",
            schema=_reviewer_report_schema(),
            system_prompt=_review_system_prompt(role),
            user_payload=payload,
        )
        return ReviewerReportResult(
            role=str(result["role"]),
            recommendation=str(result["recommendation"]),
            score=float(result["score"]),
            confidence=float(result["confidence"]),
            summary=str(result["summary"]),
            strengths=tuple(str(item) for item in result["strengths"]),
            weaknesses=tuple(str(item) for item in result["weaknesses"]),
            required_evidence=tuple(str(item) for item in result["required_evidence"]),
            evidence_item_ids=tuple(int(item) for item in result["evidence_item_ids"]),
            questions_for_editor=tuple(str(item) for item in result["questions_for_editor"]),
        )

    def handling_editor(
        self,
        dossier: dict[str, Any],
        reports: list[dict[str, Any]],
    ) -> EditorialDecisionResult:
        payload = {
            "dossier": _compact_dossier(dossier),
            "reports": reports,
            "product": "practitioner/applied economic forecasting digest",
        }
        result = self._request_json(
            model=self.review_model,
            schema_name="ets4_editorial_decision",
            schema=_editorial_decision_schema(),
            system_prompt=_handling_editor_system_prompt(),
            user_payload=payload,
        )
        return EditorialDecisionResult(
            decision=str(result["decision"]),
            publication_track=str(result["publication_track"]),
            deep_dive_score=float(result["deep_dive_score"]),
            confidence=float(result["confidence"]),
            rationale=str(result["rationale"]),
            majority_view=str(result["majority_view"]),
            minority_view=str(result["minority_view"]),
            evidence_item_ids=tuple(int(item) for item in result["evidence_item_ids"]),
            questions_for_human=tuple(str(item) for item in result["questions_for_human"]),
        )

    def _request_json(
        self,
        *,
        model: str,
        schema_name: str,
        schema: dict[str, Any],
        system_prompt: str,
        user_payload: dict[str, Any],
    ) -> dict[str, Any]:
        client = self._openai_client()
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, sort_keys=True)},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "schema": schema,
                        "strict": True,
                    }
                },
            )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, sort_keys=True)},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": schema,
                        "strict": True,
                    },
                },
            )
        self._last_usage = _usage_from_response(response)
        output_text = _response_output_text(response)
        try:
            result = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI provider returned invalid JSON: {exc}") from exc
        if not isinstance(result, dict):
            raise ValueError("OpenAI provider returned a non-object JSON payload")
        return result

    def _openai_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - package dependency covers this
            raise RuntimeError("OpenAI provider requires the openai Python package") from exc
        self._client = OpenAI()
        return self._client


def _count_evidence_by_kind(evidence_items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evidence_items:
        kind = str(item.get("kind", "unknown"))
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _review_recommendation(score: float, missing: tuple[str, ...]) -> str:
    if len(missing) >= 3:
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
    paper_text: str,
    has_forecasting: bool,
    has_economic: bool,
    has_adjacent_economic: bool,
    has_financial_method: bool,
    applied_note_terms: tuple[str, ...],
    applied_method_terms: tuple[str, ...],
) -> str:
    if has_financial_method and not _contains_any_term(paper_text, economic_terms_for_track()):
        return "reject"
    if has_forecasting and has_economic and _contains_any_term(paper_text, applied_note_terms):
        return "applied_note"
    if has_forecasting and has_economic and _contains_any_term(paper_text, applied_method_terms):
        return "applied_method"
    if has_forecasting and has_economic and _contains_any_term(paper_text, direct_forecast_terms()):
        return "deep_dive"
    if has_forecasting and has_economic:
        return "applied_note"
    if has_forecasting and (has_financial_method or has_adjacent_economic):
        return "methods_watch"
    return "reject"


def _publication_track_for_decision(*, decision: str, track_fit: str) -> str:
    if decision == "full_deep_dive":
        return "deep_dive" if track_fit == "deep_dive" else "applied_note"
    if decision == "short_mention":
        return "applied_note"
    if decision == "watchlist":
        return "methods_watch" if track_fit == "methods_watch" else "reject"
    if decision == "needs_human_adjudication":
        return "reject"
    return "reject"


def direct_forecast_terms() -> tuple[str, ...]:
    return (
        "forecast",
        "forecasts",
        "forecasting",
        "predict",
        "predicts",
        "prediction",
        "predictions",
        "predictive",
        "nowcast",
        "nowcasting",
    )


def economic_terms_for_track() -> tuple[str, ...]:
    return (
        "economic",
        "economy",
        "macroeconomic",
        "inflation",
        "gdp",
        "monetary",
        "central bank",
        "federal reserve",
        "reserves",
        "employment",
        "labor",
        "prices",
        "scenario",
    )


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


def _usable_model_name(value: str | None, default: str) -> str:
    if not value or value.startswith("fake-"):
        return default
    return value


def _response_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)
    choices = getattr(response, "choices", None) or []
    for choice in choices:
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if content:
            return str(content)
    output = getattr(response, "output", None) or []
    for item in output:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                return str(text)
    raise ValueError("OpenAI provider response did not contain output text")


def _usage_from_response(response: Any) -> ModelCallUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    input_tokens = _optional_int(
        getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
    )
    output_tokens = _optional_int(
        getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None)
    )
    total_tokens = _optional_int(getattr(usage, "total_tokens", None))
    metadata = {
        "estimated_cost_status": "not_configured",
    }
    return ModelCallUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=0.0,
        metadata=metadata,
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compact_dossier(dossier: dict[str, Any]) -> dict[str, Any]:
    evidence_items = []
    for item in list(dossier.get("evidence_items", []))[:80]:
        evidence_items.append(
            {
                "id": item.get("id"),
                "kind": item.get("kind"),
                "source_locator": item.get("source_locator"),
                "text": str(item.get("text", ""))[:1200],
            }
        )
    return {
        "paper": dossier.get("paper", {}),
        "evidence_count": dossier.get("evidence_count", len(dossier.get("evidence_items", []))),
        "evidence_items": evidence_items,
        "limitations": dossier.get("limitations", []),
    }


def _triage_system_prompt() -> str:
    return (
        "You are ETS4's managing editor for a practitioner/applied economic "
        "forecasting digest. Return only the requested JSON. Desk-screen papers "
        "for applied forecasting, nowcasting, forecast evaluation, risk monitoring, "
        "scenario analysis, or economic decision support. Reject work without a "
        "forecasting signal. Use borderline when applied economic fit is plausible "
        "but uncertain."
    )


def _review_system_prompt(role: str) -> str:
    return (
        f"You are ETS4's independent {role} reviewer. Return only the requested "
        "JSON. Ground judgments in supplied evidence item ids. Preserve caveats "
        "and uncertainty; do not invent evidence not present in the dossier."
    )


def _handling_editor_system_prompt() -> str:
    return (
        "You are ETS4's handling editor. Return only the requested JSON. "
        "Reconcile independent reviews for a practitioner/applied economic "
        "forecasting digest. Do not promote weakly applied or weakly evidenced "
        "papers into publication tracks. Escalate genuine disagreement or missing "
        "evidence to human adjudication."
    )


def _triage_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["reject", "borderline", "assign_reviewers"]},
            "category_hint": {
                "type": "string",
                "enum": ["directly_relevant", "paper_of_interest", "not_relevant"],
            },
            "forecasting_signal": {"type": "string", "enum": ["explicit", "implied", "absent"]},
            "economic_signal": {"type": "string", "enum": ["explicit", "implied", "absent"]},
            "score": {"type": "number", "minimum": 0, "maximum": 10},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
        },
        "required": [
            "decision",
            "category_hint",
            "forecasting_signal",
            "economic_signal",
            "score",
            "confidence",
            "reason",
        ],
        "additionalProperties": False,
    }


def _reviewer_report_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": ["relevance", "methods", "evidence", "practitioner", "transferability"],
            },
            "recommendation": {
                "type": "string",
                "enum": [
                    "support_deep_dive",
                    "support_short_mention",
                    "watchlist",
                    "needs_editor",
                    "reject",
                ],
            },
            "score": {"type": "number", "minimum": 0, "maximum": 10},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "weaknesses": {"type": "array", "items": {"type": "string"}},
            "required_evidence": {"type": "array", "items": {"type": "string"}},
            "evidence_item_ids": {"type": "array", "items": {"type": "integer"}},
            "questions_for_editor": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "role",
            "recommendation",
            "score",
            "confidence",
            "summary",
            "strengths",
            "weaknesses",
            "required_evidence",
            "evidence_item_ids",
            "questions_for_editor",
        ],
        "additionalProperties": False,
    }


def _editorial_decision_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": [
                    "full_deep_dive",
                    "short_mention",
                    "watchlist",
                    "needs_human_adjudication",
                    "reject",
                ],
            },
            "publication_track": {
                "type": "string",
                "enum": ["deep_dive", "applied_note", "methods_watch", "reject"],
            },
            "deep_dive_score": {"type": "number", "minimum": 0, "maximum": 10},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
            "majority_view": {"type": "string"},
            "minority_view": {"type": "string"},
            "evidence_item_ids": {"type": "array", "items": {"type": "integer"}},
            "questions_for_human": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "decision",
            "publication_track",
            "deep_dive_score",
            "confidence",
            "rationale",
            "majority_view",
            "minority_view",
            "evidence_item_ids",
            "questions_for_human",
        ],
        "additionalProperties": False,
    }


def get_model_provider(
    name: str,
    *,
    triage_model: str | None = None,
    review_model: str | None = None,
    prompt_version: str = "dev",
) -> ModelProvider:
    if name == "fake":
        return FakeModelProvider()
    if name == "openai":
        return OpenAIModelProvider(
            triage_model=triage_model,
            review_model=review_model,
            prompt_version=prompt_version,
        )
    raise ValueError(f"Unknown model provider: {name}")
