"""Evaluation harness for labeled ETS4 benchmark runs."""

from .labels import Benchmark, PaperLabel, load_benchmark
from .report import (
    EvaluationMismatch,
    error_summary_dict,
    evaluation_mismatches,
    mismatch_dicts,
)
from .runner import EvaluationResult, evaluate_run
from .template import BenchmarkTemplateResult, create_benchmark_template
from .validate import (
    BenchmarkSubsetResult,
    BenchmarkValidationResult,
    create_benchmark_subset,
    validate_benchmark_file,
)

__all__ = [
    "Benchmark",
    "BenchmarkSubsetResult",
    "BenchmarkTemplateResult",
    "BenchmarkValidationResult",
    "EvaluationMismatch",
    "EvaluationResult",
    "PaperLabel",
    "create_benchmark_template",
    "create_benchmark_subset",
    "error_summary_dict",
    "evaluation_mismatches",
    "evaluate_run",
    "load_benchmark",
    "mismatch_dicts",
    "validate_benchmark_file",
]
