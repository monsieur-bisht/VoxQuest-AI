from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import httpx


def run(base_url: str, session_id: str, file_path: Path) -> None:
    samples = json.loads(file_path.read_text())
    latencies = []
    wers = []

    with httpx.Client(timeout=30) as client:
        for sample in samples:
            response = client.post(
                f"{base_url}/api/game/turn",
                json={
                    "session_id": session_id,
                    "transcript": sample["transcript"],
                    "expected_transcript": sample.get("expected_transcript"),
                    "confidence": sample.get("confidence", 0.9),
                    "noise_level": sample.get("noise_level", "medium"),
                    "accent_tag": sample.get("accent_tag", "neutral"),
                },
            )
            response.raise_for_status()
            data = response.json()["benchmark"]
            latencies.append(data["latency_ms"])
            if data["wer"] is not None:
                wers.append(data["wer"])

    summary = {
        "samples": len(samples),
        "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else 0,
        "wer_avg": round(statistics.mean(wers), 4) if wers else None,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run VoxQuest benchmark turns from JSON samples")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--file", type=Path, required=True, help="JSON array with transcript samples")
    args = parser.parse_args()
    run(args.base_url, args.session_id, args.file)
