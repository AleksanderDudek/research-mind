"""Session-level fixtures, shared constants, and test-environment patches.

Auth strategy
-------------
get_current_user is overridden ONCE at the session level to return an ADMIN
user so all existing tests pass without modification.

For role-specific tests, use the `as_user` or `as_superadmin` function-scoped
fixtures, which temporarily swap the override for a single test and restore it.
"""
import asyncio
import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ── Test environment (set before any app import) ──────────────────────────────
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
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_JWT_SECRET", "")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "")

# ── Shared test identity ──────────────────────────────────────────────────────
TEST_ORG_ID   = "00000000-0000-0000-0000-000000000001"
TEST_USER_ID  = "00000000-0000-0000-0000-000000000002"  # admin in tests
TEST_USER2_ID = "00000000-0000-0000-0000-000000000003"  # plain user in tests

# ── Shared text constants ─────────────────────────────────────────────────────
LONG_TEXT = (
    "Retrieval-augmented generation (RAG) combines information retrieval "
    "with large language model generation. Dense passage retrieval uses "
    "dual-encoder models to embed queries and passages into a shared "
    "vector space for semantic similarity search. "
) * 8

SHORT_TEXT = "Hi"


# ── Local Qdrant async patch ──────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _patch_async_qdrant_local_mode():
    """Wrap VectorStore async methods with run_in_executor in local Qdrant mode."""
    if not os.environ.get("QDRANT_LOCAL_PATH"):
        yield
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


# ── Auth dependency override ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client(_patch_async_qdrant_local_mode):
    """Shared TestClient. get_current_user is overridden to an ADMIN user.

    All tests run as admin by default. Use the `as_user` / `as_superadmin`
    fixtures to temporarily switch roles within a single test.
    """
    from app.auth.deps import AuthUser, get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        user_id=TEST_USER_ID,
        org_id=TEST_ORG_ID,
        role="admin",
        email="admin@test.example",
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_current_user, None)


def _set_role(role: str, user_id: str = TEST_USER2_ID):
    """Swap the auth override to *role* and return the old override."""
    from app.auth.deps import AuthUser, get_current_user
    from app.main import app

    old = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        user_id=user_id,
        org_id=TEST_ORG_ID,
        role=role,
        email=f"{role}@test.example",
    )
    return old


def _restore_role(old):
    from app.auth.deps import get_current_user
    from app.main import app

    if old is not None:
        app.dependency_overrides[get_current_user] = old
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def as_user(client):
    """Temporarily make the client act as a USER for this one test."""
    old = _set_role("user", TEST_USER2_ID)
    yield client
    _restore_role(old)


@pytest.fixture
def as_superadmin(client):
    """Temporarily make the client act as a SUPERADMIN for this one test."""
    old = _set_role("superadmin", "00000000-0000-0000-0000-000000000004")
    yield client
    _restore_role(old)


# ── Context fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def context_id(client):
    """Shared context for light-weight session-scoped tests."""
    r = client.post("/contexts", json={"name": "Shared Test Context"})
    assert r.status_code == 200
    return r.json()["context_id"]


@pytest.fixture
def fresh_context(client):
    """Brand-new context per test; always created/deleted as ADMIN even when
    the test temporarily switches to a different role via as_user."""
    from app.auth.deps import AuthUser, get_current_user
    from app.main import app

    admin = lambda: AuthUser(  # noqa: E731
        user_id=TEST_USER_ID, org_id=TEST_ORG_ID,
        role="admin", email="admin@test.example",
    )
    current = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = admin

    r = client.post("/contexts", json={"name": "Fresh Context"})
    assert r.status_code == 200
    ctx_id = r.json()["context_id"]

    # Restore whatever override the test set
    if current is not None:
        app.dependency_overrides[get_current_user] = current
    else:
        app.dependency_overrides.pop(get_current_user, None)

    yield ctx_id

    # Delete as admin regardless of current role
    app.dependency_overrides[get_current_user] = admin
    client.delete(f"/contexts/{ctx_id}")
    if current is not None:
        app.dependency_overrides[get_current_user] = current
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def seeded_context(client):
    """Context with one document ingested — always created/deleted as ADMIN."""
    from app.auth.deps import AuthUser, get_current_user
    from app.main import app

    admin = lambda: AuthUser(  # noqa: E731
        user_id=TEST_USER_ID, org_id=TEST_ORG_ID,
        role="admin", email="admin@test.example",
    )
    current = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = admin

    r = client.post("/contexts", json={"name": "Seeded Context"})
    assert r.status_code == 200
    ctx_id = r.json()["context_id"]
    client.post("/ingest/raw-text", json={
        "text": LONG_TEXT, "title": "Seed Doc", "context_id": ctx_id,
    })

    if current is not None:
        app.dependency_overrides[get_current_user] = current
    else:
        app.dependency_overrides.pop(get_current_user, None)

    yield ctx_id

    app.dependency_overrides[get_current_user] = admin
    client.delete(f"/contexts/{ctx_id}")
    if current is not None:
        app.dependency_overrides[get_current_user] = current
    else:
        app.dependency_overrides.pop(get_current_user, None)


# ── Cache isolation ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_ask_cache():
    """Prevent cached answers from leaking between tests."""
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
