# fast-whisper

Microsserviço FastAPI para transcrição de áudio usando [OpenAI Whisper](https://github.com/openai/whisper). Projetado para integração com **n8n** via webhook — recebe um arquivo de áudio, transcreve e devolve o texto em JSON.

## Funcionalidades

- Endpoint `POST /transcribe` com autenticação Bearer token
- Upload de áudio via `multipart/form-data` (`.ogg`, `.mp3`, `.wav` e qualquer formato que o ffmpeg aceite)
- Modelo Whisper configurável via variável de ambiente (padrão: `base`)
- Idioma configurável (padrão: `pt`)
- Modelo carregado uma única vez no startup do container (sem cold-start por request)
- Arquivos temporários deletados após transcrição

## Resposta

```json
{
  "text": "mensagem transcrita aqui",
  "language": "pt",
  "duration_seconds": 4.2
}
```

## Requisitos

- Docker + Docker Compose
- Rede Docker externa `aurora_net` (ou ajustar o nome no `docker-compose.yml`)

## Início rápido

```bash
cp .env.example .env
# Edite .env e defina WHISPER_TOKEN com um valor seguro

docker compose up -d whisper-service
docker compose logs -f whisper-service
```

O serviço estará disponível em `http://localhost:8001` (porta mapeada para dev; remova em produção).

## Variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|----------|:-----------:|--------|-----------|
| `WHISPER_TOKEN` | Sim | — | Bearer token exigido no header `Authorization` |
| `WHISPER_MODEL` | Não | `base` | Modelo Whisper: `tiny`, `base`, `small`, `medium` |
| `WHISPER_LANGUAGE` | Não | `pt` | Código de idioma passado ao Whisper |

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

**Respostas:**

| Status | Descrição |
|--------|-----------|
| `200` | Transcrição concluída |
| `401` | Token ausente ou inválido |
| `422` | Campo `audio` ausente ou corrompido |
| `500` | Erro interno do Whisper |

**Exemplo com curl:**
```bash
curl -X POST http://localhost:8001/transcribe \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -F "audio=@audio.ogg"
```

## Desenvolvimento local

### Pré-requisitos

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) no PATH
- `pip install -r whisper_service/requirements.txt`

### Rodar os testes

```bash
python -m pytest tests/ -v
```

Os testes usam o modelo `tiny` (definido via `WHISPER_MODEL=tiny` no topo do arquivo de testes) para manter a suite rápida.

## Integração com n8n

Consulte [docs/n8n-workflow-setup.md](docs/n8n-workflow-setup.md) para o guia completo de configuração do workflow Telegram → whisper-service → chat-ai.

## Performance (CPU)

| Modelo | RAM | Latência por min de áudio |
|--------|-----|--------------------------|
| `tiny` | ~75 MB | ~2–4s |
| `base` | ~145 MB | ~5–10s |
| `small` | ~461 MB | ~15–30s |

Para uso com GPU, altere a imagem base no `Dockerfile` para `pytorch/pytorch` com suporte CUDA e ajuste `WHISPER_MODEL` para `medium` ou `large`.
