from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .config import AppConfig
from .identity import normalize_title


@dataclass(frozen=True)
class SelectionResult:
    selected_count: int
    candidate_count: int


PRIORITY_BONUS = {
    "high": 0.4,
    "medium": 0.2,
    "low": 0.0,
}
CATEGORY_BONUS = {
    "directly_relevant": 0.5,
    "paper_of_interest": 0.2,
    "not_relevant": -1.0,
}


def select_full_review_candidates(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    config: AppConfig,
) -> SelectionResult:
    rows = conn.execute(
        """
        SELECT
            papers.id,
            papers.title,
            papers.canonical_url,
            papers.normalized_title,
            COALESCE(sources.priority, 'medium') AS source_priority,
            triage_reviews.score,
            triage_reviews.confidence,
            triage_reviews.category_hint,
            triage_reviews.decision
        FROM triage_reviews
        JOIN papers ON papers.id = triage_reviews.paper_id
        LEFT JOIN sources ON sources.id = papers.source_id
        WHERE triage_reviews.run_id = ?
          AND triage_reviews.decision IN ('assign_reviewers', 'borderline')
        """,
        (run_id,),
    ).fetchall()

    force_include = {_normalize_selector(value) for value in config.issue.force_include}
    force_exclude = {_normalize_selector(value) for value in config.issue.force_exclude}

    ranked = []
    for row in rows:
        selectors = _row_selectors(row)
        if selectors & force_exclude:
            continue
        forced = bool(selectors & force_include)
        score = _selection_score(row)
        if forced:
            score += 100.0
        ranked.append((score, forced, row))

    ranked.sort(key=lambda item: (-item[0], item[2]["title"].lower()))
    selected = ranked[: config.issue.max_papers_to_full_review]

    conn.execute(
        "DELETE FROM candidate_selections WHERE run_id = ? AND selection_stage = ?",
        (run_id, "full_review"),
    )

    for rank, (score, forced, row) in enumerate(selected, start=1):
        conn.execute(
            """
            INSERT INTO candidate_selections (
                run_id, paper_id, selection_stage, rank, selection_score, forced, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                row["id"],
                "full_review",
                rank,
                round(score, 4),
                1 if forced else 0,
                _selection_reason(row, forced),
            ),
        )
        conn.execute(
            "UPDATE papers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            ("selected_for_review", row["id"]),
        )

    conn.commit()
    return SelectionResult(selected_count=len(selected), candidate_count=len(ranked))


def _selection_score(row: sqlite3.Row) -> float:
    return (
        float(row["score"])
        + 0.5 * float(row["confidence"])
        + PRIORITY_BONUS.get(str(row["source_priority"]).lower(), 0.1)
        + CATEGORY_BONUS.get(str(row["category_hint"]).lower(), 0.0)
    )


def _selection_reason(row: sqlite3.Row, forced: bool) -> str:
    reason = (
        f"triage_score={row['score']:.2f}; confidence={row['confidence']:.2f}; "
        f"category={row['category_hint']}; source_priority={row['source_priority']}"
    )
    if forced:
        return f"human force_include override; {reason}"
    return reason


def _row_selectors(row: sqlite3.Row) -> set[str]:
    return {
        _normalize_selector(row["id"]),
        _normalize_selector(row["canonical_url"]),
        _normalize_selector(row["title"]),
        _normalize_selector(row["normalized_title"]),
    }


def _normalize_selector(value: str | None) -> str:
    if not value:
        return ""
    normalized = normalize_title(str(value))
    return normalized or str(value).strip().lower()

