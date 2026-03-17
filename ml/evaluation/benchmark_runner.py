"""Benchmark runner: orchestrates ASR evaluation over a set of test cases."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """A single benchmark test case.

    Parameters
    ----------
    audio_path:
        Filesystem path to a WAV audio file, **or** ``None`` to generate
        speech from *reference_text* using the built-in TTS fallback.
    reference_text:
        Ground-truth transcript used to compute WER/CER.
    language:
        BCP-47 language tag (e.g. ``"en"``, ``"hi"``).
    accent_tag:
        Human-readable accent label (e.g. ``"neutral"``, ``"indian"``).
    noise_level:
        Noise condition label (e.g. ``"clean"``, ``"noisy"``).
    expected_wer_threshold:
        Maximum acceptable WER – used to mark the test case as PASS/FAIL.
    """

    audio_path: Optional[str]
    reference_text: str
    language: str = "en"
    accent_tag: str = "neutral"
    noise_level: str = "clean"
    expected_wer_threshold: float = 0.2


@dataclass
class BenchmarkConfig:
    """Configuration for a full benchmark run.

    Parameters
    ----------
    model_name:
        Registry key for the ASR model to evaluate (e.g. ``"whisper-base"``).
    test_cases:
        Ordered list of :class:`TestCase` objects.
    output_dir:
        Directory where result JSON files will be written.
    generate_report:
        When ``True``, :meth:`BenchmarkRunner.run` also writes a Markdown
        report alongside the JSON results.
    """

    model_name: str
    test_cases: List[TestCase] = field(default_factory=list)
    output_dir: str = "./benchmark_results"
    generate_report: bool = True


class BenchmarkRunner:
    """Run an ASR benchmark and collect structured results.

    Parameters
    ----------
    config:
        A fully-populated :class:`BenchmarkConfig`.
    """

    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
        self.results: List[dict] = []
        self._asr_model = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Execute all test cases and return a results summary dict.

        Side effects
        ------------
        * Writes ``<output_dir>/<model_name>_results.json``.
        * Writes ``<output_dir>/<model_name>_report.md`` when
          ``config.generate_report`` is ``True``.
        """
        self.results = []
        model = self._get_model()

        logger.info(
            "Starting benchmark: model=%s, test_cases=%d",
            self.config.model_name,
            len(self.config.test_cases),
        )

        for tc in self.config.test_cases:
            result = self.run_single(tc)
            self.results.append(result)

        summary = self._build_summary()

        os.makedirs(self.config.output_dir, exist_ok=True)
        safe_name = self.config.model_name.replace("/", "_")
        json_path = os.path.join(self.config.output_dir, f"{safe_name}_results.json")
        self.save_results(json_path)

        if self.config.generate_report:
            from ml.evaluation.report_generator import ReportGenerator

            rg = ReportGenerator()
            md_path = os.path.join(
                self.config.output_dir, f"{safe_name}_report.md"
            )
            md_content = rg.generate_markdown_report(summary)
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(md_content)
            logger.info("Markdown report written to %s", md_path)

        logger.info("Benchmark complete. JSON results: %s", json_path)
        return summary

    def run_single(self, test_case: TestCase) -> dict:
        """Evaluate a single :class:`TestCase` and return a result dict.

        The result dict contains:
        ``test_case``, ``transcript``, ``wer``, ``cer``, ``processing_time_ms``,
        ``audio_duration_s``, ``rtf``, ``passed``.
        """
        from ml.evaluation.metrics import calculate_wer, calculate_cer, calculate_rtf

        model = self._get_model()
        audio_bytes = self._load_audio(test_case)

        start = time.monotonic()
        asr_result = model.transcribe(audio_bytes, language=test_case.language)
        elapsed_s = time.monotonic() - start

        wer = calculate_wer(test_case.reference_text, asr_result.transcript)
        cer = calculate_cer(test_case.reference_text, asr_result.transcript)

        # Estimate audio duration from byte count if not inferable.
        try:
            from ml.utils.audio_utils import get_audio_duration

            audio_duration_s = get_audio_duration(audio_bytes)
        except Exception:
            audio_duration_s = max(1.0, len(audio_bytes) / 32000.0)

        rtf = calculate_rtf(audio_duration_s, elapsed_s)
        passed = wer <= test_case.expected_wer_threshold

        result = {
            "test_case": asdict(test_case),
            "transcript": asr_result.transcript,
            "confidence": round(asr_result.confidence, 4),
            "wer": round(wer, 4),
            "cer": round(cer, 4),
            "processing_time_ms": round(asr_result.processing_time_ms, 2),
            "audio_duration_s": round(audio_duration_s, 3),
            "rtf": round(rtf, 4),
            "passed": passed,
        }

        status = "PASS" if passed else "FAIL"
        logger.info(
            "[%s] WER=%.3f CER=%.3f RTF=%.2f | %s",
            status,
            wer,
            cer,
            rtf,
            test_case.reference_text[:60],
        )
        return result

    def save_results(self, output_path: str) -> None:
        """Serialise current results and summary to *output_path* as JSON."""
        payload = self._build_summary()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        logger.info("Results saved to %s", output_path)

    @staticmethod
    def load_results(path: str) -> dict:
        """Load and return a previously saved results JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_model(self):
        """Return the ASR model, creating it on first call."""
        if self._asr_model is None:
            from ml.asr.model_registry import get_asr_model

            self._asr_model = get_asr_model(self.config.model_name)
        return self._asr_model

    def _load_audio(self, test_case: TestCase) -> bytes:
        """Return audio bytes for *test_case*.

        If ``audio_path`` is set and exists, the file is read directly.
        Otherwise, the reference text is synthesised via the gTTS fallback.
        """
        if test_case.audio_path and os.path.isfile(test_case.audio_path):
            with open(test_case.audio_path, "rb") as fh:
                return fh.read()

        # Generate TTS audio as a stand-in.
        logger.debug(
            "No audio file for test case; generating TTS for '%s'.",
            test_case.reference_text[:40],
        )
        try:
            from ml.tts.gtts_model import GTTSModel

            tts = GTTSModel()
            tts_result = tts.synthesize(
                test_case.reference_text, language=test_case.language
            )
            return tts_result.audio_bytes
        except Exception as exc:
            logger.warning("TTS generation failed (%s); returning silent audio.", exc)
            # Return minimal valid WAV (44-byte header, no samples).
            return _silent_wav()

    def _build_summary(self) -> dict:
        """Aggregate per-sample results into a summary dict."""
        from ml.evaluation.metrics import (
            calculate_latency_stats,
            EvaluationMetrics,
        )

        metrics = EvaluationMetrics()
        for r in self.results:
            metrics.add_result(r["wer"], r["cer"], r["processing_time_ms"])

        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)

        return {
            "model_name": self.config.model_name,
            "total_test_cases": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "aggregate_metrics": metrics.summarize(),
            "results": self.results,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _silent_wav(sample_rate: int = 16000, duration_ms: int = 100) -> bytes:
    """Return a minimal silent WAV byte string."""
    import struct

    n_samples = int(sample_rate * duration_ms / 1000)
    data_size = n_samples * 2  # 16-bit PCM
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,          # PCM
        1,          # mono
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + b"\x00" * data_size
