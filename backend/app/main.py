from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.routers import contexts, history, ingest, messages, query, sources, voice
from app.services.stores.chat_store import _ensure_collection as _ensure_chat
from app.services.stores.context_store import _ensure_collection as _ensure_contexts
from app.services.stores.history_store import _ensure_collection as _ensure_history
from app.services.stores.source_store import _ensure_collection as _ensure_sources


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("ResearchMind API starting up — initialising collections…")
    _ensure_contexts()
    _ensure_sources()
    _ensure_history()
    _ensure_chat()
    logger.info("All collections ready.")
    yield
    logger.info("ResearchMind API shutting down.")


app = FastAPI(
    title="ResearchMind API",
    version="0.1.0",
    lifespan=lifespan,
)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for _router in (ingest.router, query.router, contexts.router,
                sources.router, history.router, messages.router, voice.router):
    app.include_router(_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
