"""Single typed rendering boundary for all stage prompts."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from ets4.domain.schemas import RefereeProfile

PROMPT_VERSION = "1.1.0"
StageName = Literal["initial_editor", "referee", "final_editor"]


class PromptRenderingError(ValueError):
    """Raised when a prompt template or rendering context is incomplete."""


class InitialEditorContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    referee_count: int = Field(ge=1, le=12)


class RefereeContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: RefereeProfile


class FinalEditorContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    referee_count: int = Field(ge=1, le=12)


class _StrictFormatMap(dict[str, Any]):
    def __missing__(self, key: str) -> Any:
        raise PromptRenderingError(f"prompt rendering context is missing: {key}")


class PromptRepository:
    """Load immutable packaged prompt assets and render them in one place."""

    def __init__(self, version: str = PROMPT_VERSION) -> None:
        self.version = version
        self._root = files("ets4.prompts").joinpath("templates")

    def versions(self) -> dict[str, str]:
        return {
            "initial_editor": self.version,
            "referee": self.version,
            "final_editor": self.version,
        }

    def metadata(self, stage: StageName) -> dict[str, Any]:
        resource = self._root.joinpath(stage, f"{self.version}.json")
        try:
            value = json.loads(resource.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise PromptRenderingError("prompt metadata must be a JSON object")
            return cast(dict[str, Any], value)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise PromptRenderingError(
                f"invalid prompt metadata for {stage} {self.version}"
            ) from exc

    def _template(self, stage: StageName) -> str:
        resource = self._root.joinpath(stage, f"{self.version}.txt")
        try:
            return resource.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise PromptRenderingError(
                f"missing prompt template for {stage} {self.version}"
            ) from exc

    def render_initial_editor(self, referee_count: int) -> str:
        context = InitialEditorContext(referee_count=referee_count)
        return self._template("initial_editor").format_map(
            _StrictFormatMap(referee_count=context.referee_count)
        )

    def render_referee(self, profile: RefereeProfile) -> str:
        context = RefereeContext(profile=profile)
        values = {
            "referee_id": context.profile.referee_id,
            "functional_slot": context.profile.functional_slot,
            "research_orientation": context.profile.research_orientation,
            "primary_expertise": context.profile.primary_expertise,
            "specialist_topics": "\n".join(
                f"- {topic}" for topic in context.profile.specialist_topics
            ),
            "primary_audit_mandate": context.profile.primary_audit_mandate,
            "unique_contribution": context.profile.unique_contribution,
            "non_authority_areas": "\n".join(
                f"- {area}" for area in context.profile.non_authority_areas
            ),
        }
        return self._template("referee").format_map(_StrictFormatMap(values))

    def render_final_editor(self, referee_count: int) -> str:
        context = FinalEditorContext(referee_count=referee_count)
        return self._template("final_editor").format_map(
            _StrictFormatMap(referee_count=context.referee_count)
        )
