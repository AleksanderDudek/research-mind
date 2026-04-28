from fastapi import APIRouter

from app.services.stores.history_store import list_history

router = APIRouter(prefix="/contexts", tags=["history"])


@router.get("/{context_id}/history")
def get_history(context_id: str) -> list:
    return list_history(context_id)
