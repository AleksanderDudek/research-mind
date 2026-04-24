from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.services.context_store import (
    list_contexts,
    get_context,
    create_context,
    rename_context,
    delete_context,
)
from app.services.source_store import (
    list_sources,
    get_source,
    delete_source,
    delete_sources_for_context,
)
from app.services.history_store import list_history, delete_history_for_context
from app.services.chat_store import save_message, list_messages, delete_messages_for_context
from app.services.vector_store import VectorStore
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/contexts", tags=["contexts"])

_404 = {404: {"description": "Not found"}}
_400 = {400: {"description": "Bad request"}}


def get_store() -> VectorStore:
    return VectorStore()


def get_ingestion() -> IngestionService:
    return IngestionService()


StoreDep = Annotated[VectorStore, Depends(get_store)]
IngestionDep = Annotated[IngestionService, Depends(get_ingestion)]


class CreateRequest(BaseModel):
    name: str | None = None


class RenameRequest(BaseModel):
    name: str


class EditSourceRequest(BaseModel):
    text: str
    title: str


# ── Context CRUD ────────────────────────────────────────────────────────────────

@router.get("")
def get_all_contexts() -> list:
    return list_contexts()


@router.post("")
def post_context(req: CreateRequest) -> dict:
    return create_context(req.name)


@router.patch("/{context_id}", responses=_404)
def patch_context(context_id: str, req: RenameRequest) -> dict:
    result = rename_context(context_id, req.name)
    if result is None:
        raise HTTPException(status_code=404, detail="Context not found")
    return result


@router.delete("/{context_id}", responses=_404)
def delete_context_endpoint(context_id: str, store: StoreDep) -> dict:
    if not get_context(context_id):
        raise HTTPException(status_code=404, detail="Context not found")
    store.delete_by_context(context_id)
    delete_sources_for_context(context_id)
    delete_history_for_context(context_id)
    delete_messages_for_context(context_id)
    delete_context(context_id)
    logger.info(f"Fully deleted context {context_id!r}")
    return {"deleted": context_id}


# ── Sources ─────────────────────────────────────────────────────────────────────

@router.get("/{context_id}/sources")
def get_sources(context_id: str) -> list:
    sources = list_sources(context_id)
    for s in sources:
        s.pop("image_data", None)  # too large for list view; fetched individually
    return sources


@router.get("/{context_id}/sources/{document_id}/text", responses=_404)
def get_source_text(context_id: str, document_id: str) -> dict:
    source = get_source(context_id, document_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return {
        "raw_text": source.get("raw_text", ""),
        "title": source.get("title", ""),
        "source_type": source.get("source_type", ""),
        "image_data": source.get("image_data"),
        "image_mime_type": source.get("image_mime_type"),
    }


@router.put("/{context_id}/sources/{document_id}", responses={**_404, **_400})
def edit_source(
    context_id: str,
    document_id: str,
    req: EditSourceRequest,
    service: IngestionDep,
) -> dict:
    source = get_source(context_id, document_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    try:
        return service.reingest_text(
            document_id=document_id,
            new_text=req.text,
            title=req.title,
            source_type=source.get("source_type", "text"),
            context_id=context_id,
            url=source.get("url"),
        )
    except Exception as e:
        logger.exception("reingest_text failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{context_id}/sources/{document_id}")
def delete_source_endpoint(context_id: str, document_id: str, store: StoreDep) -> dict:
    store.delete_by_document(document_id, context_id=context_id)
    delete_source(document_id)
    return {"deleted": document_id}


# ── History ─────────────────────────────────────────────────────────────────────

@router.get("/{context_id}/history")
def get_history(context_id: str) -> list:
    return list_history(context_id)


# ── Chat messages ────────────────────────────────────────────────────────────────

class SaveMessageRequest(BaseModel):
    role: str
    content: str
    sources: list | None = None
    action_taken: str | None = None
    iterations: int | None = None
    critique: dict | None = None


@router.get("/{context_id}/messages")
def get_messages(context_id: str) -> list:
    return list_messages(context_id)


@router.post("/{context_id}/messages")
def post_message(context_id: str, req: SaveMessageRequest) -> dict:
    return save_message(
        context_id=context_id,
        role=req.role,
        content=req.content,
        sources=req.sources,
        action_taken=req.action_taken,
        iterations=req.iterations,
        critique=req.critique,
    )
