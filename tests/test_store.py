from datetime import date

from ets4.config import load_config
from ets4.manifest import create_manifest
from ets4.store.db import (
    connect,
    init_db,
    insert_manifest,
    insert_source_event,
    upsert_paper,
    upsert_source,
)


def test_init_db_and_insert_records(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(db_path) as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        upsert_source(conn, config.sources[0])
        upsert_paper(
            conn,
            paper_id="paper-1",
            title="GDP forecasting",
            canonical_url="https://example.test/paper-1",
            abstract="Forecasting GDP.",
            source_id=config.sources[0].id,
        )
        conn.commit()

        assert conn.execute("SELECT COUNT(*) FROM run_manifests").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 1


def test_upsert_paper_deduplicates_by_doi_arxiv_url_and_fuzzy_title(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    with connect(db_path) as conn:
        init_db(conn)
        first_id = upsert_paper(
            conn,
            paper_id="paper-1",
            title="Inflation Forecasting with Probabilistic Time Series Models",
            canonical_url="https://arxiv.org/abs/2601.12345?utm_source=test",
            abstract="Forecasting inflation.",
            doi="10.1234/ets4.2026.001",
            arxiv_id="2601.12345",
        )
        fuzzy_duplicate = upsert_paper(
            conn,
            paper_id="paper-4",
            title="Inflation forecasting with probabilistic time series model",
            canonical_url="https://example.test/fuzzy",
        )
        doi_duplicate = upsert_paper(
            conn,
            paper_id="paper-2",
            title="Inflation Forecasting with Probabilistic Time-Series Models",
            canonical_url="https://example.test/working-paper",
            abstract="Updated abstract.",
            doi="10.1234/ets4.2026.001",
        )
        arxiv_duplicate = upsert_paper(
            conn,
            paper_id="paper-3",
            title="Different title",
            canonical_url="https://arxiv.org/pdf/2601.12345",
            arxiv_id="2601.12345",
        )
        conn.commit()

        assert first_id == "paper-1"
        assert doi_duplicate == "paper-1"
        assert arxiv_duplicate == "paper-1"
        assert fuzzy_duplicate == "paper-1"
        assert conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 1


def test_source_events_are_persistent(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(db_path) as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        upsert_source(conn, config.sources[0])
        insert_source_event(
            conn,
            source_id=config.sources[0].id,
            run_id=manifest.run_id,
            status="ok",
            message="Collected 2 candidates",
            candidate_count=2,
        )
        conn.commit()

        row = conn.execute("SELECT status, candidate_count FROM source_events").fetchone()
        assert row["status"] == "ok"
        assert row["candidate_count"] == 2
