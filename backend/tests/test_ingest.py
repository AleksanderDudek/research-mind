"""Integration tests for all ingestion endpoints."""
from unittest.mock import AsyncMock

from tests.conftest import LONG_TEXT, SHORT_TEXT


class TestIngestRawText:
    def test_success(self, client, context_id):
        r = client.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "Test Doc", "context_id": context_id,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["source_type"] == "text"
        assert data["chunks_ingested"] >= 1
        assert "document_id" in data
        assert data["context_id"] == context_id

    def test_too_short_rejected(self, client, context_id):
        r = client.post("/ingest/raw-text", json={
            "text": SHORT_TEXT, "title": "Short", "context_id": context_id,
        })
        assert r.status_code == 400

    def test_missing_context_id_rejected(self, client):
        r = client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "No ctx"})
        assert r.status_code == 422

    def test_appears_in_source_list(self, client, fresh_context):
        client.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "Source Check", "context_id": fresh_context,
        })
        sources = client.get(f"/contexts/{fresh_context}/sources").json()
        assert any(s["title"] == "Source Check" for s in sources)

    def test_creates_history_entry(self, client, fresh_context):
        client.post("/ingest/raw-text", json={
            "text": LONG_TEXT, "title": "History Check", "context_id": fresh_context,
        })
        history = client.get(f"/contexts/{fresh_context}/history").json()
        assert any(e["action"] == "source_added" for e in history)


class TestIngestPdfUpload:
    def test_success(self, client, context_id, mocker):
        mocker.patch("app.services.pdf_parser.PDFParser.parse_bytes", return_value=LONG_TEXT)
        mocker.patch("app.services.pdf_parser.PDFParser.metadata",
                     return_value={"title": "PDF Doc", "author": "", "num_pages": 3})
        r = client.post(
            "/ingest/pdf-upload",
            files={"file": ("paper.pdf", b"%PDF-1.4 fake", "application/pdf")},
            data={"context_id": context_id},
        )
        assert r.status_code == 200
        assert r.json()["source_type"] == "pdf"

    def test_wrong_extension_rejected(self, client, context_id):
        r = client.post(
            "/ingest/pdf-upload",
            files={"file": ("doc.txt", b"not a pdf", "text/plain")},
            data={"context_id": context_id},
        )
        assert r.status_code == 400


class TestIngestWebUrl:
    def test_success(self, client, context_id, mocker):
        mocker.patch(
            "app.services.scraper.WebScraper.fetch_and_extract",
            new_callable=AsyncMock,
            return_value=(LONG_TEXT, {"title": "Web Page", "sitename": "example.com"}),
        )
        r = client.post("/ingest/web-url", json={
            "url": "https://example.com/article", "context_id": context_id,
        })
        assert r.status_code == 200
        assert r.json()["source_type"] == "web"


class TestIngestPdfUrl:
    def test_success(self, client, context_id, mocker):
        mocker.patch(
            "app.services.scraper.WebScraper.fetch_pdf",
            new_callable=AsyncMock,
            return_value=b"%PDF-1.4 fake",
        )
        mocker.patch("app.services.pdf_parser.PDFParser.parse_bytes", return_value=LONG_TEXT)
        mocker.patch("app.services.pdf_parser.PDFParser.metadata",
                     return_value={"title": "ArXiv", "author": "", "num_pages": 10})
        r = client.post("/ingest/pdf-url", json={
            "url": "https://arxiv.org/pdf/2005.11401.pdf", "context_id": context_id,
        })
        assert r.status_code == 200
        assert r.json()["source_type"] == "pdf"


class TestIngestAudioUpload:
    def test_success(self, client, context_id, mocker):
        mocker.patch("app.services.transcriber.Transcriber.transcribe", return_value=LONG_TEXT)
        r = client.post(
            "/ingest/audio-upload",
            files={"file": ("talk.mp3", b"fake audio bytes", "audio/mpeg")},
            data={"context_id": context_id},
        )
        assert r.status_code == 200
        assert r.json()["source_type"] == "audio"


class TestIngestImageUpload:
    _PNG = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
        b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
        b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )

    def test_success(self, client, context_id, mocker):
        mocker.patch(
            "app.llm.client.LLMClient.complete_vision",
            new_callable=AsyncMock,
            return_value="An image showing a neural network diagram with labelled layers. " * 6,
        )
        r = client.post(
            "/ingest/image-upload",
            files={"file": ("diagram.png", self._PNG, "image/png")},
            data={"context_id": context_id},
        )
        assert r.status_code == 200
        assert r.json()["source_type"] == "image"
