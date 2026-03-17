"""Abstract base class and result dataclass for TTS backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TTSResult:
    """Holds the output of a single TTS synthesis call.

    Attributes
    ----------
    audio_bytes:
        Raw audio data.  Format depends on the engine (MP3 for gTTS, WAV for
        pyttsx3).
    duration_s:
        Estimated duration of the synthesised audio in seconds.
    engine:
        Short identifier for the TTS engine (e.g. ``"gtts"``, ``"pyttsx3"``).
    language:
        BCP-47 language tag used for synthesis (e.g. ``"en"``, ``"hi"``).
    """

    audio_bytes: bytes
    duration_s: float
    engine: str
    language: str


class BaseTTS(ABC):
    """Abstract interface for text-to-speech backends."""

    @abstractmethod
    def synthesize(self, text: str, language: str = "en", **kwargs) -> TTSResult:
        """Convert *text* to speech and return a :class:`TTSResult`.

        Parameters
        ----------
        text:
            The text to synthesise.
        language:
            BCP-47 language tag.
        **kwargs:
            Engine-specific keyword arguments (e.g. voice, speed).
        """
