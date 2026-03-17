"""Evaluation sub-package: metrics, benchmark runner, and report generation."""

from ml.evaluation.metrics import (
    calculate_wer,
    calculate_cer,
    calculate_bleu,
    normalize_text,
    calculate_rtf,
    calculate_latency_stats,
    EvaluationMetrics,
)
from ml.evaluation.benchmark_runner import BenchmarkRunner, BenchmarkConfig, TestCase
from ml.evaluation.report_generator import ReportGenerator

__all__ = [
    "calculate_wer",
    "calculate_cer",
    "calculate_bleu",
    "normalize_text",
    "calculate_rtf",
    "calculate_latency_stats",
    "EvaluationMetrics",
    "BenchmarkRunner",
    "BenchmarkConfig",
    "TestCase",
    "ReportGenerator",
]
