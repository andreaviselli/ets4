from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ets4.store.db import insert_evaluation_item, insert_evaluation_run

from .labels import Benchmark, load_benchmark
from .metrics import aggregate_metrics, evaluate_paper
from .report import EvaluationMismatch, evaluation_mismatches, mismatch_dicts

EVALUATOR_VERSION = "pilot-report-v1"


@dataclass(frozen=True)
class EvaluationResult:
    evaluation_run_id: str
    run_id: str
    benchmark_version: str
    metrics: dict[str, Any]
    item_results: tuple[dict[str, Any], ...]
    mismatches: tuple[EvaluationMismatch, ...]


def evaluate_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    labels_path: str | Path,
    store: bool = True,
) -> EvaluationResult:
    benchmark = load_benchmark(labels_path)
    item_results = [evaluate_paper(conn, run_id=run_id, label=label) for label in benchmark.labels]
    item_tuple = tuple(item_results)
    metrics = aggregate_metrics(item_results)
    metrics["mismatches"] = mismatch_dicts(item_tuple)
    metrics["benchmark_version"] = benchmark.version
    metrics["run_id"] = run_id
    metrics["evaluator_version"] = EVALUATOR_VERSION
    evaluation_run_id = _evaluation_run_id(
        run_id=run_id,
        benchmark=benchmark,
        labels_path=str(labels_path),
    )
    result = EvaluationResult(
        evaluation_run_id=evaluation_run_id,
        run_id=run_id,
        benchmark_version=benchmark.version,
        metrics=metrics,
        item_results=item_tuple,
        mismatches=evaluation_mismatches(item_tuple),
    )
    if store:
        insert_evaluation_run(
            conn,
            evaluation_run_id=evaluation_run_id,
            run_id=run_id,
            benchmark_version=benchmark.version,
            labels_path=str(labels_path),
            evaluator_version=EVALUATOR_VERSION,
            metrics_json=metrics,
            status="ok",
        )
        conn.execute(
            "DELETE FROM evaluation_items WHERE evaluation_run_id = ?",
            (evaluation_run_id,),
        )
        for item in item_results:
            insert_evaluation_item(
                conn,
                evaluation_run_id=evaluation_run_id,
                paper_id=str(item["paper_id"]),
                item_json=item,
                status="ok",
            )
        conn.commit()
    return result


def _evaluation_run_id(*, run_id: str, benchmark: Benchmark, labels_path: str) -> str:
    digest = hashlib.sha256(
        f"{run_id}|{benchmark.version}|{labels_path}|{EVALUATOR_VERSION}".encode("utf-8")
    ).hexdigest()
    return f"eval-{digest[:16]}"
