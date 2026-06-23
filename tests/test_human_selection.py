from __future__ import annotations

from datetime import date
import json

import pytest

from ets4.config import load_config
from ets4.human_selection import (
    apply_human_selection_review,
    create_human_selection_review_template,
)
from ets4.manifest import create_manifest
from ets4.store.db import connect, init_db, insert_manifest, upsert_paper


def test_human_selection_review_applies_final_publication_choices(tmp_path) -> None:
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config, date(2026, 6, 8))
    review_path = tmp_path / "selection-review.json"

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        _reviewed_paper(
            conn,
            run_id=manifest.run_id,
            paper_id="paper-1",
            title="Scenario forecasting with policy relevance",
            decision="full_deep_dive",
            publication_track="deep_dive",
            selection_stage="deep_dive_draft",
            selection_rank=1,
        )
        _reviewed_paper(
            conn,
            run_id=manifest.run_id,
            paper_id="paper-2",
            title="Routine financial risk forecasting",
            decision="short_mention",
            publication_track="applied_note",
            selection_stage="short_mention",
            selection_rank=1,
        )
        conn.commit()

        result = create_human_selection_review_template(
            conn,
            run_id=manifest.run_id,
            output_path=review_path,
        )

        assert result.paper_count == 2

    payload = json.loads(review_path.read_text(encoding="utf-8"))
    for paper in payload["papers"]:
        paper["human_review"]["status"] = "accepted"
        if paper["paper_id"] == "paper-1":
            paper["human_review"]["selection_stage"] = "short_mention"
            paper["human_review"]["editorial_decision"] = "short_mention"
            paper["human_review"]["publication_track"] = "applied_note"
            paper["human_review"]["notes"] = "Useful applied note, not a main deep dive."
        if paper["paper_id"] == "paper-2":
            paper["human_review"]["selection_stage"] = "not_selected"
            paper["human_review"]["editorial_decision"] = "reject"
            paper["human_review"]["publication_track"] = "reject"
            paper["human_review"]["notes"] = "Too routine for the issue."
    review_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        applied = apply_human_selection_review(conn, input_path=review_path)

        assert applied.deep_dive_selected_count == 0
        assert applied.short_mention_selected_count == 1
        assert applied.deviation_count == 2
        selections = conn.execute(
            """
            SELECT paper_id, selection_stage, rank, forced, reason
            FROM candidate_selections
            WHERE run_id = ?
            ORDER BY selection_stage, rank
            """,
            (manifest.run_id,),
        ).fetchall()
        assert [(row["paper_id"], row["selection_stage"]) for row in selections] == [
            ("paper-1", "short_mention")
        ]
        assert selections[0]["forced"] == 1
        assert "Useful applied note" in selections[0]["reason"]
        registry_rows = conn.execute(
            """
            SELECT paper_id, human_selection_stage, human_notes, deviation
            FROM human_selection_reviews
            WHERE run_id = ?
            ORDER BY paper_id
            """,
            (manifest.run_id,),
        ).fetchall()
        assert [row["deviation"] for row in registry_rows] == [1, 1]
        assert registry_rows[0]["human_selection_stage"] == "short_mention"
        assert registry_rows[1]["human_notes"] == "Too routine for the issue."


def test_human_selection_review_requires_notes_for_deviations(tmp_path) -> None:
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config, date(2026, 6, 8))
    review_path = tmp_path / "selection-review.json"

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        _reviewed_paper(
            conn,
            run_id=manifest.run_id,
            paper_id="paper-1",
            title="Applied inflation forecast",
            decision="full_deep_dive",
            publication_track="deep_dive",
            selection_stage="deep_dive_draft",
            selection_rank=1,
        )
        conn.commit()
        create_human_selection_review_template(
            conn,
            run_id=manifest.run_id,
            output_path=review_path,
        )

    payload = json.loads(review_path.read_text(encoding="utf-8"))
    payload["papers"][0]["human_review"]["status"] = "accepted"
    payload["papers"][0]["human_review"]["selection_stage"] = "not_selected"
    review_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        with pytest.raises(ValueError, match="empty human_review.notes"):
            apply_human_selection_review(conn, input_path=review_path)


def _reviewed_paper(
    conn,
    *,
    run_id: str,
    paper_id: str,
    title: str,
    decision: str,
    publication_track: str,
    selection_stage: str,
    selection_rank: int,
) -> None:
    upsert_paper(
        conn,
        paper_id=paper_id,
        title=title,
        canonical_url=f"https://example.test/{paper_id}",
        abstract="Applied forecasting paper.",
    )
    conn.execute(
        """
        INSERT INTO triage_reviews (
            paper_id, run_id, provider, decision, category_hint,
            forecasting_signal, economic_signal, score, confidence, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paper_id,
            run_id,
            "fake",
            "assign_reviewers",
            "directly_relevant",
            "explicit",
            "explicit",
            8.0,
            0.75,
            "fixture",
        ),
    )
    conn.execute(
        """
        INSERT INTO review_dossiers (
            id, paper_id, run_id, document_id, evidence_count, dossier_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"dossier-{paper_id}",
            paper_id,
            run_id,
            None,
            8,
            "{}",
            "ok",
        ),
    )
    conn.execute(
        """
        INSERT INTO editorial_decisions (
            id, paper_id, run_id, dossier_id, provider, decision,
            deep_dive_score, confidence, memo_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"decision-{paper_id}",
            paper_id,
            run_id,
            f"dossier-{paper_id}",
            "fake",
            decision,
            8.0 - selection_rank,
            0.8,
            json.dumps(
                {
                    "decision": decision,
                    "publication_track": publication_track,
                    "deep_dive_score": 8.0 - selection_rank,
                    "confidence": 0.8,
                    "rationale": "fixture",
                }
            ),
            "ok",
        ),
    )
    conn.execute(
        """
        INSERT INTO candidate_selections (
            run_id, paper_id, selection_stage, rank, selection_score, forced, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            paper_id,
            selection_stage,
            selection_rank,
            8.0 - selection_rank,
            0,
            "agent fixture",
        ),
    )
