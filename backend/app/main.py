from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.routers import ingest, query, contexts
from app.services.context_store import _ensure_collection as _ensure_contexts
from app.services.source_store import _ensure_collection as _ensure_sources
from app.services.history_store import _ensure_collection as _ensure_history
from app.services.chat_store import _ensure_collection as _ensure_chat


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    _ensure_contexts()
    _ensure_sources()
    _ensure_history()
    _ensure_chat()
    logger.info("ResearchMind API starting up...")
    yield
    logger.info("ResearchMind API shutting down.")


app = FastAPI(
    title="ResearchMind API",
    version="0.1.0",
    description="Platforma RAG do analizy badań naukowych",
    lifespan=lifespan,
)

_origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(contexts.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
