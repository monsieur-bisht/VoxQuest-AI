from __future__ import annotations

import argparse
import json
from pathlib import Path


def convert(input_json: Path, output_jsonl: Path) -> None:
    entries = json.loads(input_json.read_text())
    with output_jsonl.open("w", encoding="utf-8") as f:
        for row in entries:
            record = {
                "audio_id": row.get("anonymized_audio_id") or f"sample-{row['id']}",
                "text": row["transcript"],
                "language": row["language_tag"],
                "noise_level": row["noise_level"],
                "accent_tag": row["accent_tag"],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare dataset export for Whisper fine-tuning pipeline")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    convert(args.input, args.output)
