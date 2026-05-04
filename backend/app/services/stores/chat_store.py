"""Chat message persistence (rm_chat collection).

Messages now carry `user_id` (who sent/received) and `org_id` (which org).
`list_messages` accepts an optional `user_id` filter so USERs see only their
own conversations while ADMINs/SUPERADMINs see everyone's.
"""
import uuid
from datetime import datetime, timezone

from loguru import logger
from qdrant_client import models
from qdrant_client.models import PointStruct

from app.config import settings
from app.services._qdrant import get_client
from app.services.stores.base import DUMMY_VEC, ensure_collection


def _ensure_collection() -> None:
    created = ensure_collection(
        settings.qdrant_chat_collection,
        indexes=["context_id", "org_id", "user_id"],
    )
    if created:
        logger.info(f"Created collection: {settings.qdrant_chat_collection}")


def save_message(
    context_id: str,
    role: str,
    content: str,
    user_id: str = "",
    org_id: str = "",
    sources: list | None = None,
    action_taken: str | None = None,
    iterations: int | None = None,
    critique: dict | None = None,
) -> dict:
    payload: dict = {
        "context_id": context_id,
        "role":       role,
        "content":    content,
        "user_id":    user_id,
        "org_id":     org_id,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }
    if sources      is not None: payload["sources"]      = sources
    if action_taken is not None: payload["action_taken"] = action_taken
    if iterations   is not None: payload["iterations"]   = iterations
    if critique     is not None: payload["critique"]     = critique
    get_client().upsert(
        collection_name=settings.qdrant_chat_collection,
        points=[PointStruct(id=str(uuid.uuid4()), vector=DUMMY_VEC, payload=payload)],
    )
    return payload


def list_messages(context_id: str, user_id: str | None = None) -> list[dict]:
    """Return messages for a context.

    If `user_id` is supplied only that user's messages are returned (USER role).
    Passing `user_id=None` returns all messages in the context (ADMIN/SUPERADMIN).
    """
    must = [
        models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id)),
    ]
    if user_id:
        must.append(
            models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
        )
    client = get_client()
    results, _ = client.scroll(
        collection_name=settings.qdrant_chat_collection,
        scroll_filter=models.Filter(must=must),
        limit=2000,
        with_payload=True,
        with_vectors=False,
    )
    return sorted([r.payload for r in results], key=lambda m: m.get("timestamp", ""))


def delete_messages_for_context(context_id: str) -> None:
    get_client().delete(
        collection_name=settings.qdrant_chat_collection,
        points_selector=models.FilterSelector(filter=models.Filter(must=[
            models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id)),
        ])),
    )
    logger.info(f"Deleted chat messages for context {context_id!r}")
