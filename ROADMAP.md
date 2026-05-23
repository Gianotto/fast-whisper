**Update Todos**

Explorar estrutura do projeto

Fazer perguntas de clarificação

Propor abordagens (2-3)

Apresentar design e obter aprovação

Escrever spec e commitar

Invocar writing-plans
Contexto entendido. Stack atual: aurora-backend (FastAPI/Python 3.12-slim) + Postgres + n8n, todos na mesma rede Docker. O Telegram já envia mensagens via webhook n8n, mas áudio ainda não é tratado.

Pergunta 1 de 3:

O servidor onde o Aurora roda tem GPU disponível?

Sim, NVIDIA GPU — podemos rodar Whisper local com CUDA (muito mais rápido, qualidade máxima)
Não, só CPU — Whisper local funciona, mas o modelo precisa ser pequeno (tiny ou base) para latência aceitável (~5-15s por áudio)
Prefiro usar a API da OpenAI (whisper-1) — sem GPU, sem latência de modelo, paga por uso (~$0.006/min de áudio)
por enquanto só CPU
CPU só. Isso define o modelo — tiny (rápido, ~2-4s) ou base (~5-10s, melhor precisão em português).

Pergunta 2 de 3:

O Telegram envia áudios de voz como arquivos .ogg/opus. O n8n precisará baixar o arquivo e enviar para o serviço Whisper. Como você prefere que o n8n entregue o áudio ao serviço FastAPI?

Upload direto (multipart/form-data) — n8n faz download do arquivo Telegram e envia como upload HTTP para o FastAPI. Mais simples, sem dependência de armazenamento.
URL para download — n8n passa só a URL do arquivo Telegram; o próprio serviço Whisper faz o download. Menos bytes trafegando no n8n, mas o container Whisper precisa de acesso à internet.
modelo base
upload direto (n8n faz download)
Perfeito. Última pergunta:

Pergunta 3 de 3:

O endpoint FastAPI do Whisper ficará acessível apenas internamente na rede Docker (chamado só pelo n8n). Mesmo assim, você quer algum tipo de autenticação na chamada?

Sem auth — endpoint interno, rede Docker isolada, sem necessidade de token
Bearer token simples — uma variável de ambiente WHISPER_TOKEN verificada no header, igual ao padrão que o Aurora já usa em /api/messages/log
Bearer token, segurança sempre
Ótimo. Tenho tudo que preciso. Vou propor as abordagens antes do design.

Abordagens possíveis
Opção A — Container separado whisper-service (recomendada)
Novo Dockerfile + nova FastAPI app dedicada, adicionada ao docker-compose.yml existente como serviço whisper-service. O n8n chama http://whisper-service:8001/transcribe internamente.

Prós: aurora-backend continua lean (~200MB); Whisper + PyTorch somam ~3GB e ficam isolados; restart e rebuild independentes; interface limpa via HTTP.

Contras: Um container a mais para gerenciar.

Opção B — Embutido no aurora-backend
Adiciona openai-whisper + torch ao requirements.txt existente e cria um endpoint /api/transcribe dentro do FastAPI atual.

Prós: Stack mais simples (um serviço a menos).

Contras: Imagem do aurora-backend vai de ~200MB para ~3GB; qualquer rebuild do backend força rebuild do Whisper; mistura responsabilidades.

Opção C — Script n8n puro via API OpenAI whisper-1
Sem novo container — n8n chama direto api.openai.com/v1/audio/transcriptions com a chave OpenAI.

Prós: Zero infra adicional, zero latência de cold start.

Contras: Custo por uso, dados de áudio saem para a nuvem, requer chave OpenAI válida e créditos.

Minha recomendação é a Opção A. Container separado mantém o aurora-backend enxuto, o Whisper pode reiniciar sem derrubar o backend, e o isolamento facilita trocar para GPU no futuro sem tocar no resto da stack.

Concorda com a Opção A para seguirmos com o design?

opção A
Design — Seção 1: Arquitetura Geral

Telegram
   │
   │  voz (.ogg)
   ▼
n8n (webhook-telegram)
   │
   ├─► [se texto] ──────────────────────────────► workflow chat-ai → resposta
   │
   └─► [se voz]
          │
          │  1. GET file_path via Telegram Bot API
          │  2. Download do .ogg
          │  3. POST multipart/form-data
          ▼
   whisper-service:8001/transcribe
   (Bearer token)
          │
          │  {"text": "mensagem transcrita..."}
          ▼
   n8n injeta o texto como mensagem
          │
          ▼
   workflow chat-ai → resposta ao usuário
Componentes novos:

whisper-service/ — pasta nova no repo com Dockerfile, FastAPI app e requirements
Novo serviço no docker-compose.snippet.yml
Atualização do workflow n8n do Telegram (branching: texto vs voz)
Componentes inalterados:

aurora-backend — não muda nada
Workflow chat-ai do n8n — não muda nada
Schema do banco — não muda nada
Isso está alinhado com o que você imaginou?

c:\Dev\aurora_final\ROADMAP.md
sim, vou puxar isso para outro workspace e trabalhar separado.
Design — Seção 2: whisper-service FastAPI
Estrutura de arquivos:


whisper-service/
├── Dockerfile
├── requirements.txt
└── main.py
Endpoint único:


POST /transcribe
Authorization: Bearer <WHISPER_TOKEN>
Content-Type: multipart/form-data

Campo: audio (file) — .ogg, .mp3, .wav, qualquer formato que o ffmpeg aceite

Resposta 200:
{
  "text": "mensagem transcrita aqui",
  "language": "pt",
  "duration_seconds": 8.4
}

Resposta 401: token inválido ou ausente
Resposta 422: arquivo ausente ou corrompido
Resposta 500: erro interno do Whisper
Comportamento:

Modelo base carregado uma única vez na inicialização do container (evita ~5s de cold start por request)
language="pt" fixo no parâmetro de transcrição (melhora precisão, evita detecção errada)
Arquivo recebido salvo em /tmp com nome aleatório, deletado após transcrição
ffmpeg instalado via apt (dependência do Whisper para decodificar .ogg/opus)
Variáveis de ambiente:


WHISPER_TOKEN=<bearer token>
WHISPER_MODEL=base        # permite trocar para tiny/small via env
WHISPER_LANGUAGE=pt       # padrão, sobrescritível
Faz sentido? Alguma coisa a ajustar antes de ir para a parte do Docker e n8n?


adicione os arquivos que não tem impacto no app, no dockerignore.
faça o cleanup do projeto
Crie documentação no README.md
git push e commit (https://github.com/Gianotto/fast-whisper)