"""Speech evaluation metrics: WER, CER, BLEU, RTF, latency statistics."""

from __future__ import annotations

import re
import statistics
import string
from typing import List


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

def normalize_text(
    text: str,
    lowercase: bool = True,
    remove_punctuation: bool = True,
) -> str:
    """Normalise *text* for metric computation.

    Parameters
    ----------
    text:
        Raw string to normalise.
    lowercase:
        Convert to lower case when ``True``.
    remove_punctuation:
        Strip ASCII punctuation when ``True``.
    """
    if lowercase:
        text = text.lower()
    if remove_punctuation:
        text = text.translate(str.maketrans("", "", string.punctuation))
    # Collapse whitespace.
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Edit-distance helpers
# ---------------------------------------------------------------------------

def _edit_distance(seq_a: list, seq_b: list) -> int:
    """Return the Levenshtein edit distance between two token sequences."""
    m, n = len(seq_a), len(seq_b)
    # Use two-row DP to save memory.
    prev = list(range(n + 1))
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            if seq_a[i - 1] == seq_b[j - 1]:
                curr[j] = prev[j - 1]
            else:
                curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
        prev, curr = curr, prev
    return prev[n]


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def calculate_wer(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (WER).

    Uses ``jiwer`` when available for speed; falls back to a pure-Python
    implementation so the package works without ML dependencies installed.

    Returns
    -------
    float
        WER in the range ``[0.0, …]``.  Values > 1.0 are possible when
        insertions exceed the reference length.  Returns ``0.0`` for an
        empty reference (perfect match by convention).
    """
    reference = normalize_text(reference)
    hypothesis = normalize_text(hypothesis)

    if not reference:
        return 0.0

    try:
        import jiwer  # type: ignore

        return float(jiwer.wer(reference, hypothesis))
    except ImportError:
        pass

    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 0.0
    distance = _edit_distance(ref_words, hyp_words)
    return distance / len(ref_words)


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (CER).

    Returns
    -------
    float
        CER in the range ``[0.0, …]``.  Returns ``0.0`` for an empty
        reference.
    """
    reference = normalize_text(reference)
    hypothesis = normalize_text(hypothesis)

    if not reference:
        return 0.0

    try:
        import jiwer  # type: ignore

        return float(jiwer.cer(reference, hypothesis))
    except ImportError:
        pass

    ref_chars = list(reference)
    hyp_chars = list(hypothesis)
    if not ref_chars:
        return 0.0
    distance = _edit_distance(ref_chars, hyp_chars)
    return distance / len(ref_chars)


def calculate_bleu(reference: str, hypothesis: str) -> float:
    """Compute a sentence-level BLEU score (unigram through 4-gram).

    Uses ``nltk.translate.bleu_score`` when available; falls back to a
    simple unigram-precision implementation.

    Returns
    -------
    float
        BLEU score in ``[0.0, 1.0]``.
    """
    reference = normalize_text(reference)
    hypothesis = normalize_text(hypothesis)

    ref_tokens = reference.split()
    hyp_tokens = hypothesis.split()

    if not ref_tokens or not hyp_tokens:
        return 0.0

    try:
        from nltk.translate.bleu_score import (  # type: ignore
            SmoothingFunction,
            sentence_bleu,
        )

        sf = SmoothingFunction().method1
        return float(sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=sf))
    except ImportError:
        pass

    # Fallback: unigram precision with brevity penalty.
    ref_set = set(ref_tokens)
    matches = sum(1 for t in hyp_tokens if t in ref_set)
    precision = matches / len(hyp_tokens) if hyp_tokens else 0.0
    bp = min(1.0, len(hyp_tokens) / len(ref_tokens)) if ref_tokens else 0.0
    return float(bp * precision)


def calculate_rtf(audio_duration_s: float, processing_time_s: float) -> float:
    """Compute Real-Time Factor (RTF).

    RTF = processing_time / audio_duration.  A value < 1.0 means the model
    runs faster than real-time.

    Returns
    -------
    float
        RTF value; returns ``0.0`` when *audio_duration_s* is zero.
    """
    if audio_duration_s <= 0:
        return 0.0
    return processing_time_s / audio_duration_s


def calculate_latency_stats(latencies: List[float]) -> dict:
    """Return descriptive latency statistics from a list of latency values.

    Parameters
    ----------
    latencies:
        List of latency measurements (any unit, e.g. milliseconds).

    Returns
    -------
    dict
        Keys: ``count``, ``mean``, ``min``, ``max``, ``p50``, ``p90``,
        ``p95``, ``p99``.
    """
    if not latencies:
        return {
            "count": 0,
            "mean": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }

    sorted_lat = sorted(latencies)
    n = len(sorted_lat)

    def _percentile(p: float) -> float:
        idx = (p / 100) * (n - 1)
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        frac = idx - lo
        return sorted_lat[lo] * (1 - frac) + sorted_lat[hi] * frac

    return {
        "count": n,
        "mean": round(statistics.mean(sorted_lat), 3),
        "min": round(sorted_lat[0], 3),
        "max": round(sorted_lat[-1], 3),
        "p50": round(_percentile(50), 3),
        "p90": round(_percentile(90), 3),
        "p95": round(_percentile(95), 3),
        "p99": round(_percentile(99), 3),
    }


# ---------------------------------------------------------------------------
# Aggregate evaluation
# ---------------------------------------------------------------------------

class EvaluationMetrics:
    """Accumulate per-sample evaluation results and compute aggregates."""

    def __init__(self) -> None:
        self.wer_scores: List[float] = []
        self.cer_scores: List[float] = []
        self.latencies_ms: List[float] = []

    def add_result(
        self,
        wer: float,
        cer: float,
        latency_ms: float,
    ) -> None:
        """Record a single sample's metrics."""
        self.wer_scores.append(float(wer))
        self.cer_scores.append(float(cer))
        self.latencies_ms.append(float(latency_ms))

    def summarize(self) -> dict:
        """Return a summary dict with mean WER/CER and latency percentiles."""
        n = len(self.wer_scores)
        if n == 0:
            return {
                "sample_count": 0,
                "mean_wer": None,
                "mean_cer": None,
                "latency_stats_ms": calculate_latency_stats([]),
            }
        return {
            "sample_count": n,
            "mean_wer": round(statistics.mean(self.wer_scores), 4),
            "mean_cer": round(statistics.mean(self.cer_scores), 4),
            "latency_stats_ms": calculate_latency_stats(self.latencies_ms),
        }
