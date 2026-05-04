from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.deps import AuthUserDep
from app.services.stores.chat_store import save_message, list_messages

router = APIRouter(prefix="/contexts", tags=["messages"])


class SaveMessageRequest(BaseModel):
    role: str
    content: str
    sources: list | None = None
    action_taken: str | None = None
    iterations: int | None = None
    critique: dict | None = None


@router.get("/{context_id}/messages")
def get_messages(context_id: str, user: AuthUserDep) -> list:
    # USERs see only their own messages; ADMINs and SUPERADMINs see all.
    scoped_user_id = user.user_id if user.role == "user" else None
    return list_messages(context_id, user_id=scoped_user_id)


@router.post("/{context_id}/messages")
def post_message(context_id: str, req: SaveMessageRequest, user: AuthUserDep) -> dict:
    return save_message(
        context_id=context_id,
        role=req.role,
        content=req.content,
        user_id=user.user_id,
        org_id=user.org_id,
        sources=req.sources,
        action_taken=req.action_taken,
        iterations=req.iterations,
        critique=req.critique,
    )
