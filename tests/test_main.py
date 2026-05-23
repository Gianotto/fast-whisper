import io
import os
import struct
import wave

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("WHISPER_TOKEN", "test-secret")
os.environ.setdefault("WHISPER_MODEL", "tiny")
os.environ.setdefault("WHISPER_LANGUAGE", "pt")


def _make_silent_wav(duration_s: float = 1.0, sample_rate: int = 16000) -> bytes:
    num_samples = int(sample_rate * duration_s)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<" + "h" * num_samples, *([0] * num_samples)))
    return buf.getvalue()


from whisper_service.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="session")
def live_client():
    with TestClient(app) as c:
        yield c


def test_missing_token_returns_401():
    response = client.post("/transcribe")
    assert response.status_code == 401


def test_wrong_token_returns_401():
    response = client.post(
        "/transcribe",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_valid_token_without_file_returns_422():
    response = client.post(
        "/transcribe",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 422


def test_transcribe_silent_audio_returns_200(live_client):
    wav_bytes = _make_silent_wav()
    response = live_client.post(
        "/transcribe",
        headers={"Authorization": "Bearer test-secret"},
        files={"audio": ("test.wav", wav_bytes, "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "text" in body
    assert "language" in body
    assert "duration_seconds" in body
    assert isinstance(body["duration_seconds"], float)


def test_transcribe_missing_file_returns_422():
    response = client.post(
        "/transcribe",
        headers={"Authorization": "Bearer test-secret"},
        data={},
    )
    assert response.status_code == 422
