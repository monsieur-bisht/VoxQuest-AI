#!/usr/bin/env python3
"""
VoxQuest-AI Speech Benchmark CLI
=================================

Usage examples::

    # Run a full benchmark
    python -m ml.cli.benchmark_cli run --model whisper-base --test-file test_cases.json

    # Generate a report from saved results
    python -m ml.cli.benchmark_cli report --results-file results.json

    # List all available ASR models
    python -m ml.cli.benchmark_cli list-models

    # Quick single-phrase transcription test
    python -m ml.cli.benchmark_cli quick-test --text "Hello world" --model whisper-base
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import List, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("benchmark_cli")


# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    """Execute a full benchmark run from a JSON test-case file."""
    from ml.evaluation.benchmark_runner import BenchmarkConfig, BenchmarkRunner, TestCase
    from ml.evaluation.report_generator import ReportGenerator

    # Load test cases from JSON or use built-in scenario phrases.
    if args.test_file:
        if not os.path.isfile(args.test_file):
            print(f"ERROR: test file not found: {args.test_file}", file=sys.stderr)
            return 1
        with open(args.test_file, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        # Support both a list of test-case dicts and a dict with a "test_cases" key.
        if isinstance(raw, list):
            tc_dicts = raw
        else:
            tc_dicts = raw.get("test_cases", raw.get("benchmark_phrases", []))
        test_cases = [
            TestCase(
                audio_path=tc.get("audio_path"),
                reference_text=tc.get("reference_text") or tc.get("text", ""),
                language=tc.get("language", "en"),
                accent_tag=tc.get("accent_tag", "neutral"),
                noise_level=tc.get("noise_level", "clean"),
                expected_wer_threshold=float(tc.get("expected_wer_threshold", 0.2)),
            )
            for tc in tc_dicts
            if tc.get("reference_text") or tc.get("text")
        ]
    else:
        # Fall back to the bundled multilingual scenario phrases.
        print("No --test-file specified; using built-in scenario benchmark phrases.")
        from ml.scenarios.scenario_loader import ScenarioLoader

        loader = ScenarioLoader()
        scenario = loader.load()
        phrases = loader.get_benchmark_phrases(scenario)
        test_cases = [
            TestCase(
                audio_path=None,
                reference_text=p["text"],
                language=p.get("language", "en"),
            )
            for p in phrases
        ]

    if not test_cases:
        print("ERROR: No test cases found.", file=sys.stderr)
        return 1

    print(f"Model      : {args.model}")
    print(f"Test cases : {len(test_cases)}")
    print(f"Output dir : {args.output_dir}")
    print()

    config = BenchmarkConfig(
        model_name=args.model,
        test_cases=test_cases,
        output_dir=args.output_dir,
        generate_report=not args.no_report,
    )
    runner = BenchmarkRunner(config)

    try:
        results = runner.run()
    except Exception as exc:
        print(f"ERROR: Benchmark failed: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    rg = ReportGenerator()
    rg.print_summary(results)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate a Markdown (and optionally JSON) report from a saved results file."""
    from ml.evaluation.benchmark_runner import BenchmarkRunner
    from ml.evaluation.report_generator import ReportGenerator

    if not os.path.isfile(args.results_file):
        print(f"ERROR: Results file not found: {args.results_file}", file=sys.stderr)
        return 1

    results = BenchmarkRunner.load_results(args.results_file)
    rg = ReportGenerator()

    if args.format in ("markdown", "both"):
        md = rg.generate_markdown_report(results)
        if args.output:
            out_path = args.output
        else:
            base = os.path.splitext(args.results_file)[0]
            out_path = base + "_report.md"
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"Markdown report written to: {out_path}")

    if args.format in ("json", "both"):
        json_report = rg.generate_json_report(results)
        if args.output and args.format == "json":
            out_path = args.output
        else:
            base = os.path.splitext(args.results_file)[0]
            out_path = base + "_report.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(json_report, fh, indent=2, ensure_ascii=False)
        print(f"JSON report written to: {out_path}")

    rg.print_summary(results)
    return 0


def cmd_list_models(args: argparse.Namespace) -> int:
    """Print all registered ASR model names."""
    from ml.asr.model_registry import ASR_REGISTRY

    print("\nAvailable ASR models:")
    print(f"  {'Name':<30} {'Type'}")
    print(f"  {'-'*30} {'-'*20}")
    for name in sorted(ASR_REGISTRY):
        model_type = "Whisper" if name.startswith("whisper") else "Wav2Vec2"
        print(f"  {name:<30} {model_type}")
    print()
    return 0


def cmd_quick_test(args: argparse.Namespace) -> int:
    """Transcribe a single phrase and print WER against the input text."""
    from ml.asr.model_registry import get_asr_model
    from ml.evaluation.metrics import calculate_wer, calculate_cer
    from ml.tts.gtts_model import GTTSModel

    print(f"Model    : {args.model}")
    print(f"Text     : {args.text}")
    print(f"Language : {args.language}")
    print()

    # Generate TTS audio for the phrase.
    print("Generating TTS audio…")
    tts = GTTSModel()
    try:
        tts_result = tts.synthesize(args.text, language=args.language)
        audio_bytes = tts_result.audio_bytes
        print(f"TTS audio : {len(audio_bytes)} bytes  (~{tts_result.duration_s:.2f}s)")
    except Exception as exc:
        print(f"WARNING: TTS failed ({exc}), using silent audio.", file=sys.stderr)
        audio_bytes = _silent_wav()

    # Transcribe with the chosen model.
    print("Transcribing…")
    try:
        model = get_asr_model(args.model)
        asr_result = model.transcribe(audio_bytes, language=args.language)
    except KeyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Transcription failed: {exc}", file=sys.stderr)
        return 1

    wer = calculate_wer(args.text, asr_result.transcript)
    cer = calculate_cer(args.text, asr_result.transcript)

    print()
    print(f"Reference  : {args.text}")
    print(f"Transcript : {asr_result.transcript}")
    print(f"Confidence : {asr_result.confidence:.4f}")
    print(f"WER        : {wer:.4f}  ({wer:.1%})")
    print(f"CER        : {cer:.4f}  ({cer:.1%})")
    print(f"Latency    : {asr_result.processing_time_ms:.1f} ms")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="benchmark_cli",
        description="VoxQuest-AI Speech Benchmark CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging.",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------
    run_p = sub.add_parser(
        "run",
        help="Run a full benchmark against an ASR model.",
        description="Run a full benchmark. Test cases are loaded from --test-file "
                    "or the built-in scenario when omitted.",
    )
    run_p.add_argument(
        "--model", "-m",
        default="whisper-base",
        metavar="MODEL",
        help="ASR model registry key (default: whisper-base).",
    )
    run_p.add_argument(
        "--test-file", "-t",
        metavar="FILE",
        help="Path to a JSON file containing test cases.",
    )
    run_p.add_argument(
        "--output-dir", "-o",
        default="./benchmark_results",
        metavar="DIR",
        help="Directory for result files (default: ./benchmark_results).",
    )
    run_p.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating the Markdown report.",
    )
    run_p.set_defaults(func=cmd_run)

    # ------------------------------------------------------------------
    # report
    # ------------------------------------------------------------------
    report_p = sub.add_parser(
        "report",
        help="Generate a report from a saved results JSON file.",
    )
    report_p.add_argument(
        "--results-file", "-r",
        required=True,
        metavar="FILE",
        help="Path to a saved benchmark results JSON file.",
    )
    report_p.add_argument(
        "--format", "-f",
        choices=["markdown", "json", "both"],
        default="both",
        help="Output format (default: both).",
    )
    report_p.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Output file path (only used when --format is not 'both').",
    )
    report_p.set_defaults(func=cmd_report)

    # ------------------------------------------------------------------
    # list-models
    # ------------------------------------------------------------------
    lm_p = sub.add_parser(
        "list-models",
        help="Show all available ASR models.",
    )
    lm_p.set_defaults(func=cmd_list_models)

    # ------------------------------------------------------------------
    # quick-test
    # ------------------------------------------------------------------
    qt_p = sub.add_parser(
        "quick-test",
        help="Transcribe a single phrase and display WER.",
    )
    qt_p.add_argument(
        "--text", "-t",
        required=True,
        help="Reference text to synthesise and transcribe.",
    )
    qt_p.add_argument(
        "--model", "-m",
        default="whisper-base",
        metavar="MODEL",
        help="ASR model registry key (default: whisper-base).",
    )
    qt_p.add_argument(
        "--language", "-l",
        default="en",
        metavar="LANG",
        help="BCP-47 language tag (default: en).",
    )
    qt_p.set_defaults(func=cmd_quick_test)

    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _silent_wav(sample_rate: int = 16000, duration_ms: int = 500) -> bytes:
    import struct

    n_samples = int(sample_rate * duration_ms / 1000)
    data_size = n_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1,
        sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    return header + b"\x00" * data_size


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("ml").setLevel(logging.DEBUG)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
