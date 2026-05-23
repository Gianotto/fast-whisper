import os
import uuid
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import whisper
from fastapi import Depends, FastAPI, HTTPException, Request, Security, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

WHISPER_TOKEN: str = os.environ["WHISPER_TOKEN"]
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "pt")

_model: whisper.Whisper | None = None
_bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model
    _model = whisper.load_model(WHISPER_MODEL)
    yield
    _model = None


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
):
    suffix = Path(audio.filename or "audio.ogg").suffix or ".ogg"
    tmp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}{suffix}"
    try:
        tmp_path.write_bytes(await audio.read())
        result = _model.transcribe(str(tmp_path), language=WHISPER_LANGUAGE)
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "text": result["text"].strip(),
        "language": result.get("language", WHISPER_LANGUAGE),
        "duration_seconds": round(
            sum(s["end"] - s["start"] for s in result.get("segments", [])), 2
        ),
    }
