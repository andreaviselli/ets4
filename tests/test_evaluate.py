import json
from datetime import date

from ets4.cli import main
from ets4.config import load_config
from ets4.documents import process_document_for_paper
from ets4.evaluate import create_benchmark_template, evaluate_run, load_benchmark
from ets4.manifest import create_manifest
from ets4.models import FakeModelProvider
from ets4.review import run_panel_review_for_paper
from ets4.selection import select_full_review_candidates, select_publication_candidates
from ets4.store.db import connect, init_db, insert_manifest, upsert_paper

LABELS_PATH = "tests/fixtures/evaluation/benchmark.json"


def test_load_benchmark_fixture() -> None:
    benchmark = load_benchmark(LABELS_PATH)

    assert benchmark.version == "phase5-fixture-v1"
    assert len(benchmark.labels) == 2
    assert benchmark.labels[0].paper_id == "paper-1"
    assert benchmark.labels[1].hard_negative is True


def test_evaluate_run_persists_metrics_and_items(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_evaluable_run(db_path)

    with connect(db_path) as conn:
        result = evaluate_run(conn, run_id=run_id, labels_path=LABELS_PATH)

        assert result.metrics["labeled_papers"] == 2
        assert result.metrics["triage"]["decision_accuracy"] == 1.0
        assert result.metrics["triage"]["hard_negative_false_positive_rate"] == 0.0
        assert result.metrics["evidence"]["required_kind_coverage"] == 1.0
        assert result.metrics["review"]["editorial_decision_accuracy"] == 1.0
        assert result.metrics["selection"]["deep_dive_accuracy"] == 1.0
        assert conn.execute("SELECT COUNT(*) FROM evaluation_runs").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM evaluation_items").fetchone()[0] == 2


def test_cli_evaluate_completed_run(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_evaluable_run(db_path)

    assert (
        main(
            [
                "--config",
                "config/feeds.example.toml",
                "--db",
                str(db_path),
                "evaluate",
                "--run-id",
                run_id,
                "--labels",
                LABELS_PATH,
            ]
        )
        == 0
    )

    with connect(db_path) as conn:
        assert conn.execute("SELECT benchmark_version FROM evaluation_runs").fetchone()[0] == (
            "phase5-fixture-v1"
        )


def test_create_benchmark_template_requires_human_acceptance(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    output_path = tmp_path / "benchmark-template.json"
    run_id = _create_evaluable_run(db_path)

    with connect(db_path) as conn:
        result = create_benchmark_template(conn, run_id=run_id, output_path=output_path)

    assert result.paper_count == 2
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["source_run_id"] == run_id
    assert payload["papers"][0]["label_status"] == "needs_human_label"
    assert payload["papers"][0]["system_context"]["selection"]

    try:
        load_benchmark(output_path)
    except ValueError as exc:
        assert "set label_status to 'accepted'" in str(exc)
    else:
        raise AssertionError("draft benchmark template should not load as accepted labels")


def test_cli_benchmark_template_writes_editable_json(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    output_path = tmp_path / "benchmark-template.json"
    run_id = _create_evaluable_run(db_path)

    assert (
        main(
            [
                "--config",
                "config/feeds.example.toml",
                "--db",
                str(db_path),
                "benchmark-template",
                "--run-id",
                run_id,
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["version"] == f"{run_id}-human-v1"
    assert len(payload["papers"]) == 2
    assert payload["papers"][0]["relevance_label"] is None


def _create_evaluable_run(db_path) -> str:
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
        upsert_paper(
            conn,
            paper_id="paper-2",
            title="Structural VAR evidence on monetary policy transmission",
            canonical_url="https://example.test/paper-2",
            abstract="We estimate causal impulse responses and variance decompositions.",
        )
        _triage_all(conn, run_id=manifest.run_id, provider=provider)
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


def _triage_all(conn, *, run_id: str, provider: FakeModelProvider) -> None:
    rows = conn.execute(
        "SELECT id, title, abstract FROM papers ORDER BY id ASC",
    ).fetchall()
    for row in rows:
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
    conn.commit()
