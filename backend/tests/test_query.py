"""Integration tests for /query/* — search, ask, streaming, transcription, cache."""
import json
from unittest.mock import AsyncMock

from tests.conftest import LONG_TEXT

_FAKE = {
    "question":     "What is RAG?",
    "answer":       "RAG combines retrieval with generation.",
    "action_taken": "SEARCH",
    "sources":      [{"text": "ctx", "source": "doc.pdf", "source_type": "pdf", "score": 0.9}],
    "critique":     {"score": 4},
    "iterations":   0,
}


# ── /query/documents ──────────────────────────────────────────────────────────

def test_list_documents_shape(client):
    r = client.get("/query/documents")
    assert r.status_code == 200
    data = r.json()
    assert "documents" in data
    assert "count" in data


def test_list_documents_context_filter(client, seeded_context):
    r = client.get(f"/query/documents?context_id={seeded_context}")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(d["context_id"] == seeded_context for d in data["documents"])


# ── /query/search ─────────────────────────────────────────────────────────────

def test_search_returns_list(client, seeded_context):
    r = client.post("/query/search", json={
        "question": "dense passage retrieval", "top_k": 3, "context_id": seeded_context,
    })
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["results"], list)
    assert len(data["results"]) <= 3


def test_search_result_has_required_fields(client, seeded_context):
    r = client.post("/query/search", json={"question": "RAG", "context_id": seeded_context})
    assert r.status_code == 200
    for hit in r.json()["results"]:
        assert "score" in hit
        assert "text" in hit
        assert "source_type" in hit


def test_search_source_type_filter(client, seeded_context):
    r = client.post("/query/search", json={
        "question": "retrieval", "top_k": 5,
        "source_type": "text", "context_id": seeded_context,
    })
    assert r.status_code == 200
    for hit in r.json()["results"]:
        assert hit["source_type"] == "text"


def test_search_without_context(client):
    r = client.post("/query/search", json={"question": "any query", "top_k": 2})
    assert r.status_code == 200


# ── /query/ask ────────────────────────────────────────────────────────────────

def test_ask_returns_answer(client, context_id, mocker):
    mocker.patch(
        "app.agents.research_agent.ResearchAgent.run",
        new_callable=AsyncMock,
        return_value=_FAKE,
    )
    r = client.post("/query/ask", json={"question": "What is RAG?", "context_id": context_id})
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == _FAKE["answer"]
    assert "sources" in data
    assert "action_taken" in data


def test_ask_cache_hit_skips_agent(client, context_id, mocker):
    """Second identical call must hit the cache — agent.run called exactly once."""
    mock_run = mocker.patch(
        "app.agents.research_agent.ResearchAgent.run",
        new_callable=AsyncMock,
        return_value=_FAKE,
    )
    q = "unique cache test question xyzzy42"
    r1 = client.post("/query/ask", json={"question": q, "context_id": context_id})
    r2 = client.post("/query/ask", json={"question": q, "context_id": context_id})
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()
    assert mock_run.call_count == 1, "agent.run must only be called once (second is a cache hit)"


def test_ask_cache_miss_on_different_question(client, context_id, mocker):
    mock_run = mocker.patch(
        "app.agents.research_agent.ResearchAgent.run",
        new_callable=AsyncMock,
        return_value=_FAKE,
    )
    client.post("/query/ask", json={"question": "distinct question A99", "context_id": context_id})
    client.post("/query/ask", json={"question": "distinct question B99", "context_id": context_id})
    assert mock_run.call_count == 2


# ── /query/ask/stream ─────────────────────────────────────────────────────────

def test_stream_content_type(client, context_id, mocker):
    async def _gen(self, question, context_id=None):
        yield 'data: {"type":"chunk","text":"Hi"}\n\n'
        yield 'data: {"type":"done","answer":"Hi","sources":[],"action_taken":"SEARCH"}\n\n'

    from app.agents.research_agent import ResearchAgent
    mocker.patch.object(ResearchAgent, "stream_run", new=_gen)
    r = client.post("/query/ask/stream", json={"question": "stream test q1", "context_id": context_id})
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]


def test_stream_contains_chunk_and_done(client, context_id, mocker):
    async def _gen(self, question, context_id=None):
        yield 'data: {"type":"chunk","text":"word"}\n\n'
        yield 'data: {"type":"done","answer":"word","sources":[],"action_taken":"DIRECT"}\n\n'

    from app.agents.research_agent import ResearchAgent
    mocker.patch.object(ResearchAgent, "stream_run", new=_gen)
    r = client.post("/query/ask/stream", json={"question": "stream test q2", "context_id": context_id})
    body = r.text
    assert '"chunk"' in body
    assert '"done"' in body


def test_stream_cache_replay_skips_stream_run(client, context_id, mocker):
    """If /ask already populated the cache, /ask/stream replays without calling stream_run."""
    mocker.patch(
        "app.agents.research_agent.ResearchAgent.run",
        new_callable=AsyncMock,
        return_value=_FAKE,
    )
    mock_stream = mocker.patch("app.agents.research_agent.ResearchAgent.stream_run")
    unique_q = "cached stream replay test q777"
    # Populate cache via /ask
    client.post("/query/ask", json={"question": unique_q, "context_id": context_id})
    # /ask/stream for same question should replay, not call stream_run
    r = client.post("/query/ask/stream", json={"question": unique_q, "context_id": context_id})
    assert r.status_code == 200
    mock_stream.assert_not_called()


# ── /query/transcribe ─────────────────────────────────────────────────────────

def test_transcribe_returns_text(client, mocker):
    mocker.patch("app.services.transcriber.Transcriber.transcribe",
                 return_value="Hello world transcription.")
    r = client.post(
        "/query/transcribe",
        files={"file": ("voice.webm", b"fake audio", "audio/webm")},
    )
    assert r.status_code == 200
    assert r.json()["text"] == "Hello world transcription."


def test_transcribe_empty_file_rejected(client):
    r = client.post(
        "/query/transcribe",
        files={"file": ("empty.webm", b"", "audio/webm")},
    )
    assert r.status_code == 400


def test_transcribe_language_param_forwarded(client, mocker):
    mock_transcribe = mocker.patch(
        "app.services.transcriber.Transcriber.transcribe", return_value="Cześć"
    )
    client.post(
        "/query/transcribe",
        files={"file": ("voice.webm", b"fake audio", "audio/webm")},
        data={"language": "pl"},
    )
    _, kwargs = mock_transcribe.call_args
    assert kwargs.get("language") == "pl"
