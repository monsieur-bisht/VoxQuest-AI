"""Abstract base class and result dataclass for ASR models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ASRResult:
    """Holds the output of a single ASR transcription pass."""

    transcript: str
    confidence: float
    language: str
    processing_time_ms: float
    word_timestamps: Optional[list] = field(default=None)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        self.processing_time_ms = max(0.0, float(self.processing_time_ms))


class BaseASR(ABC):
    """Abstract base class that every ASR backend must implement."""

    model_name: str = "base"
    supported_languages: list = ["en"]

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def load_model(self) -> None:
        """Load model weights into memory.

        Implementations should be idempotent – calling this multiple times
        should not reload an already-loaded model.
        """

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, language: str = "en") -> ASRResult:
        """Transcribe *audio_bytes* (WAV/PCM) and return an :class:`ASRResult`.

        Parameters
        ----------
        audio_bytes:
            Raw audio data in WAV or raw PCM format (16 kHz, mono).
        language:
            BCP-47 language tag (e.g. ``"en"``, ``"hi"``).
        """

    # ------------------------------------------------------------------
    # Concrete helpers
    # ------------------------------------------------------------------

    def is_loaded(self) -> bool:
        """Return ``True`` when the model is loaded and ready to transcribe."""
        return getattr(self, "_model", None) is not None
