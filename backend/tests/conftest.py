import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Must be set before any app module is imported so pydantic-settings picks them up.
_QDRANT_DIR = tempfile.mkdtemp(prefix="rm_test_qdrant_")
os.environ.setdefault("QDRANT_LOCAL_PATH", _QDRANT_DIR)
os.environ.setdefault("QDRANT_API_KEY", "")
os.environ.setdefault("LITELLM_BASE_URL", "http://localhost:11434")
os.environ.setdefault("LITELLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
os.environ.setdefault("EMBEDDING_DIM", "384")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "")


@pytest.fixture(scope="session")
def client():
    from app.main import app  # import after env vars are set
    with TestClient(app) as c:
        yield c
