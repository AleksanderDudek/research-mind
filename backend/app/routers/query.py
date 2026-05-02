"""Query endpoints — search, ask (blocking + streaming), transcribe.

Performance additions:
- Exact-match TTL cache on /ask and /ask/stream (15-min window, 512 entries).
- Critic runs as a BackgroundTask so it never blocks the /ask response.
"""
import hashlib
import json
from typing import Annotated

from cachetools import TTLCache
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from app.agents.research_agent import ResearchAgent
from app.schemas import TranscribeResult
from app.services.embedder import Embedder
from app.services.transcriber import Transcriber
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/query", tags=["query"])

# ── Response cache ─────────────────────────────────────────────────────────────
# Exact-match keyed on sha256(question|context_id). In-process only — not shared
# across Cloud Run instances, but still eliminates 100% of repeated work within
# a single instance's lifetime.
_ask_cache: TTLCache = TTLCache(maxsize=512, ttl=900)  # 15-minute TTL


def _cache_key(question: str, context_id: str | None) -> str:
    return hashlib.sha256(f"{question}|{context_id or ''}".encode()).hexdigest()


# ── Dependencies ───────────────────────────────────────────────────────────────

def get_embedder() -> Embedder:
    return Embedder()


def get_store() -> VectorStore:
    return VectorStore()


def get_agent() -> ResearchAgent:
    return ResearchAgent()


EmbedderDep = Annotated[Embedder,       Depends(get_embedder)]
StoreDep    = Annotated[VectorStore,    Depends(get_store)]
AgentDep    = Annotated[ResearchAgent,  Depends(get_agent)]

_500 = {500: {"description": "Internal server error"}}


class SearchRequest(BaseModel):
    question:   str
    top_k:      int = 5
    source_type: str | None = None
    context_id:  str | None = None


class AskRequest(BaseModel):
    question:   str
    context_id: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/documents", responses=_500)
async def list_documents(store: StoreDep, context_id: str | None = None) -> dict:
    try:
        docs = store.list_documents(context_id=context_id)
        return {"count": len(docs), "documents": docs}
    except Exception as e:
        logger.exception("list_documents failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", responses=_500)
async def semantic_search(req: SearchRequest, embedder: EmbedderDep, store: StoreDep) -> dict:
    try:
        vec = await embedder.embed_one_async(req.question)
        filters: dict[str, str] = {}
        if req.source_type:
            filters["source_type"] = req.source_type
        if req.context_id:
            filters["context_id"] = req.context_id
        hits = await store.search_async(vec, top_k=req.top_k, filters=filters or None)
        return {
            "question": req.question,
            "results": [
                {
                    "score":      h.score,
                    "text":       h.payload.get("text"),
                    "source_type": h.payload.get("source_type"),
                    "metadata":   {k: v for k, v in h.payload.items() if k != "text"},
                }
                for h in hits
            ],
        }
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", responses=_500)
async def ask_agent(req: AskRequest, agent: AgentDep, background: BackgroundTasks) -> dict:
    """Blocking ask — critic runs in the background so it never delays the response."""
    key = _cache_key(req.question, req.context_id)
    if key in _ask_cache:
        logger.info("[cache] hit /ask")
        return _ask_cache[key]

    try:
        result = await agent.run(req.question, context_id=req.context_id, background_tasks=background)
        _ask_cache[key] = result
        return result
    except Exception as e:
        logger.exception("Agent failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/stream")
async def ask_agent_stream(req: AskRequest, agent: AgentDep) -> StreamingResponse:
    """Stream agent answer as Server-Sent Events.

    ``{"type":"chunk","text":"..."}`` — one LLM token
    ``{"type":"done","answer":"...","sources":[...],"action_taken":"..."}``
    """
    key = _cache_key(req.question, req.context_id)

    if key in _ask_cache:
        logger.info("[cache] hit /ask/stream — replaying as instant stream")
        cached = _ask_cache[key]

        async def _replay():
            # Single chunk containing the full cached answer, then done
            yield f'data: {json.dumps({"type": "chunk", "text": cached["answer"]})}\n\n'
            yield f'data: {json.dumps({"type": "done", "answer": cached["answer"], "sources": cached.get("sources", []), "action_taken": cached.get("action_taken", "SEARCH")})}\n\n'

        return StreamingResponse(_replay(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return StreamingResponse(
        agent.stream_run(req.question, req.context_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/transcribe", response_model=TranscribeResult, responses=_500)
async def transcribe_audio(
    file: Annotated[UploadFile, File()],
    language: Annotated[str | None, Form()] = None,
) -> dict:
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
        text = Transcriber().transcribe(audio_bytes, file.filename or "audio.webm", language=language)
        return {"text": text}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=str(e))
