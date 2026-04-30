# ResearchMind

AI-powered research assistant that lets you build isolated knowledge contexts from PDFs, web pages, images, audio recordings, and raw text — then chat with an agentic RAG pipeline over them.  Includes a full voice mode with VAD, Whisper transcription, quality gating, and browser TTS.

---

## Features

- **Multiple source types** — PDF (URL or upload), web page scraping, image description (vision LLM), audio transcription (Whisper), raw text paste
- **Context isolation** — each project/topic lives in its own named context; queries never cross contexts
- **Agentic RAG pipeline** — LangGraph agent with router → retrieve → generate → critic loop; iterates until quality threshold is met
- **Voice mode** — tap-to-speak UI with Silero VAD, faster-whisper STT, multi-signal quality gate, barge-in support, and browser TTS
- **LiteLLM proxy** — swap between Ollama (local), Groq (free cloud), vLLM (GPU), or OpenAI without changing application code
- **Qdrant** — vector store for chunks + metadata collections for contexts, sources, history, and chat
- **Multilingual UI** — English / Polish, toggle via URL param `?lang=pl`
- **Mobile-first frontend** — Streamlit, no sidebar, centered layout, pill-based source selector, floating mic + voice FABs

---

## Architecture

```
Browser (Streamlit :8501)
    │
    ▼
FastAPI backend (:8001 / :8000 in Docker)
    ├── /contexts        — CRUD for research contexts
    ├── /ingest/*        — PDF URL, web, upload, raw text, image, audio
    ├── /query/ask       — LangGraph agentic RAG
    ├── /query/transcribe — Whisper STT (used by mic FAB)
    └── /voice/turn      — full voice pipeline (VAD → STT → gate → LLM → TTS)
          │
          ├── Qdrant          — vector + metadata store
          ├── LiteLLM proxy   — unified LLM API (:4000)
          │     ├── Ollama (local)   llama3.1:8b / qwen2.5:3b
          │     ├── Groq (cloud)     llama-3.1-8b-instant
          │     └── vLLM (GPU)       Qwen2.5-7B
          ├── Silero VAD      — speech activity detection
          ├── faster-whisper  — audio transcription (local)
          └── OpenAI TTS      — voice responses (optional)
```

---

## Quick Start (local, no GPU)

**Prerequisites:** Docker + Docker Compose, or Python 3.11+ with `uv`.

### Dev CLI (fastest)

```bash
# Start both backend and frontend, stream logs
python dev.py start

# Per-service control
python dev.py backend restart
python dev.py frontend stop
python dev.py status
```

The CLI kills any existing process on the port before starting, so re-running is always safe.

### Docker Compose

```bash
docker compose up -d
docker exec researchmind-ollama ollama pull qwen2.5:3b
```

Open `http://localhost:8501`.

### Manual

```bash
# 1. Start Qdrant
docker compose up qdrant -d

# 2. Backend (backend/.env already set for embedded Qdrant + Ollama)
cd backend
uv venv && uv pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8001

# 3. Frontend (new terminal)
cd frontend
uv venv && uv pip install -r requirements.txt
.venv/bin/streamlit run app.py --server.port 8501
```

The `backend/.env` ships pre-configured for local development:
`QDRANT_LOCAL_PATH=./qdrant_db`, Ollama at `localhost:11434`.

---

## Configuration

### Core backend variables (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `QDRANT_HOST` | `qdrant` | Qdrant hostname or Cloud cluster URL |
| `QDRANT_PORT` | `6333` | Qdrant port (ignored for Cloud) |
| `QDRANT_API_KEY` | _(empty)_ | Qdrant Cloud API key |
| `QDRANT_LOCAL_PATH` | _(empty)_ | Local embedded path (e.g. `./qdrant_db`) |
| `LITELLM_BASE_URL` | `http://litellm:4000` | LiteLLM proxy URL |
| `LITELLM_API_KEY` | `sk-researchmind-local` | LiteLLM master key |
| `LLM_MODEL` | `local-llm` | Model name as defined in `litellm_config.yaml` |
| `VISION_MODEL` | `local-vision` | Model used for image description |
| `WHISPER_MODEL` | `base` | faster-whisper model size (`tiny`/`base`/`small`/`medium`/`large-v3`) |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Sentence-transformers model for chunk embeddings |
| `EMBEDDING_DIM` | `1024` | Embedding dimension (must match the model) |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Character overlap between chunks |

### Voice pipeline variables (`VOICE_` prefix)

| Variable | Default | Description |
|---|---|---|
| `VOICE_WHISPER_MODEL_SIZE` | `small` | Whisper model for voice turns (separate from ingest Whisper) |
| `VOICE_WHISPER_DEVICE` | `auto` | `cpu`, `cuda`, or `auto` |
| `VOICE_VAD_THRESHOLD` | `0.5` | Silero speech-probability threshold |
| `VOICE_VAD_MIN_SILENCE_MS` | `1500` | Trailing silence before turn ends |
| `VOICE_NO_SPEECH_PROB_THRESHOLD` | `0.6` | Gate: all-silent segment threshold |
| `VOICE_AVG_LOGPROB_THRESHOLD` | `-1.0` | Gate: bad-logprob threshold |
| `VOICE_LOW_CONFIDENCE_LOGPROB` | `-0.7` | Gate: borderline-confidence threshold |
| `VOICE_LLM_ARBITER_ENABLED` | `true` | Use LLM to resolve LOW_CONFIDENCE turns |
| `VOICE_LLM_ARBITER_MODEL` | `gpt-4o-mini` | Model for the quality-gate arbiter |
| `VOICE_TTS_MODEL` | `tts-1` | OpenAI TTS model |
| `VOICE_TTS_VOICE` | `nova` | OpenAI TTS voice |
| `OPENAI_API_KEY` | _(required for TTS)_ | If absent, TTS falls back to browser Web Speech API |

### LLM models

Models are defined in `litellm_config.yaml`. Switch at runtime by changing `LLM_MODEL`:

| Model name | Provider | Notes |
|---|---|---|
| `local-llm-small` | Ollama `qwen2.5:3b` | Default, runs on CPU |
| `local-llm` | Ollama `llama3.1:8b` | Better quality, needs ~8 GB RAM |
| `local-vision` | Ollama `llava` | Image description |
| `groq-llama` | Groq API | Free tier, requires `GROQ_API_KEY` |
| `groq-llama-large` | Groq API | 70B, best quality |

---

## Voice Mode

The voice pipeline runs entirely on the backend — the frontend sends raw audio and receives text.

**Flow:** record audio → VAD trim → Whisper STT → quality gate → LLM → browser TTS

**Quality gate** (5 rules, in order):
1. `EMPTY` — blank transcript
2. `HALLUCINATION` — matches known Whisper artefacts ("thanks for watching", repetitions)
3. `LIKELY_NOISE` — all-silent segments, word rate out of range (< 1 or > 5 wps), all-bad logprobs
4. `LOW_CONFIDENCE` — borderline logprob / elevated no_speech_prob / very short clip; optionally escalated to LLM arbiter
5. `VALID` — sent to the RAG agent

**Barge-in:** clicking the 🎙️ or 🗣️ FAB while TTS is playing cancels browser speech immediately and POSTs `/voice/interrupt` to abort any backend streaming.

**Vocabulary biasing:** at session start, the top-50 frequent domain terms from the active Qdrant context are extracted and passed to Whisper as `initial_prompt`, improving recognition of jargon.

### Running threshold tuning

```bash
cd backend
# Add .wav fixtures to tests/voice/fixtures/ (see README there)
python tests/voice/tune_thresholds.py
```

---

## Deployment variants

### Cloud (Groq + Qdrant Cloud)

```bash
cp .env.cloud.example .env.cloud
# fill in GROQ_API_KEY, QDRANT_HOST, QDRANT_API_KEY, LANGFUSE_* secrets
docker compose -f docker-compose.yml -f docker-compose.cloud.yml --env-file .env.cloud up -d
```

### GPU (vLLM + Qwen2.5-7B)

Requires an NVIDIA GPU with the NVIDIA Container Toolkit installed.

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### Kubernetes

```bash
# Edit k8s/secrets.yaml first
make k8s-apply
make k8s-status
```

### Batch ingestion (PySpark)

```bash
make spark INPUT=data/urls.csv
```

CSV format: one URL per line, or `url,context_id` columns.

---

## Development

```bash
# Dev CLI (replaces manual uvicorn/streamlit commands)
python dev.py start              # start both
python dev.py backend restart    # restart backend only
python dev.py frontend stop      # stop frontend only
python dev.py status             # show running PIDs

# Tests
make test                        # or: cd backend && uv run pytest

# Lint (ruff, auto-fix)
make lint

# Build Docker images
make build
```

Tests live in `backend/tests/`.
 Set `QDRANT_LOCAL_PATH=./qdrant_db` in `backend/.env` for embedded Qdrant without Docker.

---

## Project structure

```
researchmind/
├── dev.py                       # Dev CLI (start/stop/restart/status per service)
├── backend/
│   ├── app/
│   │   ├── agents/              # LangGraph research agent
│   │   ├── enums.py             # SourceType, HistoryAction, DetailLevel
│   │   ├── schemas.py           # Pydantic response models
│   │   ├── routers/             # FastAPI routes
│   │   │   ├── contexts.py      # context CRUD
│   │   │   ├── sources.py       # source CRUD
│   │   │   ├── history.py       # audit history
│   │   │   ├── messages.py      # chat persistence
│   │   │   ├── ingest.py        # 6 ingest endpoints
│   │   │   ├── query.py         # search, ask, transcribe
│   │   │   └── voice.py         # /voice/turn, /voice/interrupt
│   │   ├── services/
│   │   │   ├── ingest/          # IngestionService + pipeline helpers
│   │   │   └── stores/          # context, source, history, chat stores
│   │   ├── voice/               # Voice pipeline
│   │   │   ├── settings.py      # VoiceSettings (VOICE_ prefix)
│   │   │   ├── schemas.py       # GateDecision, VoiceTurn, etc.
│   │   │   ├── capture.py       # decode audio, energy gates, domain prompt
│   │   │   ├── vad.py           # Silero VAD wrapper
│   │   │   ├── transcribe.py    # faster-whisper singleton
│   │   │   ├── hallucinations.py# blocklist + repetition detector
│   │   │   ├── quality_gate.py  # 5-rule gate + LLM arbiter
│   │   │   ├── intents.py       # cancel / ack / repeat (EN + PL)
│   │   │   ├── tts.py           # OpenAI TTS + disk cache
│   │   │   └── state.py         # run_turn() FSM + Langfuse spans
│   │   ├── llm/                 # LiteLLM client wrapper
│   │   └── config.py            # Pydantic settings
│   └── tests/
│       └── voice/               # 61 unit tests + tuning script
├── frontend/
│   ├── app.py                   # Streamlit entry point
│   ├── modules/
│   │   ├── chat/                # _history, _state, __init__ (chat_content)
│   │   ├── ingest/              # _dialogs, _tabs, _accordions, lang_toggle
│   │   ├── i18n/                # _en.py, _pl.py, __init__
│   │   ├── assets/              # styles.css, voice.js
│   │   ├── context_panel.py     # Home screen (context list)
│   │   ├── context_view.py      # Context screen (chat + sources tabs)
│   │   ├── voice_mode.py        # Voice mode UI page
│   │   ├── voice.py             # Mic + voice FAB JS injection
│   │   └── styles.py            # CSS loader (reads assets/styles.css)
│   └── .streamlit/
│       └── config.toml          # Light theme (base = "light")
├── spark/                       # PySpark batch ingestion job
├── k8s/                         # Kubernetes manifests
├── litellm_config.yaml          # LLM routing config
└── docker-compose.yml           # Full local stack
```
