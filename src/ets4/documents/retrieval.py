from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .resolver import resolve_document_uri


@dataclass(frozen=True)
class RetrievedDocument:
    source_uri: str
    content: bytes
    content_type: str


class DocumentRetrievalError(RuntimeError):
    pass


def retrieve_document(source_uri: str) -> RetrievedDocument:
    source_uri = resolve_document_uri(source_uri)
    parsed = urlparse(source_uri)
    if parsed.scheme in ("http", "https"):
        return _retrieve_http(source_uri)
    if parsed.scheme == "file":
        return _retrieve_file(Path(unquote(parsed.path)), source_uri)
    return _retrieve_file(Path(source_uri), source_uri)


def _retrieve_http(source_uri: str) -> RetrievedDocument:
    response = _get(source_uri)
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    inferred = content_type or infer_content_type(source_uri, response.content)
    if inferred == "text/html":
        pdf_uri = _find_pdf_link(source_uri, response.text)
        if pdf_uri:
            pdf_response = _get(pdf_uri)
            pdf_content_type = pdf_response.headers.get("content-type", "").split(";")[0].strip()
            return RetrievedDocument(
                source_uri=pdf_uri,
                content=pdf_response.content,
                content_type=pdf_content_type
                or infer_content_type(pdf_uri, pdf_response.content),
            )
    return RetrievedDocument(
        source_uri=source_uri,
        content=response.content,
        content_type=inferred,
    )


def _get(source_uri: str) -> requests.Response:
    try:
        response = requests.get(source_uri, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DocumentRetrievalError(str(exc)) from exc
    return response


def _find_pdf_link(source_uri: str, html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    scored_links: list[tuple[int, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        text = " ".join(anchor.get_text(" ", strip=True).lower().split())
        href_lower = href.lower()
        score = 0
        if href_lower.endswith(".pdf") or ".pdf?" in href_lower:
            score += 5
        if "pdf" in text:
            score += 3
        if "full paper" in text or "download" in text:
            score += 2
        if score:
            scored_links.append((score, urljoin(source_uri, href)))
    if not scored_links:
        return None
    scored_links.sort(key=lambda item: (-item[0], item[1]))
    return scored_links[0][1]


def _retrieve_file(path: Path, source_uri: str) -> RetrievedDocument:
    if not path.exists():
        raise DocumentRetrievalError(f"Document not found: {path}")
    if not path.is_file():
        raise DocumentRetrievalError(f"Document is not a file: {path}")
    content = path.read_bytes()
    return RetrievedDocument(
        source_uri=source_uri,
        content=content,
        content_type=infer_content_type(str(path), content),
    )


def infer_content_type(source_uri: str, content: bytes) -> str:
    suffix = Path(urlparse(source_uri).path).suffix.lower()
    if content.startswith(b"%PDF") or suffix == ".pdf":
        return "application/pdf"
    stripped = content[:2048].lstrip().lower()
    if suffix in (".html", ".htm") or stripped.startswith(b"<!doctype html") or stripped.startswith(b"<html"):
        return "text/html"
    if suffix in (".txt", ".md", ".text"):
        return "text/plain"
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return "application/octet-stream"
    return "text/plain"
