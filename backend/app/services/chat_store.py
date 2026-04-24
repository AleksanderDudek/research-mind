"""
Persists chat messages (user + assistant) per context in rm_chat collection.
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
    if settings.qdrant_chat_collection not in names:
        logger.info(f"Creating collection: {settings.qdrant_chat_collection}")
        client.create_collection(
            collection_name=settings.qdrant_chat_collection,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=settings.qdrant_chat_collection,
            field_name="context_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def save_message(
    context_id: str,
    role: str,
    content: str,
    sources: list | None = None,
    action_taken: str | None = None,
    iterations: int | None = None,
    critique: dict | None = None,
) -> dict:
    client = get_client()
    payload: dict = {
        "context_id": context_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if sources is not None:
        payload["sources"] = sources
    if action_taken is not None:
        payload["action_taken"] = action_taken
    if iterations is not None:
        payload["iterations"] = iterations
    if critique is not None:
        payload["critique"] = critique
    client.upsert(
        collection_name=settings.qdrant_chat_collection,
        points=[PointStruct(id=str(uuid.uuid4()), vector=_DUMMY_VEC, payload=payload)],
    )
    return payload


def list_messages(context_id: str) -> list[dict]:
    client = get_client()
    results, _ = client.scroll(
        collection_name=settings.qdrant_chat_collection,
        scroll_filter=models.Filter(must=[
            models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id))
        ]),
        limit=2000,
        with_payload=True,
        with_vectors=False,
    )
    messages = [r.payload for r in results]
    return sorted(messages, key=lambda m: m.get("timestamp", ""))


def delete_messages_for_context(context_id: str) -> None:
    client = get_client()
    client.delete(
        collection_name=settings.qdrant_chat_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(must=[
                models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id))
            ])
        ),
    )
    logger.info(f"Deleted chat messages for context {context_id!r}")
