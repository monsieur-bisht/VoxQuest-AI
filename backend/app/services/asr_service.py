import io
import os
import tempfile
import time
from abc import ABC, abstractmethod
from typing import Optional

from app.models.schemas import AudioTranscriptionResponse
from app.services.eval_service import calculate_wer


class BaseASR(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict:
        """Return dict with keys: transcript, confidence, audio_duration_s"""


class WhisperASR(BaseASR):
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model(self.model_size)
            except Exception as exc:
                raise RuntimeError(f"Failed to load Whisper model: {exc}") from exc

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict:
        self._load_model()
        import whisper
        import numpy as np

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            audio = whisper.load_audio(tmp_path)
            duration_s = len(audio) / 16000.0
            result = self._model.transcribe(
                audio,
                language=language if language != "en" else None,
                fp16=False,
            )
            transcript = result.get("text", "").strip()
            segments = result.get("segments", [])
            avg_logprob = (
                sum(s.get("avg_logprob", -1.0) for s in segments) / len(segments)
                if segments
                else -1.0
            )
            confidence = max(0.0, min(1.0, float(1.0 + avg_logprob)))
            return {
                "transcript": transcript,
                "confidence": confidence,
                "audio_duration_s": duration_s,
            }
        finally:
            os.unlink(tmp_path)


class StubASR(BaseASR):
    """Fallback stub ASR for environments without Whisper."""

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> dict:
        duration_s = max(1.0, len(audio_bytes) / 32000.0)
        return {
            "transcript": "[stub transcription - whisper not available]",
            "confidence": 0.5,
            "audio_duration_s": duration_s,
        }


class ASRService:
    def __init__(self, model_size: str = "base"):
        self._model_size = model_size
        self._asr: Optional[BaseASR] = None

    def _get_asr(self) -> BaseASR:
        if self._asr is None:
            try:
                import whisper  # noqa: F401
                self._asr = WhisperASR(self._model_size)
            except ImportError:
                self._asr = StubASR()
        return self._asr

    def switch_model(self, model_size: str):
        self._model_size = model_size
        self._asr = None

    def list_models(self) -> list:
        return ["tiny", "base", "small", "medium", "large"]

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language: str = "en",
        session_id: str = "",
        expected_text: Optional[str] = None,
    ) -> AudioTranscriptionResponse:
        start_ms = time.monotonic() * 1000
        asr = self._get_asr()
        result = asr.transcribe(audio_bytes, language=language)
        elapsed_ms = time.monotonic() * 1000 - start_ms

        wer: Optional[float] = None
        if expected_text:
            wer = calculate_wer(expected_text, result["transcript"])

        return AudioTranscriptionResponse(
            session_id=session_id,
            transcript=result["transcript"],
            confidence=result["confidence"],
            language=language,
            wer=wer,
            processing_time_ms=round(elapsed_ms, 2),
            audio_duration_s=round(result["audio_duration_s"], 3),
        )
