from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluate.labels import VALID_EDITORIAL_DECISIONS, VALID_PUBLICATION_TRACKS
from .store.db import upsert_human_selection_review

VALID_HUMAN_REVIEW_STATUSES = {"pending", "accepted"}
VALID_SELECTION_STAGES = {"deep_dive_draft", "short_mention", "not_selected"}


@dataclass(frozen=True)
class HumanSelectionTemplateResult:
    path: Path
    run_id: str
    paper_count: int
    pending_count: int


@dataclass(frozen=True)
class HumanSelectionApplyResult:
    path: Path
    run_id: str
    reviewed_count: int
    deviation_count: int
    deep_dive_selected_count: int
    short_mention_selected_count: int


def create_human_selection_review_template(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    output_path: str | Path,
) -> HumanSelectionTemplateResult:
    papers = [_review_item(row) for row in _review_rows(conn, run_id=run_id)]
    if not papers:
        raise ValueError(f"No reviewed papers found for run {run_id}")

    payload = {
        "version": f"{run_id}-human-selection-v1",
        "source_run_id": run_id,
        "review_status": "draft",
        "instructions": {
            "purpose": (
                "Review the agent's publication selection after panel review. "
                "The human editor has the final word before export."
            ),
            "workflow": (
                "For each paper, set human_review.status to 'accepted'. Keep or edit "
                "human_review.selection_stage, human_review.editorial_decision, and "
                "human_review.publication_track."
            ),
            "deviation_notes": (
                "If any human_review field differs from agent_assessment, write a short "
                "human_review.notes explanation. The note becomes part of the historical "
                "selection registry."
            ),
            "apply": "ets4 human-selection-apply --input <this-file>",
            "selection_stage": (
                "Use deep_dive_draft for main features, short_mention for applied notes, "
                "and not_selected for cuts, watchlist items, rejects, or papers needing "
                "human adjudication outside the automated export."
            ),
        },
        "selection_options": {
            "human_review.status": sorted(VALID_HUMAN_REVIEW_STATUSES),
            "human_review.selection_stage": sorted(VALID_SELECTION_STAGES),
            "human_review.editorial_decision": sorted(VALID_EDITORIAL_DECISIONS),
            "human_review.publication_track": sorted(VALID_PUBLICATION_TRACKS),
        },
        "papers": papers,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return HumanSelectionTemplateResult(
        path=path,
        run_id=run_id,
        paper_count=len(papers),
        pending_count=len(papers),
    )


def apply_human_selection_review(
    conn: sqlite3.Connection,
    *,
    input_path: str | Path,
    run_id: str | None = None,
) -> HumanSelectionApplyResult:
    path = Path(input_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    resolved_run_id = str(run_id or payload.get("source_run_id") or "")
    if not resolved_run_id:
        raise ValueError("Human selection review file is missing source_run_id")
    if run_id and payload.get("source_run_id") and payload["source_run_id"] != run_id:
        raise ValueError(
            f"Review file source_run_id={payload['source_run_id']} does not match {run_id}"
        )
    if not conn.execute(
        "SELECT 1 FROM run_manifests WHERE run_id = ?",
        (resolved_run_id,),
    ).fetchone():
        raise ValueError(f"Run manifest not found: {resolved_run_id}")

    papers = payload.get("papers")
    if not isinstance(papers, list) or not papers:
        raise ValueError("Human selection review file must contain at least one paper")

    reviewed = [_validated_review_item(item) for item in papers]
    pending = [item for item in reviewed if item["human_review"]["status"] != "accepted"]
    if pending:
        paper_ids = ", ".join(item["paper_id"] for item in pending[:5])
        raise ValueError(
            "All papers must have human_review.status='accepted' before applying "
            f"the selection review. Pending examples: {paper_ids}"
        )
    _validate_unique_paper_ids(reviewed)
    _validate_reviewed_papers(conn, run_id=resolved_run_id, items=reviewed)

    conn.execute(
        """
        DELETE FROM candidate_selections
        WHERE run_id = ?
          AND selection_stage IN ('deep_dive_draft', 'short_mention')
        """,
        (resolved_run_id,),
    )

    deviation_count = 0
    for item in reviewed:
        agent = item["agent_assessment"]
        human = item["human_review"]
        deviation = _has_deviation(agent, human)
        if deviation:
            deviation_count += 1
        upsert_human_selection_review(
            conn,
            run_id=resolved_run_id,
            paper_id=item["paper_id"],
            review_file_path=str(path),
            review_status=human["status"],
            agent_selection_stage=agent["selection_stage"],
            agent_editorial_decision=agent["editorial_decision"],
            agent_publication_track=agent["publication_track"],
            agent_payload=agent,
            human_selection_stage=human["selection_stage"],
            human_editorial_decision=human["editorial_decision"],
            human_publication_track=human["publication_track"],
            human_notes=human["notes"],
            deviation=deviation,
        )

    deep_count = _write_human_selection_stage(
        conn,
        run_id=resolved_run_id,
        items=reviewed,
        stage="deep_dive_draft",
    )
    short_count = _write_human_selection_stage(
        conn,
        run_id=resolved_run_id,
        items=reviewed,
        stage="short_mention",
    )
    conn.commit()
    return HumanSelectionApplyResult(
        path=path,
        run_id=resolved_run_id,
        reviewed_count=len(reviewed),
        deviation_count=deviation_count,
        deep_dive_selected_count=deep_count,
        short_mention_selected_count=short_count,
    )


def _review_rows(conn: sqlite3.Connection, *, run_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
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
            editorial_decisions.memo_json,
            review_dossiers.evidence_count,
            GROUP_CONCAT(
                candidate_selections.selection_stage || ':' ||
                candidate_selections.rank || ':' ||
                printf('%.4f', candidate_selections.selection_score),
                '|'
            ) AS selection_summary
        FROM editorial_decisions
        JOIN papers ON papers.id = editorial_decisions.paper_id
        LEFT JOIN sources ON sources.id = papers.source_id
        LEFT JOIN triage_reviews
          ON triage_reviews.paper_id = papers.id
         AND triage_reviews.run_id = editorial_decisions.run_id
        LEFT JOIN review_dossiers
          ON review_dossiers.id = editorial_decisions.dossier_id
        LEFT JOIN candidate_selections
          ON candidate_selections.paper_id = papers.id
         AND candidate_selections.run_id = editorial_decisions.run_id
        WHERE editorial_decisions.run_id = ?
          AND editorial_decisions.status = 'ok'
        GROUP BY papers.id
        ORDER BY
            CASE WHEN SUM(candidate_selections.selection_stage = 'deep_dive_draft') > 0 THEN 0
                 WHEN SUM(candidate_selections.selection_stage = 'short_mention') > 0 THEN 1
                 ELSE 2
            END,
            editorial_decisions.deep_dive_score DESC,
            papers.title ASC
        """,
        (run_id,),
    ).fetchall()


def _review_item(row: sqlite3.Row) -> dict[str, Any]:
    selections = _selection_map(row["selection_summary"])
    agent_selection_stage = _agent_selection_stage(selections)
    agent_track = _publication_track(row)
    agent_decision = str(row["editorial_decision"])
    return {
        "paper_id": row["paper_id"],
        "title": row["title"],
        "authors": row["authors"],
        "canonical_url": row["canonical_url"],
        "published_date": row["published_date"],
        "source_name": row["source_name"],
        "abstract": row["abstract"],
        "agent_assessment": {
            "selection_stage": agent_selection_stage,
            "editorial_decision": agent_decision,
            "publication_track": agent_track,
            "deep_dive_score": _optional_float(row["deep_dive_score"]),
            "confidence": _optional_float(row["editorial_confidence"]),
            "selection": selections,
            "evidence_count": int(row["evidence_count"] or 0),
            "triage": {
                "decision": row["triage_decision"],
                "category_hint": row["triage_category_hint"],
                "score": _optional_float(row["triage_score"]),
                "confidence": _optional_float(row["triage_confidence"]),
                "reason": row["triage_reason"],
            },
            "memo": _load_json(row["memo_json"]),
        },
        "human_review": {
            "status": "pending",
            "selection_stage": agent_selection_stage,
            "editorial_decision": agent_decision,
            "publication_track": agent_track,
            "notes": "",
        },
    }


def _validated_review_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Each human selection paper must be an object")
    paper_id = str(item.get("paper_id") or "")
    if not paper_id:
        raise ValueError("Human selection paper is missing paper_id")
    agent = item.get("agent_assessment")
    human = item.get("human_review")
    if not isinstance(agent, dict) or not isinstance(human, dict):
        raise ValueError(f"Paper {paper_id} is missing agent_assessment or human_review")

    status = _required_choice(
        human,
        "status",
        VALID_HUMAN_REVIEW_STATUSES,
        paper_id=paper_id,
    )
    human_selection_stage = _required_choice(
        human,
        "selection_stage",
        VALID_SELECTION_STAGES,
        paper_id=paper_id,
    )
    human_editorial_decision = _required_choice(
        human,
        "editorial_decision",
        VALID_EDITORIAL_DECISIONS,
        paper_id=paper_id,
    )
    human_publication_track = _required_choice(
        human,
        "publication_track",
        VALID_PUBLICATION_TRACKS,
        paper_id=paper_id,
    )
    normalized_human = {
        "status": status,
        "selection_stage": human_selection_stage,
        "editorial_decision": human_editorial_decision,
        "publication_track": human_publication_track,
        "notes": str(human.get("notes") or "").strip(),
    }

    normalized_agent = {
        "selection_stage": _optional_choice(
            agent.get("selection_stage"),
            VALID_SELECTION_STAGES,
            paper_id=paper_id,
            field="agent_assessment.selection_stage",
        )
        or "not_selected",
        "editorial_decision": _optional_choice(
            agent.get("editorial_decision"),
            VALID_EDITORIAL_DECISIONS,
            paper_id=paper_id,
            field="agent_assessment.editorial_decision",
        ),
        "publication_track": _optional_choice(
            agent.get("publication_track"),
            VALID_PUBLICATION_TRACKS,
            paper_id=paper_id,
            field="agent_assessment.publication_track",
        ),
        "deep_dive_score": agent.get("deep_dive_score"),
        "confidence": agent.get("confidence"),
        "selection": agent.get("selection") or {},
        "evidence_count": agent.get("evidence_count"),
        "triage": agent.get("triage") or {},
        "memo": agent.get("memo") or {},
    }

    if status == "accepted" and _has_deviation(normalized_agent, normalized_human):
        if not normalized_human["notes"]:
            raise ValueError(
                f"Paper {paper_id} changes the agent assessment but has empty human_review.notes"
            )

    normalized = dict(item)
    normalized["paper_id"] = paper_id
    normalized["agent_assessment"] = normalized_agent
    normalized["human_review"] = normalized_human
    return normalized


def _write_human_selection_stage(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    items: list[dict[str, Any]],
    stage: str,
) -> int:
    selected = [item for item in items if item["human_review"]["selection_stage"] == stage]
    for rank, item in enumerate(selected, start=1):
        human = item["human_review"]
        conn.execute(
            """
            INSERT INTO candidate_selections (
                run_id, paper_id, selection_stage, rank, selection_score, forced, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                item["paper_id"],
                stage,
                rank,
                _selection_score(item),
                1,
                _human_selection_reason(human),
            ),
        )
    return len(selected)


def _human_selection_reason(human: dict[str, Any]) -> str:
    reason = (
        "human selection review; "
        f"editorial_decision={human['editorial_decision']}; "
        f"publication_track={human['publication_track']}"
    )
    if human["notes"]:
        reason += f"; note={human['notes']}"
    return reason


def _selection_score(item: dict[str, Any]) -> float:
    agent = item["agent_assessment"]
    stage = item["human_review"]["selection_stage"]
    selection = agent.get("selection") or {}
    if isinstance(selection, dict) and stage in selection:
        stage_selection = selection[stage]
        if isinstance(stage_selection, dict) and stage_selection.get("score") is not None:
            return float(stage_selection["score"])
    score = agent.get("deep_dive_score")
    return 0.0 if score is None else round(float(score), 4)


def _has_deviation(agent: dict[str, Any], human: dict[str, Any]) -> bool:
    return (
        human["selection_stage"] != agent.get("selection_stage")
        or human["editorial_decision"] != agent.get("editorial_decision")
        or human["publication_track"] != agent.get("publication_track")
    )


def _validate_unique_paper_ids(items: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        paper_id = item["paper_id"]
        if paper_id in seen:
            duplicates.add(paper_id)
        seen.add(paper_id)
    if duplicates:
        raise ValueError(f"Duplicate human selection paper ids: {', '.join(sorted(duplicates))}")


def _validate_reviewed_papers(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    items: list[dict[str, Any]],
) -> None:
    rows = conn.execute(
        """
        SELECT paper_id
        FROM editorial_decisions
        WHERE run_id = ? AND status = 'ok'
        """,
        (run_id,),
    ).fetchall()
    reviewed_paper_ids = {str(row["paper_id"]) for row in rows}
    missing = sorted(item["paper_id"] for item in items if item["paper_id"] not in reviewed_paper_ids)
    if missing:
        raise ValueError(
            "Human selection review contains papers without successful panel review: "
            + ", ".join(missing[:5])
        )


def _agent_selection_stage(selections: dict[str, dict[str, float | int]]) -> str:
    if "deep_dive_draft" in selections:
        return "deep_dive_draft"
    if "short_mention" in selections:
        return "short_mention"
    return "not_selected"


def _selection_map(value: str | None) -> dict[str, dict[str, float | int]]:
    selections: dict[str, dict[str, float | int]] = {}
    if not value:
        return selections
    for item in str(value).split("|"):
        stage, rank, score = item.split(":", maxsplit=2)
        selections[stage] = {"rank": int(rank), "score": float(score)}
    return selections


def _publication_track(row: sqlite3.Row) -> str:
    memo = _load_json(row["memo_json"])
    if isinstance(memo, dict) and memo.get("publication_track") in VALID_PUBLICATION_TRACKS:
        return str(memo["publication_track"])
    decision = str(row["editorial_decision"])
    if decision == "full_deep_dive":
        return "deep_dive"
    if decision == "short_mention":
        return "applied_note"
    if decision == "watchlist":
        return "methods_watch"
    return "reject"


def _load_json(value: str | None) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _required_choice(
    raw: dict[str, Any],
    field: str,
    choices: set[str],
    *,
    paper_id: str,
) -> str:
    value = raw.get(field)
    if value is None:
        raise ValueError(f"Paper {paper_id} is missing human_review.{field}")
    value = str(value)
    if value not in choices:
        raise ValueError(f"Paper {paper_id} has invalid human_review.{field}: {value}")
    return value


def _optional_choice(
    value: Any,
    choices: set[str],
    *,
    paper_id: str,
    field: str,
) -> str | None:
    if value is None:
        return None
    value = str(value)
    if value not in choices:
        raise ValueError(f"Paper {paper_id} has invalid {field}: {value}")
    return value
