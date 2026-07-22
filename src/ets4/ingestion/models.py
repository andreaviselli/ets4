"""Provider-neutral manuscript package."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ManuscriptPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    text: str
    section_hint: str | None = None


class ManuscriptMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    source_kind: str
    resolved_url: str | None = None
    filename: str
    media_type: str = "application/pdf"
    sha256: str
    byte_size: int
    page_count: int
    text_character_count: int
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    encrypted: bool = False
    extraction_engine: str = "PyMuPDF"


@dataclass(frozen=True, slots=True)
class ManuscriptPackage:
    """The canonical PDF plus complete, page-preserving normalized text."""

    pdf_bytes: bytes
    metadata: ManuscriptMetadata
    pages: tuple[ManuscriptPage, ...]

    @property
    def paginated_text(self) -> str:
        return "\n\n".join(f"[Page {page.page_number}]\n{page.text}" for page in self.pages)

    @property
    def estimated_text_tokens(self) -> int:
        return max(1, len(self.paginated_text) // 4)
