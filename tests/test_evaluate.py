import json
from datetime import date

from ets4.cli import main
from ets4.config import load_config
from ets4.documents import process_document_for_paper
from ets4.evaluate import (
    assess_provider_gate,
    benchmark_validation_dict,
    create_benchmark_subset,
    create_benchmark_template,
    error_summary_dict,
    evaluate_run,
    load_benchmark,
    validate_benchmark_file,
    provider_gate_dict,
)
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
    assert benchmark.labels[0].audience_fit == "practitioner"
    assert benchmark.labels[0].publication_track == "deep_dive"
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
        assert result.metrics["rubric"]["publication_track_accuracy"] == 1.0
        assert result.metrics["rubric"]["audience_fit_distribution"] == {
            "out_of_scope": 1,
            "practitioner": 1,
        }
        assert result.metrics["error_summary"]["mismatch_count"] == 0
        assert result.metrics["mismatches"] == []
        assert result.item_results[1]["editorial"]["present"] is False
        assert result.item_results[1]["editorial"]["decision"] == "reject"
        assert conn.execute("SELECT COUNT(*) FROM evaluation_runs").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM evaluation_items").fetchone()[0] == 2


def test_provider_gate_blocks_small_benchmark_before_provider_adoption(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_evaluable_run(db_path)
    validation = validate_benchmark_file(LABELS_PATH)

    with connect(db_path) as conn:
        result = evaluate_run(conn, run_id=run_id, labels_path=LABELS_PATH)

    gate = assess_provider_gate(
        metrics=result.metrics,
        item_results=result.item_results,
        benchmark_validation=validation,
    )
    payload = provider_gate_dict(gate)

    assert gate.ready is False
    assert gate.status == "not_ready"
    failed = {check["name"] for check in payload["checks"] if not check["passed"]}
    assert failed == {"benchmark_incomplete_labels", "labeled_papers", "full_review_examples"}
    assert payload["failed_count"] == 3


def test_evaluate_run_reports_per_paper_mismatches(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    labels_path = tmp_path / "mismatch-labels.json"
    run_id = _create_evaluable_run(db_path)
    labels_path.write_text(
        json.dumps(
            {
                "version": "mismatch-fixture-v1",
                "papers": [
                    {
                        "paper_id": "paper-1",
                        "label_status": "accepted",
                        "relevance_label": "directly_relevant",
                        "audience_fit": "practitioner",
                        "application_type": "forecasting",
                        "economic_relevance": "high",
                        "forecasting_contribution": "genuine_application",
                        "publication_track": "reject",
                        "social_hook_potential": "medium",
                        "expected_category": "not_relevant",
                        "expected_triage_decision": "reject",
                        "expected_editorial_decision": "reject",
                        "expected_deep_dive": False,
                        "expected_short_mention": True,
                        "required_evidence_kinds": ["method", "unavailable_kind"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with connect(db_path) as conn:
        result = evaluate_run(conn, run_id=run_id, labels_path=labels_path)

    mismatch_fields = {mismatch["field"] for mismatch in result.metrics["mismatches"]}
    assert mismatch_fields == {
        "category",
        "deep_dive_selection",
        "editorial_decision",
        "publication_track",
        "required_evidence",
        "short_mention_selection",
        "triage_decision",
    }
    assert result.metrics["mismatches"][0]["title"] == (
        "Inflation forecasting with probabilistic models"
    )
    assert result.metrics["mismatches"][0]["failure_type"] == "triage_overpromotion"
    assert result.metrics["error_summary"]["by_failure_type"] == {
        "deep_dive_overselection": 1,
        "editorial_overpromotion": 1,
        "evidence_kind_gap": 1,
        "publication_track_overpromotion": 1,
        "scope_overclassification": 1,
        "short_mention_underselection": 1,
        "triage_overpromotion": 1,
    }
    assert result.metrics["error_summary"]["missing_required_evidence_kinds"] == {
        "unavailable_kind": 1
    }
    assert result.metrics["error_summary"]["recommendations"] == [
        "Tighten desk-screening scope for practitioner/applied economic forecasting.",
        "Make handling-editor and publication-track gates more conservative before provider work.",
        "Review deep-dive ranking penalties for applied value, evidence quality, and track fit.",
        "Improve evidence extraction or kind mapping for: unavailable_kind.",
    ]
    assert result.mismatches[0].paper_id == "paper-1"
    assert any(
        mismatch["reason"] == "Missing required evidence kinds: unavailable_kind."
        for mismatch in result.metrics["mismatches"]
    )


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


def test_cli_evaluate_json_includes_provider_gate(tmp_path, capsys) -> None:
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
                "--gate",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["provider_gate"]["ready"] is False
    assert payload["provider_gate"]["status"] == "not_ready"
    assert {
        check["name"]
        for check in payload["provider_gate"]["checks"]
        if not check["passed"]
    } == {"benchmark_incomplete_labels", "labeled_papers", "full_review_examples"}


def test_cli_evaluate_errors_prints_mismatch_report(tmp_path, capsys) -> None:
    db_path = tmp_path / "ets4.sqlite"
    labels_path = tmp_path / "mismatch-labels.json"
    run_id = _create_evaluable_run(db_path)
    labels_path.write_text(
        json.dumps(
            {
                "version": "mismatch-fixture-v1",
                "papers": [
                    {
                        "paper_id": "paper-1",
                        "label_status": "accepted",
                        "relevance_label": "directly_relevant",
                        "audience_fit": "practitioner",
                        "application_type": "forecasting",
                        "economic_relevance": "high",
                        "forecasting_contribution": "genuine_application",
                        "publication_track": "reject",
                        "social_hook_potential": "medium",
                        "expected_category": "not_relevant",
                        "expected_triage_decision": "reject",
                        "expected_editorial_decision": "reject",
                        "expected_deep_dive": False,
                        "expected_short_mention": True,
                        "required_evidence_kinds": ["unavailable_kind"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

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
                str(labels_path),
                "--errors",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "Error summary:" in output
    assert "triage_overpromotion: 1" in output
    assert "Improve evidence extraction or kind mapping for: unavailable_kind." in output
    assert "Mismatches: 7" in output
    assert "- Inflation forecasting with probabilistic models [paper-1]" in output
    assert (
        "triage_decision: human=reject; system=assign_reviewers; "
        "type=triage_overpromotion" in output
    )
    assert "required_evidence: human=[unavailable_kind]" in output


def test_cli_replay_baseline_evaluates_source_run_papers(tmp_path, capsys) -> None:
    db_path = tmp_path / "ets4.sqlite"
    run_id = _create_evaluable_run(db_path)

    assert (
        main(
            [
                "--config",
                "config/feeds.example.toml",
                "--db",
                str(db_path),
                "replay-baseline",
                "--source-run-id",
                run_id,
                "--labels",
                LABELS_PATH,
                "--errors",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert f"Source run: {run_id}" in output
    assert "Replay run: run-" in output
    assert "Triaged papers: 2" in output
    assert "Selected for full review: 1/1 eligible candidates" in output
    assert "Panel-reviewed papers: 1" in output
    assert "Triage decision accuracy: 1.000" in output
    assert "Error summary:" in output
    assert "Mismatches: 0" in output
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM run_manifests").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM evaluation_runs").fetchone()[0] == 1
        replay_run_id = conn.execute(
            "SELECT run_id FROM run_manifests WHERE run_id != ?",
            (run_id,),
        ).fetchone()[0]
        assert conn.execute(
            "SELECT COUNT(*) FROM triage_reviews WHERE run_id = ?",
            (replay_run_id,),
        ).fetchone()[0] == 2


def test_error_summary_dict_groups_by_failure_type() -> None:
    items = (
        {
            "paper_id": "paper-1",
            "title": "Forecasting paper",
            "label": {
                "expected_triage_decision": "reject",
                "expected_category": "not_relevant",
                "expected_editorial_decision": "reject",
                "expected_deep_dive": False,
                "expected_short_mention": False,
                "publication_track": "reject",
                "required_evidence_kinds": ["scenario"],
            },
            "triage": {"decision": "assign_reviewers", "category_hint": "directly_relevant"},
            "selection": {"selected_deep_dive": True, "selected_short_mention": False},
            "evidence": {
                "evidence_kinds": ["method"],
                "missing_required_kinds": ["scenario"],
            },
            "editorial": {"decision": "full_deep_dive", "publication_track": "deep_dive"},
        },
    )

    summary = error_summary_dict(items)

    assert summary["mismatch_count"] == 6
    assert summary["paper_count"] == 1
    assert summary["by_field"]["required_evidence"] == 1
    assert summary["by_failure_type"]["publication_track_overpromotion"] == 1
    assert summary["missing_required_evidence_kinds"] == {"scenario": 1}


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


def test_validate_benchmark_template_reports_draft_incomplete_labels(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    output_path = tmp_path / "benchmark-template.json"
    run_id = _create_evaluable_run(db_path)

    with connect(db_path) as conn:
        create_benchmark_template(conn, run_id=run_id, output_path=output_path)

    result = validate_benchmark_file(output_path)

    assert result.paper_count == 2
    assert result.accepted_count == 0
    assert result.not_accepted_count == 2
    assert result.incomplete_count == 2
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.ready_for_evaluation is False
    assert result.paper_statuses[0].label_status == "needs_human_label"
    assert "relevance_label" in result.paper_statuses[0].missing_fields
    assert "audience_fit" in result.paper_statuses[0].missing_fields
    assert "publication_track" in result.paper_statuses[0].missing_fields


def test_validate_benchmark_file_reports_label_consistency_warnings(tmp_path) -> None:
    labels_path = tmp_path / "warning-labels.json"
    labels_path.write_text(
        json.dumps(
            {
                "version": "warning-fixture-v1",
                "papers": [
                    {
                        "paper_id": "paper-1",
                        "label_status": "accepted",
                        "title": "Applied method paper",
                        "relevance_label": "directly_relevant",
                        "audience_fit": "applied_researcher",
                        "application_type": "forecasting",
                        "economic_relevance": "medium",
                        "forecasting_contribution": "novel_method",
                        "publication_track": "applied_note",
                        "expected_category": "directly_relevant",
                        "expected_triage_decision": "assign_reviewers",
                        "expected_editorial_decision": "full_deep_dive",
                        "expected_deep_dive": True,
                        "expected_short_mention": True,
                        "required_evidence_kinds": ["method"],
                        "hard_negative": False,
                        "high_value": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = validate_benchmark_file(labels_path)

    assert result.ready_for_evaluation is True
    assert result.error_count == 0
    assert result.warning_count == 2
    warnings = result.paper_statuses[0].warnings
    assert tuple(warning.code for warning in warnings) == (
        "full_deep_dive_with_non_deep_dive_track",
        "full_deep_dive_with_short_mention_selection",
    )
    payload = benchmark_validation_dict(result)
    assert payload["warning_count"] == 2
    assert payload["warnings"][0]["paper_id"] == "paper-1"
    assert payload["warnings"][0]["fields"] == [
        "expected_editorial_decision",
        "publication_track",
    ]
    assert "Choose whether this paper belongs" in payload["warnings"][0]["suggested_action"]


def test_create_benchmark_subset_preserves_draft_labels(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    template_path = tmp_path / "benchmark-template.json"
    subset_path = tmp_path / "benchmark-subset.json"
    run_id = _create_evaluable_run(db_path)

    with connect(db_path) as conn:
        create_benchmark_template(conn, run_id=run_id, output_path=template_path)

    result = create_benchmark_subset(template_path, subset_path, size=1)

    assert result.paper_count == 1
    payload = json.loads(subset_path.read_text(encoding="utf-8"))
    assert payload["version"] == f"{run_id}-human-v1-subset"
    assert payload["labeling_status"] == "draft_subset"
    assert len(payload["papers"]) == 1
    assert payload["papers"][0]["label_status"] == "needs_human_label"
    assert payload["papers"][0]["relevance_label"] is None
    assert payload["papers"][0]["audience_fit"] is None
    assert payload["papers"][0]["publication_track"] is None


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


def test_cli_benchmark_status_writes_subset(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    template_path = tmp_path / "benchmark-template.json"
    subset_path = tmp_path / "benchmark-subset.json"
    run_id = _create_evaluable_run(db_path)

    with connect(db_path) as conn:
        create_benchmark_template(conn, run_id=run_id, output_path=template_path)

    assert (
        main(
            [
                "--config",
                "config/feeds.example.toml",
                "--db",
                str(db_path),
                "benchmark-status",
                "--labels",
                str(template_path),
                "--subset-output",
                str(subset_path),
                "--subset-size",
                "1",
            ]
        )
        == 0
    )

    payload = json.loads(subset_path.read_text(encoding="utf-8"))
    assert len(payload["papers"]) == 1
    assert payload["papers"][0]["label_status"] == "needs_human_label"


def test_cli_benchmark_status_json_includes_warning_and_subset_details(tmp_path, capsys) -> None:
    labels_path = tmp_path / "warning-labels.json"
    subset_path = tmp_path / "warning-subset.json"
    labels_path.write_text(
        json.dumps(
            {
                "version": "warning-fixture-v1",
                "papers": [
                    {
                        "paper_id": "paper-1",
                        "label_status": "accepted",
                        "title": "Applied method paper",
                        "relevance_label": "directly_relevant",
                        "audience_fit": "applied_researcher",
                        "application_type": "forecasting",
                        "economic_relevance": "medium",
                        "forecasting_contribution": "novel_method",
                        "publication_track": "applied_note",
                        "expected_category": "directly_relevant",
                        "expected_triage_decision": "assign_reviewers",
                        "expected_editorial_decision": "full_deep_dive",
                        "expected_deep_dive": True,
                        "expected_short_mention": True,
                        "required_evidence_kinds": ["method"],
                        "hard_negative": False,
                        "high_value": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--config",
                "config/feeds.example.toml",
                "benchmark-status",
                "--labels",
                str(labels_path),
                "--subset-output",
                str(subset_path),
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ready_for_evaluation"] is True
    assert payload["warning_count"] == 2
    assert payload["warnings"][0]["title"] == "Applied method paper"
    assert payload["warnings"][0]["code"] == "full_deep_dive_with_non_deep_dive_track"
    assert payload["subset"] == {
        "path": str(subset_path),
        "paper_count": 1,
        "paper_ids": ["paper-1"],
    }


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
