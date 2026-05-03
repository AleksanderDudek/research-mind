"""Session-level fixtures, shared constants, and test-environment patches.

Env vars are set at module-level so pydantic-settings reads them from
os.environ before any app module is imported.

Key patches applied here
------------------------
_patch_async_qdrant_local_mode (session, autouse)
    AsyncQdrantClient cannot open a path already held by QdrantClient because
    qdrant-client uses an exclusive file lock on the embedded storage folder.
    In local test mode (QDRANT_LOCAL_PATH set) we patch VectorStore.search_async
    and upsert_async to run the sync equivalents in a thread-pool executor instead.
    This keeps the async interface intact without touching any source file.
"""
import asyncio
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# ── Test environment ──────────────────────────────────────────────────────────
_QDRANT_DIR = tempfile.mkdtemp(prefix="rm_test_qdrant_")
os.environ.setdefault("QDRANT_LOCAL_PATH", _QDRANT_DIR)
os.environ.setdefault("QDRANT_API_KEY", "")
os.environ.setdefault("LITELLM_BASE_URL", "http://localhost:11434")
os.environ.setdefault("LITELLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
os.environ.setdefault("EMBEDDING_DIM", "384")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "")

# ── Shared text constants ─────────────────────────────────────────────────────
LONG_TEXT = (
    "Retrieval-augmented generation (RAG) combines information retrieval "
    "with large language model generation. Dense passage retrieval uses "
    "dual-encoder models to embed queries and passages into a shared "
    "vector space for semantic similarity search. "
) * 8  # long enough to produce ≥1 chunk after splitting

SHORT_TEXT = "Hi"  # below the 50-char minimum


# ── Local Qdrant async patch ──────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _patch_async_qdrant_local_mode():
    """Patch VectorStore.{search,upsert}_async to use executor in local mode.

    AsyncQdrantClient cannot share the embedded storage folder (file lock).
    Patching the two async methods on the class is safe because:
      • Python attribute lookup finds class methods before instance ones.
      • The singleton VectorStore instance delegates through the class.
      • Remote-mode tests (no QDRANT_LOCAL_PATH) are unaffected.
    """
    from unittest.mock import patch

    if not os.environ.get("QDRANT_LOCAL_PATH"):
        yield  # remote Qdrant: real async client works fine
        return

    from app.services.vector_store import VectorStore

    async def _search_via_executor(self, query_vector, top_k=5, filters=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.search, query_vector, top_k, filters)

    async def _upsert_via_executor(self, points):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.upsert, points)

    with (
        patch.object(VectorStore, "search_async", new=_search_via_executor),
        patch.object(VectorStore, "upsert_async", new=_upsert_via_executor),
    ):
        yield


# ── App fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client(_patch_async_qdrant_local_mode):
    """One shared TestClient for the entire session."""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def context_id(client):
    """One shared context for light-weight session-scoped tests."""
    r = client.post("/contexts", json={"name": "Shared Test Context"})
    assert r.status_code == 200
    return r.json()["context_id"]


@pytest.fixture
def fresh_context(client):
    """Brand-new context per test; cleaned up afterwards for isolation."""
    r = client.post("/contexts", json={"name": "Fresh Context"})
    assert r.status_code == 200
    ctx_id = r.json()["context_id"]
    yield ctx_id
    client.delete(f"/contexts/{ctx_id}")


@pytest.fixture
def seeded_context(client):
    """Context with one document already ingested — ready for query tests."""
    r = client.post("/contexts", json={"name": "Seeded Context"})
    assert r.status_code == 200
    ctx_id = r.json()["context_id"]
    client.post("/ingest/raw-text", json={
        "text": LONG_TEXT, "title": "Seed Doc", "context_id": ctx_id,
    })
    yield ctx_id
    client.delete(f"/contexts/{ctx_id}")


@pytest.fixture(autouse=True)
def _clear_ask_cache():
    """Clear the /ask TTL cache before and after every test.

    Prevents a cached answer from one test masking a failure in another when
    the same question+context_id combination is reused.
    """
    try:
        from app.routers.query import _ask_cache
        _ask_cache.clear()
    except Exception:
        pass
    yield
    try:
        from app.routers.query import _ask_cache
        _ask_cache.clear()
    except Exception:
        pass
