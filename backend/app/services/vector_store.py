from qdrant_client import models
from qdrant_client.models import Distance, VectorParams, PointStruct
from loguru import logger
from app.config import settings
from app.services._qdrant import get_client


class VectorStore:
    _instance: "VectorStore | None" = None

    def __new__(cls) -> "VectorStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = get_client()
            cls._instance.collection = settings.qdrant_collection
            cls._instance._ensure_collection()
        return cls._instance

    def _ensure_collection(self) -> None:
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection not in collections:
            logger.info(f"Creating collection: {self.collection}")
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            for field in ("source_type", "document_id", "context_id"):
                self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

    def list_documents(self, context_id: str | None = None) -> list[dict]:
        seen: set[str] = set()
        results: list[dict] = []
        offset = None
        scroll_filter = None
        if context_id is not None:
            scroll_filter = models.Filter(must=[
                models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id))
            ])
        while True:
            records, offset = self.client.scroll(
                collection_name=self.collection,
                limit=100,
                offset=offset,
                scroll_filter=scroll_filter,
                with_payload=True,
                with_vectors=False,
            )
            for r in records:
                doc_id = r.payload.get("document_id", "")
                if doc_id and doc_id not in seen:
                    seen.add(doc_id)
                    results.append({
                        "document_id": doc_id,
                        "title": r.payload.get("title") or r.payload.get("source", ""),
                        "source_type": r.payload.get("source_type", ""),
                        "ingested_at": r.payload.get("ingested_at", ""),
                        "context_id": r.payload.get("context_id"),
                    })
            if offset is None:
                break
        return results

    def upsert(self, points: list[PointStruct]) -> None:
        self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, str] | None = None,
    ) -> list:
        conditions = []
        if filters:
            conditions = [
                models.FieldCondition(key=k, match=models.MatchValue(value=v))
                for k, v in filters.items()
            ]
        query_filter = models.Filter(must=conditions) if conditions else None

        return self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )

    def delete_by_document(self, document_id: str, context_id: str | None = None) -> None:
        must = [models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        if context_id:
            must.append(models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id)))
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(filter=models.Filter(must=must)),
        )
        logger.info(f"Deleted vectors for document {document_id!r}")

    def delete_by_context(self, context_id: str) -> None:
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(key="context_id", match=models.MatchValue(value=context_id))
                ])
            ),
        )
        logger.info(f"Deleted all vectors for context {context_id!r}")
