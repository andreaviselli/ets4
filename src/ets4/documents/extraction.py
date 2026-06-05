from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


class DocumentExtractionError(RuntimeError):
    pass


def extract_pages(content: bytes, content_type: str) -> list[PageText]:
    if content_type == "application/pdf":
        return _extract_pdf_pages(content)
    if content_type == "text/html":
        return _extract_html_pages(content)
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


def _extract_html_pages(content: bytes) -> list[PageText]:
    try:
        html = content.decode("utf-8")
    except UnicodeDecodeError:
        html = content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "header", "footer", "form", "noscript"]):
        element.decompose()

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find("body")
        or soup
    )
    text = main.get_text(separator="\n", strip=True)
    lines = [_clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if _keep_html_line(line)]
    cleaned = "\n".join(lines)
    if not cleaned:
        raise DocumentExtractionError("HTML document did not contain readable text")
    return _split_text_into_pages(cleaned)


def _split_text_into_pages(text: str, *, page_chars: int = 6000) -> list[PageText]:
    chunks = []
    current: list[str] = []
    current_len = 0
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if current and current_len + len(paragraph) > page_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += len(paragraph)
    if current:
        chunks.append("\n".join(current))
    return [
        PageText(page_number=index, text=chunk)
        for index, chunk in enumerate(chunks, start=1)
    ]


def _clean_line(line: str) -> str:
    return " ".join(line.split())


def _keep_html_line(line: str) -> bool:
    if len(line) < 30:
        return False
    lowered = line.lower()
    boilerplate = (
        "javascript",
        "cookie",
        "privacy policy",
        "search",
        "download",
        "bookmark",
        "share",
        "navigation",
    )
    return not any(term in lowered for term in boilerplate)


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
