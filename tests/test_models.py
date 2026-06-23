import json
from types import SimpleNamespace

from ets4.models import FakeModelProvider, OpenAIModelProvider, get_model_provider


def test_fake_provider_shortlists_economic_forecasting_paper() -> None:
    provider = FakeModelProvider()

    result = provider.triage(
        "Inflation forecasting with probabilistic time series models",
        "We forecast inflation using macroeconomic predictors.",
        "NEP Forecasting",
    )

    assert result.decision == "assign_reviewers"
    assert result.category_hint == "directly_relevant"
    assert result.score == 8.0


def test_fake_provider_rejects_non_forecasting_paper() -> None:
    provider = FakeModelProvider()

    result = provider.triage(
        "Structural VAR evidence on monetary policy transmission",
        "We estimate causal impulse responses and variance decompositions.",
    )

    assert result.decision == "reject"
    assert result.category_hint == "not_relevant"


def test_fake_provider_routes_financial_method_paper_to_borderline() -> None:
    provider = FakeModelProvider()

    result = provider.triage(
        "Multi-Scale Markov Switching GARCH",
        "We forecast volatility regimes in financial time series.",
    )

    assert result.decision == "borderline"
    assert result.category_hint == "paper_of_interest"


def test_fake_provider_routes_trading_risk_without_applied_economic_fit_to_borderline() -> None:
    provider = FakeModelProvider()

    result = provider.triage(
        "Forecasting Value at Risk and Expected Shortfall in Equity Markets",
        "We forecast downside risk for equity trading portfolios.",
    )

    assert result.decision == "borderline"
    assert result.category_hint == "paper_of_interest"


def test_fake_provider_rejects_descriptive_finance_without_forecasting_signal() -> None:
    provider = FakeModelProvider()

    result = provider.triage(
        "Long-Range Dependence in Financial Markets",
        "We study market efficiency with generative modeling of synthetic financial data.",
    )

    assert result.decision == "reject"
    assert result.category_hint == "not_relevant"


def test_fake_provider_routes_economic_scenario_paper_to_review() -> None:
    provider = FakeModelProvider()

    result = provider.triage(
        "Alternative Scenarios at the Federal Reserve",
        "We evaluate central bank scenarios for policy and reserves.",
    )

    assert result.decision == "assign_reviewers"
    assert result.category_hint == "directly_relevant"


def test_fake_handling_editor_does_not_treat_generic_market_disruption_as_financial_method() -> None:
    provider = FakeModelProvider()
    dossier = {
        "paper": {
            "title": "Directional-Shift Dirichlet ARMA Models",
            "abstract": (
                "Policy changes and market disruptions can create structural breaks. "
                "The model produces coherent probabilistic forecasts through scenarios."
            ),
        },
        "evidence_count": 8,
        "evidence_items": [{"id": idx, "kind": "method"} for idx in range(1, 9)],
    }
    reports = [
        {
            "role": role,
            "recommendation": "support_deep_dive",
            "score": 8.0,
            "evidence_item_ids": [1, 2],
        }
        for role in ("relevance", "methods", "evidence", "practitioner", "transferability")
    ]

    result = provider.handling_editor(dossier, reports)

    assert result.decision == "full_deep_dive"
    assert result.publication_track == "applied_note"


def test_fake_handling_editor_routes_scenario_evaluation_to_applied_note() -> None:
    provider = FakeModelProvider()
    dossier = {
        "paper": {
            "title": "Alternative Scenarios at the Federal Reserve",
            "abstract": (
                "Historical scenario evaluation and interpretation for central bank policy."
            ),
        },
        "evidence_count": 8,
        "evidence_items": [{"id": idx, "kind": "dataset"} for idx in range(1, 9)],
    }
    reports = [
        {
            "role": role,
            "recommendation": "support_deep_dive",
            "score": 8.0,
            "evidence_item_ids": [1, 2],
        }
        for role in ("relevance", "methods", "evidence", "practitioner", "transferability")
    ]

    result = provider.handling_editor(dossier, reports)

    assert result.decision == "short_mention"
    assert result.publication_track == "applied_note"


def test_fake_handling_editor_caps_financial_method_paper() -> None:
    provider = FakeModelProvider()
    dossier = {
        "paper": {
            "title": "Multi-Scale Markov Switching GARCH",
            "abstract": "We forecast volatility regimes in financial time series.",
        },
        "evidence_count": 8,
        "evidence_items": [{"id": idx, "kind": "method"} for idx in range(1, 9)],
    }
    reports = [
        {
            "role": role,
            "recommendation": "support_deep_dive",
            "score": 8.0,
            "evidence_item_ids": [1, 2],
        }
        for role in ("relevance", "methods", "evidence", "practitioner", "transferability")
    ]

    result = provider.handling_editor(dossier, reports)

    assert result.decision == "needs_human_adjudication"
    assert result.publication_track == "reject"
    assert "Applied forecasting fit is limited" in result.questions_for_human[-1]


def test_fake_reviewer_does_not_block_high_score_for_two_missing_kinds() -> None:
    provider = FakeModelProvider()
    dossier = {
        "paper": {"title": "Scenario evaluation"},
        "evidence_items": [
            {"id": 1, "kind": "dataset"},
            {"id": 2, "kind": "metric"},
        ],
    }

    result = provider.review("practitioner", dossier)

    assert result.recommendation == "support_short_mention"


def test_get_model_provider_returns_openai_provider_with_configured_models() -> None:
    provider = get_model_provider(
        "openai",
        triage_model="gpt-test-triage",
        review_model="gpt-test-review",
        prompt_version="test-v1",
    )

    assert isinstance(provider, OpenAIModelProvider)
    assert provider.triage_model == "gpt-test-triage"
    assert provider.review_model == "gpt-test-review"


def test_openai_provider_parses_structured_triage_output_and_usage() -> None:
    client = _StubOpenAIClient(
        [
            {
                "decision": "assign_reviewers",
                "category_hint": "directly_relevant",
                "forecasting_signal": "explicit",
                "economic_signal": "explicit",
                "score": 8.5,
                "confidence": 0.82,
                "reason": "Applied macro forecasting task.",
            }
        ]
    )
    provider = OpenAIModelProvider(
        triage_model="gpt-test-triage",
        review_model="gpt-test-review",
        client=client,
    )

    result = provider.triage(
        "Inflation nowcasting",
        "We nowcast inflation using macroeconomic indicators.",
        "NEP Forecasting",
    )

    assert result.decision == "assign_reviewers"
    assert result.category_hint == "directly_relevant"
    assert provider.last_usage().input_tokens == 123
    assert client.responses.calls[0]["model"] == "gpt-test-triage"
    assert client.responses.calls[0]["text"]["format"]["name"] == "ets4_triage"


def test_openai_provider_parses_reviewer_and_editor_outputs() -> None:
    client = _StubOpenAIClient(
        [
            {
                "role": "evidence",
                "recommendation": "support_short_mention",
                "score": 6.5,
                "confidence": 0.7,
                "summary": "Evidence supports a limited applied note.",
                "strengths": ["Uses a clear forecast metric."],
                "weaknesses": ["Baseline comparison is thin."],
                "required_evidence": ["metric", "baseline"],
                "evidence_item_ids": [1, 2],
                "questions_for_editor": ["Check baseline detail."],
            },
            {
                "decision": "short_mention",
                "publication_track": "applied_note",
                "deep_dive_score": 6.2,
                "confidence": 0.68,
                "rationale": "Useful but not a main feature.",
                "majority_view": "Most reviewers support short mention.",
                "minority_view": "No material minority recommendation.",
                "evidence_item_ids": [1, 2],
                "questions_for_human": ["Verify practical value."],
            },
        ]
    )
    provider = OpenAIModelProvider(client=client)
    dossier = {
        "paper": {"title": "Inflation nowcasting"},
        "evidence_count": 2,
        "evidence_items": [
            {"id": 1, "kind": "metric", "text": "RMSE improves."},
            {"id": 2, "kind": "baseline", "text": "AR benchmark."},
        ],
    }

    report = provider.review("evidence", dossier)
    decision = provider.handling_editor(dossier, [report.to_dict()])

    assert report.role == "evidence"
    assert report.evidence_item_ids == (1, 2)
    assert decision.decision == "short_mention"
    assert decision.publication_track == "applied_note"
    assert len(client.responses.calls) == 2


class _StubOpenAIClient:
    def __init__(self, payloads: list[dict]) -> None:
        self.responses = _StubResponses(payloads)


class _StubResponses:
    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = list(payloads)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        payload = self._payloads.pop(0)
        return SimpleNamespace(
            output_text=json.dumps(payload),
            usage=SimpleNamespace(input_tokens=123, output_tokens=45, total_tokens=168),
        )
