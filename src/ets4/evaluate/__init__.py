"""Evaluation harness for labeled ETS4 benchmark runs."""

from .gate import GateCheck, ProviderGateResult, assess_provider_gate, provider_gate_dict
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
    PaperLabelWarning,
    benchmark_validation_dict,
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
    "GateCheck",
    "PaperLabel",
    "PaperLabelWarning",
    "ProviderGateResult",
    "assess_provider_gate",
    "benchmark_validation_dict",
    "create_benchmark_template",
    "create_benchmark_subset",
    "error_summary_dict",
    "evaluation_mismatches",
    "evaluate_run",
    "load_benchmark",
    "mismatch_dicts",
    "provider_gate_dict",
    "validate_benchmark_file",
]
