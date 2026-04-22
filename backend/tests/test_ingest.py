from unittest.mock import AsyncMock

LONG_TEXT = "Retrieval-augmented generation (RAG) is a technique. " * 10


def test_ingest_raw_text(client):
    r = client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Test doc"})
    assert r.status_code == 200
    data = r.json()
    assert data["chunks_ingested"] >= 1
    assert data["source_type"] == "text"
    assert "document_id" in data


def test_ingest_raw_text_too_short(client):
    r = client.post("/ingest/raw-text", json={"text": "Too short", "title": "X"})
    assert r.status_code == 400


def test_ingest_pdf_upload(client, mocker):
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
    )
    assert r.status_code == 200
    assert r.json()["source_type"] == "pdf"


def test_ingest_pdf_upload_wrong_extension(client):
    r = client.post(
        "/ingest/pdf-upload",
        files={"file": ("doc.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


def test_ingest_web_url(client, mocker):
    mocker.patch(
        "app.services.scraper.WebScraper.fetch_and_extract",
        new_callable=AsyncMock,
        return_value=(LONG_TEXT, {"title": "Test Page", "author": "", "date": "", "sitename": "example.com"}),
    )
    r = client.post("/ingest/web-url", json={"url": "https://example.com/article"})
    assert r.status_code == 200
    assert r.json()["source_type"] == "web"


def test_ingest_pdf_url(client, mocker):
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
    r = client.post("/ingest/pdf-url", json={"url": "https://arxiv.org/pdf/2005.11401.pdf"})
    assert r.status_code == 200
    assert r.json()["source_type"] == "pdf"
