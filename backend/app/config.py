from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Qdrant
    # - local embedded:  set qdrant_local_path (e.g. "./qdrant_db")
    # - self-hosted:     set qdrant_host + qdrant_port
    # - Qdrant Cloud:    set qdrant_host (cluster URL) + qdrant_api_key
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "research_papers"
    qdrant_contexts_collection: str = "rm_contexts"
    qdrant_sources_collection: str = "rm_sources"
    qdrant_history_collection: str = "rm_history"
    qdrant_local_path: str = ""
    qdrant_api_key: str = ""

    # LiteLLM
    litellm_base_url: str = "http://litellm:4000"
    litellm_api_key: str = "sk-researchmind-local"
    llm_model: str = "local-llm"

    # Embeddings
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Ingestion
    max_pdf_size_mb: int = 100
    request_timeout_sec: int = 60

    # Langfuse (leave empty to disable tracing)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"


settings = Settings()
