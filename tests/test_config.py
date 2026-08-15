from __future__ import annotations

from pathlib import Path

import pytest

from ets4.config import (
    ConfigurationError,
    ReviewSettings,
    load_settings,
    validate_provider_environment,
)
from ets4.limits import MAX_REVIEW_REQUIREMENTS


def test_configuration_precedence_and_no_secret_persistence(tmp_path: Path) -> None:
    config = tmp_path / "ets4.toml"
    config.write_text(
        "[review]\nreferee_count = 2\n[provider]\nprovider = 'mock'\nmodel = 'file-model'\n",
        encoding="utf-8",
    )
    settings = load_settings(
        config,
        {"referee_count": 5},
        {"ETS4_MODEL": "environment-model", "OPENAI_API_KEY": "sk-secret-value"},
    )
    assert settings.referee_count == 5
    assert settings.model == "environment-model"
    serialized = str(settings.manifest_dict())
    assert "sk-secret-value" not in serialized
    assert "OPENAI_API_KEY" not in serialized


def test_referee_count_cannot_exceed_configured_ceiling() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        ReviewSettings(referee_count=9, max_referees=8)


def test_review_requirement_count_supports_auto_exact_and_a_visible_maximum(
    tmp_path: Path,
) -> None:
    assert ReviewSettings().review_requirement_count is None
    assert ReviewSettings(review_requirement_count=3).review_requirement_count == 3
    with pytest.raises(ValueError):
        ReviewSettings(review_requirement_count=MAX_REVIEW_REQUIREMENTS + 1)

    config = tmp_path / "ets4.toml"
    config.write_text(
        "[review]\nreview_requirement_count = 4\n",
        encoding="utf-8",
    )
    assert load_settings(config).review_requirement_count == 4
    automatic = load_settings(config, {"review_requirement_count": "auto"})
    assert automatic.review_requirement_count is None
    assert (
        load_settings(
            config,
            environ={"ETS4_REVIEW_REQUIREMENT_COUNT": "2"},
        ).review_requirement_count
        == 2
    )


def test_openai_preflight_requires_environment_key() -> None:
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        validate_provider_environment(ReviewSettings(provider="openai"), environ={})


def test_api_key_is_not_an_accepted_configuration_field() -> None:
    with pytest.raises(ValueError):
        ReviewSettings.model_validate({"provider": "openai", "api_key": "secret"})
