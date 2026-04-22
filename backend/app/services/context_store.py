"""
Stores context metadata in Qdrant (rm_contexts collection).
Each context is one Qdrant point with a dummy vector.
"""

import uuid
from datetime import datetime, timezone

from loguru import logger
from qdrant_client import models
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings
from app.services._qdrant import get_client

_DUMMY_VEC = [0.0]
_LEGACY_ID = "00000000-0000-0000-0000-000000000000"
_LEGACY_NAME = "Imported data"


def _ensure_collection() -> None:
    client = get_client()
    names = [c.name for c in client.get_collections().collections]
    if settings.qdrant_contexts_collection not in names:
        logger.info(f"Creating collection: {settings.qdrant_contexts_collection}")
        client.create_collection(
            collection_name=settings.qdrant_contexts_collection,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=settings.qdrant_contexts_collection,
            field_name="context_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        _seed_legacy()


def _seed_legacy() -> None:
    client = get_client()
    client.upsert(
        collection_name=settings.qdrant_contexts_collection,
        points=[
            PointStruct(
                id=_LEGACY_ID,
                vector=_DUMMY_VEC,
                payload={
                    "context_id": _LEGACY_ID,
                    "name": _LEGACY_NAME,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        ],
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def list_contexts() -> list[dict]:
    client = get_client()
    _ensure_collection()
    results, _ = client.scroll(
        collection_name=settings.qdrant_contexts_collection,
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    return [r.payload for r in results]


def get_context(context_id: str) -> dict | None:
    client = get_client()
    _ensure_collection()
    results = client.retrieve(
        collection_name=settings.qdrant_contexts_collection,
        ids=[context_id],
        with_payload=True,
    )
    return results[0].payload if results else None


def create_context(name: str | None = None) -> dict:
    client = get_client()
    _ensure_collection()
    context_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    if not name:
        name = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M")
    payload = {
        "context_id": context_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
    }
    client.upsert(
        collection_name=settings.qdrant_contexts_collection,
        points=[PointStruct(id=context_id, vector=_DUMMY_VEC, payload=payload)],
    )
    logger.info(f"Created context {context_id!r} name={name!r}")
    return payload


def rename_context(context_id: str, name: str) -> dict | None:
    client = get_client()
    _ensure_collection()
    existing = get_context(context_id)
    if not existing:
        return None
    existing["name"] = name
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    client.upsert(
        collection_name=settings.qdrant_contexts_collection,
        points=[PointStruct(id=context_id, vector=_DUMMY_VEC, payload=existing)],
    )
    return existing


def delete_context(context_id: str) -> bool:
    client = get_client()
    _ensure_collection()
    existing = get_context(context_id)
    if not existing:
        return False
    client.delete(
        collection_name=settings.qdrant_contexts_collection,
        points_selector=models.PointIdsList(points=[context_id]),
    )
    logger.info(f"Deleted context {context_id!r}")
    return True
