"""Shared helpers for metadata-only Qdrant collections."""
from qdrant_client import models
from qdrant_client.models import Distance, VectorParams

from app.services._qdrant import get_client

DUMMY_VEC: list[float] = [0.0]


def ensure_collection(name: str, indexes: list[str]) -> bool:
    """Create *name* collection if absent; add keyword indexes. Returns True if created."""
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return False
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=1, distance=Distance.COSINE),
    )
    for field in indexes:
        client.create_payload_index(
            collection_name=name,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    return True
