from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExportRecord:
    paper_id: str
    stage: str
    rank: int
    title: str
    canonical_url: str
    decision: dict[str, Any]
    dossier: dict[str, Any]
    reviewer_reports: tuple[dict[str, Any], ...]


def load_export_records(conn: sqlite3.Connection, *, run_id: str) -> list[ExportRecord]:
    rows = conn.execute(
        """
        SELECT
            candidate_selections.paper_id,
            candidate_selections.selection_stage,
            candidate_selections.rank,
            papers.title,
            papers.canonical_url,
            editorial_decisions.memo_json,
            review_dossiers.dossier_json
        FROM candidate_selections
        JOIN papers ON papers.id = candidate_selections.paper_id
        JOIN editorial_decisions
          ON editorial_decisions.paper_id = candidate_selections.paper_id
         AND editorial_decisions.run_id = candidate_selections.run_id
        JOIN review_dossiers ON review_dossiers.id = editorial_decisions.dossier_id
        WHERE candidate_selections.run_id = ?
          AND candidate_selections.selection_stage IN ('deep_dive_draft', 'short_mention')
          AND editorial_decisions.status = 'ok'
        ORDER BY
            CASE candidate_selections.selection_stage
                WHEN 'deep_dive_draft' THEN 1
                ELSE 2
            END,
            candidate_selections.rank ASC
        """,
        (run_id,),
    ).fetchall()
    records = []
    for row in rows:
        reports = conn.execute(
            """
            SELECT report_json
            FROM reviewer_reports
            WHERE run_id = ? AND paper_id = ? AND status = 'ok'
            ORDER BY reviewer_role ASC
            """,
            (run_id, row["paper_id"]),
        ).fetchall()
        records.append(
            ExportRecord(
                paper_id=row["paper_id"],
                stage=row["selection_stage"],
                rank=int(row["rank"]),
                title=row["title"],
                canonical_url=row["canonical_url"],
                decision=json.loads(row["memo_json"]),
                dossier=json.loads(row["dossier_json"]),
                reviewer_reports=tuple(json.loads(report["report_json"]) for report in reports),
            )
        )
    return records


def load_manifest_metadata(conn: sqlite3.Connection, *, run_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT run_id, issue_id, issue_date, created_at, prompt_version, model_policy_json
        FROM run_manifests
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"Run manifest not found: {run_id}")
    return {
        "run_id": row["run_id"],
        "issue_id": row["issue_id"],
        "issue_date": row["issue_date"],
        "created_at": row["created_at"],
        "prompt_version": row["prompt_version"],
        "model_policy": json.loads(row["model_policy_json"]),
    }
