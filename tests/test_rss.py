from datetime import datetime, timezone
from pathlib import Path

from ets4.collect.rss import parse_rss_content
from ets4.config import SourceConfig


def test_parse_rss_fixture_extracts_identifiers() -> None:
    source = SourceConfig(
        id="fixture",
        name="Fixture",
        type="rss",
        url="https://example.test/rss.xml",
        lookback_days=30,
    )
    content = Path("tests/fixtures/rss/sample.xml").read_text()

    candidates = parse_rss_content(
        source,
        content,
        now=datetime(2026, 6, 4, tzinfo=timezone.utc),
    )

    assert len(candidates) == 2
    assert candidates[0].canonical_url == "https://arxiv.org/abs/2601.12345"
    assert candidates[0].doi == "10.1234/ets4.2026.001"
    assert candidates[0].arxiv_id == "2601.12345"
    assert "forecast inflation" in candidates[0].abstract.lower()

