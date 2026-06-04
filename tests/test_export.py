from datetime import date

import pytest

from ets4.cli import main
from ets4.config import load_config
from ets4.documents import process_document_for_paper
from ets4.export import export_run
from ets4.export.writer import ExportWriteError
from ets4.manifest import create_manifest
from ets4.models import FakeModelProvider
from ets4.review import run_panel_review_for_paper
from ets4.selection import select_full_review_candidates, select_publication_candidates
from ets4.store.db import connect, init_db, insert_manifest, upsert_paper


def test_export_run_writes_draft_and_internal_notes(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_reviewed_run(db_path)

    with connect(db_path) as conn:
        result = export_run(conn, run_id=run_id, output_dir=tmp_path / "exports")

        assert result.artifact_count == 2
        issue_path = result.output_dir / "issue.md"
        notes_path = result.output_dir / "internal-notes.md"
        assert issue_path.exists()
        assert notes_path.exists()
        assert "draft: true" in issue_path.read_text(encoding="utf-8")
        assert "Claim ledger:" in issue_path.read_text(encoding="utf-8")
        assert "Final human decision: TODO" in notes_path.read_text(encoding="utf-8")
        assert conn.execute("SELECT COUNT(*) FROM export_artifacts").fetchone()[0] == 2


def test_export_refuses_to_overwrite_human_edits_without_force(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_reviewed_run(db_path)

    with connect(db_path) as conn:
        result = export_run(conn, run_id=run_id, output_dir=tmp_path / "exports")
        export_run(conn, run_id=run_id, output_dir=tmp_path / "exports")
        issue_path = result.output_dir / "issue.md"
        issue_path.write_text(
            issue_path.read_text(encoding="utf-8") + "\nHuman edit.\n",
            encoding="utf-8",
        )

        with pytest.raises(ExportWriteError):
            export_run(conn, run_id=run_id, output_dir=tmp_path / "exports")

        forced = export_run(conn, run_id=run_id, output_dir=tmp_path / "exports", force=True)
        assert forced.artifact_count == 2


def test_cli_export_completed_run(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_reviewed_run(db_path)
    output_dir = tmp_path / "exports"

    assert (
        main(
            [
                "--config",
                "config/feeds.example.toml",
                "--db",
                str(db_path),
                "export",
                "--run-id",
                run_id,
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    assert (output_dir / "ets4-2026-06-08" / "issue.md").exists()
    assert (output_dir / "ets4-2026-06-08" / "internal-notes.md").exists()


def _create_reviewed_run(db_path) -> str:
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config=config, issue_date=date(2026, 6, 8))
    provider = FakeModelProvider()
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
        result = provider.triage(
            "Inflation forecasting with probabilistic models",
            "We forecast inflation with macroeconomic predictors.",
        )
        conn.execute(
            """
            INSERT INTO triage_reviews (
                paper_id, run_id, provider, decision, category_hint,
                forecasting_signal, economic_signal, score, confidence, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "paper-1",
                manifest.run_id,
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
        select_full_review_candidates(conn, run_id=manifest.run_id, config=config)
        process_document_for_paper(
            conn,
            paper_id="paper-1",
            source_uri="tests/fixtures/documents/sample.txt",
            run_id=manifest.run_id,
        )
        run_panel_review_for_paper(
            conn,
            paper_id="paper-1",
            run_id=manifest.run_id,
            provider=provider,
        )
        select_publication_candidates(conn, run_id=manifest.run_id, config=config)
    return manifest.run_id
