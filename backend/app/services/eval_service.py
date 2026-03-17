import re
import string
from typing import Dict, List

try:
    import jiwer
    JIWER_AVAILABLE = True
except ImportError:
    JIWER_AVAILABLE = False


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def calculate_wer(reference: str, hypothesis: str) -> float:
    ref = normalize_text(reference)
    hyp = normalize_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    if JIWER_AVAILABLE:
        try:
            return float(jiwer.wer(ref, hyp))
        except Exception:
            pass
    ref_words = ref.split()
    hyp_words = hyp.split()
    return _edit_distance(ref_words, hyp_words) / max(len(ref_words), 1)


def calculate_cer(reference: str, hypothesis: str) -> float:
    ref = normalize_text(reference)
    hyp = normalize_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    if JIWER_AVAILABLE:
        try:
            return float(jiwer.cer(ref, hyp))
        except Exception:
            pass
    return _edit_distance(list(ref), list(hyp)) / max(len(ref), 1)


def _edit_distance(seq1: list, seq2: list) -> int:
    m, n = len(seq1), len(seq2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if seq1[i - 1] == seq2[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def calculate_latency_percentiles(latencies: List[float]) -> Dict[str, float]:
    if not latencies:
        return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)

    def percentile(p: float) -> float:
        idx = int(p / 100.0 * n)
        return sorted_lat[min(idx, n - 1)]

    return {
        "p50": percentile(50),
        "p90": percentile(90),
        "p95": percentile(95),
        "p99": percentile(99),
    }


class EvalService:
    def evaluate_batch(
        self, references: List[str], hypotheses: List[str]
    ) -> Dict[str, float]:
        if not references or len(references) != len(hypotheses):
            return {"avg_wer": 0.0, "avg_cer": 0.0}
        wers = [calculate_wer(r, h) for r, h in zip(references, hypotheses)]
        cers = [calculate_cer(r, h) for r, h in zip(references, hypotheses)]
        return {
            "avg_wer": sum(wers) / len(wers),
            "avg_cer": sum(cers) / len(cers),
            "wer_per_sample": wers,
            "cer_per_sample": cers,
        }

    def evaluate_single(self, reference: str, hypothesis: str) -> Dict[str, float]:
        return {
            "wer": calculate_wer(reference, hypothesis),
            "cer": calculate_cer(reference, hypothesis),
        }
