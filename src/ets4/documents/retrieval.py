from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests


@dataclass(frozen=True)
class RetrievedDocument:
    source_uri: str
    content: bytes
    content_type: str


class DocumentRetrievalError(RuntimeError):
    pass


def retrieve_document(source_uri: str) -> RetrievedDocument:
    parsed = urlparse(source_uri)
    if parsed.scheme in ("http", "https"):
        return _retrieve_http(source_uri)
    if parsed.scheme == "file":
        return _retrieve_file(Path(unquote(parsed.path)), source_uri)
    return _retrieve_file(Path(source_uri), source_uri)


def _retrieve_http(source_uri: str) -> RetrievedDocument:
    try:
        response = requests.get(source_uri, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DocumentRetrievalError(str(exc)) from exc
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    return RetrievedDocument(
        source_uri=source_uri,
        content=response.content,
        content_type=content_type or infer_content_type(source_uri, response.content),
    )


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
    if suffix in (".txt", ".md", ".text"):
        return "text/plain"
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return "application/octet-stream"
    return "text/plain"

