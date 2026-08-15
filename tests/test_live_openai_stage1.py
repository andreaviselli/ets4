from __future__ import annotations

import os
from pathlib import Path

import pytest

from ets4.config import ReviewSettings
from ets4.domain.schemas import ReviewRequirementDiscovery
from ets4.ingestion.pdf import ManuscriptIngestor
from ets4.prompts.renderer import PromptRepository
from ets4.providers.base import StageRequest
from ets4.providers.openai import OpenAIProvider

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    os.environ.get("ETS4_RUN_LIVE_OPENAI") != "1",
    reason="set ETS4_RUN_LIVE_OPENAI=1 to authorize the paid Stage 1 smoke test",
)
def test_live_openai_requirement_discovery_with_small_pdf(
    manuscript_path: Path,
) -> None:
    settings = ReviewSettings(
        provider="openai",
        model="gpt-5.6",
        referee_count=2,
        max_provider_retries=0,
        max_repair_attempts=0,
        retain_raw_responses=False,
        store_provider_responses=False,
    )
    manuscript = ManuscriptIngestor(settings).ingest(manuscript_path)
    provider = OpenAIProvider(settings)
    provider.preflight(manuscript)
    result = provider.generate(
        StageRequest(
            stage="requirement_discovery",
            agent_id="initial-editor-requirements",
            model="gpt-5.6",
            prompt=PromptRepository().render_requirement_discovery(3),
            manuscript=manuscript,
            response_model=ReviewRequirementDiscovery,
            metadata={"review_requirement_count": 3},
        )
    )

    assert len(result.parsed.manuscript_review_map) == 3
    assert result.response_id
