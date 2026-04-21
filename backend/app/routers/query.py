from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.services.embedder import Embedder
from app.services.vector_store import VectorStore
from app.agents.research_agent import ResearchAgent

router = APIRouter(prefix="/query", tags=["query"])
embedder = Embedder()
store = VectorStore()
agent = ResearchAgent()


_500 = {500: {"description": "Internal server error"}}


class SearchRequest(BaseModel):
    question: str
    top_k: int = 5
    source_type: str | None = None


class AskRequest(BaseModel):
    question: str


@router.get("/documents", responses=_500)
async def list_documents() -> dict:
    """Lista wszystkich zaindeksowanych dokumentów."""
    try:
        docs = store.list_documents()
        return {"count": len(docs), "documents": docs}
    except Exception as e:
        logger.exception("list_documents failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", responses=_500)
async def semantic_search(req: SearchRequest) -> dict:
    """Wyszukiwanie semantyczne bez LLM (tylko retrieval)."""
    try:
        vec = embedder.embed_one(req.question)
        filters = {"source_type": req.source_type} if req.source_type else None
        hits = store.search(vec, top_k=req.top_k, filters=filters)
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
async def ask_agent(req: AskRequest) -> dict:
    """Zapytanie do agenta LangGraph z pełnym workflow."""
    try:
        result = await agent.run(req.question)
        return result
    except Exception as e:
        logger.exception("Agent failed")
        raise HTTPException(status_code=500, detail=str(e))
