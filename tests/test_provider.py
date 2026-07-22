from __future__ import annotations

from typing import Any

import httpx
import pytest
from openai import BadRequestError
from openai.lib._parsing._responses import type_to_text_format_param
from pydantic import BaseModel, ConfigDict

from ets4.config import ReviewSettings
from ets4.domain.schemas import EditorPanelDesign, FinalEditorDecision, RefereeReport
from ets4.prompts.renderer import PromptRepository
from ets4.providers.base import ProviderError, StageRequest
from ets4.providers.mock import MockProvider
from ets4.providers.openai import OpenAIProvider


class FakeUsage:
    def model_dump(self, **_kwargs: object) -> dict[str, int]:
        return {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}


class FakeOpenAIResponse:
    def __init__(self, parsed: EditorPanelDesign) -> None:
        self.id = "resp-test"
        self.output_parsed = parsed
        self.usage = FakeUsage()
        self.model_dump_kwargs: dict[str, object] | None = None

    def model_dump(self, **kwargs: object) -> dict[str, object]:
        self.model_dump_kwargs = kwargs
        return {"id": self.id, "output": self.output_parsed.model_dump(mode="json")}


class FakeResponses:
    def __init__(self, parsed: EditorPanelDesign) -> None:
        self.parsed = parsed
        self.arguments: dict[str, Any] | None = None
        self.response: FakeOpenAIResponse | None = None

    def parse(self, **kwargs: Any) -> FakeOpenAIResponse:
        self.arguments = kwargs
        self.response = FakeOpenAIResponse(self.parsed)
        return self.response


class FakeClient:
    def __init__(self, parsed: EditorPanelDesign) -> None:
        self.responses = FakeResponses(parsed)


class RaisingResponses:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def parse(self, **_kwargs: Any) -> None:
        raise self.error


class RaisingClient:
    def __init__(self, error: Exception) -> None:
        self.responses = RaisingResponses(error)


class DynamicMapOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage: dict[str, str]


def test_openai_adapter_uses_responses_structured_output_and_native_pdf(manuscript) -> None:
    prompt = PromptRepository().render_initial_editor(2)
    mock_request = StageRequest(
        stage="initial_editor",
        agent_id="initial-editor",
        model="mock",
        prompt=prompt,
        manuscript=manuscript,
        response_model=EditorPanelDesign,
        metadata={"referee_count": 2},
    )
    panel = MockProvider().generate(mock_request).parsed
    client = FakeClient(panel)
    settings = ReviewSettings(provider="openai", referee_count=2, model="gpt-5.6")
    provider = OpenAIProvider(settings, client=client)
    provider.preflight(manuscript)
    result = provider.generate(
        StageRequest(
            stage="initial_editor",
            agent_id="initial-editor",
            model=settings.model,
            prompt=prompt,
            manuscript=manuscript,
            response_model=EditorPanelDesign,
            metadata={"referee_count": 2},
        )
    )
    assert result.parsed == panel
    arguments = client.responses.arguments
    assert arguments is not None
    assert arguments["text_format"] is EditorPanelDesign
    assert arguments["store"] is False
    assert "tools" not in arguments
    content = arguments["input"][0]["content"]
    file_input = content[0]
    assert file_input["type"] == "input_file"
    assert file_input["file_data"].startswith("data:application/pdf;base64,")
    assert file_input["detail"] == "high"
    assert client.responses.response is not None
    assert client.responses.response.model_dump_kwargs == {
        "mode": "json",
        "warnings": False,
    }


def test_provider_preflight_rejects_explicit_context_overflow(manuscript) -> None:
    settings = ReviewSettings(
        provider="openai",
        model_context_tokens=8192,
        max_output_tokens=7000,
    )
    provider = OpenAIProvider(settings, client=FakeClient(None))  # type: ignore[arg-type]
    try:
        provider.preflight(manuscript)
    except Exception as exc:
        assert "complete manuscript" in str(exc)
    else:
        raise AssertionError("context overflow should fail before a paid request")


def test_bad_request_preserves_only_sanitized_diagnostics_and_is_not_retryable(
    manuscript,
) -> None:
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/responses",
        headers={"Authorization": "Bearer sk-never-log-this-secret"},
    )
    response = httpx.Response(
        400,
        request=request,
        headers={"x-request-id": "req_diagnostic_123"},
    )
    error = BadRequestError(
        "do not persist the SDK-rendered response or request",
        response=response,
        body={
            "message": "Invalid schema containing api_key=topsecret",
            "code": "invalid_json_schema",
            "param": "text.format.schema",
            "type": "invalid_request_error",
        },
    )
    settings = ReviewSettings(provider="openai", referee_count=2)
    provider = OpenAIProvider(settings, client=RaisingClient(error))
    prompt = PromptRepository().render_initial_editor(2)

    with pytest.raises(ProviderError) as caught:
        provider.generate(
            StageRequest(
                stage="initial_editor",
                agent_id="initial-editor",
                model=settings.model,
                prompt=prompt,
                manuscript=manuscript,
                response_model=EditorPanelDesign,
            )
        )

    failure = caught.value
    assert failure.retryable is False
    assert failure.details == {
        "provider": "openai",
        "exception_type": "BadRequestError",
        "message": "Invalid schema containing api_key=[REDACTED]",
        "code": "invalid_json_schema",
        "parameter": "text.format.schema",
        "status": 400,
        "request_id": "req_diagnostic_123",
    }
    serialized = str(failure.details)
    assert "topsecret" not in serialized
    assert "never-log-this-secret" not in serialized
    assert "Authorization" not in serialized


def test_dynamic_key_schema_is_rejected_locally_before_any_paid_call(manuscript) -> None:
    client = FakeClient(None)  # type: ignore[arg-type]
    provider = OpenAIProvider(ReviewSettings(provider="openai"), client=client)

    with pytest.raises(ProviderError) as caught:
        provider.generate(
            StageRequest(
                stage="schema_regression",
                agent_id="schema-regression",
                model="gpt-5.6",
                prompt="Return the schema.",
                manuscript=manuscript,
                response_model=DynamicMapOutput,
            )
        )

    assert caught.value.retryable is False
    assert caught.value.details["code"] == "unsupported_strict_schema"
    assert caught.value.details["parameter"] == "text.format.schema"
    assert client.responses.arguments is None


@pytest.mark.parametrize(
    "response_model",
    [EditorPanelDesign, RefereeReport, FinalEditorDecision],
)
def test_all_provider_output_schemas_pass_local_strict_compatibility(
    response_model: type[BaseModel],
) -> None:
    OpenAIProvider._validate_strict_schema(response_model)


def test_sdk_serializes_planned_coverage_as_strict_typed_cells() -> None:
    text_format = type_to_text_format_param(EditorPanelDesign)
    schema = text_format["schema"]
    coverage = schema["$defs"]["PlannedCoverageRow"]["properties"]["coverage"]
    requirement = schema["$defs"]["ManuscriptRequirement"]

    assert coverage["type"] == "array"
    assert "additionalProperties" not in coverage
    assert set(requirement["required"]) == set(requirement["properties"])
    assert "default" not in requirement["properties"]["central_claim"]
