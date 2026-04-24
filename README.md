# ResearchMind

AI-powered research assistant that lets you build isolated knowledge contexts from PDFs, web pages, images, audio recordings, and raw text — then chat with an agentic RAG pipeline over them.

---

## Features

- **Multiple source types** — PDF (URL or upload), web page scraping, image description (vision LLM), audio transcription (Whisper), raw text paste
- **Context isolation** — each project/topic lives in its own named context; queries never cross contexts
- **Agentic RAG pipeline** — LangGraph agent with router → retrieve → generate → critic loop; iterates until quality threshold is met
- **LiteLLM proxy** — swap between Ollama (local), Groq (free cloud), vLLM (GPU), or OpenAI without changing application code
- **Qdrant** — vector store for chunks + metadata collections for contexts, sources, history, and chat
- **Multilingual UI** — English / Polish, toggle via URL param `?lang=pl`
- **Mobile-first frontend** — Streamlit, no sidebar, centered layout, pill-based source selector

---

## Architecture

```
Browser (Streamlit :8501)
    │
    ▼
FastAPI backend (:8001 / :8000 in Docker)
    ├── /contexts    — CRUD for research contexts
    ├── /ingest/*    — PDF URL, web, upload, raw text, image, audio
    └── /query/ask   — LangGraph agentic RAG
          │
          ├── Qdrant          — vector + metadata store
          ├── LiteLLM proxy   — unified LLM API (:4000)
          │     ├── Ollama (local)   llama3.1:8b / qwen2.5:3b
          │     ├── Groq (cloud)     llama-3.1-8b-instant
          │     └── vLLM (GPU)       Qwen2.5-7B
          └── faster-whisper  — audio transcription (local)
```

---

## Quick Start (local, no GPU)

**Prerequisites:** Docker + Docker Compose, or Python 3.11+ with `uv`.

### Docker Compose (recommended)

```bash
docker compose up -d
```

Pull the default model once Ollama is running:

```bash
docker exec researchmind-ollama ollama pull qwen2.5:3b
```

Open `http://localhost:8501`.

### Manual (development)

```bash
# 1. Start Qdrant
docker compose up qdrant -d

# 2. Backend
cd backend
uv venv && uv pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# 3. Frontend (new terminal)
cd frontend
uv venv && uv pip install -r requirements.txt
.venv/bin/streamlit run app.py --server.port 8501
```

---

## Configuration

The backend reads configuration from environment variables (or a `.env` file in `backend/`).

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

Ingest a CSV of URLs in parallel:

```bash
make spark INPUT=data/urls.csv
```

CSV format: one URL per line, or `url,context_id` columns.

---

## Development

```bash
# Run tests
make test

# Lint (ruff, auto-fix)
make lint

# Build Docker images
make build

# All make targets
make help
```

Tests live in `backend/tests/`. The backend requires a running Qdrant instance — set `QDRANT_LOCAL_PATH=./qdrant_db` in `backend/.env` to use an embedded instance without Docker.

---

## Project structure

```
researchmind/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph research agent
│   │   ├── routers/         # FastAPI routes (contexts, ingest, query)
│   │   ├── services/        # Qdrant stores, ingestion pipeline, Whisper
│   │   ├── llm/             # LiteLLM client wrapper
│   │   └── config.py        # Pydantic settings
│   └── tests/
├── frontend/
│   ├── app.py               # Streamlit entry point
│   ├── modules/
│   │   ├── chat.py          # Chat view + pending question recovery
│   │   ├── context_panel.py # Home screen (context list)
│   │   ├── context_view.py  # Context screen (chat + sources tabs)
│   │   ├── sidebar.py       # Ingest helpers + dialogs
│   │   ├── styles.py        # CSS injection
│   │   └── i18n.py          # EN/PL translations
│   └── .streamlit/
│       └── config.toml      # Light theme
├── spark/                   # PySpark batch ingestion job
├── k8s/                     # Kubernetes manifests
├── litellm_config.yaml      # LLM routing config
└── docker-compose.yml       # Full local stack
```
