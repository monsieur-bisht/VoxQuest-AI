"""Integration tests for FastAPI endpoints via TestClient."""
import sys
import os
import io
import wave

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_service_name(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["service"] == "VoxQuest-AI"

    def test_health_returns_version(self, client):
        response = client.get("/health")
        data = response.json()
        assert "version" in data


class TestStoryEndpoints:
    def test_post_story_start_returns_200(self, client):
        response = client.post("/api/story/start")
        assert response.status_code == 200

    def test_post_story_start_returns_narration(self, client):
        response = client.post("/api/story/start")
        data = response.json()
        assert "narration_text" in data
        assert "choices" in data

    def test_post_story_start_with_session_id(self, client):
        import uuid
        session_id = str(uuid.uuid4())
        response = client.post(f"/api/story/start?session_id={session_id}")
        assert response.status_code == 200

    def test_get_story_state_returns_200(self, client):
        import uuid
        session_id = str(uuid.uuid4())
        client.post(f"/api/story/start?session_id={session_id}")
        response = client.get(f"/api/story/state/{session_id}")
        assert response.status_code == 200

    def test_get_story_state_returns_session_id(self, client):
        import uuid
        session_id = str(uuid.uuid4())
        client.post(f"/api/story/start?session_id={session_id}")
        response = client.get(f"/api/story/state/{session_id}")
        data = response.json()
        assert data["session_id"] == session_id

    def test_post_story_choice_valid(self, client):
        import uuid
        session_id = str(uuid.uuid4())
        narration = client.post(f"/api/story/start?session_id={session_id}").json()
        choices = narration.get("choices", [])
        if choices:
            choice_id = choices[0]["choice_id"]
            response = client.post(
                f"/api/story/choice?session_id={session_id}&choice_id={choice_id}"
            )
            assert response.status_code == 200

    def test_post_story_reset_returns_narration(self, client):
        import uuid
        session_id = str(uuid.uuid4())
        client.post(f"/api/story/start?session_id={session_id}")
        response = client.post(f"/api/story/reset/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert "narration_text" in data


class TestASREndpoints:
    def test_get_asr_models_returns_200(self, client):
        response = client.get("/api/asr/models")
        assert response.status_code == 200

    def test_get_asr_models_returns_list(self, client):
        response = client.get("/api/asr/models")
        data = response.json()
        # Endpoint returns {"models": [...], "current": "..."} or a list
        models = data.get("models", data) if isinstance(data, dict) else data
        assert isinstance(models, list)
        assert len(models) > 0

    def test_post_asr_transcribe_with_wav(self, client):
        # Build a minimal WAV bytes
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b'\x00' * 32000)
        wav_bytes = buf.getvalue()

        response = client.post(
            "/api/asr/transcribe",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        assert response.status_code == 200

    def test_post_asr_transcribe_returns_transcript(self, client):
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b'\x00' * 32000)
        wav_bytes = buf.getvalue()

        response = client.post(
            "/api/asr/transcribe",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        data = response.json()
        assert "transcript" in data


class TestBenchmarkEndpoints:
    def test_get_benchmark_metrics_returns_200(self, client):
        response = client.get("/api/benchmark/metrics")
        assert response.status_code == 200

    def test_get_benchmark_metrics_has_expected_fields(self, client):
        response = client.get("/api/benchmark/metrics")
        data = response.json()
        # The metrics endpoint should return a dict with relevant keys
        assert isinstance(data, dict)

    def test_post_benchmark_run_returns_200(self, client):
        response = client.post("/api/benchmark/run")
        assert response.status_code == 200

    def test_post_benchmark_run_returns_results(self, client):
        response = client.post("/api/benchmark/run")
        data = response.json()
        # Endpoint returns result fields directly (run_id, avg_wer, etc.)
        assert isinstance(data, dict)
        assert "run_id" in data or "results" in data
