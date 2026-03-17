"""pyttsx3 (offline) TTS backend."""

from __future__ import annotations

import io
import logging
import os
import struct
import tempfile
import time
from typing import Optional

from ml.tts.base_tts import BaseTTS, TTSResult

logger = logging.getLogger(__name__)


class PyTTSX3Model(BaseTTS):
    """Offline TTS backend using ``pyttsx3``.

    pyttsx3 drives the platform's native speech engine (SAPI5 on Windows,
    NSSpeechSynthesizer on macOS, espeak/festival on Linux).

    Parameters
    ----------
    rate:
        Speech rate in words per minute (default: 150).
    volume:
        Volume in the range ``[0.0, 1.0]`` (default: 1.0).
    voice_id:
        Optional voice identifier string.  When ``None``, the engine default
        is used.
    """

    def __init__(
        self,
        rate: int = 150,
        volume: float = 1.0,
        voice_id: Optional[str] = None,
    ) -> None:
        self.rate = rate
        self.volume = volume
        self.voice_id = voice_id

    def synthesize(self, text: str, language: str = "en", **kwargs) -> TTSResult:
        """Synthesise *text* offline via pyttsx3 and return WAV bytes.

        pyttsx3 does not support per-call language switching; *language* is
        recorded in the result but does not change the voice unless *voice_id*
        is set to a language-specific voice.

        Parameters
        ----------
        text:
            Text to synthesise.
        language:
            BCP-47 tag (recorded in result; does not switch TTS voice).
        **kwargs:
            ``rate`` and ``volume`` keyword arguments override instance defaults.
        """
        rate = kwargs.get("rate", self.rate)
        volume = kwargs.get("volume", self.volume)
        start = time.monotonic()

        try:
            import pyttsx3  # type: ignore

            engine = pyttsx3.init()
            engine.setProperty("rate", rate)
            engine.setProperty("volume", float(volume))

            if self.voice_id:
                engine.setProperty("voice", self.voice_id)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                engine.save_to_file(text, tmp_path)
                engine.runAndWait()
                engine.stop()

                with open(tmp_path, "rb") as fh:
                    audio_bytes = fh.read()
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except ImportError:
            logger.warning("pyttsx3 is not installed; returning silent WAV.")
            audio_bytes = _silent_wav()

        except Exception as exc:
            logger.error("pyttsx3 synthesis failed: %s", exc)
            audio_bytes = _silent_wav()

        elapsed_s = time.monotonic() - start
        duration_s = _wav_duration(audio_bytes)

        return TTSResult(
            audio_bytes=audio_bytes,
            duration_s=duration_s,
            engine="pyttsx3",
            language=language,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _wav_duration(wav_bytes: bytes) -> float:
    """Parse a WAV header to extract the audio duration in seconds."""
    try:
        if len(wav_bytes) < 44:
            return 0.1
        # Standard WAV: bytes 24-27 = sample_rate, 34-35 = bits_per_sample,
        # 22-23 = num_channels, 40-43 = data chunk size.
        sample_rate = struct.unpack_from("<I", wav_bytes, 24)[0]
        bits_per_sample = struct.unpack_from("<H", wav_bytes, 34)[0]
        num_channels = struct.unpack_from("<H", wav_bytes, 22)[0]
        data_size = struct.unpack_from("<I", wav_bytes, 40)[0]
        bytes_per_sample = bits_per_sample // 8
        if sample_rate == 0 or bytes_per_sample == 0 or num_channels == 0:
            return 0.1
        n_samples = data_size // (bytes_per_sample * num_channels)
        return n_samples / sample_rate
    except Exception:
        return max(0.1, len(wav_bytes) / 32000.0)


def _silent_wav(sample_rate: int = 16000, duration_ms: int = 100) -> bytes:
    """Return a minimal silent WAV byte string."""
    n_samples = int(sample_rate * duration_ms / 1000)
    data_size = n_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,          # PCM
        1,          # mono
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + b"\x00" * data_size
