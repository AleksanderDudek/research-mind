from fastapi import APIRouter

from app.auth.deps import AuthUserDep
from app.services.stores.history_store import list_history

router = APIRouter(prefix="/contexts", tags=["history"])


@router.get("/{context_id}/history")
def get_history(context_id: str, user: AuthUserDep) -> list:
    return list_history(context_id)
