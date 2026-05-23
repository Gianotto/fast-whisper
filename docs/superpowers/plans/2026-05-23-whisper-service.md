# whisper-service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar um microsserviço FastAPI que recebe upload de áudio via multipart/form-data, transcreve com Whisper (modelo base, CPU) e retorna o texto — protegido por Bearer token.

**Architecture:** Container Docker isolado (`whisper-service`) rodando FastAPI na porta 8001. O modelo Whisper é carregado uma única vez no startup (evita cold-start por request). Arquivos de áudio são salvos em `/tmp` com UUID e deletados após transcrição.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, openai-whisper, ffmpeg (apt), pytest, httpx

---

## File Map

| Arquivo | Responsabilidade |
|---------|-----------------|
| `whisper-service/main.py` | App FastAPI: startup, auth, endpoint `/transcribe`, limpeza de temp |
| `whisper-service/requirements.txt` | Dependências Python do serviço |
| `whisper-service/Dockerfile` | Imagem Docker com Python 3.11-slim + ffmpeg + deps |
| `tests/test_main.py` | Testes do endpoint (TestClient) |
| `docker-compose.yml` | Definição do serviço para integração com n8n |

---

## Task 1: requirements.txt e estrutura base

**Files:**
- Create: `whisper-service/requirements.txt`

- [ ] **Step 1: Criar requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
openai-whisper==20231117
python-multipart==0.0.9
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.6
```

- [ ] **Step 2: Commit**

```bash
git init
git add whisper-service/requirements.txt
git commit -m "chore: add requirements.txt for whisper-service"
```

---

## Task 2: FastAPI app — esqueleto com auth

**Files:**
- Create: `whisper-service/main.py`
- Create: `tests/test_main.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Escrever o teste de autenticação (falha)**

```python
# tests/test_main.py
import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("WHISPER_TOKEN", "test-secret")
os.environ.setdefault("WHISPER_MODEL", "tiny")   # tiny para testes — não baixa base
os.environ.setdefault("WHISPER_LANGUAGE", "pt")

from whisper_service.main import app   # noqa: E402

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
```

- [ ] **Step 2: Criar `whisper-service/__init__.py` vazio**

```bash
touch whisper-service/__init__.py
```

> No Windows: `New-Item -ItemType File whisper-service/__init__.py`

- [ ] **Step 3: Rodar os testes para confirmar falha**

```bash
cd c:\Dev\fast-whisper
python -m pytest tests/test_main.py -v
```

Esperado: `ModuleNotFoundError: No module named 'whisper_service'` — confirma que o módulo não existe ainda.

- [ ] **Step 4: Criar `whisper-service/main.py` com esqueleto + auth**

```python
# whisper-service/main.py
import os
import uuid
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import whisper
from fastapi import Depends, FastAPI, HTTPException, Security, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
WHISPER_TOKEN: str = os.environ["WHISPER_TOKEN"]
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "pt")

_model: whisper.Whisper | None = None
_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# Lifespan — load model once at startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model
    _model = whisper.load_model(WHISPER_MODEL)
    yield
    _model = None


app = FastAPI(title="whisper-service", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> None:
    if credentials.credentials != WHISPER_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
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
```

- [ ] **Step 5: Criar `conftest.py` para o pytest achar o módulo**

```python
# conftest.py  (raiz do projeto)
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
```

> Isso adiciona `c:\Dev\fast-whisper` ao path, então `from whisper_service.main import app` funciona.

- [ ] **Step 6: Renomear pasta para módulo Python**

A pasta `whisper-service` usa hífen, que não é importável. Crie um link simbólico ou use a convenção `whisper_service`:

```bash
# Renomear a pasta
Rename-Item whisper-service whisper_service
```

E atualize o `Dockerfile` (Task 4) para usar `whisper_service/`.

- [ ] **Step 7: Rodar os testes de auth**

```bash
python -m pytest tests/test_main.py::test_missing_token_returns_401 tests/test_main.py::test_wrong_token_returns_401 tests/test_main.py::test_valid_token_without_file_returns_422 -v
```

Esperado: os 3 passam. O `test_valid_token_without_file_returns_422` pode demorar pois carrega o modelo `tiny`.

- [ ] **Step 8: Commit**

```bash
git add whisper_service/main.py whisper_service/__init__.py tests/ conftest.py
git commit -m "feat: FastAPI skeleton with bearer token auth"
```

---

## Task 3: Endpoint /transcribe — teste com áudio real

**Files:**
- Modify: `tests/test_main.py`

- [ ] **Step 1: Adicionar fixture com arquivo de áudio mínimo**

O Whisper precisa de um arquivo de áudio válido. Crie um WAV silencioso de 1s para os testes (sem ffmpeg instalado no ambiente de dev, use um WAV raw):

```python
# Adicionar no topo de tests/test_main.py (após os imports existentes)
import io
import struct
import wave


def _make_silent_wav(duration_s: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Gera um WAV PCM mono silencioso em memória."""
    num_samples = int(sample_rate * duration_s)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<" + "h" * num_samples, *([0] * num_samples)))
    return buf.getvalue()
```

- [ ] **Step 2: Escrever o teste de transcrição bem-sucedida**

```python
def test_transcribe_silent_audio_returns_200():
    wav_bytes = _make_silent_wav()
    response = client.post(
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
```

- [ ] **Step 3: Rodar o teste**

```bash
python -m pytest tests/test_main.py::test_transcribe_silent_audio_returns_200 -v -s
```

Esperado: PASS. O texto transcrito de silêncio geralmente é `""` ou `" ."` — qualquer string é válida.

- [ ] **Step 4: Escrever teste de arquivo ausente**

```python
def test_transcribe_missing_file_returns_422():
    response = client.post(
        "/transcribe",
        headers={"Authorization": "Bearer test-secret"},
        data={},   # sem campo 'audio'
    )
    assert response.status_code == 422
```

- [ ] **Step 5: Rodar todos os testes**

```bash
python -m pytest tests/ -v
```

Esperado: 4 testes passando.

- [ ] **Step 6: Commit**

```bash
git add tests/test_main.py
git commit -m "test: add transcription and auth test coverage"
```

---

## Task 4: Dockerfile

**Files:**
- Create: `whisper_service/Dockerfile`

- [ ] **Step 1: Escrever o Dockerfile**

```dockerfile
FROM python:3.11-slim

# ffmpeg necessário para decodificar .ogg/opus/mp3
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pré-baixar o modelo no build para evitar download no primeiro request
ARG WHISPER_MODEL=base
RUN python -c "import whisper; whisper.load_model('${WHISPER_MODEL}')"

COPY whisper_service/ ./whisper_service/

EXPOSE 8001

CMD ["uvicorn", "whisper_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

> O `RUN python -c "import whisper; whisper.load_model(...)"` baixa os pesos durante o `docker build`, não no startup do container. Isso deixa o cold-start do container < 2s.

- [ ] **Step 2: Criar `.dockerignore`**

```
# .dockerignore
tests/
docs/
conftest.py
*.md
__pycache__/
*.pyc
.git/
```

- [ ] **Step 3: Build de teste local (opcional — requer Docker)**

```bash
docker build -f whisper_service/Dockerfile -t whisper-service:local .
```

Esperado: imagem ~3.5 GB (PyTorch + Whisper weights). Build demora ~5 min na primeira vez.

- [ ] **Step 4: Commit**

```bash
git add whisper_service/Dockerfile .dockerignore
git commit -m "feat: add Dockerfile with ffmpeg and pre-downloaded model"
```

---

## Task 5: docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Escrever o docker-compose.yml**

```yaml
services:
  whisper-service:
    build:
      context: .
      dockerfile: whisper_service/Dockerfile
      args:
        WHISPER_MODEL: ${WHISPER_MODEL:-base}
    image: whisper-service:latest
    restart: unless-stopped
    ports:
      - "8001:8001"          # remover esta linha em produção; n8n acessa via rede interna
    environment:
      WHISPER_TOKEN: ${WHISPER_TOKEN}
      WHISPER_MODEL: ${WHISPER_MODEL:-base}
      WHISPER_LANGUAGE: ${WHISPER_LANGUAGE:-pt}
    networks:
      - aurora_net            # mesma rede do n8n — ajuste o nome se diferente

networks:
  aurora_net:
    external: true            # rede já existente criada pelo docker-compose do aurora
```

- [ ] **Step 2: Criar `.env.example`**

```bash
# .env.example
WHISPER_TOKEN=troque-por-token-seguro
WHISPER_MODEL=base
WHISPER_LANGUAGE=pt
```

- [ ] **Step 3: Subir o serviço**

```bash
cp .env.example .env
# edite .env e defina WHISPER_TOKEN

docker compose up -d whisper-service
docker compose logs -f whisper-service
```

Esperado nos logs:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

- [ ] **Step 4: Smoke test manual**

```bash
# Teste de auth
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/transcribe
# Esperado: 403

# Teste com token errado
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer errado" \
  -X POST http://localhost:8001/transcribe
# Esperado: 401

# Teste com token correto e arquivo de áudio
curl -s -X POST http://localhost:8001/transcribe \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -F "audio=@caminho/para/audio.ogg"
# Esperado: {"text":"...","language":"pt","duration_seconds":...}
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add docker-compose with whisper-service and env example"
```

---

## Task 6: Configuração do n8n (workflow snippet)

Esta tarefa não envolve código Python — é a configuração do nó HTTP Request no n8n para chamar o whisper-service.

- [ ] **Step 1: No workflow do Telegram no n8n, adicionar branch para mensagens de voz**

Adicione um nó **If** após o webhook Telegram:
- Condition: `{{ $json.message.voice != undefined }}`
- Branch `true` → fluxo de transcrição
- Branch `false` → fluxo de texto existente

- [ ] **Step 2: Nó para baixar o arquivo de voz do Telegram**

Adicione um nó **HTTP Request** após o If:
- Method: `GET`
- URL: `https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/getFile?file_id={{ $json.message.voice.file_id }}`
- Salvar resultado como `file_path`

Adicione outro **HTTP Request** para download binário:
- Method: `GET`
- URL: `https://api.telegram.org/file/bot{{ $env.TELEGRAM_BOT_TOKEN }}/{{ $json.result.file_path }}`
- Response Format: `File`

- [ ] **Step 3: Nó HTTP Request para o whisper-service**

- Method: `POST`
- URL: `http://whisper-service:8001/transcribe`
- Authentication: `Header Auth`
  - Name: `Authorization`
  - Value: `Bearer {{ $env.WHISPER_TOKEN }}`
- Body Content Type: `Form-Data Multipart`
  - Field: `audio` → tipo `Binary`, valor `{{ $binary.data }}`

- [ ] **Step 4: Injetar o texto transcrito no fluxo chat-ai**

Após a resposta do whisper-service, use um nó **Set** para sobrescrever o campo de texto:
```
message.text = {{ $json.text }}
```
Conecte ao workflow chat-ai existente.

---

## Variáveis de Ambiente — Resumo

| Variável | Obrigatória | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `WHISPER_TOKEN` | Sim | — | Bearer token verificado no header `Authorization` |
| `WHISPER_MODEL` | Não | `base` | Modelo Whisper: `tiny`, `base`, `small` |
| `WHISPER_LANGUAGE` | Não | `pt` | Código de idioma passado ao Whisper |

---

## Notas de Operação

- **Latência esperada (CPU):** modelo `base` → ~5–10s por minuto de áudio; `tiny` → ~2–4s
- **Memória:** modelo `base` usa ~145 MB de RAM; `small` usa ~461 MB
- **Escalabilidade:** uvicorn com 1 worker (padrão) processa 1 request por vez — adequado para uso pessoal/n8n sequencial
- **Logs:** uvicorn loga cada request com status HTTP e latência por padrão
