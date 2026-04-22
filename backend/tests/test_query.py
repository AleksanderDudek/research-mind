import pytest
from unittest.mock import AsyncMock

LONG_TEXT = "Dense passage retrieval uses dual-encoder models for search. " * 10

FAKE_AGENT_RESPONSE = {
    "question": "What is RAG?",
    "answer": "RAG combines retrieval with generation.",
    "action_taken": "SEARCH",
    "sources": [{"text": "Some context", "source": "test", "score": 0.9}],
    "critique": {"score": 4, "reasoning": "Good answer"},
    "iterations": 1,
}


@pytest.fixture(scope="module", autouse=True)
def seed_document(client):
    """Index one document so query tests have data to work with."""
    client.post("/ingest/raw-text", json={"text": LONG_TEXT, "title": "Seed"})


def test_list_documents(client):
    r = client.get("/query/documents")
    assert r.status_code == 200
    data = r.json()
    assert "documents" in data
    assert "count" in data


def test_semantic_search(client):
    r = client.post(
        "/query/search",
        json={"question": "dense passage retrieval", "top_k": 3},
    )
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_semantic_search_with_filter(client):
    r = client.post(
        "/query/search",
        json={"question": "retrieval", "top_k": 5, "source_type": "text"},
    )
    assert r.status_code == 200


def test_ask_agent(client, mocker):
    mocker.patch(
        "app.agents.research_agent.ResearchAgent.run",
        new_callable=AsyncMock,
        return_value=FAKE_AGENT_RESPONSE,
    )
    r = client.post("/query/ask", json={"question": "What is RAG?"})
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == FAKE_AGENT_RESPONSE["answer"]
    assert "sources" in data
