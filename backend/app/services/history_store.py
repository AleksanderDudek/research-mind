"""
Audit log for context changes, stored in rm_history.
"""

import uuid
from datetime import datetime, timezone

from loguru import logger
from qdrant_client import models
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings
from app.services._qdrant import get_client

_DUMMY_VEC = [0.0]


def _ensure_collection() -> None:
    client = get_client()
    names = [c.name for c in client.get_collections().collections]
    if settings.qdrant_history_collection not in names:
        logger.info(f"Creating collection: {settings.qdrant_history_collection}")
        client.create_collection(
            collection_name=settings.qdrant_history_collection,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=settings.qdrant_history_collection,
            field_name="context_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


# ── Public API ─────────────────────────────────────────────────────────────────

def append(context_id: str, action: str, detail: str) -> dict:
    client = get_client()
    _ensure_collection()
    entry_id = str(uuid.uuid4())
    payload = {
        "context_id": context_id,
        "action": action,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    client.upsert(
        collection_name=settings.qdrant_history_collection,
        points=[PointStruct(id=entry_id, vector=_DUMMY_VEC, payload=payload)],
    )
    return payload


def list_history(context_id: str) -> list[dict]:
    client = get_client()
    _ensure_collection()
    results, _ = client.scroll(
        collection_name=settings.qdrant_history_collection,
        scroll_filter=models.Filter(must=[
            models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id))
        ]),
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    entries = [r.payload for r in results]
    return sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)


def delete_history_for_context(context_id: str) -> None:
    client = get_client()
    _ensure_collection()
    client.delete(
        collection_name=settings.qdrant_history_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(must=[
                models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id))
            ])
        ),
    )
