"""Unit tests for ResearchAgent — LLM and Qdrant are fully mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.research_agent import ResearchAgent, _route_heuristic


def _hit(text="Context chunk about RAG.", source="doc.pdf", score=0.88):
    h = MagicMock()
    h.payload = {"text": text, "source": source, "source_type": "pdf"}
    h.score = score
    return h


# ── _route_heuristic (exhaustive) ─────────────────────────────────────────────

class TestRouteHeuristicTable:
    @pytest.mark.parametrize("q,ctx,expected", [
        ("",             None,     "CLARIFY"),
        ("  ",           None,     "CLARIFY"),
        ("yes",          None,     "CLARIFY"),
        ("ok sure",      None,     "CLARIFY"),
        ("What is RAG?", None,     "DIRECT"),
        ("Who is Turing?",None,    "DIRECT"),
        ("What is RAG?", "abc",    "SEARCH"),
        ("Explain transformer architecture in depth", None, "SEARCH"),
        ("Summarise my documents", "ctx-1",            "SEARCH"),
    ])
    def test_routing(self, q, ctx, expected):
        assert _route_heuristic(q, ctx) == expected


# ── ResearchAgent.run() ───────────────────────────────────────────────────────

class TestAgentRun:
    @pytest.fixture(autouse=True)
    def _mocks(self, mocker):
        mocker.patch("app.services.embedder.Embedder.embed_one", return_value=[0.0] * 384)
        mocker.patch(
            "app.services.vector_store.VectorStore.search_async",
            new_callable=AsyncMock,
            return_value=[_hit()],
        )
        mocker.patch(
            "app.agents.research_agent.LLMClient.complete",
            new_callable=AsyncMock,
            return_value="The answer is RAG.",
        )

    @pytest.mark.asyncio
    async def test_search_path_answer_and_sources(self):
        result = await ResearchAgent().run("Tell me about RAG", context_id="ctx-1")
        assert result["answer"] == "The answer is RAG."
        assert result["action_taken"] == "SEARCH"
        assert len(result["sources"]) == 1

    @pytest.mark.asyncio
    async def test_clarify_path_no_llm_call(self, mocker):
        spy = mocker.patch(
            "app.agents.research_agent.LLMClient.complete", new_callable=AsyncMock
        )
        result = await ResearchAgent().run("hi", context_id=None)
        assert result["action_taken"] == "CLARIFY"
        assert "niejasne" in result["answer"]
        spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_direct_path_skips_retrieve(self, mocker):
        search_spy = mocker.patch(
            "app.services.vector_store.VectorStore.search_async", new_callable=AsyncMock
        )
        result = await ResearchAgent().run("What is Python?", context_id=None)
        assert result["action_taken"] == "DIRECT"
        search_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_critic_scheduled_as_background_task(self, mocker):
        from fastapi import BackgroundTasks
        bg = BackgroundTasks()
        spy = mocker.spy(bg, "add_task")
        await ResearchAgent().run("Tell me about RAG", context_id="ctx-1", background_tasks=bg)
        spy.assert_called_once()

    @pytest.mark.asyncio
    async def test_result_has_required_keys(self):
        result = await ResearchAgent().run("Tell me about RAG", context_id="ctx-1")
        for key in ("question", "answer", "action_taken", "sources", "critique", "iterations"):
            assert key in result


# ── ResearchAgent.stream_run() ────────────────────────────────────────────────

class TestAgentStreamRun:
    @pytest.fixture(autouse=True)
    def _mocks(self, mocker):
        mocker.patch("app.services.embedder.Embedder.embed_one", return_value=[0.0] * 384)
        mocker.patch(
            "app.services.vector_store.VectorStore.search_async",
            new_callable=AsyncMock,
            return_value=[_hit()],
        )

        async def _fake_tokens(*args, **kwargs):
            yield "Part one. "
            yield "Part two."

        mocker.patch("app.agents.research_agent.LLMClient.stream", new=_fake_tokens)

    @pytest.mark.asyncio
    async def test_emits_chunk_and_done_events(self):
        events = [line async for line in ResearchAgent().stream_run("Explain the RAG architecture in depth", "ctx-1")]
        assert any('"chunk"' in e for e in events)
        assert any('"done"'  in e for e in events)

    @pytest.mark.asyncio
    async def test_done_event_full_answer(self):
        import json as _json
        done_line = None
        async for line in ResearchAgent().stream_run("Explain the RAG architecture in depth", "ctx-1"):
            if '"done"' in line:
                done_line = line
        assert done_line is not None
        done = _json.loads(done_line.removeprefix("data: ").strip())
        assert done["answer"] == "Part one. Part two."
        assert done["action_taken"] == "SEARCH"

    @pytest.mark.asyncio
    async def test_clarify_path_single_done_event(self):
        events = [line async for line in ResearchAgent().stream_run("hi", None)]
        done_events = [e for e in events if '"done"' in e]
        assert len(done_events) == 1
        assert "CLARIFY" in done_events[0]
