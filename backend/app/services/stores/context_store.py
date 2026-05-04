"""Context metadata store (rm_contexts collection).

Each context now carries an `org_id` field so rows can be filtered by org.
`created_by` captures the user_id of the ADMIN who created the context.
"""
import uuid
from datetime import datetime, timezone

from cachetools import TTLCache
from loguru import logger
from qdrant_client import models
from qdrant_client.models import PointStruct

from app.config import settings
from app.services._qdrant import get_client
from app.services.stores.base import DUMMY_VEC, ensure_collection

# Context metadata changes infrequently — cache list for 60 s, individual lookups for 120 s.
_list_cache: TTLCache  = TTLCache(maxsize=256, ttl=60)
_item_cache: TTLCache  = TTLCache(maxsize=512, ttl=120)


def _ensure_collection() -> None:
    created = ensure_collection(
        settings.qdrant_contexts_collection,
        indexes=["context_id", "org_id"],
    )
    if created:
        logger.info(f"Created collection: {settings.qdrant_contexts_collection}")


def list_contexts(org_id: str | None = None) -> list[dict]:
    """Return all contexts, optionally filtered to a single organisation."""
    cache_key = org_id or "all"
    if cache_key in _list_cache:
        return _list_cache[cache_key]

    client = get_client()
    scroll_filter = None
    if org_id:
        scroll_filter = models.Filter(must=[
            models.FieldCondition(key="org_id", match=models.MatchValue(value=org_id)),
        ])
    results, _ = client.scroll(
        collection_name=settings.qdrant_contexts_collection,
        scroll_filter=scroll_filter,
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    data = [r.payload for r in results]
    _list_cache[cache_key] = data
    return data


def get_context(context_id: str) -> dict | None:
    if context_id in _item_cache:
        return _item_cache[context_id]
    results = get_client().retrieve(
        collection_name=settings.qdrant_contexts_collection,
        ids=[context_id],
        with_payload=True,
    )
    payload = results[0].payload if results else None
    if payload:
        _item_cache[context_id] = payload
    return payload


def create_context(
    name: str | None = None,
    org_id: str = "",
    created_by: str = "",
) -> dict:
    client = get_client()
    context_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "context_id": context_id,
        "name":       name or datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M"),
        "org_id":     org_id,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    client.upsert(
        collection_name=settings.qdrant_contexts_collection,
        points=[PointStruct(id=context_id, vector=DUMMY_VEC, payload=payload)],
    )
    _list_cache.clear()
    logger.info(f"Created context {context_id!r} org={org_id!r} name={payload['name']!r}")
    return payload


def rename_context(context_id: str, name: str) -> dict | None:
    existing = get_context(context_id)
    if not existing:
        return None
    existing["name"] = name
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    get_client().upsert(
        collection_name=settings.qdrant_contexts_collection,
        points=[PointStruct(id=context_id, vector=DUMMY_VEC, payload=existing)],
    )
    _item_cache[context_id] = existing
    _list_cache.clear()
    return existing


def delete_context(context_id: str) -> bool:
    if not get_context(context_id):
        return False
    get_client().delete(
        collection_name=settings.qdrant_contexts_collection,
        points_selector=models.PointIdsList(points=[context_id]),
    )
    _item_cache.pop(context_id, None)
    _list_cache.clear()
    logger.info(f"Deleted context {context_id!r}")
    return True
