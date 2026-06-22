from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .labels import (
    VALID_APPLICATION_TYPES,
    VALID_AUDIENCE_FITS,
    VALID_ECONOMIC_RELEVANCE,
    VALID_EDITORIAL_DECISIONS,
    VALID_FORECASTING_CONTRIBUTIONS,
    VALID_PUBLICATION_TRACKS,
    VALID_RELEVANCE_LABELS,
    VALID_SOCIAL_HOOK_POTENTIAL,
    VALID_TRIAGE_DECISIONS,
)


@dataclass(frozen=True)
class BenchmarkTemplateResult:
    path: Path
    run_id: str
    paper_count: int
    accepted_count: int


def create_benchmark_template(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    output_path: str | Path,
    limit: int | None = None,
    include_untriaged: bool = False,
) -> BenchmarkTemplateResult:
    papers = [_paper_template(row) for row in _benchmark_rows(conn, run_id=run_id, limit=limit)]
    if include_untriaged:
        present = {paper["paper_id"] for paper in papers}
        papers.extend(
            _untriaged_paper_template(row)
            for row in _untriaged_rows(conn, run_id=run_id, exclude_paper_ids=present)
        )

    if not papers:
        raise ValueError(f"No papers found for benchmark template in run {run_id}")

    payload = {
        "version": f"{run_id}-human-v1",
        "source_run_id": run_id,
        "labeling_status": "draft",
        "instructions": {
            "gold_labels": (
                "Edit each paper after human review. Set label_status to 'accepted' only "
                "when the label is ready to be used by ets4 evaluate."
            ),
            "evaluate": f"ets4 evaluate --run-id {run_id} --labels <this-file>",
            "required_evidence_kinds": (
                "Keep only evidence kinds that should be required for this paper's review. "
                "Use an empty list for triage-only or unavailable full-text examples."
            ),
            "rubric": (
                "The default ETS4 product is a practitioner/applied economic forecasting "
                "digest. Use methods_watch for academically interesting methods that are "
                "not yet strong applied recommendations. Social hook potential is secondary "
                "metadata, not a reason to promote a paper."
            ),
        },
        "label_options": {
            "relevance_label": list(VALID_RELEVANCE_LABELS),
            "audience_fit": sorted(VALID_AUDIENCE_FITS),
            "application_type": sorted(VALID_APPLICATION_TYPES),
            "economic_relevance": sorted(VALID_ECONOMIC_RELEVANCE),
            "forecasting_contribution": sorted(VALID_FORECASTING_CONTRIBUTIONS),
            "publication_track": sorted(VALID_PUBLICATION_TRACKS),
            "social_hook_potential": sorted(VALID_SOCIAL_HOOK_POTENTIAL),
            "expected_triage_decision": list(VALID_TRIAGE_DECISIONS),
            "expected_editorial_decision": list(VALID_EDITORIAL_DECISIONS),
        },
        "papers": papers,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return BenchmarkTemplateResult(
        path=path,
        run_id=run_id,
        paper_count=len(papers),
        accepted_count=sum(1 for paper in papers if paper.get("label_status") == "accepted"),
    )


def _benchmark_rows(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    limit: int | None,
) -> list[sqlite3.Row]:
    sql = """
        SELECT
            papers.id AS paper_id,
            papers.title,
            papers.canonical_url,
            papers.abstract,
            papers.authors,
            papers.published_date,
            COALESCE(sources.name, '') AS source_name,
            triage_reviews.decision AS triage_decision,
            triage_reviews.category_hint AS triage_category_hint,
            triage_reviews.score AS triage_score,
            triage_reviews.confidence AS triage_confidence,
            triage_reviews.reason AS triage_reason,
            editorial_decisions.decision AS editorial_decision,
            editorial_decisions.deep_dive_score,
            editorial_decisions.confidence AS editorial_confidence,
            review_dossiers.evidence_count,
            evidence_summary.available_kinds,
            documents.status AS document_status,
            documents.error_message AS document_error,
            GROUP_CONCAT(
                candidate_selections.selection_stage || ':' ||
                candidate_selections.rank || ':' ||
                printf('%.4f', candidate_selections.selection_score),
                '|'
            ) AS selection_summary
        FROM triage_reviews
        JOIN papers ON papers.id = triage_reviews.paper_id
        LEFT JOIN sources ON sources.id = papers.source_id
        LEFT JOIN editorial_decisions
          ON editorial_decisions.paper_id = papers.id
         AND editorial_decisions.run_id = triage_reviews.run_id
        LEFT JOIN review_dossiers
          ON review_dossiers.paper_id = papers.id
         AND review_dossiers.run_id = triage_reviews.run_id
        LEFT JOIN documents
          ON documents.paper_id = papers.id
         AND documents.run_id = triage_reviews.run_id
        LEFT JOIN (
            SELECT paper_id, GROUP_CONCAT(kind, '|') AS available_kinds
            FROM (
                SELECT DISTINCT paper_id, kind
                FROM evidence_items
                ORDER BY paper_id, kind
            )
            GROUP BY paper_id
        ) AS evidence_summary ON evidence_summary.paper_id = papers.id
        LEFT JOIN candidate_selections
          ON candidate_selections.paper_id = papers.id
         AND candidate_selections.run_id = triage_reviews.run_id
        WHERE triage_reviews.run_id = ?
        GROUP BY papers.id
        ORDER BY
            CASE WHEN SUM(candidate_selections.selection_stage = 'deep_dive_draft') > 0 THEN 0
                 WHEN SUM(candidate_selections.selection_stage = 'short_mention') > 0 THEN 1
                 WHEN SUM(candidate_selections.selection_stage = 'full_review') > 0 THEN 2
                 ELSE 3
            END,
            triage_reviews.score DESC,
            papers.title ASC
    """
    params: list[Any] = [run_id]
    if limit is not None:
        sql += "\n        LIMIT ?"
        params.append(limit)
    return conn.execute(sql, tuple(params)).fetchall()


def _untriaged_rows(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    exclude_paper_ids: set[str],
) -> list[sqlite3.Row]:
    if not exclude_paper_ids:
        return conn.execute(
            """
            SELECT
                papers.id AS paper_id,
                papers.title,
                papers.canonical_url,
                papers.abstract,
                papers.authors,
                papers.published_date,
                COALESCE(sources.name, '') AS source_name
            FROM papers
            LEFT JOIN sources ON sources.id = papers.source_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM triage_reviews
                WHERE triage_reviews.paper_id = papers.id
                  AND triage_reviews.run_id = ?
            )
            ORDER BY papers.created_at ASC
            """,
            (run_id,),
        ).fetchall()

    placeholders = ",".join("?" for _ in exclude_paper_ids)
    return conn.execute(
        f"""
        SELECT
            papers.id AS paper_id,
            papers.title,
            papers.canonical_url,
            papers.abstract,
            papers.authors,
            papers.published_date,
            COALESCE(sources.name, '') AS source_name
        FROM papers
        LEFT JOIN sources ON sources.id = papers.source_id
        WHERE papers.id NOT IN ({placeholders})
          AND NOT EXISTS (
              SELECT 1
              FROM triage_reviews
              WHERE triage_reviews.paper_id = papers.id
                AND triage_reviews.run_id = ?
          )
        ORDER BY papers.created_at ASC
        """,
        (*sorted(exclude_paper_ids), run_id),
    ).fetchall()


def _paper_template(row: sqlite3.Row) -> dict[str, Any]:
    paper_id = str(row["paper_id"])
    selections = _selection_map(row["selection_summary"])
    evidence_kinds = _evidence_kinds(row)
    return {
        "paper_id": paper_id,
        "label_status": "needs_human_label",
        "title": row["title"],
        "authors": row["authors"],
        "canonical_url": row["canonical_url"],
        "published_date": row["published_date"],
        "source_name": row["source_name"],
        "abstract": row["abstract"],
        "human_notes": "",
        "relevance_label": None,
        "audience_fit": None,
        "application_type": None,
        "economic_relevance": None,
        "forecasting_contribution": None,
        "publication_track": None,
        "social_hook_potential": None,
        "expected_category": None,
        "expected_triage_decision": None,
        "expected_editorial_decision": None,
        "expected_deep_dive": None,
        "expected_short_mention": None,
        "required_evidence_kinds": evidence_kinds,
        "hard_negative": False,
        "high_value": False,
        "system_context": {
            "triage": {
                "decision": row["triage_decision"],
                "category_hint": row["triage_category_hint"],
                "score": _optional_float(row["triage_score"]),
                "confidence": _optional_float(row["triage_confidence"]),
                "reason": row["triage_reason"],
            },
            "selection": selections,
            "document": {
                "status": row["document_status"],
                "error": row["document_error"],
            },
            "evidence": {
                "count": int(row["evidence_count"] or 0),
                "available_kinds": evidence_kinds,
            },
            "editorial": {
                "decision": row["editorial_decision"],
                "deep_dive_score": _optional_float(row["deep_dive_score"]),
                "confidence": _optional_float(row["editorial_confidence"]),
            },
        },
    }


def _untriaged_paper_template(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "paper_id": row["paper_id"],
        "label_status": "needs_human_label",
        "title": row["title"],
        "authors": row["authors"],
        "canonical_url": row["canonical_url"],
        "published_date": row["published_date"],
        "source_name": row["source_name"],
        "abstract": row["abstract"],
        "human_notes": "",
        "relevance_label": None,
        "audience_fit": None,
        "application_type": None,
        "economic_relevance": None,
        "forecasting_contribution": None,
        "publication_track": None,
        "social_hook_potential": None,
        "expected_category": None,
        "expected_triage_decision": None,
        "expected_editorial_decision": None,
        "expected_deep_dive": None,
        "expected_short_mention": None,
        "required_evidence_kinds": [],
        "hard_negative": False,
        "high_value": False,
        "system_context": {
            "triage": None,
            "selection": {},
            "document": None,
            "evidence": {"count": 0, "available_kinds": []},
            "editorial": None,
        },
    }


def _selection_map(value: str | None) -> dict[str, dict[str, float | int]]:
    selections: dict[str, dict[str, float | int]] = {}
    if not value:
        return selections
    for item in value.split("|"):
        stage, rank, score = item.split(":", maxsplit=2)
        selections[stage] = {"rank": int(rank), "score": float(score)}
    return selections


def _evidence_kinds(row: sqlite3.Row) -> list[str]:
    count = int(row["evidence_count"] or 0)
    if count <= 0:
        return []
    value = row["available_kinds"]
    if not value:
        return []
    return [kind for kind in str(value).split("|") if kind]


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
