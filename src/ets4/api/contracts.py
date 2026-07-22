"""Provider-independent request/response contracts for a future asynchronous backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateReviewRequest(ApiModel):
    manuscript_url: HttpUrl | None = None
    upload_token: str | None = None
    provider: Literal["openai", "mock"] = "openai"
    model: str
    referee_count: int = Field(default=4, ge=1, le=12)

    @model_validator(mode="after")
    def require_exactly_one_manuscript_source(self) -> CreateReviewRequest:
        if (self.manuscript_url is None) == (self.upload_token is None):
            raise ValueError("provide exactly one of manuscript_url or upload_token")
        return self


class CreateReviewResponse(ApiModel):
    run_id: str
    status_url: str


class ReviewStatusResponse(ApiModel):
    run_id: str
    workflow_state: str
    completed_stages: list[str]
    failed_stages: list[str]
    resumable: bool


class ArtifactDescriptor(ApiModel):
    name: str
    media_type: str
    sha256: str
    download_url: str
