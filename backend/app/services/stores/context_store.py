"""Context metadata store (rm_contexts collection)."""
import uuid
from datetime import datetime, timezone

from cachetools import TTLCache
from loguru import logger
from qdrant_client import models
from qdrant_client.models import PointStruct

from app.config import settings
from app.services._qdrant import get_client
from app.services.stores.base import DUMMY_VEC, ensure_collection

_LEGACY_ID   = "00000000-0000-0000-0000-000000000000"
_LEGACY_NAME = "Imported data"

# Context metadata changes infrequently — cache list for 60 s, individual lookups for 120 s.
_list_cache: TTLCache  = TTLCache(maxsize=4,   ttl=60)
_item_cache: TTLCache  = TTLCache(maxsize=512, ttl=120)


def _ensure_collection() -> None:
    created = ensure_collection(
        settings.qdrant_contexts_collection,
        indexes=["context_id"],
    )
    if created:
        logger.info(f"Created collection: {settings.qdrant_contexts_collection}")
        _seed_legacy()


def _seed_legacy() -> None:
    client = get_client()
    now = datetime.now(timezone.utc).isoformat()
    client.upsert(
        collection_name=settings.qdrant_contexts_collection,
        points=[PointStruct(
            id=_LEGACY_ID,
            vector=DUMMY_VEC,
            payload={
                "context_id": _LEGACY_ID,
                "name": _LEGACY_NAME,
                "created_at": now,
                "updated_at": now,
            },
        )],
    )


def list_contexts() -> list[dict]:
    if "all" in _list_cache:
        return _list_cache["all"]
    client = get_client()
    results, _ = client.scroll(
        collection_name=settings.qdrant_contexts_collection,
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    data = [r.payload for r in results]
    _list_cache["all"] = data
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


def create_context(name: str | None = None) -> dict:
    client = get_client()
    context_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "context_id": context_id,
        "name": name or datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M"),
        "created_at": now,
        "updated_at": now,
    }
    client.upsert(
        collection_name=settings.qdrant_contexts_collection,
        points=[PointStruct(id=context_id, vector=DUMMY_VEC, payload=payload)],
    )
    _list_cache.clear()
    logger.info(f"Created context {context_id!r} name={payload['name']!r}")
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
