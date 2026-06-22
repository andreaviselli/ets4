from ets4.models import FakeModelProvider


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


def test_fake_provider_rejects_trading_risk_without_applied_economic_fit() -> None:
    provider = FakeModelProvider()

    result = provider.triage(
        "Forecasting Value at Risk and Expected Shortfall in Equity Markets",
        "We forecast downside risk for equity trading portfolios.",
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

    assert result.decision == "watchlist"
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
