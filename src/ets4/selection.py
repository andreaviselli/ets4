from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from .config import AppConfig
from .identity import normalize_title


@dataclass(frozen=True)
class SelectionResult:
    selected_count: int
    candidate_count: int


@dataclass(frozen=True)
class PublicationSelectionResult:
    deep_dive_selected_count: int
    short_mention_selected_count: int
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
    update_paper_status: bool = True,
    require_successful_document: bool = False,
) -> SelectionResult:
    document_filter = (
        """
          AND EXISTS (
              SELECT 1
              FROM documents
              WHERE documents.paper_id = papers.id
                AND documents.status = 'ok'
          )
        """
        if require_successful_document
        else ""
    )
    rows = conn.execute(
        f"""
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
        {document_filter}
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
        if update_paper_status:
            conn.execute(
                "UPDATE papers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                ("selected_for_review", row["id"]),
            )

    conn.commit()
    return SelectionResult(selected_count=len(selected), candidate_count=len(ranked))


def select_publication_candidates(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    config: AppConfig,
) -> PublicationSelectionResult:
    rows = conn.execute(
        """
        SELECT
            papers.id,
            papers.title,
            papers.canonical_url,
            papers.normalized_title,
            editorial_decisions.decision,
            editorial_decisions.deep_dive_score,
            editorial_decisions.confidence,
            editorial_decisions.memo_json,
            review_dossiers.evidence_count
        FROM editorial_decisions
        JOIN papers ON papers.id = editorial_decisions.paper_id
        JOIN review_dossiers ON review_dossiers.id = editorial_decisions.dossier_id
        WHERE editorial_decisions.run_id = ?
          AND editorial_decisions.status = 'ok'
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
        score = _publication_score(row)
        if forced:
            score += 100.0
        ranked.append((score, forced, row))

    ranked.sort(key=lambda item: (-item[0], item[2]["title"].lower()))
    deep_candidates = [
        item
        for item in ranked
        if item[2]["decision"] == "full_deep_dive"
        and _row_publication_track(item[2]) == "deep_dive"
    ]
    deep_selected = deep_candidates[: config.issue.max_deep_dive_drafts]
    deep_ids = {item[2]["id"] for item in deep_selected}
    short_candidates = [
        item
        for item in ranked
        if item[2]["id"] not in deep_ids
        and (
            item[2]["decision"] == "short_mention"
            or _row_publication_track(item[2]) == "applied_note"
        )
    ]
    short_selected = short_candidates[: config.issue.max_short_mentions]

    _write_publication_selection(
        conn,
        run_id=run_id,
        stage="deep_dive_draft",
        selected=deep_selected,
    )
    _write_publication_selection(
        conn,
        run_id=run_id,
        stage="short_mention",
        selected=short_selected,
    )
    conn.commit()
    return PublicationSelectionResult(
        deep_dive_selected_count=len(deep_selected),
        short_mention_selected_count=len(short_selected),
        candidate_count=len(ranked),
    )


def _selection_score(row: sqlite3.Row) -> float:
    return (
        float(row["score"])
        + 0.5 * float(row["confidence"])
        + PRIORITY_BONUS.get(str(row["source_priority"]).lower(), 0.1)
        + CATEGORY_BONUS.get(str(row["category_hint"]).lower(), 0.0)
    )


def _publication_score(row: sqlite3.Row) -> float:
    decision_bonus = {
        "full_deep_dive": 1.2,
        "short_mention": 0.5,
        "watchlist": 0.0,
        "needs_human_adjudication": -0.6,
        "reject": -5.0,
    }
    return (
        float(row["deep_dive_score"])
        + float(row["confidence"])
        + min(int(row["evidence_count"]), 20) * 0.03
        + decision_bonus.get(str(row["decision"]), -1.0)
    )


def _selection_reason(row: sqlite3.Row, forced: bool) -> str:
    reason = (
        f"triage_score={row['score']:.2f}; confidence={row['confidence']:.2f}; "
        f"category={row['category_hint']}; source_priority={row['source_priority']}"
    )
    if forced:
        return f"human force_include override; {reason}"
    return reason


def _publication_reason(row: sqlite3.Row, forced: bool) -> str:
    reason = (
        f"editor_decision={row['decision']}; deep_dive_score={row['deep_dive_score']:.2f}; "
        f"confidence={row['confidence']:.2f}; evidence_count={row['evidence_count']}; "
        f"publication_track={_row_publication_track(row)}"
    )
    if forced:
        return f"human force_include override; {reason}"
    return reason


def _row_publication_track(row: sqlite3.Row) -> str | None:
    try:
        memo = json.loads(row["memo_json"])
    except (KeyError, TypeError, json.JSONDecodeError):
        memo = {}
    if isinstance(memo, dict) and memo.get("publication_track"):
        return str(memo["publication_track"])
    decision = str(row["decision"])
    if decision == "full_deep_dive":
        return "deep_dive"
    if decision == "short_mention":
        return "applied_note"
    if decision == "watchlist":
        return "methods_watch"
    if decision == "reject":
        return "reject"
    return None


def _write_publication_selection(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    stage: str,
    selected: list[tuple[float, bool, sqlite3.Row]],
) -> None:
    conn.execute(
        "DELETE FROM candidate_selections WHERE run_id = ? AND selection_stage = ?",
        (run_id, stage),
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
                stage,
                rank,
                round(score, 4),
                1 if forced else 0,
                _publication_reason(row, forced),
            ),
        )


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
