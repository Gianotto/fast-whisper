# n8n Workflow — Integração com whisper-service

## Visão Geral do Fluxo

```
Telegram (voz) → webhook n8n → getFile → download .ogg → POST /transcribe → texto → chat-ai
Telegram (texto) ────────────────────────────────────────────────────────────────→ chat-ai
```

---

## Passo 1 — Branch no webhook Telegram

Adicione um nó **If** após o nó webhook do Telegram:

- **Condition:** `{{ $json.message.voice != undefined }}`
- Branch **true** → fluxo de transcrição (passos 2-4)
- Branch **false** → workflow chat-ai existente (sem mudança)

---

## Passo 2 — Obter URL do arquivo de voz

Adicione um nó **HTTP Request**:

| Campo | Valor |
|-------|-------|
| Method | `GET` |
| URL | `https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/getFile?file_id={{ $json.message.voice.file_id }}` |
| Response Format | `JSON` |

Resultado em `$json.result.file_path`.

---

## Passo 3 — Download do arquivo .ogg

Adicione outro nó **HTTP Request**:

| Campo | Valor |
|-------|-------|
| Method | `GET` |
| URL | `https://api.telegram.org/file/bot{{ $env.TELEGRAM_BOT_TOKEN }}/{{ $json.result.file_path }}` |
| Response Format | `File` |

O arquivo binário fica em `$binary.data`.

---

## Passo 4 — Chamar whisper-service

Adicione um nó **HTTP Request**:

| Campo | Valor |
|-------|-------|
| Method | `POST` |
| URL | `http://whisper-service:8001/transcribe` |
| Authentication | Header Auth |
| Header Name | `Authorization` |
| Header Value | `Bearer {{ $env.WHISPER_TOKEN }}` |
| Body Content Type | `Form-Data Multipart` |
| Field name | `audio` |
| Field type | `Binary` |
| Binary property | `data` |

Resposta:
```json
{"text": "mensagem transcrita", "language": "pt", "duration_seconds": 4.2}
```

---

## Passo 5 — Injetar texto no fluxo chat-ai

Adicione um nó **Set**:

- Campo: `message.text`
- Valor: `{{ $json.text }}`

Conecte ao workflow chat-ai existente.

---

## Variável de ambiente no n8n

Adicione no `.env` do n8n (ou nas variáveis de ambiente do container):

```
WHISPER_TOKEN=<mesmo valor do .env do whisper-service>
```
