"""Tests for /contexts/{id}/sources/* endpoints."""
from tests.conftest import LONG_TEXT

GHOST = "00000000-0000-0000-0000-000000000099"


def _ingest(client, ctx_id, title="Doc"):
    """Helper: ingest LONG_TEXT and return the resulting document_id."""
    client.post("/ingest/raw-text", json={
        "text": LONG_TEXT, "title": title, "context_id": ctx_id,
    })
    return client.get(f"/contexts/{ctx_id}/sources").json()[0]["document_id"]


class TestSources:
    def test_empty_list_on_new_context(self, client, fresh_context):
        r = client.get(f"/contexts/{fresh_context}/sources")
        assert r.status_code == 200
        assert r.json() == []

    def test_source_listed_after_ingest(self, client, fresh_context):
        _ingest(client, fresh_context, "My Source")
        sources = client.get(f"/contexts/{fresh_context}/sources").json()
        assert len(sources) == 1
        assert sources[0]["title"] == "My Source"
        assert sources[0]["source_type"] == "text"
        assert sources[0]["chunk_count"] >= 1

    def test_get_source_text(self, client, fresh_context):
        doc_id = _ingest(client, fresh_context, "Text Source")
        r = client.get(f"/contexts/{fresh_context}/sources/{doc_id}/text")
        assert r.status_code == 200
        data = r.json()
        assert data["raw_text"] == LONG_TEXT
        assert data["title"] == "Text Source"

    def test_get_source_text_not_found(self, client, fresh_context):
        r = client.get(f"/contexts/{fresh_context}/sources/{GHOST}/text")
        assert r.status_code == 404

    def test_edit_source_replaces_content(self, client, fresh_context):
        doc_id = _ingest(client, fresh_context, "Original")
        new_text = "Edited content about deep learning and neural networks. " * 8
        r = client.put(f"/contexts/{fresh_context}/sources/{doc_id}",
                       json={"text": new_text, "title": "Edited Title"})
        assert r.status_code == 200
        assert r.json()["chunks_ingested"] >= 1
        updated = client.get(f"/contexts/{fresh_context}/sources/{doc_id}/text").json()
        assert updated["raw_text"] == new_text
        assert updated["title"] == "Edited Title"

    def test_delete_source(self, client, fresh_context):
        doc_id = _ingest(client, fresh_context, "To Remove")
        r = client.delete(f"/contexts/{fresh_context}/sources/{doc_id}")
        assert r.status_code == 200
        assert r.json()["deleted"] == doc_id
        remaining = client.get(f"/contexts/{fresh_context}/sources").json()
        assert all(s["document_id"] != doc_id for s in remaining)

    def test_sources_are_context_scoped(self, client, fresh_context):
        _ingest(client, fresh_context, "Context A Doc")
        other = client.post("/contexts", json={"name": "Other Ctx"}).json()["context_id"]
        assert client.get(f"/contexts/{other}/sources").json() == []
        client.delete(f"/contexts/{other}")
