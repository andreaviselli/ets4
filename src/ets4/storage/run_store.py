"""Atomic, auditable file-backed run persistence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ets4.domain.schemas import RunManifest
from ets4.ingestion.models import ManuscriptMetadata, ManuscriptPackage, ManuscriptPage

RUN_ID_PATTERN = re.compile(r"^run-[a-f0-9]{12}$")


class RunStoreError(RuntimeError):
    """Raised when durable run state is missing or inconsistent."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def redact_secrets(text: str) -> str:
    patterns = [
        (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_API_KEY]"),
        (re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;]+"), r"\1[REDACTED]"),
    ]
    result = text
    for pattern, replacement in patterns:
        result = pattern.sub(replacement, result)
    return result


class RunStore:
    """Persist completed paid stages before allowing subsequent workflow steps."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise RunStoreError(f"invalid run id: {run_id}")
        return self.root / run_id

    def create(self, run_id: str) -> Path:
        directory = self.run_dir(run_id)
        try:
            directory.mkdir(parents=True, exist_ok=False)
            (directory / "logs").mkdir()
            (directory / "logs" / "raw").mkdir()
        except FileExistsError as exc:
            raise RunStoreError(f"run directory already exists: {run_id}") from exc
        return directory

    def exists(self, run_id: str) -> bool:
        return (self.run_dir(run_id) / "run-manifest.json").is_file()

    def artifact_exists(self, run_id: str, relative_path: str) -> bool:
        return self._artifact_path(run_id, relative_path).is_file()

    def write_manifest(self, manifest: RunManifest) -> None:
        self.write_json(manifest.run_id, "run-manifest.json", manifest.model_dump(mode="json"))

    def load_manifest(self, run_id: str) -> RunManifest:
        return RunManifest.model_validate(self.read_json(run_id, "run-manifest.json"))

    def write_manuscript(self, run_id: str, manuscript: ManuscriptPackage) -> dict[str, str]:
        checksums = {
            "manuscript.pdf": self.write_bytes(run_id, "manuscript.pdf", manuscript.pdf_bytes),
            "manuscript-metadata.json": self.write_json(
                run_id,
                "manuscript-metadata.json",
                manuscript.metadata.model_dump(mode="json"),
            ),
            "manuscript-pages.json": self.write_json(
                run_id,
                "manuscript-pages.json",
                [page.model_dump(mode="json") for page in manuscript.pages],
            ),
        }
        return checksums

    def load_manuscript(self, run_id: str) -> ManuscriptPackage:
        pdf_bytes = self.read_bytes(run_id, "manuscript.pdf")
        metadata = ManuscriptMetadata.model_validate(
            self.read_json(run_id, "manuscript-metadata.json")
        )
        if sha256_bytes(pdf_bytes) != metadata.sha256:
            raise RunStoreError("stored manuscript checksum does not match metadata")
        pages = tuple(
            ManuscriptPage.model_validate(item)
            for item in self.read_json(run_id, "manuscript-pages.json")
        )
        if len(pages) != metadata.page_count:
            raise RunStoreError("stored manuscript page count is inconsistent")
        return ManuscriptPackage(pdf_bytes=pdf_bytes, metadata=metadata, pages=pages)

    def write_json(self, run_id: str, relative_path: str, value: Any) -> str:
        payload = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return self.write_bytes(run_id, relative_path, payload)

    def read_json(self, run_id: str, relative_path: str) -> Any:
        try:
            return json.loads(self.read_bytes(run_id, relative_path).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunStoreError(f"invalid JSON artifact: {relative_path}") from exc

    def write_text(self, run_id: str, relative_path: str, value: str) -> str:
        return self.write_bytes(run_id, relative_path, value.encode("utf-8"))

    def read_bytes(self, run_id: str, relative_path: str) -> bytes:
        path = self._artifact_path(run_id, relative_path)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise RunStoreError(f"cannot read run artifact: {relative_path}") from exc

    def write_bytes(self, run_id: str, relative_path: str, payload: bytes) -> str:
        path = self._artifact_path(run_id, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return sha256_bytes(payload)

    def append_event(self, run_id: str, event: str, **fields: Any) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            **fields,
        }
        payload = redact_secrets(json.dumps(record, ensure_ascii=False, sort_keys=True)) + "\n"
        path = self._artifact_path(run_id, "logs/events.jsonl")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload)

    def _artifact_path(self, run_id: str, relative_path: str) -> Path:
        if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            raise RunStoreError("artifact path must stay inside its run directory")
        run_directory = self.run_dir(run_id)
        path = run_directory / relative_path
        if run_directory not in path.parents:
            raise RunStoreError("artifact path escapes its run directory")
        return path
