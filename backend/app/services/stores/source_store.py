"""Source document metadata store (rm_sources collection)."""
import uuid
from datetime import datetime, timezone

from threading import RLock

from cachetools import TTLCache
from loguru import logger
from qdrant_client import models
from qdrant_client.models import PointStruct

from app.config import settings
from app.services._qdrant import get_client
from app.services.stores.base import DUMMY_VEC, ensure_collection

# TTLCache is not thread-safe; protect with a lock.
_list_cache: TTLCache = TTLCache(maxsize=256, ttl=60)
_cache_lock = RLock()


def _ensure_collection() -> None:
    created = ensure_collection(
        settings.qdrant_sources_collection,
        indexes=["context_id", "document_id", "source_type", "org_id"],
    )
    if created:
        logger.info(f"Created collection: {settings.qdrant_sources_collection}")


def save_source(
    context_id: str,
    document_id: str,
    title: str,
    source_type: str,
    raw_text: str,
    url: str | None,
    chunk_count: int,
    org_id: str = "",
    image_data: str | None = None,
    image_mime_type: str | None = None,
) -> dict:
    record_id = str(uuid.uuid5(uuid.NAMESPACE_OID, document_id))
    payload: dict = {
        "context_id":  context_id,
        "document_id": document_id,
        "title":       title,
        "source_type": source_type,
        "raw_text":    raw_text,
        "url":         url,
        "chunk_count": chunk_count,
        "org_id":      org_id,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    if image_data:
        payload["image_data"] = image_data
    if image_mime_type:
        payload["image_mime_type"] = image_mime_type
    get_client().upsert(
        collection_name=settings.qdrant_sources_collection,
        points=[PointStruct(id=record_id, vector=DUMMY_VEC, payload=payload)],
    )
    with _cache_lock:
        _list_cache.pop(context_id, None)
    return payload


def list_sources(context_id: str) -> list[dict]:
    with _cache_lock:
        if context_id in _list_cache:
            return _list_cache[context_id]
    client = get_client()
    results, _ = client.scroll(
        collection_name=settings.qdrant_sources_collection,
        scroll_filter=models.Filter(must=[
            models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id)),
        ]),
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    data = [r.payload for r in results]
    with _cache_lock:
        _list_cache[context_id] = data
    return data


def get_source(context_id: str, document_id: str) -> dict | None:
    client = get_client()
    results, _ = client.scroll(
        collection_name=settings.qdrant_sources_collection,
        scroll_filter=models.Filter(must=[
            models.FieldCondition(key="context_id",  match=models.MatchValue(value=context_id)),
            models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
        ]),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    return results[0].payload if results else None


def delete_source(document_id: str, context_id: str | None = None) -> bool:
    record_id = str(uuid.uuid5(uuid.NAMESPACE_OID, document_id))
    get_client().delete(
        collection_name=settings.qdrant_sources_collection,
        points_selector=models.PointIdsList(points=[record_id]),
    )
    with _cache_lock:
        if context_id:
            _list_cache.pop(context_id, None)
        else:
            _list_cache.clear()
    return True


def delete_sources_for_context(context_id: str) -> None:
    get_client().delete(
        collection_name=settings.qdrant_sources_collection,
        points_selector=models.FilterSelector(filter=models.Filter(must=[
            models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id)),
        ])),
    )
    with _cache_lock:
        _list_cache.pop(context_id, None)
