"""Sentence-Transformer embedding singleton with LRU cache and async support."""
import asyncio
from concurrent.futures import ThreadPoolExecutor

from cachetools import LRUCache
from loguru import logger
from sentence_transformers import SentenceTransformer

from app.config import settings

# LRU cache: avoids re-embedding the same query text on repeated calls.
_embed_cache: LRUCache = LRUCache(maxsize=2048)

# Thread-pool for CPU-bound encode() — prevents blocking the async event loop.
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embedder")


class Embedder:
    _instance: "Embedder | None" = None

    def __new__(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            cls._instance.model = SentenceTransformer(settings.embedding_model)
        return cls._instance

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Batch-encode texts. SentenceTransformer encodes all texts in one pass."""
        vectors = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return vectors.tolist()

    def embed_one(self, text: str) -> list[float]:
        """Encode a single text, with LRU caching for repeated inputs."""
        if text in _embed_cache:
            return _embed_cache[text]
        vec = self.embed([text])[0]
        _embed_cache[text] = vec
        return vec

    async def embed_one_async(self, text: str) -> list[float]:
        """Non-blocking embed: runs in a thread pool so the event loop stays free."""
        if text in _embed_cache:
            return _embed_cache[text]
        loop = asyncio.get_event_loop()
        vec = await loop.run_in_executor(_executor, self.embed_one, text)
        return vec
