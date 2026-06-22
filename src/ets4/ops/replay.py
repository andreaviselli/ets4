from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date

from ets4.config import AppConfig
from ets4.manifest import create_manifest
from ets4.models import ModelProvider
from ets4.ops.retry import retry_call
from ets4.ops.usage import record_fake_usage
from ets4.review.workflow import run_panel_review_for_paper, selected_review_targets
from ets4.selection import select_full_review_candidates, select_publication_candidates
from ets4.store.db import insert_manifest, insert_run_event, run_exists


@dataclass(frozen=True)
class BaselineReplayResult:
    source_run_id: str
    replay_run_id: str
    triaged_count: int
    full_review_selected_count: int
    full_review_candidate_count: int
    reviewed_count: int
    review_error_count: int
    deep_dive_selected_count: int
    short_mention_selected_count: int


def replay_baseline_run(
    conn: sqlite3.Connection,
    *,
    config: AppConfig,
    source_run_id: str,
    provider: ModelProvider,
    issue_date: date | None = None,
) -> BaselineReplayResult:
    if not run_exists(conn, source_run_id):
        raise ValueError(f"Source run manifest not found: {source_run_id}")

    replay_issue_date = issue_date or _source_issue_date(conn, source_run_id)
    manifest = create_manifest(
        config=config,
        issue_date=replay_issue_date,
        automation_mode="evaluation",
        allowed_actions=("triage", "review", "evaluate"),
    )
    insert_manifest(conn, manifest)
    insert_run_event(
        conn,
        run_id=manifest.run_id,
        stage="replay",
        status="started",
        message=f"Baseline replay started from {source_run_id}",
        metadata={"source_run_id": source_run_id},
    )

    triaged_count = _replay_triage(
        conn,
        source_run_id=source_run_id,
        replay_run_id=manifest.run_id,
        config=config,
        provider=provider,
    )
    selection = select_full_review_candidates(
        conn,
        run_id=manifest.run_id,
        config=config,
        update_paper_status=False,
    )
    reviewed_count, review_error_count = _replay_reviews(
        conn,
        replay_run_id=manifest.run_id,
        config=config,
        provider=provider,
    )
    publication_selection = select_publication_candidates(
        conn,
        run_id=manifest.run_id,
        config=config,
    )
    insert_run_event(
        conn,
        run_id=manifest.run_id,
        stage="replay",
        status="error" if review_error_count else "ok",
        message=(
            f"Replayed {triaged_count} triage decisions and "
            f"{reviewed_count} reviews with {review_error_count} review errors"
        ),
        metadata={"source_run_id": source_run_id},
    )
    conn.commit()
    return BaselineReplayResult(
        source_run_id=source_run_id,
        replay_run_id=manifest.run_id,
        triaged_count=triaged_count,
        full_review_selected_count=selection.selected_count,
        full_review_candidate_count=selection.candidate_count,
        reviewed_count=reviewed_count,
        review_error_count=review_error_count,
        deep_dive_selected_count=publication_selection.deep_dive_selected_count,
        short_mention_selected_count=publication_selection.short_mention_selected_count,
    )


def _source_issue_date(conn: sqlite3.Connection, run_id: str) -> date:
    row = conn.execute(
        "SELECT issue_date FROM run_manifests WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"Source run manifest not found: {run_id}")
    return date.fromisoformat(str(row["issue_date"]))


def _replay_triage(
    conn: sqlite3.Connection,
    *,
    source_run_id: str,
    replay_run_id: str,
    config: AppConfig,
    provider: ModelProvider,
) -> int:
    rows = conn.execute(
        """
        SELECT
            papers.id,
            papers.title,
            papers.abstract,
            COALESCE(sources.name, '') AS source_name
        FROM triage_reviews
        JOIN papers ON papers.id = triage_reviews.paper_id
        LEFT JOIN sources ON sources.id = papers.source_id
        WHERE triage_reviews.run_id = ?
        ORDER BY triage_reviews.id ASC
        LIMIT ?
        """,
        (source_run_id, config.issue.max_candidates_to_triage),
    ).fetchall()
    for row in rows:
        input_text = f"{row['title']}\n{row['abstract']}\n{row['source_name']}"
        result = retry_call(
            lambda row=row: provider.triage(row["title"], row["abstract"], row["source_name"])
        )
        record_fake_usage(
            conn,
            run_id=replay_run_id,
            stage="triage",
            provider=provider.name,
            model=config.model_policy.triage_model,
            input_text=input_text,
            output_text=json.dumps(result.__dict__, sort_keys=True),
            metadata={"paper_id": row["id"], "source_run_id": source_run_id},
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO triage_reviews (
                paper_id, run_id, provider, decision, category_hint,
                forecasting_signal, economic_signal, score, confidence, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                replay_run_id,
                provider.name,
                result.decision,
                result.category_hint,
                result.forecasting_signal,
                result.economic_signal,
                result.score,
                result.confidence,
                result.reason,
            ),
        )
    conn.commit()
    return len(rows)


def _replay_reviews(
    conn: sqlite3.Connection,
    *,
    replay_run_id: str,
    config: AppConfig,
    provider: ModelProvider,
) -> tuple[int, int]:
    reviewed_count = 0
    error_count = 0
    for paper_id in selected_review_targets(conn, run_id=replay_run_id):
        result = run_panel_review_for_paper(
            conn,
            paper_id=paper_id,
            run_id=replay_run_id,
            provider=provider,
            model_name=config.model_policy.review_model,
            update_paper_status=False,
        )
        reviewed_count += 1
        if result.status != "ok":
            error_count += 1
    return reviewed_count, error_count
