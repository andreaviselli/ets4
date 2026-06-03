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

