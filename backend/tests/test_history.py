"""Tests for /contexts/{id}/history endpoint."""
from tests.conftest import LONG_TEXT


class TestHistory:
    def test_empty_on_new_context(self, client, fresh_context):
        r = client.get(f"/contexts/{fresh_context}/history")
        assert r.status_code == 200
        assert r.json() == []

    def test_ingest_appends_source_added_entry(self, client, fresh_context):
        client.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "History Doc", "context_id": fresh_context,
        })
        history = client.get(f"/contexts/{fresh_context}/history").json()
        assert len(history) >= 1
        assert any(e["action"] == "source_added" for e in history)

    def test_entry_has_required_fields(self, client, fresh_context):
        client.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "Fields Test", "context_id": fresh_context,
        })
        entry = client.get(f"/contexts/{fresh_context}/history").json()[0]
        for field in ("action", "detail", "timestamp"):
            assert field in entry

    def test_edit_source_appends_source_edited_entry(self, client, fresh_context):
        client.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "Edit Me", "context_id": fresh_context,
        })
        doc_id = client.get(f"/contexts/{fresh_context}/sources").json()[0]["document_id"]
        new_text = "Updated content about information retrieval systems. " * 8
        client.put(f"/contexts/{fresh_context}/sources/{doc_id}",
                   json={"text": new_text, "title": "Edited"})
        actions = [e["action"] for e in
                   client.get(f"/contexts/{fresh_context}/history").json()]
        assert "source_edited" in actions
