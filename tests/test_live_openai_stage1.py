from __future__ import annotations

import os
from pathlib import Path

import pytest

from ets4.config import ReviewSettings
from ets4.domain.schemas import EditorPanelDesign
from ets4.ingestion.pdf import ManuscriptIngestor
from ets4.prompts.renderer import PromptRepository
from ets4.providers.base import StageRequest
from ets4.providers.openai import OpenAIProvider

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    os.environ.get("ETS4_RUN_LIVE_OPENAI") != "1",
    reason="set ETS4_RUN_LIVE_OPENAI=1 to authorize the paid Stage 1 smoke test",
)
def test_live_openai_initial_editor_with_small_pdf(
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
            stage="initial_editor",
            agent_id="initial-editor",
            model="gpt-5.6",
            prompt=PromptRepository().render_initial_editor(2),
            manuscript=manuscript,
            response_model=EditorPanelDesign,
            metadata={"referee_count": 2},
        )
    )

    assert result.parsed.requested_referee_count == 2
    assert len(result.parsed.referee_profiles) == 2
    assert result.response_id
