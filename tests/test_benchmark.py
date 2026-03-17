"""Tests for the ML benchmark runner module."""
import sys
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ml.evaluation.benchmark_runner import TestCase, BenchmarkConfig, BenchmarkRunner


class TestTestCase:
    def test_create_minimal(self):
        tc = TestCase(audio_path=None, reference_text="hello world")
        assert tc.reference_text == "hello world"
        assert tc.audio_path is None

    def test_default_language_is_english(self):
        tc = TestCase(audio_path=None, reference_text="hello")
        assert tc.language == "en"

    def test_default_wer_threshold(self):
        tc = TestCase(audio_path=None, reference_text="hello")
        assert tc.expected_wer_threshold == 0.2

    def test_custom_language(self):
        tc = TestCase(audio_path=None, reference_text="नमस्ते", language="hi")
        assert tc.language == "hi"

    def test_custom_accent_and_noise(self):
        tc = TestCase(
            audio_path=None,
            reference_text="test",
            accent_tag="indian",
            noise_level="noisy",
        )
        assert tc.accent_tag == "indian"
        assert tc.noise_level == "noisy"


class TestBenchmarkConfig:
    def test_create_config(self):
        config = BenchmarkConfig(model_name="whisper-base")
        assert config.model_name == "whisper-base"
        assert config.test_cases == []

    def test_config_with_test_cases(self):
        cases = [TestCase(audio_path=None, reference_text="hello")]
        config = BenchmarkConfig(model_name="whisper-base", test_cases=cases)
        assert len(config.test_cases) == 1

    def test_default_output_dir(self):
        config = BenchmarkConfig(model_name="test")
        assert config.output_dir == "./benchmark_results"


def _make_mock_asr_result(transcript="hello world"):
    """Return a mock object with ASR result attributes."""
    mock = MagicMock()
    mock.transcript = transcript
    mock.confidence = 0.9
    mock.processing_time_ms = 50.0
    return mock


class TestBenchmarkRunner:
    def _make_runner_with_mock_asr(self, test_cases, tmp_path):
        config = BenchmarkConfig(
            model_name="mock-model",
            test_cases=test_cases,
            output_dir=str(tmp_path),
            generate_report=False,
        )
        runner = BenchmarkRunner(config)

        mock_model = MagicMock()
        mock_model.transcribe.return_value = _make_mock_asr_result("hello world")
        runner._asr_model = mock_model
        return runner

    def test_run_single_returns_result_dict(self, tmp_path):
        tc = TestCase(audio_path=None, reference_text="hello world")
        runner = self._make_runner_with_mock_asr([tc], tmp_path)
        result = runner.run_single(tc)
        assert isinstance(result, dict)
        assert "wer" in result
        assert "cer" in result
        assert "transcript" in result

    def test_run_single_perfect_match_passes(self, tmp_path):
        tc = TestCase(audio_path=None, reference_text="hello world")
        runner = self._make_runner_with_mock_asr([tc], tmp_path)
        result = runner.run_single(tc)
        assert result["wer"] == 0.0
        assert result["passed"] is True

    def test_run_single_high_wer_fails(self, tmp_path):
        tc = TestCase(
            audio_path=None,
            reference_text="the quick brown fox",
            expected_wer_threshold=0.1,
        )
        config = BenchmarkConfig(
            model_name="mock-model",
            test_cases=[tc],
            output_dir=str(tmp_path),
            generate_report=False,
        )
        runner = BenchmarkRunner(config)
        mock_model = MagicMock()
        mock_model.transcribe.return_value = _make_mock_asr_result("completely different text here")
        runner._asr_model = mock_model
        result = runner.run_single(tc)
        assert result["passed"] is False

    def test_run_returns_summary(self, tmp_path):
        cases = [
            TestCase(audio_path=None, reference_text="hello world"),
            TestCase(audio_path=None, reference_text="foo bar"),
        ]
        runner = self._make_runner_with_mock_asr(cases, tmp_path)
        summary = runner.run()
        assert "model_name" in summary
        assert "total_test_cases" in summary
        assert summary["total_test_cases"] == 2
        assert "results" in summary

    def test_run_saves_json(self, tmp_path):
        cases = [TestCase(audio_path=None, reference_text="hello world")]
        runner = self._make_runner_with_mock_asr(cases, tmp_path)
        runner.run()
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1

    def test_save_and_load_results(self, tmp_path):
        cases = [TestCase(audio_path=None, reference_text="hello world")]
        runner = self._make_runner_with_mock_asr(cases, tmp_path)
        runner.run()

        json_files = list(tmp_path.glob("*.json"))
        loaded = BenchmarkRunner.load_results(str(json_files[0]))
        assert "model_name" in loaded
        assert loaded["model_name"] == "mock-model"

    def test_summary_has_aggregate_metrics(self, tmp_path):
        cases = [TestCase(audio_path=None, reference_text="hello world")]
        runner = self._make_runner_with_mock_asr(cases, tmp_path)
        summary = runner.run()
        assert "aggregate_metrics" in summary
        assert "mean_wer" in summary["aggregate_metrics"]
