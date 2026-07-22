"""Narrow provider contract used by the workflow orchestrator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from ets4.ingestion.models import ManuscriptPackage

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)
ProviderErrorDetails = dict[str, str | int | None]


class ProviderError(RuntimeError):
    """Provider failure with retry classification and optional raw response."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        raw_response: Any | None = None,
        details: ProviderErrorDetails | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.raw_response = raw_response
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    provider_name: str
    structured_outputs: bool
    native_pdf_input: bool
    paginated_text_fallback: bool
    supports_reasoning_effort: bool
    supports_store_control: bool


@dataclass(frozen=True, slots=True)
class StageRequest(Generic[StructuredModel]):
    stage: str
    agent_id: str
    model: str
    prompt: str
    manuscript: ManuscriptPackage
    response_model: type[StructuredModel]
    supplemental_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderResult(Generic[StructuredModel]):
    parsed: StructuredModel
    raw_response: Any
    response_id: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)


class Provider(ABC):
    """A stateless structured-generation boundary; each call is an isolated execution."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @property
    def runtime_metadata(self) -> dict[str, str]:
        return {"provider": self.capabilities.provider_name}

    @abstractmethod
    def preflight(self, manuscript: ManuscriptPackage) -> None:
        """Reject unsupported inputs before any paid stage call."""

    @abstractmethod
    def generate(self, request: StageRequest[StructuredModel]) -> ProviderResult[StructuredModel]:
        """Generate and validate one isolated stage output."""
