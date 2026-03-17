"""Tests for ASR service (uses StubASR to avoid requiring Whisper)."""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.asr_service import StubASR, ASRService


class TestStubASR:
    def setup_method(self):
        self.asr = StubASR()

    def test_transcribe_returns_dict(self, sample_audio_bytes):
        result = self.asr.transcribe(sample_audio_bytes)
        assert isinstance(result, dict)

    def test_result_has_required_fields(self, sample_audio_bytes):
        result = self.asr.transcribe(sample_audio_bytes)
        assert "transcript" in result
        assert "confidence" in result
        assert "audio_duration_s" in result

    def test_transcript_is_string(self, sample_audio_bytes):
        result = self.asr.transcribe(sample_audio_bytes)
        assert isinstance(result["transcript"], str)

    def test_confidence_in_range(self, sample_audio_bytes):
        result = self.asr.transcribe(sample_audio_bytes)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_audio_duration_positive(self, sample_audio_bytes):
        result = self.asr.transcribe(sample_audio_bytes)
        assert result["audio_duration_s"] > 0.0

    def test_language_parameter_accepted(self, sample_audio_bytes):
        result = self.asr.transcribe(sample_audio_bytes, language="hi")
        assert isinstance(result["transcript"], str)


class TestASRService:
    def setup_method(self):
        # Force stub by using a model size that triggers StubASR fallback
        self.service = ASRService(model_size="base")
        # Manually inject StubASR so tests don't try to load Whisper
        from app.services.asr_service import StubASR
        self.service._asr = StubASR()

    def test_list_models(self):
        models = self.service.list_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "base" in models

    def test_switch_model_resets_asr(self):
        self.service.switch_model("tiny")
        assert self.service._model_size == "tiny"
        assert self.service._asr is None

    @pytest.mark.asyncio
    async def test_transcribe_audio_returns_response(self, sample_audio_bytes):
        from app.services.asr_service import StubASR
        self.service._asr = StubASR()
        response = await self.service.transcribe_audio(
            audio_bytes=sample_audio_bytes,
            language="en",
            session_id="test-session",
        )
        assert response.transcript is not None
        assert isinstance(response.transcript, str)
        assert response.language == "en"
        assert response.processing_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_transcribe_with_expected_text_computes_wer(self, sample_audio_bytes):
        from app.services.asr_service import StubASR
        self.service._asr = StubASR()
        response = await self.service.transcribe_audio(
            audio_bytes=sample_audio_bytes,
            language="en",
            session_id="test-session",
            expected_text="hello world",
        )
        assert response.wer is not None
        assert response.wer >= 0.0

    @pytest.mark.asyncio
    async def test_transcribe_without_expected_text_wer_is_none(self, sample_audio_bytes):
        from app.services.asr_service import StubASR
        self.service._asr = StubASR()
        response = await self.service.transcribe_audio(
            audio_bytes=sample_audio_bytes,
            language="en",
            session_id="test-session",
        )
        assert response.wer is None
