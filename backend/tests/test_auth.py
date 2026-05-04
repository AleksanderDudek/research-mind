"""Tests for authentication and role-based access control.

Uses as_user / as_superadmin fixtures from conftest to temporarily
switch the auth override for a single test.

Note: FastAPI's HTTPBearer(auto_error=True) returns 403 (not 401) when
no Authorization header is supplied — this is standard FastAPI behaviour.
"""
import pytest
from tests.conftest import LONG_TEXT, TEST_ORG_ID


# ── No-auth requests ──────────────────────────────────────────────────────────

class TestUnauthenticated:
    """Requests without a Bearer token return 403 (HTTPBearer default) or 503."""

    @pytest.fixture(autouse=True)
    def _remove_auth_override(self):
        """Run each test in this class with the real auth dependency (no override)."""
        from app.auth.deps import get_current_user
        from app.main import app

        old = app.dependency_overrides.pop(get_current_user, None)
        yield
        if old is not None:
            app.dependency_overrides[get_current_user] = old

    def test_contexts_blocked_without_token(self, client):
        r = client.get("/contexts")
        assert r.status_code in (401, 403, 503)

    def test_ingest_blocked_without_token(self, client):
        r = client.post("/ingest/raw-text",
                        json={"text": LONG_TEXT, "title": "x", "context_id": "y"})
        assert r.status_code in (401, 403, 503)

    def test_ask_blocked_without_token(self, client):
        r = client.post("/query/ask", json={"question": "test"})
        assert r.status_code in (401, 403, 503)

    def test_health_is_public(self, client):
        r = client.get("/health")
        assert r.status_code == 200


# ── USER role restrictions ────────────────────────────────────────────────────

class TestUserRoleRestrictions:
    """USERs can read and query but cannot create/edit/ingest."""

    def test_user_cannot_create_context(self, as_user):
        r = as_user.post("/contexts", json={"name": "Forbidden"})
        assert r.status_code == 403

    def test_user_cannot_ingest(self, as_user, context_id):
        r = as_user.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "Forbidden", "context_id": context_id,
        })
        assert r.status_code == 403

    def test_user_cannot_rename_context(self, as_user, context_id):
        r = as_user.patch(f"/contexts/{context_id}", json={"name": "Hijacked"})
        assert r.status_code == 403

    def test_user_can_list_contexts(self, as_user):
        r = as_user.get("/contexts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_user_can_search(self, as_user, seeded_context):
        r = as_user.post("/query/search", json={
            "question": "retrieval", "context_id": seeded_context,
        })
        assert r.status_code == 200

    def test_user_sees_only_own_messages(self, as_user, fresh_context):
        """Post as user; a second post with a different user_id should not appear."""
        from app.auth.deps import AuthUser, get_current_user
        from app.main import app
        from tests.conftest import TEST_USER_ID, TEST_ORG_ID

        # Post as a completely different user (admin user_id)
        old_override = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: AuthUser(
            user_id=TEST_USER_ID, org_id=TEST_ORG_ID,
            role="admin", email="admin@test.example",
        )
        as_user.post(f"/contexts/{fresh_context}/messages",
                     json={"role": "user", "content": "admin-only message"})

        # Restore user override
        if old_override:
            app.dependency_overrides[get_current_user] = old_override

        # Now query as USER — should NOT see the admin's message
        msgs = as_user.get(f"/contexts/{fresh_context}/messages").json()
        assert all(m.get("content") != "admin-only message" for m in msgs)

    def test_user_can_post_own_message(self, as_user, fresh_context):
        r = as_user.post(f"/contexts/{fresh_context}/messages",
                         json={"role": "user", "content": "my own message"})
        assert r.status_code == 200

    def test_user_can_transcribe(self, as_user, mocker):
        mocker.patch("app.services.transcriber.Transcriber.transcribe",
                     return_value="hello")
        r = as_user.post(
            "/query/transcribe",
            files={"file": ("v.webm", b"fake", "audio/webm")},
        )
        assert r.status_code == 200


# ── ADMIN rights ──────────────────────────────────────────────────────────────

class TestAdminRights:
    """ADMINs (the default client) can do everything within their org."""

    def test_admin_can_create_and_delete_context(self, client):
        r = client.post("/contexts", json={"name": "Admin Created"})
        assert r.status_code == 200
        client.delete(f"/contexts/{r.json()['context_id']}")

    def test_admin_can_ingest(self, client, context_id):
        r = client.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "Admin Doc", "context_id": context_id,
        })
        assert r.status_code == 200

    def test_admin_sees_all_messages(self, client, fresh_context):
        client.post(f"/contexts/{fresh_context}/messages",
                    json={"role": "user", "content": "visible to admin"})
        msgs = client.get(f"/contexts/{fresh_context}/messages").json()
        assert any(m["content"] == "visible to admin" for m in msgs)


# ── SUPERADMIN rights ─────────────────────────────────────────────────────────

class TestSuperAdminRights:
    def test_superadmin_can_list_contexts(self, as_superadmin):
        r = as_superadmin.get("/contexts")
        assert r.status_code == 200

    def test_superadmin_can_ingest(self, as_superadmin, context_id):
        r = as_superadmin.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "SA Doc", "context_id": context_id,
        })
        assert r.status_code == 200
