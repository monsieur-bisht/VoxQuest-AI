import csv
import io
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.schemas import DatasetEntry, MetricsResponse

logger = logging.getLogger(__name__)


class DatasetService:
    def __init__(self, data_dir: str = "./data"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._dataset_file = self._data_dir / "dataset.json"
        self._entries: List[DatasetEntry] = []
        self._latencies: List[float] = []
        self._load()

    def _load(self):
        if self._dataset_file.exists():
            try:
                with open(self._dataset_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._entries = [DatasetEntry(**e) for e in raw]
                logger.info("Loaded %d dataset entries", len(self._entries))
            except Exception as exc:
                logger.error("Failed to load dataset: %s", exc)
                self._entries = []

    def _save(self):
        try:
            with open(self._dataset_file, "w", encoding="utf-8") as f:
                json.dump(
                    [e.model_dump() for e in self._entries],
                    f,
                    indent=2,
                    default=str,
                )
        except Exception as exc:
            logger.error("Failed to save dataset: %s", exc)

    def log_interaction(
        self,
        session_id: str,
        audio_path: str,
        transcript: str,
        expected_text: Optional[str] = None,
        wer: Optional[float] = None,
        language: str = "en",
        accent_tag: Optional[str] = None,
        noise_level: Optional[str] = None,
    ) -> DatasetEntry:
        entry = DatasetEntry(
            session_id=session_id,
            audio_path=audio_path,
            transcript=transcript,
            expected_text=expected_text,
            wer=wer,
            language=language,
            accent_tag=accent_tag,
            noise_level=noise_level,
            created_at=datetime.utcnow(),
        )
        self._entries.append(entry)
        self._save()
        return entry

    def log_latency(self, latency_ms: float):
        self._latencies.append(latency_ms)

    def get_entries(self, filters: Optional[Dict[str, Any]] = None) -> List[DatasetEntry]:
        if not filters:
            return list(self._entries)
        result = []
        for e in self._entries:
            match = True
            for k, v in filters.items():
                if getattr(e, k, None) != v:
                    match = False
                    break
            if match:
                result.append(e)
        return result

    def export_dataset(self, fmt: str = "json") -> bytes:
        if fmt == "csv":
            buf = io.StringIO()
            if not self._entries:
                return b""
            fields = list(self._entries[0].model_fields.keys())
            writer = csv.DictWriter(buf, fieldnames=fields)
            writer.writeheader()
            for e in self._entries:
                writer.writerow({k: str(v) for k, v in e.model_dump().items()})
            return buf.getvalue().encode("utf-8")

        data = [e.model_dump() for e in self._entries]
        return json.dumps(data, indent=2, default=str).encode("utf-8")

    def get_metrics(self) -> MetricsResponse:
        total_sessions = len({e.session_id for e in self._entries})
        wers = [e.wer for e in self._entries if e.wer is not None]
        avg_wer = sum(wers) / len(wers) if wers else 0.0
        avg_latency_ms = (
            sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        )

        lang_counts: Dict[str, int] = defaultdict(int)
        for e in self._entries:
            lang_counts[e.language] += 1
        top_languages = sorted(
            [{"language": k, "count": v} for k, v in lang_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        sessions_by_time: Dict[str, Any] = {}
        for e in self._entries:
            sid = e.session_id
            if sid not in sessions_by_time:
                sessions_by_time[sid] = e.created_at
            elif e.created_at > sessions_by_time[sid]:
                sessions_by_time[sid] = e.created_at

        recent_sessions = sorted(
            [{"session_id": k, "last_active": str(v)} for k, v in sessions_by_time.items()],
            key=lambda x: x["last_active"],
            reverse=True,
        )[:10]

        return MetricsResponse(
            total_sessions=total_sessions,
            avg_wer=round(avg_wer, 4),
            avg_latency_ms=round(avg_latency_ms, 2),
            top_languages=top_languages,
            recent_sessions=recent_sessions,
        )
