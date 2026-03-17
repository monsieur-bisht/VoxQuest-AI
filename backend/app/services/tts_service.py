import io
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.models.schemas import TTSResponse


class BaseTTS(ABC):
    @abstractmethod
    def synthesize(self, text: str, language: str = "en") -> bytes:
        """Return MP3 audio bytes."""


class GTTSEngine(BaseTTS):
    def synthesize(self, text: str, language: str = "en") -> bytes:
        from gtts import gTTS
        from gtts.tts import gTTSError
        buf = io.BytesIO()
        try:
            tts = gTTS(text=text, lang=language, slow=False)
            tts.write_to_fp(buf)
        except (gTTSError, Exception) as exc:
            # Network unavailable - fall back to stub
            raise RuntimeError(f"gTTS network error: {exc}") from exc
        buf.seek(0)
        return buf.read()


class StubTTS(BaseTTS):
    """Silent stub TTS for environments without gTTS."""

    def synthesize(self, text: str, language: str = "en") -> bytes:
        # Minimal valid MP3 header (ID3 tag) so clients receive bytes
        return b"ID3" + b"\x00" * 7


class TTSService:
    def __init__(self, engine_name: str = "gtts", data_dir: str = "./data"):
        self._engine_name = engine_name
        self._data_dir = Path(data_dir)
        self._audio_dir = self._data_dir / "audio"
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._engine: BaseTTS = self._build_engine(engine_name)

    def _build_engine(self, name: str) -> BaseTTS:
        if name == "gtts":
            try:
                from gtts import gTTS  # noqa: F401
                return GTTSEngine()
            except ImportError:
                return StubTTS()
        return StubTTS()

    def list_voices(self) -> list:
        return [
            {"voice_id": "en-US", "language": "en", "name": "English (US)"},
            {"voice_id": "en-GB", "language": "en", "name": "English (UK)"},
            {"voice_id": "fr-FR", "language": "fr", "name": "French"},
            {"voice_id": "de-DE", "language": "de", "name": "German"},
            {"voice_id": "es-ES", "language": "es", "name": "Spanish"},
            {"voice_id": "ja-JP", "language": "ja", "name": "Japanese"},
        ]

    async def synthesize(
        self,
        text: str,
        language: str = "en",
        voice_id: str = "",
    ) -> TTSResponse:
        lang_code = language.split("-")[0] if "-" in language else language
        try:
            audio_bytes = self._engine.synthesize(text, language=lang_code)
        except RuntimeError:
            # Fall back to stub when primary engine fails (e.g., no network)
            audio_bytes = StubTTS().synthesize(text, language=lang_code)

        filename = f"{uuid.uuid4()}.mp3"
        file_path = self._audio_dir / filename
        file_path.write_bytes(audio_bytes)

        # Estimate duration: ~128 kbps MP3 ≈ 16000 bytes/s
        duration_s = max(0.1, round(len(audio_bytes) / 16000.0, 2))

        return TTSResponse(
            audio_url=f"/audio/{filename}",
            duration_s=duration_s,
            engine_used=self._engine_name,
        )

    def get_audio_path(self, filename: str) -> Path:
        return self._audio_dir / filename
