from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct
from loguru import logger
from app.config import settings


class VectorStore:
    _instance: "VectorStore | None" = None

    def __new__(cls) -> "VectorStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if settings.qdrant_local_path:
                # Embedded mode — no server required, data persisted to disk
                cls._instance.client = QdrantClient(path=settings.qdrant_local_path)
            else:
                cls._instance.client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                )
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
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="source_type",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

    def list_documents(self) -> list[dict]:
        seen: set[str] = set()
        results: list[dict] = []
        offset = None
        while True:
            records, offset = self.client.scroll(
                collection_name=self.collection,
                limit=100,
                offset=offset,
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
        query_filter = None
        if filters:
            conditions = [
                models.FieldCondition(key=k, match=models.MatchValue(value=v))
                for k, v in filters.items()
            ]
            query_filter = models.Filter(must=conditions)

        return self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )
