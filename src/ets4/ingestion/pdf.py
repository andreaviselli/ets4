"""Local and remote PDF ingestion with complete-text validation."""

from __future__ import annotations

import hashlib
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import fitz  # type: ignore[import-untyped]
import requests
from bs4 import BeautifulSoup

from ets4.config import ReviewSettings
from ets4.ingestion.models import ManuscriptMetadata, ManuscriptPackage, ManuscriptPage
from ets4.ingestion.security import Resolver, UnsafeUrlError, validate_public_url


class ManuscriptIngestionError(RuntimeError):
    """Raised when the complete manuscript cannot be safely normalized."""


class ManuscriptIngestor:
    """Retrieve exactly one user-supplied manuscript and normalize every PDF page."""

    def __init__(
        self,
        settings: ReviewSettings,
        *,
        session: requests.Session | Any | None = None,
        resolver: Resolver = socket.getaddrinfo,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.resolver = resolver

    def ingest(self, source: str | Path) -> ManuscriptPackage:
        source_text = str(source)
        if urlsplit(source_text).scheme in {"http", "https"}:
            pdf_bytes, resolved_url, filename = self._retrieve_url(source_text)
            return self._normalize(
                pdf_bytes,
                source=source_text,
                source_kind="url",
                resolved_url=resolved_url,
                filename=filename,
            )

        path = Path(source).expanduser()
        try:
            path = path.resolve(strict=True)
        except OSError as exc:
            raise ManuscriptIngestionError(f"manuscript file does not exist: {path}") from exc
        if not path.is_file():
            raise ManuscriptIngestionError(f"manuscript path is not a file: {path}")
        size = path.stat().st_size
        if size > self.settings.max_file_bytes:
            raise ManuscriptIngestionError(
                f"manuscript exceeds the {self.settings.max_file_bytes}-byte limit"
            )
        try:
            pdf_bytes = path.read_bytes()
        except OSError as exc:
            raise ManuscriptIngestionError(f"cannot read manuscript file: {path}") from exc
        return self._normalize(
            pdf_bytes,
            source=str(path),
            source_kind="local_pdf",
            resolved_url=None,
            filename=path.name,
        )

    def _retrieve_url(self, source_url: str) -> tuple[bytes, str, str]:
        try:
            current_url = validate_public_url(source_url, self.resolver)
        except UnsafeUrlError as exc:
            raise ManuscriptIngestionError(str(exc)) from exc

        landing_resolved = False
        for _ in range(6):
            response = self.session.get(
                current_url,
                allow_redirects=False,
                stream=True,
                timeout=(10.0, min(self.settings.request_timeout_seconds, 120.0)),
                headers={"Accept": "application/pdf,text/html;q=0.8", "User-Agent": "ETS4/0.2"},
            )
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                if not location:
                    raise ManuscriptIngestionError("manuscript redirect did not include Location")
                current_url = self._validated_join(current_url, location)
                continue
            if response.status_code != 200:
                raise ManuscriptIngestionError(
                    f"manuscript retrieval returned HTTP {response.status_code}"
                )

            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            content = self._read_limited_response(response)
            if media_type == "application/pdf" or content.startswith(b"%PDF-"):
                filename = Path(urlsplit(current_url).path).name or "manuscript.pdf"
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"
                return content, current_url, filename

            if media_type not in {"text/html", "application/xhtml+xml"}:
                raise ManuscriptIngestionError(
                    f"manuscript URL returned unsupported content type: {media_type or 'unknown'}"
                )
            if landing_resolved:
                raise ManuscriptIngestionError("landing page did not resolve to a PDF")
            pdf_url = self._resolve_landing_page(current_url, content)
            if pdf_url is None:
                raise ManuscriptIngestionError(
                    "landing page does not expose an explicit canonical manuscript PDF"
                )
            current_url = self._validated_join(current_url, pdf_url)
            landing_resolved = True

        raise ManuscriptIngestionError("too many manuscript redirects")

    def _validated_join(self, base_url: str, location: str) -> str:
        try:
            return validate_public_url(urljoin(base_url, location), self.resolver)
        except UnsafeUrlError as exc:
            raise ManuscriptIngestionError(str(exc)) from exc

    def _read_limited_response(self, response: Any) -> bytes:
        declared_length = response.headers.get("Content-Length")
        if declared_length:
            try:
                parsed_length = int(declared_length)
            except ValueError as exc:
                raise ManuscriptIngestionError(
                    "remote manuscript returned an invalid Content-Length"
                ) from exc
            if parsed_length < 0:
                raise ManuscriptIngestionError(
                    "remote manuscript returned an invalid Content-Length"
                )
            if parsed_length > self.settings.max_file_bytes:
                raise ManuscriptIngestionError(
                    "remote manuscript exceeds configured file-size limit"
                )
        payload = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            payload.extend(chunk)
            if len(payload) > self.settings.max_file_bytes:
                raise ManuscriptIngestionError(
                    "remote manuscript exceeds configured file-size limit"
                )
        return bytes(payload)

    @staticmethod
    def _resolve_landing_page(page_url: str, content: bytes) -> str | None:
        soup = BeautifulSoup(content[:2_000_000], "html.parser")
        meta = soup.find(
            "meta",
            attrs={"name": lambda value: bool(value and value.lower() == "citation_pdf_url")},
        )
        if meta and meta.get("content"):
            return str(meta["content"])
        link = soup.find("link", attrs={"type": "application/pdf"})
        if link and link.get("href"):
            return str(link["href"])

        parsed = urlsplit(page_url)
        if parsed.hostname in {"arxiv.org", "www.arxiv.org"} and parsed.path.startswith("/abs/"):
            identifier = parsed.path.removeprefix("/abs/").strip("/")
            if identifier:
                return f"https://arxiv.org/pdf/{identifier}.pdf"
        return None

    def _normalize(
        self,
        pdf_bytes: bytes,
        *,
        source: str,
        source_kind: str,
        resolved_url: str | None,
        filename: str,
    ) -> ManuscriptPackage:
        if not pdf_bytes.startswith(b"%PDF-"):
            raise ManuscriptIngestionError("manuscript is not a valid PDF file")
        try:
            document = fitz.open(stream=pdf_bytes, filetype="pdf")
        except (fitz.FileDataError, RuntimeError, ValueError) as exc:
            raise ManuscriptIngestionError("manuscript PDF is malformed or unreadable") from exc
        try:
            if document.needs_pass:
                raise ManuscriptIngestionError("encrypted manuscript PDFs are not supported")
            if document.page_count == 0:
                raise ManuscriptIngestionError("manuscript PDF contains no pages")
            if document.page_count > self.settings.max_pdf_pages:
                raise ManuscriptIngestionError(
                    f"manuscript exceeds the {self.settings.max_pdf_pages}-page limit"
                )

            pages: list[ManuscriptPage] = []
            for page_index in range(document.page_count):
                try:
                    text = document.load_page(page_index).get_text("text").strip()
                except Exception as exc:
                    raise ManuscriptIngestionError(
                        f"failed to extract complete manuscript page {page_index + 1}"
                    ) from exc
                nonempty_lines = [line.strip() for line in text.splitlines() if line.strip()]
                section_hint = nonempty_lines[0][:160] if nonempty_lines else None
                pages.append(
                    ManuscriptPage(
                        page_number=page_index + 1,
                        text=text,
                        section_hint=section_hint,
                    )
                )
        finally:
            document.close()

        text_character_count = sum(len(page.text) for page in pages)
        if text_character_count < self.settings.min_text_characters:
            raise ManuscriptIngestionError(
                "manuscript has insufficient extractable text; it may be image-only or incomplete"
            )
        digest = hashlib.sha256(pdf_bytes).hexdigest()
        metadata = ManuscriptMetadata(
            source=source,
            source_kind=source_kind,
            resolved_url=resolved_url,
            filename=filename,
            sha256=digest,
            byte_size=len(pdf_bytes),
            page_count=len(pages),
            text_character_count=text_character_count,
        )
        return ManuscriptPackage(pdf_bytes=pdf_bytes, metadata=metadata, pages=tuple(pages))
