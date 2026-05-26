# fast-whisper

Microsserviço FastAPI para transcrição de áudio usando [OpenAI Whisper](https://github.com/openai/whisper). Projetado para integração com **n8n** via webhook — recebe um arquivo de áudio, transcreve e devolve o texto em JSON.

## Funcionalidades

- Endpoint `POST /transcribe` com autenticação Bearer token
- Upload de áudio via `multipart/form-data` (`.ogg`, `.mp3`, `.wav` e qualquer formato que o ffmpeg aceite)
- Modelo Whisper configurável via variável de ambiente (padrão: `base`)
- Idioma configurável (padrão: `pt`)
- Modelo carregado uma única vez no startup do container (sem cold-start por request)
- Arquivos temporários deletados após transcrição

---

## Instalação

### Opção 1 — Docker (recomendado)

**Requisitos:** Docker 24+ e Docker Compose v2

```bash
git clone https://github.com/Gianotto/fast-whisper.git
cd fast-whisper

cp .env.example .env
# Gere um token seguro e cole no .env:
#   openssl rand -hex 32
```

Se o seu ambiente já tem uma rede Docker externa chamada `aurora_net`:

```bash
docker compose up -d
```

Se não tiver essa rede (ambiente standalone):

```bash
# Crie a rede antes de subir o serviço
docker network create aurora_net
docker compose up -d
```

Acompanhe os logs para confirmar que o modelo foi carregado:

```bash
docker compose logs -f whisper-service
# Esperado: INFO: Application startup complete.
```

O serviço ficará disponível em `http://localhost:8001`.

---

### Opção 2 — Local (desenvolvimento / testes)

**Requisitos:** Python 3.11+, pip, ffmpeg

#### 1. Instalar ffmpeg

| Sistema | Comando |
|---------|---------|
| Ubuntu/Debian | `sudo apt install ffmpeg` |
| macOS | `brew install ffmpeg` |
| Windows | `winget install Gyan.FFmpeg` ou baixar em [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) |

Confirme que o ffmpeg está no PATH:

```bash
ffmpeg -version
```

#### 2. Clonar e instalar dependências

```bash
git clone https://github.com/Gianotto/fast-whisper.git
cd fast-whisper

pip install -r whisper_service/requirements.txt
```

#### 3. Configurar variáveis de ambiente

**Linux / macOS:**
```bash
export WHISPER_TOKEN=meu-token-secreto
export WHISPER_MODEL=base
export WHISPER_LANGUAGE=pt
```

**Windows (PowerShell):**
```powershell
$env:WHISPER_TOKEN = "meu-token-secreto"
$env:WHISPER_MODEL = "base"
$env:WHISPER_LANGUAGE = "pt"
```

#### 4. Iniciar o servidor

```bash
uvicorn whisper_service.main:app --host 0.0.0.0 --port 8001 --reload
```

#### 5. Rodar os testes

```bash
python -m pytest tests/ -v
```

Os testes usam o modelo `tiny` (configurado no topo do arquivo de testes) para manter a suite rápida.

---

## Variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|----------|:-----------:|--------|-----------|
| `WHISPER_TOKEN` | Sim | — | Bearer token exigido no header `Authorization` |
| `WHISPER_MODEL` | Não | `base` | Modelo Whisper (ver tabela abaixo) |
| `WHISPER_LANGUAGE` | Não | `pt` | Código de idioma ISO 639-1 passado ao Whisper |

---

## API

### `POST /transcribe`

**Headers:**
```
Authorization: Bearer <WHISPER_TOKEN>
Content-Type: multipart/form-data
```

**Body (form-data):**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `audio` | File | Arquivo de áudio em qualquer formato suportado pelo ffmpeg |

**Resposta 200:**
```json
{
  "text": "mensagem transcrita aqui",
  "language": "pt",
  "duration_seconds": 4.2
}
```

**Códigos de erro:**

| Status | Motivo |
|--------|--------|
| `401` | Token ausente ou inválido |
| `422` | Campo `audio` ausente na requisição |
| `500` | Erro interno durante a transcrição |

**Exemplo com curl:**
```bash
curl -X POST http://localhost:8001/transcribe \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -F "audio=@gravacao.ogg"
```

---

## Integração com n8n

Consulte [docs/n8n-workflow-setup.md](docs/n8n-workflow-setup.md) para o guia completo de configuração do workflow Telegram → whisper-service → chat-ai.

Resumo do nó HTTP Request no n8n:

| Campo | Valor |
|-------|-------|
| Method | `POST` |
| URL | `http://whisper-service:8001/transcribe` |
| Auth Header | `Authorization: Bearer {{ $env.WHISPER_TOKEN }}` |
| Body | Form-Data Multipart, campo `audio` (Binary) |

---

## Modelos disponíveis (`WHISPER_MODEL`)

| Modelo | Parâmetros | VRAM | Velocidade | Recomendado para |
|--------|-----------|------|------------|-----------------|
| `tiny` | 39 M | ~1 GB | ~32x | Testes, prototipagem |
| `base` | 74 M | ~1 GB | ~16x | Uso geral em CPU (padrão) |
| `small` | 244 M | ~2 GB | ~6x | Melhor qualidade em CPU |
| `medium` | 769 M | ~5 GB | ~2x | GPU com VRAM moderada |
| `large-v1` | 1550 M | ~10 GB | 1x | GPU, máxima qualidade (v1) |
| `large-v2` | 1550 M | ~10 GB | 1x | GPU, máxima qualidade (v2) |
| `large-v3` | 1550 M | ~10 GB | 1x | GPU, melhor qualidade atual |
| `large` | 1550 M | ~10 GB | 1x | Alias de `large-v3` |
| `turbo` | 809 M | ~6 GB | ~8x | GPU, melhor custo-benefício |

> Modelos com sufixo `.en` (ex: `tiny.en`, `base.en`) são otimizados apenas para inglês — não usar com português.

Para `base` em CPU, a qualidade é adequada para mensagens de voz do Telegram (frases curtas, vocabulário cotidiano). Para maior precisão em CPU, use `small`.

Para uso com GPU, altere a imagem base no `Dockerfile` para uma com suporte CUDA e ajuste `WHISPER_MODEL` para `turbo` ou `large-v3`.
