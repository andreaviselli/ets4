from ets4.cli import main
from ets4.store.db import connect, init_db, upsert_paper, upsert_source
from ets4.config import load_config


def test_cli_init_manifest_and_triage(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    config_path = "config/feeds.example.toml"

    assert main(["--config", config_path, "--db", str(db_path), "init-db"]) == 0
    assert (
        main(
            [
                "--config",
                config_path,
                "--db",
                str(db_path),
                "manifest",
                "--issue-date",
                "2026-06-08",
            ]
        )
        == 0
    )

    with connect(db_path) as conn:
        run_id = conn.execute("SELECT run_id FROM run_manifests LIMIT 1").fetchone()[0]

    assert (
        main(
            [
                "--config",
                config_path,
                "--db",
                str(db_path),
                "collect",
                "--dry-run",
                "--run-id",
                run_id,
            ]
        )
        == 0
    )

    config = load_config(config_path)
    with connect(db_path) as conn:
        init_db(conn)
        upsert_source(conn, config.sources[0])
        upsert_paper(
            conn,
            paper_id="paper-1",
            title="Oil price forecasting with probabilistic models",
            canonical_url="https://example.test/paper-1",
            abstract="We forecast oil prices using financial time series.",
            source_id=config.sources[0].id,
        )
        conn.commit()

    assert (
        main(
            [
                "--config",
                config_path,
                "--db",
                str(db_path),
                "triage",
                "--issue-date",
                "2026-06-08",
            ]
        )
        == 0
    )

    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM triage_reviews").fetchone()[0] == 1
        assert conn.execute("SELECT status FROM papers").fetchone()[0] == "selected_for_review"
        assert conn.execute("SELECT COUNT(*) FROM candidate_selections").fetchone()[0] == 1


def test_cli_extract_explicit_document(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    config_path = "config/feeds.example.toml"
    fixture_path = "tests/fixtures/documents/sample.txt"

    assert main(["--config", config_path, "--db", str(db_path), "init-db"]) == 0
    config = load_config(config_path)
    with connect(db_path) as conn:
        init_db(conn)
        upsert_source(conn, config.sources[0])
        upsert_paper(
            conn,
            paper_id="paper-1",
            title="Inflation forecasting",
            canonical_url="https://example.test/paper-1",
            source_id=config.sources[0].id,
        )
        conn.commit()

    assert (
        main(
            [
                "--config",
                config_path,
                "--db",
                str(db_path),
                "extract",
                "--issue-date",
                "2026-06-08",
                "--paper-id",
                "paper-1",
                "--source",
                fixture_path,
            ]
        )
        == 0
    )

    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM document_pages").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM evidence_items").fetchone()[0] >= 4
        run_id = conn.execute("SELECT run_id FROM run_manifests LIMIT 1").fetchone()[0]

    assert (
        main(
            [
                "--config",
                config_path,
                "--db",
                str(db_path),
                "review",
                "--run-id",
                run_id,
                "--paper-id",
                "paper-1",
            ]
        )
        == 0
    )

    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM review_dossiers").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM reviewer_reports").fetchone()[0] == 5
        assert (
            conn.execute("SELECT decision FROM editorial_decisions").fetchone()[0]
            == "full_deep_dive"
        )
        assert (
            conn.execute(
                """
                SELECT COUNT(*) FROM candidate_selections
                WHERE selection_stage = 'deep_dive_draft'
                """
            ).fetchone()[0]
            == 1
        )
