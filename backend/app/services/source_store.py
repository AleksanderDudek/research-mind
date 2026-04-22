"""
Stores one record per ingested document in rm_sources.
Holds the raw text so users can edit it later.
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
    if settings.qdrant_sources_collection not in names:
        logger.info(f"Creating collection: {settings.qdrant_sources_collection}")
        client.create_collection(
            collection_name=settings.qdrant_sources_collection,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )
        for field in ("context_id", "document_id", "source_type"):
            client.create_payload_index(
                collection_name=settings.qdrant_sources_collection,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )


# ── Public API ─────────────────────────────────────────────────────────────────

def save_source(
    context_id: str,
    document_id: str,
    title: str,
    source_type: str,
    raw_text: str,
    url: str | None,
    chunk_count: int,
) -> dict:
    client = get_client()
    _ensure_collection()
    record_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, document_id))
    payload = {
        "context_id": context_id,
        "document_id": document_id,
        "title": title,
        "source_type": source_type,
        "raw_text": raw_text,
        "url": url,
        "chunk_count": chunk_count,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    client.upsert(
        collection_name=settings.qdrant_sources_collection,
        points=[PointStruct(id=record_id, vector=_DUMMY_VEC, payload=payload)],
    )
    return payload


def list_sources(context_id: str) -> list[dict]:
    client = get_client()
    _ensure_collection()
    results, _ = client.scroll(
        collection_name=settings.qdrant_sources_collection,
        scroll_filter=models.Filter(
            must=[models.FieldCondition(
                key="context_id", match=models.MatchValue(value=context_id)
            )]
        ),
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    return [r.payload for r in results]


def get_source(context_id: str, document_id: str) -> dict | None:
    client = get_client()
    _ensure_collection()
    results, _ = client.scroll(
        collection_name=settings.qdrant_sources_collection,
        scroll_filter=models.Filter(must=[
            models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id)),
            models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
        ]),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    return results[0].payload if results else None


def delete_source(document_id: str) -> bool:
    client = get_client()
    _ensure_collection()
    record_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, document_id))
    client.delete(
        collection_name=settings.qdrant_sources_collection,
        points_selector=models.PointIdsList(points=[record_id]),
    )
    return True


def delete_sources_for_context(context_id: str) -> None:
    client = get_client()
    _ensure_collection()
    client.delete(
        collection_name=settings.qdrant_sources_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(must=[
                models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id))
            ])
        ),
    )
