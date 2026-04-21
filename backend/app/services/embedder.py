from sentence_transformers import SentenceTransformer
from loguru import logger
from app.config import settings


class Embedder:
    _instance: "Embedder | None" = None

    def __new__(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            cls._instance.model = SentenceTransformer(settings.embedding_model)
        return cls._instance

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
