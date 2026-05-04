"""Audit log for context changes (rm_history collection)."""
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
        settings.qdrant_history_collection,
        indexes=["context_id", "org_id"],
    )
    if created:
        logger.info(f"Created collection: {settings.qdrant_history_collection}")


def append(context_id: str, action: str, detail: str, org_id: str = "") -> dict:
    payload = {
        "context_id": context_id,
        "org_id":     org_id,
        "action":     action,
        "detail":     detail,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }
    get_client().upsert(
        collection_name=settings.qdrant_history_collection,
        points=[PointStruct(id=str(uuid.uuid4()), vector=DUMMY_VEC, payload=payload)],
    )
    return payload


def list_history(context_id: str) -> list[dict]:
    client = get_client()
    results, _ = client.scroll(
        collection_name=settings.qdrant_history_collection,
        scroll_filter=models.Filter(must=[
            models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id)),
        ]),
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    return sorted([r.payload for r in results], key=lambda e: e.get("timestamp", ""), reverse=True)


def delete_history_for_context(context_id: str) -> None:
    get_client().delete(
        collection_name=settings.qdrant_history_collection,
        points_selector=models.FilterSelector(filter=models.Filter(must=[
            models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id)),
        ])),
    )
