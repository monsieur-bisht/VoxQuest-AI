"""gTTS (Google Text-to-Speech) TTS backend."""

from __future__ import annotations

import io
import logging
import time

from ml.tts.base_tts import BaseTTS, TTSResult

logger = logging.getLogger(__name__)

# Approximate MP3 bitrate used to estimate duration when mutagen is unavailable.
_MP3_BYTES_PER_SECOND = 16_000  # ~128 kbps / 8


class GTTSModel(BaseTTS):
    """TTS backend that uses the ``gTTS`` library (requires internet access).

    Parameters
    ----------
    slow:
        When ``True``, gTTS speaks at a reduced speed.  Useful for language
        learning scenarios.
    """

    def __init__(self, slow: bool = False) -> None:
        self.slow = slow

    def synthesize(self, text: str, language: str = "en", **kwargs) -> TTSResult:
        """Synthesise *text* via gTTS and return the MP3 audio bytes.

        Handles :class:`ImportError` (gTTS not installed) and network errors
        gracefully by returning a silent placeholder.

        Parameters
        ----------
        text:
            Text to synthesise.
        language:
            BCP-47 tag supported by gTTS (e.g. ``"en"``, ``"hi"``).
        **kwargs:
            ``slow`` (bool) overrides the instance default.
        """
        slow = kwargs.get("slow", self.slow)
        start = time.monotonic()

        try:
            from gtts import gTTS  # type: ignore

            tts = gTTS(text=text, lang=language, slow=slow)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            audio_bytes = buf.getvalue()

        except ImportError:
            logger.warning("gTTS is not installed; returning silent audio.")
            audio_bytes = _silent_mp3()

        except Exception as exc:
            logger.error("gTTS synthesis failed: %s", exc)
            audio_bytes = _silent_mp3()

        elapsed_s = time.monotonic() - start
        duration_s = _estimate_mp3_duration(audio_bytes)

        return TTSResult(
            audio_bytes=audio_bytes,
            duration_s=duration_s,
            engine="gtts",
            language=language,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _estimate_mp3_duration(audio_bytes: bytes) -> float:
    """Estimate MP3 duration in seconds from byte length."""
    try:
        from mutagen.mp3 import MP3  # type: ignore
        import io

        return MP3(io.BytesIO(audio_bytes)).info.length
    except Exception:
        return max(0.1, len(audio_bytes) / _MP3_BYTES_PER_SECOND)


def _silent_mp3() -> bytes:
    """Return the smallest valid MP3 byte string (silent frame)."""
    # 4-byte minimal silent MP3 frame header.
    return bytes(
        [0xFF, 0xFB, 0x90, 0x00]
        + [0x00] * 413  # padding to complete a minimal frame
    )
