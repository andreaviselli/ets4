"""Provider construction and user-visible capability registry."""

from __future__ import annotations

from typing import Any

from ets4.config import ReviewSettings
from ets4.providers.base import Provider
from ets4.providers.mock import MockProvider
from ets4.providers.openai import OpenAIProvider


def build_provider(settings: ReviewSettings, *, client: Any | None = None) -> Provider:
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "openai":
        return OpenAIProvider(settings, client=client)
    raise ValueError(f"unsupported provider: {settings.provider}")


def provider_descriptions() -> list[dict[str, object]]:
    return [
        {
            "name": "mock",
            "paid": False,
            "native_pdf": True,
            "structured_outputs": True,
            "purpose": "deterministic workflow and test execution; not substantive review",
        },
        {
            "name": "openai",
            "paid": True,
            "native_pdf": True,
            "structured_outputs": True,
            "api": "Responses API",
            "credential_environment_variable": "OPENAI_API_KEY",
        },
    ]
