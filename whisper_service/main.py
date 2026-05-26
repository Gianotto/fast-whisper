import os
import uuid
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import whisper
from fastapi import Depends, FastAPI, HTTPException, Query, Security, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

WHISPER_TOKEN: str = os.environ["WHISPER_TOKEN"]
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "pt")

_models: dict[str, whisper.Whisper] = {}
_bearer = HTTPBearer(auto_error=False)


def get_model(name: str) -> whisper.Whisper:
    if name not in _models:
        _models[name] = whisper.load_model(name)
    return _models[name]


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_model(WHISPER_MODEL)
    yield


app = FastAPI(title="whisper-service", lifespan=lifespan)


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
) -> None:
    if credentials is None or credentials.credentials != WHISPER_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@app.post("/transcribe")
async def transcribe(
    audio: UploadFile,
    _: None = Depends(verify_token),
    model: Optional[str] = Query(default=None),
):
    model_name = model or WHISPER_MODEL
    suffix = Path(audio.filename or "audio.ogg").suffix or ".ogg"
    tmp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}{suffix}"
    try:
        tmp_path.write_bytes(await audio.read())
        result = get_model(model_name).transcribe(str(tmp_path), language=WHISPER_LANGUAGE)
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "text": result["text"].strip(),
        "language": result.get("language", WHISPER_LANGUAGE),
        "duration_seconds": round(
            sum(s["end"] - s["start"] for s in result.get("segments", [])), 2
        ),
        "model": model_name,
    }
