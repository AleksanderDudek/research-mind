from unittest.mock import AsyncMock

LONG_TEXT = "Retrieval-augmented generation (RAG) is a technique. " * 10


def test_ingest_raw_text(client, context_id):
    r = client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Test doc", "context_id": context_id})
    assert r.status_code == 200
    data = r.json()
    assert data["chunks_ingested"] >= 1
    assert data["source_type"] == "text"
    assert "document_id" in data
    assert data["context_id"] == context_id


def test_ingest_raw_text_too_short(client, context_id):
    r = client.post("/ingest/raw-text", json={"text": "Too short", "title": "X", "context_id": context_id})
    assert r.status_code == 400


def test_ingest_raw_text_missing_context_id(client):
    r = client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Test doc"})
    assert r.status_code == 422


def test_ingest_pdf_upload(client, context_id, mocker):
    mocker.patch(
        "app.services.pdf_parser.PDFParser.parse_bytes",
        return_value=LONG_TEXT,
    )
    mocker.patch(
        "app.services.pdf_parser.PDFParser.metadata",
        return_value={"title": "Mocked PDF", "author": "", "num_pages": 1},
    )
    r = client.post(
        "/ingest/pdf-upload",
        files={"file": ("paper.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        data={"context_id": context_id},
    )
    assert r.status_code == 200
    assert r.json()["source_type"] == "pdf"


def test_ingest_pdf_upload_wrong_extension(client, context_id):
    r = client.post(
        "/ingest/pdf-upload",
        files={"file": ("doc.txt", b"hello", "text/plain")},
        data={"context_id": context_id},
    )
    assert r.status_code == 400


def test_ingest_web_url(client, context_id, mocker):
    mocker.patch(
        "app.services.scraper.WebScraper.fetch_and_extract",
        new_callable=AsyncMock,
        return_value=(LONG_TEXT, {"title": "Test Page", "author": "", "date": "", "sitename": "example.com"}),
    )
    r = client.post("/ingest/web-url", json={"url": "https://example.com/article", "context_id": context_id})
    assert r.status_code == 200
    assert r.json()["source_type"] == "web"


def test_ingest_pdf_url(client, context_id, mocker):
    mocker.patch(
        "app.services.scraper.WebScraper.fetch_pdf",
        new_callable=AsyncMock,
        return_value=b"%PDF-1.4 fake",
    )
    mocker.patch(
        "app.services.pdf_parser.PDFParser.parse_bytes",
        return_value=LONG_TEXT,
    )
    mocker.patch(
        "app.services.pdf_parser.PDFParser.metadata",
        return_value={"title": "ArXiv Paper", "author": "", "num_pages": 5},
    )
    r = client.post("/ingest/pdf-url", json={"url": "https://arxiv.org/pdf/2005.11401.pdf", "context_id": context_id})
    assert r.status_code == 200
    assert r.json()["source_type"] == "pdf"
