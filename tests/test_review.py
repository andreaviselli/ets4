from datetime import date
import json

from ets4.config import load_config
from ets4.documents import process_document_for_paper
from ets4.manifest import create_manifest
from ets4.models import FakeModelProvider
from ets4.review import build_evidence_dossier, run_panel_review_for_paper
from ets4.review.schemas import REVIEWER_ROLES
from ets4.selection import select_publication_candidates
from ets4.store.db import connect, init_db, insert_manifest, upsert_paper


def test_build_evidence_dossier_from_extracted_document(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config=config, issue_date=date(2026, 6, 8))

    with connect(db_path) as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        upsert_paper(
            conn,
            paper_id="paper-1",
            title="Inflation forecasting with probabilistic models",
            canonical_url="https://example.test/paper-1",
            abstract="We forecast inflation with macroeconomic predictors.",
        )
        process_document_for_paper(
            conn,
            paper_id="paper-1",
            source_uri="tests/fixtures/documents/sample.txt",
            run_id=manifest.run_id,
        )

        dossier = build_evidence_dossier(conn, paper_id="paper-1", run_id=manifest.run_id)

    assert dossier.paper_id == "paper-1"
    assert dossier.evidence_count >= 5
    assert dossier.payload["document"]["page_count"] == 2
    assert dossier.payload["review_constraints"]["must_cite_evidence_item_ids"] is True


def test_panel_review_persists_independent_reports_and_editor_decision(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config=config, issue_date=date(2026, 6, 8))

    with connect(db_path) as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        upsert_paper(
            conn,
            paper_id="paper-1",
            title="Inflation forecasting with probabilistic models",
            canonical_url="https://example.test/paper-1",
            abstract="We forecast inflation with macroeconomic predictors.",
        )
        process_document_for_paper(
            conn,
            paper_id="paper-1",
            source_uri="tests/fixtures/documents/sample.txt",
            run_id=manifest.run_id,
        )

        result = run_panel_review_for_paper(
            conn,
            paper_id="paper-1",
            run_id=manifest.run_id,
            provider=FakeModelProvider(),
        )

        assert result.status == "ok"
        assert result.reviewer_count == len(REVIEWER_ROLES)
        assert result.decision == "full_deep_dive"
        selection = select_publication_candidates(conn, run_id=manifest.run_id, config=config)
        assert selection.deep_dive_selected_count == 1
        assert selection.short_mention_selected_count == 0
        assert conn.execute("SELECT COUNT(*) FROM review_dossiers").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM reviewer_reports").fetchone()[0] == len(
            REVIEWER_ROLES
        )
        assert conn.execute("SELECT COUNT(*) FROM editorial_decisions").fetchone()[0] == 1
        assert (
            conn.execute(
                """
                SELECT COUNT(*) FROM candidate_selections
                WHERE selection_stage = 'deep_dive_draft'
                """
            ).fetchone()[0]
            == 1
        )
        report_row = conn.execute(
            "SELECT report_json FROM reviewer_reports WHERE reviewer_role = 'methods'"
        ).fetchone()
        report = json.loads(report_row["report_json"])
        assert report["role"] == "methods"
        assert report["evidence_item_ids"]
