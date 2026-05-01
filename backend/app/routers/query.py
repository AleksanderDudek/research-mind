from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

from app.schemas import TranscribeResult
from app.services.embedder import Embedder
from app.services.transcriber import Transcriber
from app.services.vector_store import VectorStore
from app.agents.research_agent import ResearchAgent

router = APIRouter(prefix="/query", tags=["query"])


def get_embedder() -> Embedder:
    return Embedder()


def get_store() -> VectorStore:
    return VectorStore()


def get_agent() -> ResearchAgent:
    return ResearchAgent()


EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
StoreDep = Annotated[VectorStore, Depends(get_store)]
AgentDep = Annotated[ResearchAgent, Depends(get_agent)]

_500 = {500: {"description": "Internal server error"}}


class SearchRequest(BaseModel):
    question: str
    top_k: int = 5
    source_type: str | None = None
    context_id: str | None = None


class AskRequest(BaseModel):
    question: str
    context_id: str | None = None


@router.get("/documents", responses=_500)
async def list_documents(store: StoreDep, context_id: str | None = None) -> dict:
    """Lista wszystkich zaindeksowanych dokumentów."""
    try:
        docs = store.list_documents(context_id=context_id)
        return {"count": len(docs), "documents": docs}
    except Exception as e:
        logger.exception("list_documents failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", responses=_500)
async def semantic_search(req: SearchRequest, embedder: EmbedderDep, store: StoreDep) -> dict:
    """Wyszukiwanie semantyczne bez LLM (tylko retrieval)."""
    try:
        vec = embedder.embed_one(req.question)
        filters: dict[str, str] = {}
        if req.source_type:
            filters["source_type"] = req.source_type
        if req.context_id:
            filters["context_id"] = req.context_id
        hits = store.search(vec, top_k=req.top_k, filters=filters or None)
        return {
            "question": req.question,
            "results": [
                {
                    "score": h.score,
                    "text": h.payload.get("text"),
                    "source_type": h.payload.get("source_type"),
                    "metadata": {k: v for k, v in h.payload.items() if k != "text"},
                }
                for h in hits
            ],
        }
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask", responses=_500)
async def ask_agent(req: AskRequest, agent: AgentDep) -> dict:
    """Zapytanie do agenta LangGraph z pełnym workflow."""
    try:
        result = await agent.run(req.question, context_id=req.context_id)
        return result
    except Exception as e:
        logger.exception("Agent failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/stream")
async def ask_agent_stream(req: AskRequest, agent: AgentDep) -> StreamingResponse:
    """Stream the agent answer as Server-Sent Events.

    Each event is a JSON line: ``data: {...}\\n\\n``
    - ``{"type":"chunk","text":"..."}`` — one LLM token
    - ``{"type":"done","answer":"...","sources":[...],"action_taken":"..."}``
    """
    return StreamingResponse(
        agent.stream_run(req.question, req.context_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/transcribe", response_model=TranscribeResult, responses=_500)
async def transcribe_audio(
    file: Annotated[UploadFile, File()],
    language: Annotated[str | None, Form()] = None,
) -> dict:
    """Transcribes uploaded audio to text using Whisper."""
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
