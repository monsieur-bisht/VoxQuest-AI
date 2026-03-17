"""Tests for backend eval_service: WER, CER, normalize_text, latency stats."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.eval_service import (
    calculate_wer,
    calculate_cer,
    normalize_text,
    calculate_latency_percentiles,
    EvalService,
)


class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("Hello World") == "hello world"

    def test_removes_punctuation(self):
        assert normalize_text("hello, world!") == "hello world"

    def test_collapses_whitespace(self):
        assert normalize_text("hello   world") == "hello world"

    def test_strips_leading_trailing(self):
        assert normalize_text("  hello  ") == "hello"

    def test_empty_string(self):
        assert normalize_text("") == ""


class TestCalculateWER:
    def test_perfect_match(self):
        assert calculate_wer("hello world", "hello world") == 0.0

    def test_complete_mismatch(self):
        wer = calculate_wer("hello world", "foo bar")
        assert wer > 0.0

    def test_partial_match(self):
        wer = calculate_wer("hello world", "hello earth")
        assert 0.0 < wer < 1.0

    def test_empty_reference_empty_hypothesis(self):
        assert calculate_wer("", "") == 0.0

    def test_empty_reference_nonempty_hypothesis(self):
        # By convention the service returns 1.0 when ref is empty but hyp is not
        assert calculate_wer("", "hello") == 1.0

    def test_case_insensitive(self):
        assert calculate_wer("Hello World", "hello world") == 0.0

    def test_punctuation_ignored(self):
        assert calculate_wer("hello, world!", "hello world") == 0.0

    def test_single_word_deletion(self):
        wer = calculate_wer("one two three", "one three")
        assert wer > 0.0


class TestCalculateCER:
    def test_perfect_match(self):
        assert calculate_cer("hello", "hello") == 0.0

    def test_complete_mismatch(self):
        cer = calculate_cer("abc", "xyz")
        assert cer > 0.0

    def test_partial_match(self):
        cer = calculate_cer("hello world", "helo world")
        assert 0.0 < cer < 1.0

    def test_empty_reference_empty_hypothesis(self):
        assert calculate_cer("", "") == 0.0

    def test_empty_reference_nonempty_hypothesis(self):
        assert calculate_cer("", "a") == 1.0

    def test_case_insensitive(self):
        assert calculate_cer("Hello", "hello") == 0.0


class TestCalculateLatencyPercentiles:
    def test_empty_returns_zeros(self):
        result = calculate_latency_percentiles([])
        assert result == {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

    def test_single_value(self):
        result = calculate_latency_percentiles([100.0])
        assert result["p50"] == 100.0
        assert result["p99"] == 100.0

    def test_percentile_ordering(self):
        latencies = list(range(1, 101))  # 1..100
        result = calculate_latency_percentiles(latencies)
        assert result["p50"] <= result["p90"] <= result["p95"] <= result["p99"]

    def test_p99_near_max(self):
        latencies = list(range(1, 101))
        result = calculate_latency_percentiles(latencies)
        assert result["p99"] >= 95


class TestEvalService:
    def setup_method(self):
        self.service = EvalService()

    def test_evaluate_single_perfect(self):
        result = self.service.evaluate_single("hello world", "hello world")
        assert result["wer"] == 0.0
        assert result["cer"] == 0.0

    def test_evaluate_single_mismatch(self):
        result = self.service.evaluate_single("hello world", "foo bar")
        assert result["wer"] > 0.0
        assert result["cer"] > 0.0

    def test_evaluate_batch(self):
        refs = ["hello world", "foo bar"]
        hyps = ["hello world", "foo bar"]
        result = self.service.evaluate_batch(refs, hyps)
        assert result["avg_wer"] == 0.0
        assert result["avg_cer"] == 0.0

    def test_evaluate_batch_mismatched_lengths(self):
        result = self.service.evaluate_batch(["hello"], [])
        assert result["avg_wer"] == 0.0

    def test_evaluate_batch_returns_per_sample(self):
        refs = ["hello world", "test"]
        hyps = ["hello earth", "test"]
        result = self.service.evaluate_batch(refs, hyps)
        assert "wer_per_sample" in result
        assert len(result["wer_per_sample"]) == 2
