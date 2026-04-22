"""Shared Qdrant client singleton — prevents multiple local file locks."""
from qdrant_client import QdrantClient

from app.config import settings

_instance: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _instance
    if _instance is None:
        if settings.qdrant_local_path:
            _instance = QdrantClient(path=settings.qdrant_local_path)
        elif settings.qdrant_api_key:
            _instance = QdrantClient(
                url=f"https://{settings.qdrant_host}",
                api_key=settings.qdrant_api_key,
            )
        else:
            _instance = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _instance
