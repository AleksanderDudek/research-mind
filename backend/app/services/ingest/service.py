"""IngestionService — thin orchestrator that delegates to pipeline helpers."""
import base64
import mimetypes
import uuid

from loguru import logger

from app.enums import DetailLevel, HistoryAction, SourceType
from app.llm.client import LLMClient
from app.services.chunker import Chunker
from app.services.embedder import Embedder
from app.services.pdf_parser import PDFParser
from app.services.scraper import WebScraper
from app.services.stores.history_store import append as history_append
from app.services.transcriber import Transcriber
from app.services.vector_store import VectorStore
from app.services.ingest._pipeline import (
    build_chunk_points,
    delete_and_log,
    store_and_log,
)


class IngestionService:
    def __init__(self) -> None:
        self._chunker     = Chunker()
        self._embedder    = Embedder()
        self._store       = VectorStore()
        self._pdf_parser  = PDFParser()
        self._scraper     = WebScraper()
        self._transcriber = Transcriber()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _ingest_text(
        self,
        text: str,
        source_type: str,
        context_id: str,
        title: str,
        url: str | None = None,
        extra_payload: dict | None = None,
    ) -> dict:
        document_id = str(uuid.uuid4())
        points, chunks = build_chunk_points(
            text=text,
            document_id=document_id,
            context_id=context_id,
            source_type=source_type,
            chunker=self._chunker,
            embedder=self._embedder,
            extra_payload={**(extra_payload or {}), "title": title, "source": url or "manual"},
        )
        if not chunks:
            raise ValueError("Text is empty or cannot be split into chunks.")
        logger.info(
            f"Ingesting {len(chunks)} chunks → context={context_id!r} "
            f"source_type={source_type!r} doc={document_id!r}"
        )
        return store_and_log(
            store=self._store,
            points=points,
            context_id=context_id,
            document_id=document_id,
            title=title,
            source_type=source_type,
            raw_text=text,
            url=url,
            chunk_count=len(chunks),
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def ingest_raw_text(self, text: str, title: str, context_id: str) -> dict:
        return self._ingest_text(
            text=text, source_type=SourceType.TEXT,
            context_id=context_id, title=title,
        )

    def ingest_pdf_bytes(self, pdf_bytes: bytes, source: str, context_id: str) -> dict:
        text = self._pdf_parser.parse_bytes(pdf_bytes)
        meta = self._pdf_parser.metadata(pdf_bytes)
        return self._ingest_text(
            text=text, source_type=SourceType.PDF,
            context_id=context_id, title=source,
            url=source, extra_payload=meta,
        )

    async def ingest_pdf_url(self, url: str, context_id: str) -> dict:
        pdf_bytes = await self._scraper.fetch_pdf(url)
        return self.ingest_pdf_bytes(pdf_bytes, source=url, context_id=context_id)

    async def ingest_web_url(self, url: str, context_id: str) -> dict:
        text, meta = await self._scraper.fetch_and_extract(url)
        return self._ingest_text(
            text=text, source_type=SourceType.WEB,
            context_id=context_id, title=meta.get("title", url),
            url=url, extra_payload=meta,
        )

    def ingest_audio_bytes(self, audio_bytes: bytes, filename: str, context_id: str) -> dict:
        logger.info(f"Transcribing audio {filename!r}")
        transcription = self._transcriber.transcribe(audio_bytes, filename)
        if not transcription.strip():
            raise ValueError("Transcription produced no text — check audio quality.")
        return self._ingest_text(
            text=f"[Audio: {filename}]\n\n{transcription}",
            source_type=SourceType.AUDIO,
            context_id=context_id,
            title=filename,
            url=filename,
        )

    async def ingest_image_bytes(
        self,
        image_bytes: bytes,
        filename: str,
        context_id: str,
        detail_level: str = DetailLevel.STANDARD,
    ) -> dict:
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/jpeg"
        image_b64 = base64.b64encode(image_bytes).decode()
        logger.info(f"Describing image {filename!r} detail_level={detail_level!r}")
        description = await LLMClient.complete_vision(image_b64, mime_type, detail_level)
        text = f"[Image: {filename}]\n\n{description}"
        document_id = str(uuid.uuid4())
        points, chunks = build_chunk_points(
            text=text,
            document_id=document_id,
            context_id=context_id,
            source_type=SourceType.IMAGE,
            chunker=self._chunker,
            embedder=self._embedder,
            extra_payload={"title": filename, "source": filename},
        )
        return store_and_log(
            store=self._store,
            points=points,
            context_id=context_id,
            document_id=document_id,
            title=filename,
            source_type=SourceType.IMAGE,
            raw_text=description,
            url=None,
            chunk_count=len(chunks),
            image_data=image_b64,
            image_mime_type=mime_type,
        )

    def reingest_text(
        self,
        document_id: str,
        new_text: str,
        title: str,
        source_type: str,
        context_id: str,
        url: str | None,
    ) -> dict:
        delete_and_log(self._store, document_id, context_id)
        points, chunks = build_chunk_points(
            text=new_text,
            document_id=document_id,
            context_id=context_id,
            source_type=source_type,
            chunker=self._chunker,
            embedder=self._embedder,
            extra_payload={"title": title, "source": url or "manual"},
        )
        if not chunks:
            raise ValueError("Edited text is empty or cannot be chunked.")
        result = store_and_log(
            store=self._store,
            points=points,
            context_id=context_id,
            document_id=document_id,
            title=title,
            source_type=source_type,
            raw_text=new_text,
            url=url,
            chunk_count=len(chunks),
        )
        # Override action logged by store_and_log
        history_append(
            context_id=context_id,
            action=HistoryAction.SOURCE_EDITED,
            detail=f"{source_type}: {title or document_id}",
        )
        return result
