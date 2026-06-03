from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


class DocumentExtractionError(RuntimeError):
    pass


def extract_pages(content: bytes, content_type: str) -> list[PageText]:
    if content_type == "application/pdf":
        return _extract_pdf_pages(content)
    if content_type.startswith("text/") or content_type == "text/plain":
        return _extract_text_pages(content)
    raise DocumentExtractionError(f"Unsupported document type: {content_type}")


def _extract_text_pages(content: bytes) -> list[PageText]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("Text document is not valid UTF-8") from exc
    parts = text.split("\f")
    return [
        PageText(page_number=index, text=part.strip())
        for index, part in enumerate(parts, start=1)
        if part.strip()
    ]


def _extract_pdf_pages(content: bytes) -> list[PageText]:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - dependency declared in pyproject
        raise DocumentExtractionError("PyMuPDF is required for PDF extraction") from exc

    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            return [
                PageText(page_number=index, text=page.get_text().strip())
                for index, page in enumerate(doc, start=1)
                if page.get_text().strip()
            ]
    except Exception as exc:
        raise DocumentExtractionError(f"PDF extraction failed: {exc}") from exc

