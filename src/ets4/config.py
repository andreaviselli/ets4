"""Configuration loading with defaults < TOML < environment < CLI precedence."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ets4.limits import HARD_MAX_REFEREES, MAX_REVIEW_REQUIREMENTS


class ConfigurationError(ValueError):
    """Raised when run configuration is unsafe or internally inconsistent."""


class ReviewSettings(BaseModel):
    """Behaviorally relevant settings persisted in each run manifest."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["mock", "openai"] = "mock"
    model: str = "gpt-5.6"
    initial_editor_model: str | None = None
    referee_model: str | None = None
    final_editor_model: str | None = None
    referee_count: int = Field(default=4, ge=1)
    review_requirement_count: int | None = Field(
        default=None, ge=1, le=MAX_REVIEW_REQUIREMENTS
    )
    max_referees: int = Field(default=8, ge=1, le=HARD_MAX_REFEREES)
    max_concurrency: int = Field(default=4, ge=1, le=HARD_MAX_REFEREES)
    max_provider_retries: int = Field(default=2, ge=0, le=5)
    max_repair_attempts: int = Field(default=1, ge=0, le=3)
    request_timeout_seconds: float = Field(default=600.0, gt=0, le=3600)
    max_file_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    max_pdf_pages: int = Field(default=500, ge=1, le=5000)
    min_text_characters: int = Field(default=200, ge=1)
    model_context_tokens: int = Field(default=1_000_000, ge=8192)
    max_output_tokens: int = Field(default=16_000, ge=512)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "high"
    pdf_detail: Literal["auto", "low", "high"] = "high"
    retain_raw_responses: bool = True
    store_provider_responses: bool = False
    openai_base_url: str | None = None
    output_dir: Path = Path("runs")

    @model_validator(mode="after")
    def validate_limits(self) -> ReviewSettings:
        if self.referee_count > self.max_referees:
            raise ValueError(
                f"referee_count={self.referee_count} exceeds max_referees={self.max_referees}"
            )
        if self.max_output_tokens >= self.model_context_tokens:
            raise ValueError("max_output_tokens must be smaller than model_context_tokens")
        return self

    def model_for_stage(self, stage: str) -> str:
        overrides = {
            "initial_editor": self.initial_editor_model,
            "referee": self.referee_model,
            "final_editor": self.final_editor_model,
        }
        return overrides.get(stage) or self.model

    def manifest_dict(self) -> dict[str, Any]:
        """Return only non-secret, JSON-compatible configuration."""

        return self.model_dump(mode="json")


ENV_FIELDS: dict[str, str] = {
    "ETS4_PROVIDER": "provider",
    "ETS4_MODEL": "model",
    "ETS4_INITIAL_EDITOR_MODEL": "initial_editor_model",
    "ETS4_REFEREE_MODEL": "referee_model",
    "ETS4_FINAL_EDITOR_MODEL": "final_editor_model",
    "ETS4_REFEREE_COUNT": "referee_count",
    "ETS4_REVIEW_REQUIREMENT_COUNT": "review_requirement_count",
    "ETS4_MAX_REFEREES": "max_referees",
    "ETS4_MAX_CONCURRENCY": "max_concurrency",
    "ETS4_MAX_PROVIDER_RETRIES": "max_provider_retries",
    "ETS4_REQUEST_TIMEOUT_SECONDS": "request_timeout_seconds",
    "ETS4_OUTPUT_DIR": "output_dir",
    "ETS4_OPENAI_BASE_URL": "openai_base_url",
    "ETS4_RETAIN_RAW_RESPONSES": "retain_raw_responses",
    "ETS4_STORE_PROVIDER_RESPONSES": "store_provider_responses",
}


def _coerce_environment_value(field: str, value: str) -> Any:
    if field == "review_requirement_count":
        if value.strip().lower() == "auto":
            return None
        return int(value)
    if field in {
        "referee_count",
        "max_referees",
        "max_concurrency",
        "max_provider_retries",
    }:
        return int(value)
    if field == "request_timeout_seconds":
        return float(value)
    if field in {"retain_raw_responses", "store_provider_responses"}:
        normalized = value.strip().lower()
        if normalized not in {"1", "0", "true", "false", "yes", "no"}:
            raise ConfigurationError(f"{field} must be true or false")
        return normalized in {"1", "true", "yes"}
    return value


def load_settings(
    config_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    environ: dict[str, str] | None = None,
) -> ReviewSettings:
    """Load settings using documented precedence without ever reading an API key."""

    values: dict[str, Any] = {}
    if config_path is not None:
        try:
            with config_path.open("rb") as handle:
                document = tomllib.load(handle)
        except OSError as exc:
            raise ConfigurationError(f"cannot read configuration file: {config_path}") from exc
        unknown_sections = set(document) - {"review", "provider", "retention"}
        if unknown_sections:
            raise ConfigurationError(
                "unknown configuration section(s): " + ", ".join(sorted(unknown_sections))
            )
        values.update(document.get("review", {}))
        values.update(document.get("provider", {}))
        values.update(document.get("retention", {}))

    source_environment = environ if environ is not None else os.environ
    for variable, field in ENV_FIELDS.items():
        if variable in source_environment:
            values[field] = _coerce_environment_value(field, source_environment[variable])

    if cli_overrides:
        values.update({key: value for key, value in cli_overrides.items() if value is not None})

    requirement_count = values.get("review_requirement_count")
    if isinstance(requirement_count, str):
        if requirement_count.strip().lower() == "auto":
            values["review_requirement_count"] = None
        else:
            try:
                values["review_requirement_count"] = int(requirement_count)
            except ValueError as exc:
                raise ConfigurationError(
                    "review_requirement_count must be 'auto' or a positive integer"
                ) from exc

    try:
        return ReviewSettings.model_validate(values)
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc


def validate_provider_environment(
    settings: ReviewSettings, environ: dict[str, str] | None = None
) -> None:
    """Fail before a paid run when required credentials are unavailable."""

    source_environment = environ if environ is not None else os.environ
    if settings.provider == "openai" and not source_environment.get("OPENAI_API_KEY"):
        raise ConfigurationError("OPENAI_API_KEY is required for provider=openai")
