from datetime import date

from ets4.config import load_config
from ets4.manifest import create_manifest
from ets4.store.db import connect, init_db, insert_manifest, upsert_paper, upsert_source


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

