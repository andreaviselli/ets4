from pathlib import Path

from ets4.config import load_config


def test_load_example_config() -> None:
    config = load_config(Path("config/feeds.example.toml"))

    assert config.issue.max_papers_to_full_review == 20
    assert config.issue.max_deep_dive_drafts == 3
    assert config.model_policy.provider == "fake"
    assert len(config.sources) == 3
    assert config.sources[0].id == "nep-for"

