from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ets4.store.db import upsert_export_artifact

from .records import load_export_records, load_manifest_metadata
from .render import render_internal_notes, render_public_issue

CHECKSUM_PREFIX = "<!-- ets4-generated-sha256:"
CHECKSUM_SUFFIX = "-->"


class ExportWriteError(RuntimeError):
    """Raised when export output would overwrite human-edited content."""


@dataclass(frozen=True)
class ExportArtifact:
    artifact_type: str
    path: Path
    content_sha256: str


@dataclass(frozen=True)
class ExportResult:
    run_id: str
    output_dir: Path
    artifact_count: int
    selected_count: int
    artifacts: tuple[ExportArtifact, ...]


def export_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    output_dir: str | Path,
    force: bool = False,
) -> ExportResult:
    manifest = load_manifest_metadata(conn, run_id=run_id)
    records = load_export_records(conn, run_id=run_id)
    issue_dir = Path(output_dir) / _safe_name(manifest["issue_id"])
    issue_dir.mkdir(parents=True, exist_ok=True)

    public_content = _with_checksum(render_public_issue(manifest=manifest, records=records))
    notes_content = _with_checksum(render_internal_notes(manifest=manifest, records=records))
    artifacts = (
        _write_artifact(issue_dir / "issue.md", public_content, force=force, artifact_type="issue"),
        _write_artifact(
            issue_dir / "internal-notes.md",
            notes_content,
            force=force,
            artifact_type="internal_notes",
        ),
    )
    for artifact in artifacts:
        upsert_export_artifact(
            conn,
            run_id=run_id,
            artifact_type=artifact.artifact_type,
            path=str(artifact.path),
            content_sha256=artifact.content_sha256,
            status="ok",
            message=f"Exported {artifact.artifact_type}",
        )
    conn.commit()
    return ExportResult(
        run_id=run_id,
        output_dir=issue_dir,
        artifact_count=len(artifacts),
        selected_count=len(records),
        artifacts=artifacts,
    )


def _write_artifact(
    path: Path,
    content: str,
    *,
    force: bool,
    artifact_type: str,
) -> ExportArtifact:
    if path.exists() and not force and not _is_unedited_generated_file(path):
        raise ExportWriteError(
            f"Refusing to overwrite human-edited export without --force: {path}"
        )
    path.write_text(content, encoding="utf-8")
    return ExportArtifact(
        artifact_type=artifact_type,
        path=path,
        content_sha256=_content_hash(_strip_checksum(content)),
    )


def _with_checksum(content: str) -> str:
    base = _strip_checksum(content).rstrip() + "\n"
    checksum = _content_hash(base)
    return f"{base}\n{CHECKSUM_PREFIX} {checksum} {CHECKSUM_SUFFIX}\n"


def _is_unedited_generated_file(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    stored = _read_checksum(content)
    if stored is None:
        return False
    return _content_hash(_strip_checksum(content).rstrip() + "\n") == stored


def _read_checksum(content: str) -> str | None:
    for line in reversed(content.splitlines()):
        stripped = line.strip()
        if stripped.startswith(CHECKSUM_PREFIX) and stripped.endswith(CHECKSUM_SUFFIX):
            return stripped.removeprefix(CHECKSUM_PREFIX).removesuffix(CHECKSUM_SUFFIX).strip()
    return None


def _strip_checksum(content: str) -> str:
    lines = [
        line
        for line in content.splitlines()
        if not (
            line.strip().startswith(CHECKSUM_PREFIX)
            and line.strip().endswith(CHECKSUM_SUFFIX)
        )
    ]
    return "\n".join(lines).rstrip() + "\n"


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _safe_name(value: str) -> str:
    chars = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-") or "issue"
