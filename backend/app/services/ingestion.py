import base64
import mimetypes
import uuid
from datetime import datetime, timezone

from loguru import logger
from qdrant_client.models import PointStruct

from app.llm.client import LLMClient
from app.services.chunker import Chunker
from app.services.transcriber import Transcriber
from app.services.embedder import Embedder
from app.services.history_store import append as history_append
from app.services.pdf_parser import PDFParser
from app.services.scraper import WebScraper
from app.services.source_store import delete_source, save_source
from app.services.vector_store import VectorStore

_LEGACY_CONTEXT = "00000000-0000-0000-0000-000000000000"


class IngestionService:
    def __init__(self) -> None:
        self.chunker = Chunker()
        self.embedder = Embedder()
        self.store = VectorStore()
        self.pdf_parser = PDFParser()
        self.scraper = WebScraper()
        self.transcriber = Transcriber()

    def ingest_text(
        self,
        text: str,
        source_type: str,
        context_id: str,
        metadata: dict | None = None,
    ) -> dict:
        document_id = str(uuid.uuid4())
        chunks = self.chunker.split(text)
        if not chunks:
            raise ValueError("Text is empty or cannot be split into chunks.")

        logger.info(f"Ingesting {len(chunks)} chunks → context={context_id!r} doc={document_id!r}")
        vectors = self.embedder.embed(chunks)

        base_meta = metadata or {}
        title = base_meta.get("title") or base_meta.get("source", "")
        url = base_meta.get("source") if source_type in ("pdf", "web") else None

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "text": chunk,
                    "document_id": document_id,
                    "context_id": context_id,
                    "chunk_index": i,
                    "source_type": source_type,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    **base_meta,
                },
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]

        self.store.upsert(points)

        save_source(
            context_id=context_id,
            document_id=document_id,
            title=title,
            source_type=source_type,
            raw_text=text,
            url=url,
            chunk_count=len(chunks),
        )
        history_append(
            context_id=context_id,
            action="source_added",
            detail=f"{source_type}: {title or document_id}",
        )

        return {
            "document_id": document_id,
            "chunks_ingested": len(chunks),
            "source_type": source_type,
            "context_id": context_id,
            "metadata": base_meta,
        }

    def ingest_pdf_bytes(
        self, pdf_bytes: bytes, source: str, context_id: str
    ) -> dict:
        text = self.pdf_parser.parse_bytes(pdf_bytes)
        pdf_meta = self.pdf_parser.metadata(pdf_bytes)
        return self.ingest_text(
            text=text,
            source_type="pdf",
            context_id=context_id,
            metadata={"source": source, **pdf_meta},
        )

    async def ingest_pdf_url(self, url: str, context_id: str) -> dict:
        pdf_bytes = await self.scraper.fetch_pdf(url)
        return self.ingest_pdf_bytes(pdf_bytes, source=url, context_id=context_id)

    async def ingest_web_url(self, url: str, context_id: str) -> dict:
        text, meta = await self.scraper.fetch_and_extract(url)
        return self.ingest_text(
            text=text,
            source_type="web",
            context_id=context_id,
            metadata={"source": url, **meta},
        )

    def ingest_raw_text(
        self, text: str, title: str, context_id: str
    ) -> dict:
        return self.ingest_text(
            text=text,
            source_type="text",
            context_id=context_id,
            metadata={"source": "manual", "title": title},
        )

    def ingest_audio_bytes(
        self,
        audio_bytes: bytes,
        filename: str,
        context_id: str,
    ) -> dict:
        logger.info(f"Transcribing audio {filename!r}")
        transcription = self.transcriber.transcribe(audio_bytes, filename)
        if not transcription.strip():
            raise ValueError("Transcription produced no text — check audio quality.")
        return self.ingest_text(
            text=f"[Audio: {filename}]\n\n{transcription}",
            source_type="audio",
            context_id=context_id,
            metadata={"title": filename, "source": filename},
        )

    async def ingest_image_bytes(
        self,
        image_bytes: bytes,
        filename: str,
        context_id: str,
        detail_level: str = "standard",
    ) -> dict:
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/jpeg"

        image_b64 = base64.b64encode(image_bytes).decode()

        logger.info(f"Describing image {filename!r} detail_level={detail_level!r}")
        description = await LLMClient.complete_vision(image_b64, mime_type, detail_level)

        document_id = str(uuid.uuid4())
        text = f"[Image: {filename}]\n\n{description}"
        chunks = self.chunker.split(text) or [text]
        vectors = self.embedder.embed(chunks)
        now = datetime.now(timezone.utc).isoformat()

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "text": chunk,
                    "document_id": document_id,
                    "context_id": context_id,
                    "chunk_index": i,
                    "source_type": "image",
                    "title": filename,
                    "source": filename,
                    "ingested_at": now,
                },
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]
        self.store.upsert(points)

        save_source(
            context_id=context_id,
            document_id=document_id,
            title=filename,
            source_type="image",
            raw_text=description,
            url=None,
            chunk_count=len(chunks),
            image_data=image_b64,
            image_mime_type=mime_type,
        )
        history_append(context_id=context_id, action="source_added", detail=f"image: {filename}")

        return {
            "document_id": document_id,
            "chunks_ingested": len(chunks),
            "source_type": "image",
            "context_id": context_id,
        }

    def reingest_text(
        self,
        document_id: str,
        new_text: str,
        title: str,
        source_type: str,
        context_id: str,
        url: str | None,
    ) -> dict:
        """Delete old chunks for document_id and re-index with new_text."""
        self.store.delete_by_document(document_id, context_id=context_id)
        delete_source(document_id)

        chunks = self.chunker.split(new_text)
        if not chunks:
            raise ValueError("Edited text is empty or cannot be chunked.")

        vectors = self.embedder.embed(chunks)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "text": chunk,
                    "document_id": document_id,
                    "context_id": context_id,
                    "chunk_index": i,
                    "source_type": source_type,
                    "title": title,
                    "source": url or "manual",
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]
        self.store.upsert(points)

        save_source(
            context_id=context_id,
            document_id=document_id,
            title=title,
            source_type=source_type,
            raw_text=new_text,
            url=url,
            chunk_count=len(chunks),
        )
        history_append(
            context_id=context_id,
            action="source_edited",
            detail=f"{source_type}: {title or document_id}",
        )

        return {
            "document_id": document_id,
            "chunks_ingested": len(chunks),
            "source_type": source_type,
            "context_id": context_id,
        }
