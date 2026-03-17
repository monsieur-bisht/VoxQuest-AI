"""Generate Markdown, JSON, and terminal reports from benchmark results."""

from __future__ import annotations

import json
from datetime import datetime
from typing import List


class ReportGenerator:
    """Convert structured benchmark result dicts into human-readable reports."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_markdown_report(self, results: dict) -> str:
        """Return a Markdown string summarising *results*.

        The report includes:
        * A header with model name and timestamp.
        * A summary table (pass rate, mean WER/CER, latency percentiles).
        * A per-sample results table.
        """
        model_name = results.get("model_name", "unknown")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        total = results.get("total_test_cases", 0)
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        pass_rate = results.get("pass_rate", 0.0)
        agg = results.get("aggregate_metrics", {})

        mean_wer = agg.get("mean_wer", "N/A")
        mean_cer = agg.get("mean_cer", "N/A")
        lat = agg.get("latency_stats_ms", {})

        lines: List[str] = [
            f"# VoxQuest-AI ASR Benchmark Report",
            f"",
            f"**Model:** `{model_name}`  ",
            f"**Generated:** {timestamp}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total test cases | {total} |",
            f"| Passed | {passed} |",
            f"| Failed | {failed} |",
            f"| Pass rate | {pass_rate:.1%} |",
            f"| Mean WER | {_fmt(mean_wer)} |",
            f"| Mean CER | {_fmt(mean_cer)} |",
            f"| Latency p50 (ms) | {_fmt(lat.get('p50'))} |",
            f"| Latency p90 (ms) | {_fmt(lat.get('p90'))} |",
            f"| Latency p95 (ms) | {_fmt(lat.get('p95'))} |",
            f"| Latency p99 (ms) | {_fmt(lat.get('p99'))} |",
            f"",
            f"## Per-Sample Results",
            f"",
            f"| # | Reference | Transcript | WER | CER | RTF | Pass |",
            f"|---|-----------|------------|-----|-----|-----|------|",
        ]

        for idx, r in enumerate(results.get("results", []), start=1):
            tc = r.get("test_case", {})
            ref = _trunc(tc.get("reference_text", ""), 40)
            hyp = _trunc(r.get("transcript", ""), 40)
            wer = r.get("wer", "N/A")
            cer = r.get("cer", "N/A")
            rtf = r.get("rtf", "N/A")
            passed_icon = "✅" if r.get("passed") else "❌"
            lines.append(
                f"| {idx} | {ref} | {hyp} | {_fmt(wer)} | {_fmt(cer)} | {_fmt(rtf)} | {passed_icon} |"
            )

        lines.append("")
        return "\n".join(lines)

    def generate_json_report(self, results: dict) -> dict:
        """Return a structured JSON-serialisable report dict from *results*.

        Adds a ``generated_at`` timestamp and flattens the aggregate metrics
        for easier downstream consumption.
        """
        agg = results.get("aggregate_metrics", {})
        lat = agg.get("latency_stats_ms", {})

        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "model_name": results.get("model_name"),
            "summary": {
                "total_test_cases": results.get("total_test_cases", 0),
                "passed": results.get("passed", 0),
                "failed": results.get("failed", 0),
                "pass_rate": results.get("pass_rate", 0.0),
                "mean_wer": agg.get("mean_wer"),
                "mean_cer": agg.get("mean_cer"),
                "latency_p50_ms": lat.get("p50"),
                "latency_p90_ms": lat.get("p90"),
                "latency_p95_ms": lat.get("p95"),
                "latency_p99_ms": lat.get("p99"),
                "latency_mean_ms": lat.get("mean"),
            },
            "results": results.get("results", []),
        }
        return report

    def print_summary(self, results: dict) -> None:
        """Print a colour-coded terminal summary of *results*.

        Falls back to plain text if ``colorama`` is not installed.
        """
        try:
            from colorama import Fore, Style, init  # type: ignore

            init(autoreset=True)
            green = Fore.GREEN
            red = Fore.RED
            yellow = Fore.YELLOW
            cyan = Fore.CYAN
            bold = Style.BRIGHT
            reset = Style.RESET_ALL
        except ImportError:
            green = red = yellow = cyan = bold = reset = ""

        model_name = results.get("model_name", "unknown")
        total = results.get("total_test_cases", 0)
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        pass_rate = results.get("pass_rate", 0.0)
        agg = results.get("aggregate_metrics", {})
        mean_wer = agg.get("mean_wer", "N/A")
        mean_cer = agg.get("mean_cer", "N/A")
        lat = agg.get("latency_stats_ms", {})

        pass_colour = green if pass_rate >= 0.8 else (yellow if pass_rate >= 0.5 else red)

        print(f"\n{bold}{'='*55}{reset}")
        print(f"{bold}  VoxQuest-AI Benchmark Summary{reset}")
        print(f"{bold}{'='*55}{reset}")
        print(f"  {cyan}Model:{reset}      {model_name}")
        print(f"  {cyan}Test cases:{reset} {total}  ({green}{passed} passed{reset} / {red}{failed} failed{reset})")
        print(f"  {cyan}Pass rate:{reset}  {pass_colour}{pass_rate:.1%}{reset}")
        print(f"  {cyan}Mean WER:{reset}   {_fmt(mean_wer)}")
        print(f"  {cyan}Mean CER:{reset}   {_fmt(mean_cer)}")
        print(f"  {cyan}Latency:{reset}    p50={_fmt(lat.get('p50'))}ms  p95={_fmt(lat.get('p95'))}ms  p99={_fmt(lat.get('p99'))}ms")
        print(f"{bold}{'='*55}{reset}\n")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fmt(value) -> str:
    """Format a numeric value or return 'N/A'."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _trunc(text: str, max_len: int) -> str:
    """Truncate *text* to *max_len* characters, appending '…' if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
