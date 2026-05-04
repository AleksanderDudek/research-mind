from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.auth.deps import AuthUserDep
from app.auth.access import require_admin, assert_same_org
from app.services.stores.context_store import get_context
from app.services.stores.source_store import list_sources, get_source, delete_source
from app.services.vector_store import VectorStore
from app.services.ingest import IngestionService

router = APIRouter(prefix="/contexts", tags=["sources"])

_404 = {404: {"description": "Not found"}}
_400 = {400: {"description": "Bad request"}}
_SRC_NOT_FOUND = "Source not found"


def _store() -> VectorStore:
    return VectorStore()


def _ingestion() -> IngestionService:
    return IngestionService()


class EditSourceRequest(BaseModel):
    text: str
    title: str


def _check_context_org(context_id: str, user: AuthUserDep) -> dict:
    """Verify context exists and caller belongs to the same org (unless superadmin)."""
    ctx = get_context(context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    assert_same_org(user, ctx.get("org_id", ""))
    return ctx


@router.get("/{context_id}/sources", responses=_404)
def get_sources(context_id: str, user: AuthUserDep) -> list:
    _check_context_org(context_id, user)
    sources = list_sources(context_id)
    for s in sources:
        s.pop("image_data", None)  # too large for list view
    return sources


@router.get("/{context_id}/sources/{document_id}/text", responses=_404)
def get_source_text(context_id: str, document_id: str, user: AuthUserDep) -> dict:
    _check_context_org(context_id, user)
    source = get_source(context_id, document_id)
    if source is None:
        raise HTTPException(status_code=404, detail=_SRC_NOT_FOUND)
    return {
        "raw_text":        source.get("raw_text", ""),
        "title":           source.get("title", ""),
        "source_type":     source.get("source_type", ""),
        "image_data":      source.get("image_data"),
        "image_mime_type": source.get("image_mime_type"),
    }


@router.put("/{context_id}/sources/{document_id}", responses={**_404, **_400})
def edit_source(
    context_id: str,
    document_id: str,
    req: EditSourceRequest,
    user: AuthUserDep,
    service: Annotated[IngestionService, Depends(_ingestion)],
) -> dict:
    require_admin(user)
    _check_context_org(context_id, user)
    source = get_source(context_id, document_id)
    if source is None:
        raise HTTPException(status_code=404, detail=_SRC_NOT_FOUND)
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
def delete_source_endpoint(
    context_id: str,
    document_id: str,
    user: AuthUserDep,
    store: Annotated[VectorStore, Depends(_store)],
) -> dict:
    require_admin(user)
    _check_context_org(context_id, user)
    store.delete_by_document(document_id, context_id=context_id)
    delete_source(document_id)
    return {"deleted": document_id}
