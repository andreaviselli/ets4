from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass

from ets4.models import ModelProvider
from ets4.store.db import (
    insert_review_event,
    upsert_editorial_decision,
    upsert_review_dossier,
    upsert_reviewer_report,
)

from .dossier import DossierBuildError, build_evidence_dossier
from .schemas import (
    REVIEWER_ROLES,
    validate_editorial_decision,
    validate_reviewer_report,
)


@dataclass(frozen=True)
class PanelReviewResult:
    paper_id: str
    status: str
    dossier_id: str | None = None
    reviewer_count: int = 0
    decision: str | None = None
    deep_dive_score: float | None = None
    message: str = ""


def run_panel_review_for_paper(
    conn: sqlite3.Connection,
    *,
    paper_id: str,
    run_id: str,
    provider: ModelProvider,
) -> PanelReviewResult:
    try:
        dossier = build_evidence_dossier(conn, paper_id=paper_id, run_id=run_id)
    except DossierBuildError as exc:
        insert_review_event(
            conn,
            paper_id=paper_id,
            run_id=run_id,
            dossier_id=None,
            status="error",
            message=str(exc),
        )
        conn.commit()
        return PanelReviewResult(paper_id=paper_id, status="error", message=str(exc))

    upsert_review_dossier(
        conn,
        dossier_id=dossier.id,
        paper_id=paper_id,
        run_id=run_id,
        document_id=dossier.document_id,
        evidence_count=dossier.evidence_count,
        dossier_json=dossier.payload,
        status="ok",
    )

    reports: list[dict] = []
    try:
        for role in REVIEWER_ROLES:
            result = provider.review(role, dossier.payload)
            payload = result.to_dict()
            validate_reviewer_report(payload)
            report_id = _stable_id("report", run_id, paper_id, role)
            upsert_reviewer_report(
                conn,
                report_id=report_id,
                paper_id=paper_id,
                run_id=run_id,
                dossier_id=dossier.id,
                reviewer_role=role,
                provider=provider.name,
                recommendation=result.recommendation,
                score=result.score,
                confidence=result.confidence,
                report_json=payload,
                evidence_item_ids=list(result.evidence_item_ids),
                status="ok",
            )
            reports.append(payload)

        decision = provider.handling_editor(dossier.payload, reports)
        decision_payload = decision.to_dict()
        validate_editorial_decision(decision_payload)
        decision_id = _stable_id("decision", run_id, paper_id)
        upsert_editorial_decision(
            conn,
            decision_id=decision_id,
            paper_id=paper_id,
            run_id=run_id,
            dossier_id=dossier.id,
            provider=provider.name,
            decision=decision.decision,
            deep_dive_score=decision.deep_dive_score,
            confidence=decision.confidence,
            memo_json=decision_payload,
            status="ok",
        )
        _update_paper_status(conn, paper_id=paper_id, decision=decision.decision)
        insert_review_event(
            conn,
            paper_id=paper_id,
            run_id=run_id,
            dossier_id=dossier.id,
            status="ok",
            message=(
                f"Completed {len(reports)} reviewer reports; "
                f"decision={decision.decision}; score={decision.deep_dive_score:.3f}"
            ),
        )
        conn.commit()
        return PanelReviewResult(
            paper_id=paper_id,
            status="ok",
            dossier_id=dossier.id,
            reviewer_count=len(reports),
            decision=decision.decision,
            deep_dive_score=decision.deep_dive_score,
            message=decision.rationale,
        )
    except Exception as exc:
        insert_review_event(
            conn,
            paper_id=paper_id,
            run_id=run_id,
            dossier_id=dossier.id,
            status="error",
            message=str(exc),
        )
        conn.commit()
        return PanelReviewResult(
            paper_id=paper_id,
            status="error",
            dossier_id=dossier.id,
            reviewer_count=len(reports),
            message=str(exc),
        )


def selected_review_targets(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    paper_id: str | None = None,
) -> list[str]:
    if paper_id:
        return [paper_id]
    rows = conn.execute(
        """
        SELECT papers.id
        FROM candidate_selections
        JOIN papers ON papers.id = candidate_selections.paper_id
        WHERE candidate_selections.run_id = ?
          AND candidate_selections.selection_stage = 'full_review'
        ORDER BY candidate_selections.rank ASC
        """,
        (run_id,),
    ).fetchall()
    return [str(row["id"]) for row in rows]


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:16]}"


def _update_paper_status(conn: sqlite3.Connection, *, paper_id: str, decision: str) -> None:
    status_by_decision = {
        "full_deep_dive": "reviewed_deep_dive_candidate",
        "short_mention": "reviewed_short_mention_candidate",
        "watchlist": "reviewed_watchlist",
        "needs_human_adjudication": "needs_editor",
        "reject": "review_reject",
    }
    conn.execute(
        "UPDATE papers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status_by_decision.get(decision, "reviewed"), paper_id),
    )
