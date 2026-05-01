# Compatibility shim — import from new location.
from app.services.ingest.service import IngestionService  # noqa: F401

__all__ = ["IngestionService"]
