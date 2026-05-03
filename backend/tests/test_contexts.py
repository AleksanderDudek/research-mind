"""Integration tests for context CRUD and cascade delete."""
from tests.conftest import LONG_TEXT

GHOST_ID = "00000000-dead-beef-0000-000000000000"


class TestContextCRUD:
    def test_list_returns_list(self, client):
        r = client.get("/contexts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_with_name(self, client):
        r = client.post("/contexts", json={"name": "My Research"})
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "My Research"
        assert "context_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_without_name_auto_generates(self, client):
        r = client.post("/contexts", json={})
        assert r.status_code == 200
        assert r.json()["name"]  # truthy auto-generated timestamp name

    def test_created_context_appears_in_list(self, client):
        ctx = client.post("/contexts", json={"name": "List Test"}).json()
        ctx_id = ctx["context_id"]
        ids = [c["context_id"] for c in client.get("/contexts").json()]
        assert ctx_id in ids

    def test_rename(self, client, fresh_context):
        r = client.patch(f"/contexts/{fresh_context}", json={"name": "Renamed"})
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed"

    def test_rename_not_found(self, client):
        r = client.patch(f"/contexts/{GHOST_ID}", json={"name": "X"})
        assert r.status_code == 404

    def test_delete(self, client):
        ctx_id = client.post("/contexts", json={"name": "To Delete"}).json()["context_id"]
        r = client.delete(f"/contexts/{ctx_id}")
        assert r.status_code == 200
        assert r.json()["deleted"] == ctx_id

    def test_delete_not_found(self, client):
        r = client.delete(f"/contexts/{GHOST_ID}")
        assert r.status_code == 404

    def test_deleted_context_absent_from_list(self, client):
        ctx_id = client.post("/contexts", json={"name": "Gone"}).json()["context_id"]
        client.delete(f"/contexts/{ctx_id}")
        ids = [c["context_id"] for c in client.get("/contexts").json()]
        assert ctx_id not in ids


class TestContextCascadeDelete:
    def test_sources_empty_after_cascade(self, client):
        ctx_id = client.post("/contexts", json={"name": "Cascade Src"}).json()["context_id"]
        client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Doc", "context_id": ctx_id})
        assert len(client.get(f"/contexts/{ctx_id}/sources").json()) == 1

        client.delete(f"/contexts/{ctx_id}")

        assert client.get(f"/contexts/{ctx_id}/sources").json() == []

    def test_history_empty_after_cascade(self, client):
        ctx_id = client.post("/contexts", json={"name": "Cascade Hist"}).json()["context_id"]
        client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Doc", "context_id": ctx_id})
        client.delete(f"/contexts/{ctx_id}")
        assert client.get(f"/contexts/{ctx_id}/history").json() == []

    def test_messages_empty_after_cascade(self, client):
        ctx_id = client.post("/contexts", json={"name": "Cascade Msgs"}).json()["context_id"]
        client.post(f"/contexts/{ctx_id}/messages", json={"role": "user", "content": "hello"})
        client.delete(f"/contexts/{ctx_id}")
        assert client.get(f"/contexts/{ctx_id}/messages").json() == []
