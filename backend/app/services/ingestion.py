import uuid
from datetime import datetime, timezone

from loguru import logger
from qdrant_client.models import PointStruct

from app.services.chunker import Chunker
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

    async def ingest_text(
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

    async def ingest_pdf_bytes(
        self, pdf_bytes: bytes, source: str, context_id: str
    ) -> dict:
        text = self.pdf_parser.parse_bytes(pdf_bytes)
        pdf_meta = self.pdf_parser.metadata(pdf_bytes)
        return await self.ingest_text(
            text=text,
            source_type="pdf",
            context_id=context_id,
            metadata={"source": source, **pdf_meta},
        )

    async def ingest_pdf_url(self, url: str, context_id: str) -> dict:
        pdf_bytes = await self.scraper.fetch_pdf(url)
        return await self.ingest_pdf_bytes(pdf_bytes, source=url, context_id=context_id)

    async def ingest_web_url(self, url: str, context_id: str) -> dict:
        text, meta = await self.scraper.fetch_and_extract(url)
        return await self.ingest_text(
            text=text,
            source_type="web",
            context_id=context_id,
            metadata={"source": url, **meta},
        )

    async def ingest_raw_text(
        self, text: str, title: str, context_id: str
    ) -> dict:
        return await self.ingest_text(
            text=text,
            source_type="text",
            context_id=context_id,
            metadata={"source": "manual", "title": title},
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
        """Delete old chunks for document_id and re-index with new_text."""
        self.store.delete_by_document(document_id, context_id=context_id)
        delete_source(context_id, document_id)

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
