"""Qdrant client singletons — sync for startup/schema ops, async for hot paths."""
from qdrant_client import AsyncQdrantClient, QdrantClient

from app.config import settings

_sync: QdrantClient | None = None
_async: AsyncQdrantClient | None = None


def get_client() -> QdrantClient:
    global _sync
    if _sync is None:
        if settings.qdrant_local_path:
            _sync = QdrantClient(path=settings.qdrant_local_path)
        elif settings.qdrant_api_key:
            _sync = QdrantClient(url=f"https://{settings.qdrant_host}", api_key=settings.qdrant_api_key)
        else:
            _sync = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _sync


def get_async_client() -> AsyncQdrantClient:
    """Async Qdrant client for non-blocking search/upsert on the hot path."""
    global _async
    if _async is None:
        if settings.qdrant_local_path:
            _async = AsyncQdrantClient(path=settings.qdrant_local_path)
        elif settings.qdrant_api_key:
            _async = AsyncQdrantClient(
                url=f"https://{settings.qdrant_host}",
                api_key=settings.qdrant_api_key,
            )
        else:
            _async = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _async
