"""Unit tests for the Embedder singleton, LRU cache, and async wrapper."""
import math

import pytest


@pytest.fixture(autouse=True)
def _clear_embed_cache():
    """Isolate each test from stale LRU cache entries."""
    from app.services.embedder import _embed_cache
    _embed_cache.clear()
    yield
    _embed_cache.clear()


class TestEmbedder:
    @pytest.fixture(autouse=True)
    def _embedder(self):
        from app.services.embedder import Embedder
        self.embedder = Embedder()

    def test_embed_one_returns_correct_dimension(self):
        vec = self.embedder.embed_one("hello world")
        assert isinstance(vec, list)
        assert len(vec) == 384          # all-MiniLM-L6-v2 (set in conftest)

    def test_embed_one_is_unit_normalized(self):
        vec = self.embedder.embed_one("test sentence")
        magnitude = math.sqrt(sum(v ** 2 for v in vec))
        assert abs(magnitude - 1.0) < 1e-4

    def test_embed_batch_returns_matching_count(self):
        texts = ["first sentence", "second sentence", "third sentence"]
        vecs = self.embedder.embed(texts)
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)

    def test_lru_cache_populated_after_first_call(self):
        from app.services.embedder import _embed_cache
        self.embedder.embed_one("cache fill text")
        assert "cache fill text" in _embed_cache

    def test_lru_cache_returns_same_object_on_second_call(self):
        v1 = self.embedder.embed_one("repeated text")
        v2 = self.embedder.embed_one("repeated text")
        assert v1 is v2, "LRU cache should return the same list object"

    def test_different_texts_have_different_embeddings(self):
        v1 = self.embedder.embed_one("cats and kittens")
        v2 = self.embedder.embed_one("quantum physics")
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_embed_one_async_returns_cached_value(self):
        # Populate cache via sync call first
        sync_vec   = self.embedder.embed_one("async cache test")
        async_vec  = await self.embedder.embed_one_async("async cache test")
        assert sync_vec is async_vec   # must be exactly the same cached object

    @pytest.mark.asyncio
    async def test_embed_one_async_correct_dimension(self):
        vec = await self.embedder.embed_one_async("standalone async call")
        assert len(vec) == 384
