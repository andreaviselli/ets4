from datetime import date

from ets4.cli import main
from ets4.config import load_config
from ets4.documents import process_document_for_paper
from ets4.export import export_run
from ets4.manifest import create_manifest
from ets4.models import FakeModelProvider
from ets4.ops.archive import create_archive_bundle
from ets4.ops.retry import RetryConfig, retry_call
from ets4.review import run_panel_review_for_paper
from ets4.selection import select_full_review_candidates, select_publication_candidates
from ets4.store.db import connect, init_db, insert_manifest, upsert_paper


def test_retry_call_retries_until_success() -> None:
    calls = {"count": 0}
    sleeps = []

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    result = retry_call(
        flaky,
        config=RetryConfig(attempts=3, backoff_seconds=0.1),
        sleep=sleeps.append,
    )

    assert result == "ok"
    assert calls["count"] == 3
    assert sleeps == [0.1, 0.2]


def test_archive_bundle_records_artifact(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_reviewed_run(db_path)

    with connect(db_path) as conn:
        export_run(conn, run_id=run_id, output_dir=tmp_path / "exports")
        result = create_archive_bundle(conn, run_id=run_id, archive_dir=tmp_path / "archives")

        assert result.path.exists()
        assert result.file_count >= 3
        assert conn.execute("SELECT COUNT(*) FROM archive_artifacts").fetchone()[0] == 1


def test_run_scheduled_exports_and_archives_without_publishing(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_reviewable_candidate(db_path)

    assert (
        main(
            [
                "--config",
                "config/feeds.example.toml",
                "--db",
                str(db_path),
                "run-scheduled",
                "--run-id",
                run_id,
                "--skip-collect",
                "--skip-extract",
                "--output-dir",
                str(tmp_path / "exports"),
                "--archive-dir",
                str(tmp_path / "archives"),
            ]
        )
        == 0
    )

    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM run_events").fetchone()[0] >= 5
        assert conn.execute("SELECT COUNT(*) FROM usage_records").fetchone()[0] >= 6
        assert conn.execute("SELECT COUNT(*) FROM export_artifacts").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM archive_artifacts").fetchone()[0] == 1


def _create_reviewable_candidate(db_path) -> str:
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
    return manifest.run_id


def _create_reviewed_run(db_path) -> str:
    config = load_config("config/feeds.example.toml")
    provider = FakeModelProvider()
    run_id = _create_reviewable_candidate(db_path)
    with connect(db_path) as conn:
        row = conn.execute("SELECT id, title, abstract FROM papers LIMIT 1").fetchone()
        result = provider.triage(row["title"], row["abstract"])
        conn.execute(
            """
            INSERT INTO triage_reviews (
                paper_id, run_id, provider, decision, category_hint,
                forecasting_signal, economic_signal, score, confidence, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                run_id,
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
        select_full_review_candidates(conn, run_id=run_id, config=config)
        run_panel_review_for_paper(
            conn,
            paper_id=row["id"],
            run_id=run_id,
            provider=provider,
            model_name=config.model_policy.review_model,
        )
        select_publication_candidates(conn, run_id=run_id, config=config)
    return run_id
