from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TriageResult:
    decision: str
    category_hint: str
    forecasting_signal: str
    economic_signal: str
    score: float
    confidence: float
    reason: str


class ModelProvider(Protocol):
    name: str

    def triage(self, title: str, abstract: str, source_name: str = "") -> TriageResult:
        """Return a deterministic triage result for a paper."""


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
        "time series",
        "probabilistic",
    )
    economic_terms = (
        "economic",
        "economy",
        "macro",
        "inflation",
        "gdp",
        "finance",
        "financial",
        "energy",
        "oil",
        "gas",
        "electricity",
        "market",
        "asset",
        "monetary",
    )
    hard_negative_terms = (
        "causal inference",
        "treatment effect",
        "structural var",
        "variance decomposition",
    )

    def triage(self, title: str, abstract: str, source_name: str = "") -> TriageResult:
        text = f"{title} {abstract} {source_name}".lower()
        has_forecasting = any(term in text for term in self.forecasting_terms)
        has_economic = any(term in text for term in self.economic_terms)
        has_hard_negative = any(term in text for term in self.hard_negative_terms)

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


def get_model_provider(name: str) -> ModelProvider:
    if name == "fake":
        return FakeModelProvider()
    raise ValueError(f"Unknown model provider: {name}")

