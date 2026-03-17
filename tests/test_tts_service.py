"""Tests for TTS service."""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.tts_service import StubTTS, TTSService


class TestStubTTS:
    def setup_method(self):
        self.tts = StubTTS()

    def test_synthesize_returns_bytes(self):
        result = self.tts.synthesize("hello world")
        assert isinstance(result, bytes)

    def test_synthesize_returns_nonempty_bytes(self):
        result = self.tts.synthesize("hello world")
        assert len(result) > 0

    def test_synthesize_with_language(self):
        result = self.tts.synthesize("bonjour", language="fr")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_synthesize_starts_with_id3_header(self):
        result = self.tts.synthesize("hello")
        # StubTTS returns a minimal MP3 with ID3 header
        assert result[:3] == b"ID3"

    def test_synthesize_empty_text(self):
        result = self.tts.synthesize("")
        assert isinstance(result, bytes)


class TestTTSService:
    def setup_method(self, tmp_path_factory):
        pass

    @pytest.fixture(autouse=True)
    def _setup_service(self, tmp_path):
        self.service = TTSService(engine_name="stub", data_dir=str(tmp_path))
        # Ensure the engine is the stub regardless of what's installed
        from app.services.tts_service import StubTTS
        self.service._engine = StubTTS()

    def test_list_voices_returns_list(self):
        voices = self.service.list_voices()
        assert isinstance(voices, list)
        assert len(voices) > 0

    def test_list_voices_have_required_fields(self):
        voices = self.service.list_voices()
        for voice in voices:
            assert "voice_id" in voice
            assert "language" in voice

    @pytest.mark.asyncio
    async def test_synthesize_returns_tts_response(self):
        response = await self.service.synthesize("hello world")
        assert response is not None
        assert response.audio_url is not None
        assert response.duration_s > 0

    @pytest.mark.asyncio
    async def test_synthesize_saves_audio_file(self, tmp_path):
        service = TTSService(engine_name="stub", data_dir=str(tmp_path))
        from app.services.tts_service import StubTTS
        service._engine = StubTTS()
        response = await service.synthesize("hello world")
        filename = response.audio_url.split("/")[-1]
        audio_path = service.get_audio_path(filename)
        assert audio_path.exists()

    @pytest.mark.asyncio
    async def test_synthesize_audio_url_format(self):
        response = await self.service.synthesize("hello world")
        assert response.audio_url.startswith("/audio/")
        assert response.audio_url.endswith(".mp3")

    @pytest.mark.asyncio
    async def test_synthesize_with_language(self):
        response = await self.service.synthesize("bonjour", language="fr")
        assert response is not None
        assert response.audio_url is not None
