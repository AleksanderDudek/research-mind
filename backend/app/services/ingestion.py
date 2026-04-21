import uuid
from datetime import datetime
from qdrant_client.models import PointStruct
from loguru import logger

from app.services.chunker import Chunker
from app.services.embedder import Embedder
from app.services.vector_store import VectorStore
from app.services.pdf_parser import PDFParser
from app.services.scraper import WebScraper


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
        metadata: dict | None = None,
    ) -> dict:
        document_id = str(uuid.uuid4())
        chunks = self.chunker.split(text)

        if not chunks:
            raise ValueError("Tekst jest pusty lub nie da się go podzielić na fragmenty.")

        logger.info(f"Ingesting {len(chunks)} chunks for document {document_id}")
        vectors = self.embedder.embed(chunks)

        base_meta = metadata or {}
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "text": chunk,
                    "document_id": document_id,
                    "chunk_index": i,
                    "source_type": source_type,
                    "ingested_at": datetime.utcnow().isoformat(),
                    **base_meta,
                },
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]

        self.store.upsert(points)
        return {
            "document_id": document_id,
            "chunks_ingested": len(chunks),
            "source_type": source_type,
            "metadata": base_meta,
        }

    async def ingest_pdf_bytes(self, pdf_bytes: bytes, source: str = "upload") -> dict:
        text = self.pdf_parser.parse_bytes(pdf_bytes)
        pdf_meta = self.pdf_parser.metadata(pdf_bytes)
        return await self.ingest_text(
            text=text,
            source_type="pdf",
            metadata={"source": source, **pdf_meta},
        )

    async def ingest_pdf_url(self, url: str) -> dict:
        pdf_bytes = await self.scraper.fetch_pdf(url)
        return await self.ingest_pdf_bytes(pdf_bytes, source=url)

    async def ingest_web_url(self, url: str) -> dict:
        text, meta = await self.scraper.fetch_and_extract(url)
        return await self.ingest_text(
            text=text,
            source_type="web",
            metadata={"source": url, **meta},
        )

    async def ingest_raw_text(self, text: str, title: str = "Manual paste") -> dict:
        return await self.ingest_text(
            text=text,
            source_type="text",
            metadata={"source": "manual", "title": title},
        )
