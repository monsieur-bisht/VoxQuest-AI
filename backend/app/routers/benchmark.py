import logging
import time
import uuid
from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models.schemas import BenchmarkResult, BenchmarkRun
from app.services.asr_service import ASRService
from app.services.dataset_service import DatasetService
from app.services.eval_service import (
    EvalService,
    calculate_latency_percentiles,
    calculate_wer,
    calculate_cer,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/benchmark", tags=["Benchmark"])

_results_store: Dict[str, BenchmarkResult] = {}
_eval_service = EvalService()

_DEFAULT_TEST_CASES = [
    {
        "audio_id": "tc_001",
        "language": "en",
        "expected": "the quick brown fox jumps over the lazy dog",
        "simulated_transcript": "the quick brown fox jumps over the lazy dog",
    },
    {
        "audio_id": "tc_002",
        "language": "en",
        "expected": "she sells seashells by the seashore",
        "simulated_transcript": "she sells sea shells by the sea shore",
    },
    {
        "audio_id": "tc_003",
        "language": "en",
        "expected": "how much wood would a woodchuck chuck",
        "simulated_transcript": "how much wood would a wood chuck chuck",
    },
    {
        "audio_id": "tc_004",
        "language": "en",
        "expected": "peter piper picked a peck of pickled peppers",
        "simulated_transcript": "peter piper picked a peck of pickled peppers",
    },
    {
        "audio_id": "tc_005",
        "language": "en",
        "expected": "i scream you scream we all scream for ice cream",
        "simulated_transcript": "i scream you scream we all scream for ice cream",
    },
]


def get_dataset_service(settings: Annotated[Settings, Depends(get_settings)]) -> DatasetService:
    from app.routers.asr import get_dataset_service as _ds
    return _ds(settings)


def get_asr_service(settings: Annotated[Settings, Depends(get_settings)]) -> ASRService:
    from app.routers.asr import get_asr_service as _asr
    return _asr(settings)


@router.post("/run", response_model=BenchmarkResult)
async def run_benchmark(
    model_name: str = "stub",
    test_cases: List[Dict[str, Any]] | None = None,
    settings: Settings = Depends(get_settings),
):
    run_id = str(uuid.uuid4())
    cases = test_cases or _DEFAULT_TEST_CASES

    latencies: List[float] = []
    per_result = []
    lang_buckets: Dict[str, Dict[str, Any]] = {}
    passed = 0
    failed = 0

    for tc in cases:
        expected = tc.get("expected", "")
        simulated = tc.get("simulated_transcript", expected)
        lang = tc.get("language", "en")

        start = time.monotonic() * 1000
        # Simulate transcription latency
        time.sleep(0.01)
        elapsed = time.monotonic() * 1000 - start

        wer = calculate_wer(expected, simulated)
        cer = calculate_cer(expected, simulated)
        latencies.append(elapsed)

        ok = wer < 0.3
        if ok:
            passed += 1
        else:
            failed += 1

        per_result.append(
            {
                "audio_id": tc.get("audio_id", ""),
                "expected": expected,
                "transcript": simulated,
                "wer": round(wer, 4),
                "cer": round(cer, 4),
                "latency_ms": round(elapsed, 2),
                "passed": ok,
                "language": lang,
            }
        )

        if lang not in lang_buckets:
            lang_buckets[lang] = {"wers": [], "cers": [], "count": 0}
        lang_buckets[lang]["wers"].append(wer)
        lang_buckets[lang]["cers"].append(cer)
        lang_buckets[lang]["count"] += 1

    avg_wer = sum(r["wer"] for r in per_result) / max(len(per_result), 1)
    avg_cer = sum(r["cer"] for r in per_result) / max(len(per_result), 1)
    avg_latency = sum(latencies) / max(len(latencies), 1)

    results_by_language = {
        lang: {
            "avg_wer": round(sum(v["wers"]) / max(len(v["wers"]), 1), 4),
            "avg_cer": round(sum(v["cers"]) / max(len(v["cers"]), 1), 4),
            "count": v["count"],
        }
        for lang, v in lang_buckets.items()
    }

    result = BenchmarkResult(
        run_id=run_id,
        model_name=model_name,
        avg_wer=round(avg_wer, 4),
        avg_cer=round(avg_cer, 4),
        avg_latency_ms=round(avg_latency, 2),
        total_samples=len(cases),
        passed=passed,
        failed=failed,
        results_by_language=results_by_language,
    )
    _results_store[run_id] = result
    return result


@router.get("/results", response_model=List[BenchmarkResult])
async def list_results():
    return list(_results_store.values())


@router.get("/results/{run_id}", response_model=BenchmarkResult)
async def get_result(run_id: str):
    if run_id not in _results_store:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return _results_store[run_id]


@router.get("/metrics")
async def get_metrics(dataset: DatasetService = Depends(get_dataset_service)):
    metrics = dataset.get_metrics()
    latencies = [r.avg_latency_ms for r in _results_store.values()]
    percentiles = calculate_latency_percentiles(latencies) if latencies else {}
    return {
        "dataset_metrics": metrics.model_dump(),
        "benchmark_runs": len(_results_store),
        "latency_percentiles": percentiles,
    }
