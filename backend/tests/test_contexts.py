LONG_TEXT = "Context-scoped retrieval allows isolated knowledge buckets in RAG systems. " * 8


def test_list_contexts_empty_initially(client):
    r = client.get("/contexts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_context_with_name(client):
    r = client.post("/contexts", json={"name": "My Research"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "My Research"
    assert "context_id" in data
    assert "created_at" in data


def test_create_context_without_name(client):
    r = client.post("/contexts", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["name"]  # auto-generated timestamp name


def test_rename_context(client):
    ctx = client.post("/contexts", json={"name": "Old Name"}).json()
    ctx_id = ctx["context_id"]

    r = client.patch(f"/contexts/{ctx_id}", json={"name": "New Name"})
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


def test_rename_context_not_found(client):
    r = client.patch("/contexts/00000000-dead-beef-0000-000000000000", json={"name": "X"})
    assert r.status_code == 404


def test_delete_context(client):
    ctx = client.post("/contexts", json={"name": "To Delete"}).json()
    ctx_id = ctx["context_id"]

    r = client.delete(f"/contexts/{ctx_id}")
    assert r.status_code == 200
    assert r.json()["deleted"] == ctx_id


def test_delete_context_not_found(client):
    r = client.delete("/contexts/00000000-dead-beef-0000-000000000001")
    assert r.status_code == 404


def test_sources_empty_for_new_context(client):
    ctx = client.post("/contexts", json={"name": "Empty"}).json()
    r = client.get(f"/contexts/{ctx['context_id']}/sources")
    assert r.status_code == 200
    assert r.json() == []


def test_history_empty_for_new_context(client):
    ctx = client.post("/contexts", json={"name": "Empty History"}).json()
    r = client.get(f"/contexts/{ctx['context_id']}/history")
    assert r.status_code == 200
    assert r.json() == []


def test_ingest_appears_in_sources_and_history(client):
    ctx = client.post("/contexts", json={"name": "Source Test"}).json()
    ctx_id = ctx["context_id"]

    client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "My Doc", "context_id": ctx_id})

    sources = client.get(f"/contexts/{ctx_id}/sources").json()
    assert len(sources) == 1
    assert sources[0]["title"] == "My Doc"
    assert sources[0]["source_type"] == "text"
    assert sources[0]["chunk_count"] >= 1

    history = client.get(f"/contexts/{ctx_id}/history").json()
    assert len(history) >= 1
    assert any(e["action"] == "source_added" for e in history)


def test_get_source_text(client):
    ctx = client.post("/contexts", json={"name": "Edit Test"}).json()
    ctx_id = ctx["context_id"]

    client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Editable", "context_id": ctx_id})
    sources = client.get(f"/contexts/{ctx_id}/sources").json()
    doc_id = sources[0]["document_id"]

    r = client.get(f"/contexts/{ctx_id}/sources/{doc_id}/text")
    assert r.status_code == 200
    data = r.json()
    assert "raw_text" in data
    assert data["raw_text"] == LONG_TEXT


def test_edit_source(client):
    ctx = client.post("/contexts", json={"name": "Edit Source"}).json()
    ctx_id = ctx["context_id"]

    client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Original", "context_id": ctx_id})
    sources = client.get(f"/contexts/{ctx_id}/sources").json()
    doc_id = sources[0]["document_id"]

    new_text = "Edited content about information retrieval systems. " * 8
    r = client.put(
        f"/contexts/{ctx_id}/sources/{doc_id}",
        json={"text": new_text, "title": "Edited"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["chunks_ingested"] >= 1

    updated = client.get(f"/contexts/{ctx_id}/sources/{doc_id}/text").json()
    assert updated["raw_text"] == new_text
    assert updated["title"] == "Edited"

    history = client.get(f"/contexts/{ctx_id}/history").json()
    assert any(e["action"] == "source_edited" for e in history)


def test_delete_source(client):
    ctx = client.post("/contexts", json={"name": "Delete Source"}).json()
    ctx_id = ctx["context_id"]

    client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "To Remove", "context_id": ctx_id})
    sources = client.get(f"/contexts/{ctx_id}/sources").json()
    doc_id = sources[0]["document_id"]

    r = client.delete(f"/contexts/{ctx_id}/sources/{doc_id}")
    assert r.status_code == 200
    assert r.json()["deleted"] == doc_id

    remaining = client.get(f"/contexts/{ctx_id}/sources").json()
    assert all(s["document_id"] != doc_id for s in remaining)


def test_delete_context_cascades(client):
    ctx = client.post("/contexts", json={"name": "Cascade Delete"}).json()
    ctx_id = ctx["context_id"]

    client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Cascade Doc", "context_id": ctx_id})

    client.delete(f"/contexts/{ctx_id}")

    sources = client.get(f"/contexts/{ctx_id}/sources").json()
    assert sources == []

    history = client.get(f"/contexts/{ctx_id}/history").json()
    assert history == []
