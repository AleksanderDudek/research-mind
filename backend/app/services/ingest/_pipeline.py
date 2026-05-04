"""Shared chunk-build / store / log helpers used by IngestionService."""
import uuid
from datetime import datetime, timezone

from qdrant_client.models import PointStruct

from app.services.chunker import Chunker
from app.services.embedder import Embedder
from app.services.vector_store import VectorStore
from app.services.stores.source_store import save_source, delete_source
from app.services.stores.history_store import append as history_append
from app.enums import HistoryAction


def build_chunk_points(
    text: str,
    document_id: str,
    context_id: str,
    source_type: str,
    chunker: Chunker,
    embedder: Embedder,
    extra_payload: dict | None = None,
) -> tuple[list[PointStruct], list[str]]:
    """Chunk *text*, embed, build PointStructs. Returns (points, chunks)."""
    chunks = chunker.split(text)
    vectors = embedder.embed(chunks)
    now = datetime.now(timezone.utc).isoformat()
    base = extra_payload or {}
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "text":         chunk,
                "document_id":  document_id,
                "context_id":   context_id,
                "chunk_index":  i,
                "source_type":  source_type,
                "ingested_at":  now,
                **base,
            },
        )
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    return points, chunks


def store_and_log(
    store: VectorStore,
    points: list[PointStruct],
    context_id: str,
    document_id: str,
    title: str,
    source_type: str,
    raw_text: str,
    url: str | None,
    chunk_count: int,
    org_id: str = "",
    image_data: str | None = None,
    image_mime_type: str | None = None,
) -> dict:
    """Upsert vectors, persist source record, append history entry."""
    store.upsert(points)
    save_source(
        context_id=context_id,
        document_id=document_id,
        title=title,
        source_type=source_type,
        raw_text=raw_text,
        url=url,
        chunk_count=chunk_count,
        org_id=org_id,
        image_data=image_data,
        image_mime_type=image_mime_type,
    )
    history_append(
        context_id=context_id,
        action=HistoryAction.SOURCE_ADDED,
        detail=f"{source_type}: {title or document_id}",
        org_id=org_id,
    )
    return {
        "document_id":     document_id,
        "chunks_ingested": chunk_count,
        "source_type":     source_type,
        "context_id":      context_id,
    }


def delete_and_log(
    store: VectorStore,
    document_id: str,
    context_id: str,
) -> None:
    """Remove chunks and source record for document_id."""
    store.delete_by_document(document_id, context_id=context_id)
    delete_source(document_id)
