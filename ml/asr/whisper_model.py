"""OpenAI Whisper ASR implementation."""

import io
import logging
import os
import tempfile
import time
from typing import Optional

from ml.asr.base_asr import ASRResult, BaseASR

logger = logging.getLogger(__name__)


class WhisperASR(BaseASR):
    """ASR backend powered by OpenAI Whisper.

    Parameters
    ----------
    model_size:
        One of ``tiny``, ``base``, ``small``, ``medium``, ``large``.
        Larger models trade speed for accuracy.
    """

    VALID_SIZES = ("tiny", "base", "small", "medium", "large")

    model_name = "whisper"
    supported_languages = [
        "en", "hi", "fr", "de", "es", "it", "pt", "zh", "ja", "ko", "ar", "ru",
    ]

    def __init__(self, model_size: str = "base") -> None:
        if model_size not in self.VALID_SIZES:
            raise ValueError(
                f"Invalid model_size '{model_size}'. Choose from {self.VALID_SIZES}."
            )
        self.model_size = model_size
        self._model = None

    # ------------------------------------------------------------------
    # BaseASR interface
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Load Whisper weights; silently skips if already loaded."""
        if self._model is not None:
            return
        try:
            import whisper  # type: ignore

            logger.info("Loading Whisper '%s' model…", self.model_size)
            self._model = whisper.load_model(self.model_size)
            logger.info("Whisper '%s' model loaded.", self.model_size)
        except ImportError:
            logger.warning(
                "openai-whisper is not installed; WhisperASR will run in stub mode."
            )
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to load Whisper model: %s", exc)

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> ASRResult:
        """Transcribe *audio_bytes* using Whisper.

        Falls back to a stub transcript if Whisper is unavailable.
        """
        start_ms = time.monotonic() * 1000

        # Lazy-load the model on first call.
        if self._model is None:
            self.load_model()

        if self._model is None:
            # Whisper not available – return deterministic stub.
            elapsed = time.monotonic() * 1000 - start_ms
            return ASRResult(
                transcript="[whisper unavailable – stub transcript]",
                confidence=0.0,
                language=language,
                processing_time_ms=round(elapsed, 2),
            )

        try:
            import whisper  # type: ignore

            # Write bytes to a temp file because whisper.load_audio expects a path.
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                audio = whisper.load_audio(tmp_path)
                result = self._model.transcribe(
                    audio,
                    language=language if language != "en" else None,
                    fp16=False,
                )
            finally:
                os.unlink(tmp_path)

            transcript: str = result.get("text", "").strip()
            segments = result.get("segments", [])
            avg_logprob = (
                sum(s.get("avg_logprob", -1.0) for s in segments) / len(segments)
                if segments
                else -1.0
            )
            confidence = float(max(0.0, min(1.0, 1.0 + avg_logprob)))

            word_timestamps: Optional[list] = None
            if segments:
                word_timestamps = [
                    {
                        "word": w.get("word", "").strip(),
                        "start": w.get("start", 0.0),
                        "end": w.get("end", 0.0),
                    }
                    for seg in segments
                    for w in seg.get("words", [])
                ]

            elapsed = time.monotonic() * 1000 - start_ms
            return ASRResult(
                transcript=transcript,
                confidence=confidence,
                language=language,
                processing_time_ms=round(elapsed, 2),
                word_timestamps=word_timestamps or None,
            )

        except Exception as exc:  # pragma: no cover
            logger.error("Whisper transcription error: %s", exc)
            elapsed = time.monotonic() * 1000 - start_ms
            return ASRResult(
                transcript="",
                confidence=0.0,
                language=language,
                processing_time_ms=round(elapsed, 2),
            )
