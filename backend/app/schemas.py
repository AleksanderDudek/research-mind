"""Pydantic response models shared across routers."""
from pydantic import BaseModel


class IngestionResult(BaseModel):
    document_id: str
    chunks_ingested: int
    source_type: str
    context_id: str
    metadata: dict = {}


class TranscribeResult(BaseModel):
    text: str


class HealthResponse(BaseModel):
    status: str
