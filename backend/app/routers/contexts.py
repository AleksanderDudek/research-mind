from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.auth.deps import AuthUserDep
from app.auth.access import require_admin, assert_same_org
from app.services.stores.context_store import (
    list_contexts, get_context, create_context, rename_context, delete_context,
)
from app.services.stores.source_store import delete_sources_for_context
from app.services.stores.history_store import delete_history_for_context
from app.services.stores.chat_store import delete_messages_for_context
from app.services.vector_store import VectorStore

router = APIRouter(prefix="/contexts", tags=["contexts"])

_404 = {404: {"description": "Not found"}}
_CTX_NOT_FOUND = "Context not found"


class ContextCreateRequest(BaseModel):
    name: str | None = None


class ContextRenameRequest(BaseModel):
    name: str


@router.get("")
def list_all_contexts(user: AuthUserDep) -> list:
    if user.role == "superadmin":
        return list_contexts()          # all orgs
    return list_contexts(org_id=user.org_id)


@router.post("")
def create_context_endpoint(req: ContextCreateRequest, user: AuthUserDep) -> dict:
    require_admin(user)
    return create_context(
        name=req.name,
        org_id=user.org_id,
        created_by=user.user_id,
    )


@router.patch("/{context_id}", responses=_404)
def rename_context_endpoint(
    context_id: str, req: ContextRenameRequest, user: AuthUserDep,
) -> dict:
    require_admin(user)
    ctx = get_context(context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=_CTX_NOT_FOUND)
    assert_same_org(user, ctx.get("org_id", ""))
    result = rename_context(context_id, req.name)
    if result is None:
        raise HTTPException(status_code=404, detail=_CTX_NOT_FOUND)
    return result


@router.delete("/{context_id}", responses=_404)
def delete_context_endpoint(context_id: str, user: AuthUserDep) -> dict:
    require_admin(user)
    ctx = get_context(context_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=_CTX_NOT_FOUND)
    assert_same_org(user, ctx.get("org_id", ""))
    store = VectorStore()
    store.delete_by_context(context_id)
    delete_sources_for_context(context_id)
    delete_history_for_context(context_id)
    delete_messages_for_context(context_id)
    delete_context(context_id)
    logger.info(f"Fully deleted context {context_id!r}")
    return {"deleted": context_id}
