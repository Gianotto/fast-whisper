import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("WHISPER_TOKEN", "test-secret")
os.environ.setdefault("WHISPER_MODEL", "tiny")
os.environ.setdefault("WHISPER_LANGUAGE", "pt")

from whisper_service.main import app  # noqa: E402

client = TestClient(app)


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
