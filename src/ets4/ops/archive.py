from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ets4.store.db import upsert_archive_artifact


@dataclass(frozen=True)
class ArchiveResult:
    run_id: str
    path: Path
    content_sha256: str
    file_count: int


def create_archive_bundle(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    archive_dir: str | Path,
) -> ArchiveResult:
    manifest = _fetch_manifest(conn, run_id=run_id)
    archive_path = Path(archive_dir) / f"{manifest['issue_id']}-{run_id}.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    export_paths = _export_paths(conn, run_id=run_id)
    files_written = 0
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        files_written += 1
        zf.writestr(
            "run-summary.json",
            json.dumps(_run_summary(conn, run_id=run_id), indent=2, sort_keys=True),
        )
        files_written += 1
        for path in export_paths:
            if path.exists():
                zf.write(path, arcname=f"exports/{path.name}")
                files_written += 1
    content_hash = _file_hash(archive_path)
    upsert_archive_artifact(
        conn,
        run_id=run_id,
        path=str(archive_path),
        content_sha256=content_hash,
        status="ok",
        message=f"Archived {files_written} files",
    )
    conn.commit()
    return ArchiveResult(
        run_id=run_id,
        path=archive_path,
        content_sha256=content_hash,
        file_count=files_written,
    )


def _fetch_manifest(conn: sqlite3.Connection, *, run_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT *
        FROM run_manifests
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"Run manifest not found: {run_id}")
    result = dict(row)
    for key in (
        "model_policy_json",
        "cost_budget_json",
        "paper_budget_json",
        "allowed_actions_json",
        "force_include_json",
        "force_exclude_json",
    ):
        result[key] = json.loads(result[key])
    return result


def _run_summary(conn: sqlite3.Connection, *, run_id: str) -> dict[str, Any]:
    tables = (
        "source_events",
        "triage_reviews",
        "candidate_selections",
        "documents",
        "evidence_items",
        "review_dossiers",
        "reviewer_reports",
        "editorial_decisions",
        "evaluation_runs",
        "export_artifacts",
        "run_events",
        "usage_records",
    )
    counts = {
        table: conn.execute(
            _count_query(table),
            (run_id,),
        ).fetchone()[0]
        for table in tables
    }
    usage = conn.execute(
        """
        SELECT
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(estimated_cost_usd), 0.0) AS estimated_cost_usd
        FROM usage_records
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    return {
        "run_id": run_id,
        "counts": counts,
        "usage": dict(usage),
    }


def _count_query(table: str) -> str:
    if table == "evidence_items":
        return """
        SELECT COUNT(*)
        FROM evidence_items
        JOIN documents ON documents.id = evidence_items.document_id
        WHERE documents.run_id = ?
        """
    return f"SELECT COUNT(*) FROM {table} WHERE run_id = ?"


def _export_paths(conn: sqlite3.Connection, *, run_id: str) -> list[Path]:
    rows = conn.execute(
        """
        SELECT path
        FROM export_artifacts
        WHERE run_id = ? AND status = 'ok'
        ORDER BY artifact_type ASC
        """,
        (run_id,),
    ).fetchall()
    return [Path(row["path"]) for row in rows]


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
