import io
import struct
import sys
import os
import uuid
import wave

import pytest

# Add backend and project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def app():
    from app.main import app
    return app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def sample_audio_bytes():
    """Generate a simple WAV audio bytes for testing (1 second of silence)."""
    sample_rate = 16000
    n_samples = sample_rate  # 1 second
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b'\x00' * n_samples * 2)
    return buf.getvalue()


@pytest.fixture
def session_id():
    return str(uuid.uuid4())
