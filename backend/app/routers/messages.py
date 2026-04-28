from fastapi import APIRouter
from pydantic import BaseModel

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
