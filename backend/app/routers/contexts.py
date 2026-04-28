from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.services.stores.context_store import (
    list_contexts, get_context, create_context, rename_context, delete_context,
)
from app.services.stores.source_store import delete_sources_for_context
from app.services.stores.history_store import delete_history_for_context
from app.services.stores.chat_store import delete_messages_for_context
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/contexts", tags=["contexts"])

_404 = {404: {"description": "Not found"}}


class ContextCreateRequest(BaseModel):
    name: str | None = None


class ContextRenameRequest(BaseModel):
    name: str


@router.get("")
def list_all_contexts() -> list:
    return list_contexts()


@router.post("")
def create_context_endpoint(req: ContextCreateRequest) -> dict:
    return create_context(req.name)


@router.patch("/{context_id}", responses=_404)
def rename_context_endpoint(context_id: str, req: ContextRenameRequest) -> dict:
    result = rename_context(context_id, req.name)
    if result is None:
        raise HTTPException(status_code=404, detail="Context not found")
    return result


@router.delete("/{context_id}", responses=_404)
def delete_context_endpoint(context_id: str) -> dict:
    if not get_context(context_id):
        raise HTTPException(status_code=404, detail="Context not found")
    store = VectorStore()
    store.delete_by_context(context_id)
    delete_sources_for_context(context_id)
    delete_history_for_context(context_id)
    delete_messages_for_context(context_id)
    delete_context(context_id)
    logger.info(f"Fully deleted context {context_id!r}")
    return {"deleted": context_id}
