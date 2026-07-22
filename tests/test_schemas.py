from __future__ import annotations

import pytest
from pydantic import ValidationError

from ets4.domain.schemas import EditorPanelDesign, HarmonizedAnswers, RefereeReport
from ets4.prompts.renderer import PromptRepository
from ets4.providers.base import StageRequest
from ets4.providers.mock import MockProvider


def test_panel_schema_enforces_requested_count_and_matrix_primary(manuscript) -> None:
    provider = MockProvider()
    request = StageRequest(
        stage="initial_editor",
        agent_id="initial-editor",
        model="mock",
        prompt=PromptRepository().render_initial_editor(3),
        manuscript=manuscript,
        response_model=EditorPanelDesign,
        metadata={"referee_count": 3},
    )
    panel = provider.generate(request).parsed
    payload = panel.model_dump(mode="json")
    payload["planned_coverage_matrix"][0]["coverage"] = [
        {"referee_id": "referee-1", "level": "Blank"},
        {"referee_id": "referee-2", "level": "S"},
        {"referee_id": "referee-3", "level": "Blank"},
    ]
    with pytest.raises(ValidationError, match="at least one P"):
        EditorPanelDesign.model_validate(payload)


def test_harmonized_answers_reject_values_outside_enum() -> None:
    with pytest.raises(ValidationError):
        HarmonizedAnswers.model_validate(
            {
                "forecasting_contribution": "Maybe",
                "literature_positioning": "Yes",
                "scientific_soundness": "Yes",
                "forecasting_evaluation": "Yes",
                "conclusions_supported": "Yes",
                "limitations_discussed": "Yes",
                "presentation_and_replication": "Yes",
            }
        )


def test_referee_recommendation_enum_rejects_final_editor_only_value(manuscript) -> None:
    provider = MockProvider()
    panel = provider.generate(
        StageRequest(
            stage="initial_editor",
            agent_id="initial-editor",
            model="mock",
            prompt="panel",
            manuscript=manuscript,
            response_model=EditorPanelDesign,
            metadata={"referee_count": 1},
        )
    ).parsed
    report = provider.generate(
        StageRequest(
            stage="referee",
            agent_id="referee-1",
            model="mock",
            prompt="report",
            manuscript=manuscript,
            response_model=RefereeReport,
        )
    ).parsed.model_dump(mode="json")
    assert panel.requested_referee_count == 1
    report["recommendation"] = "Reject and resubmit"
    with pytest.raises(ValidationError):
        RefereeReport.model_validate(report)
