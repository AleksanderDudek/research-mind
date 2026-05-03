"""Smoke tests — the server is alive and the OpenAPI schema loads."""


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_schema_reachable(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()


def test_docs_ui_reachable(client):
    r = client.get("/docs")
    assert r.status_code == 200
