"""Research agent — LangGraph-based RAG pipeline.

Performance improvements vs original:
- Router replaced with O(1) heuristic (no LLM call) — saves ~400 ms per query.
- Critic moved to BackgroundTask so it never blocks the response.
- retrieve_node is now async: embedding in thread pool + async Qdrant search.
- stream_run also uses heuristic router and async retrieval.
"""
from __future__ import annotations

import asyncio
import json
import operator
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, AsyncGenerator, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger

from app.agents.prompts import ANSWER_PROMPT, CRITIC_PROMPT
from app.config import settings
from app.llm.client import LLMClient
from app.services.embedder import Embedder
from app.services.vector_store import VectorStore

# Shared executor for CPU-bound embedding calls
_embed_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embedder")


def _observe(func):
    """Wrap with langfuse @observe when Langfuse is configured, else no-op."""
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse import observe
            return observe(name=func.__name__)(func)
        except ImportError:
            pass
    return func


_CLARIFY_MSG = "Twoje pytanie jest niejasne. Czy mógłbyś doprecyzować, czego dokładnie szukasz?"


def _route_heuristic(question: str, context_id: str | None) -> str:
    """Classify routing intent without an LLM call — O(1).

    Returns SEARCH (default), CLARIFY, or DIRECT.
    Replaces the LLM-based router_node, saving ~400 ms per query.
    """
    q = question.strip()
    if not q:
        return "CLARIFY"
    words = q.split()
    # Very short, no punctuation — likely incomplete input
    if len(words) <= 2 and not any(c in q for c in "?!"):
        return "CLARIFY"
    # Simple factual question with no context — answer from general knowledge
    direct_starters = ("what is ", "who is ", "when did ", "define ", "hello", "hi ")
    if not context_id and any(q.lower().startswith(s) for s in direct_starters):
        return "DIRECT"
    return "SEARCH"


class AgentState(TypedDict):
    question: str
    action: str
    context: list[dict]
    answer: str
    critique: dict
    iteration: int
    messages: Annotated[list, operator.add]
    context_id: str | None


class ResearchAgent:
    MAX_ITERATIONS = 1

    def __init__(self) -> None:
        self.embedder = Embedder()
        self.store = VectorStore()
        self.graph = self._build_graph()

    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("router", self.router_node)
        g.add_node("retrieve", self.retrieve_node)
        g.add_node("generate", self.answer_node)
        g.add_node("critic", self.critic_node)
        g.add_node("clarify", self.clarify_node)
        g.set_entry_point("router")
        g.add_conditional_edges("router", lambda s: s["action"],
                                {"SEARCH": "retrieve", "CLARIFY": "clarify", "DIRECT": "generate"})
        g.add_edge("retrieve", "generate")
        g.add_edge("generate", "critic")
        g.add_conditional_edges("critic", self._after_critic, {"retry": "retrieve", "done": END})
        g.add_edge("clarify", END)
        return g.compile()

    # ── Nodes ──────────────────────────────────────────────────────────────────

    def router_node(self, state: AgentState) -> AgentState:
        """Heuristic router — no LLM call."""
        action = _route_heuristic(state["question"], state.get("context_id"))
        logger.info(f"Router (heuristic): {action}")
        return {**state, "action": action, "iteration": 0}

    async def retrieve_node(self, state: AgentState) -> AgentState:
        """Async retrieval: embedding in thread pool + async Qdrant search."""
        loop = asyncio.get_event_loop()
        vec = await loop.run_in_executor(_embed_executor, self.embedder.embed_one, state["question"])
        filters = {"context_id": state["context_id"]} if state.get("context_id") else None
        hits = await self.store.search_async(vec, top_k=5, filters=filters)
        context = [
            {
                "text":        h.payload.get("text"),
                "source":      h.payload.get("source", "unknown"),
                "source_type": h.payload.get("source_type"),
                "score":       h.score,
            }
            for h in hits
        ]
        logger.info(f"Retrieved {len(context)} chunks")
        return {**state, "context": context}

    async def answer_node(self, state: AgentState) -> AgentState:
        ctx = state.get("context", [])
        context_str = (
            "\n\n".join(f"[{i+1}] Źródło: {c['source']}\n{c['text']}" for i, c in enumerate(ctx))
            if ctx else "(brak kontekstu — odpowiadasz z wiedzy ogólnej)"
        )
        prompt = ANSWER_PROMPT.format(context=context_str, question=state["question"])
        answer = await LLMClient.complete(prompt, temperature=0.2, name="generate")
        return {**state, "answer": answer}

    async def critic_node(self, state: AgentState) -> AgentState:
        ctx = "\n\n".join(c["text"] for c in state.get("context", []))
        prompt = CRITIC_PROMPT.format(
            question=state["question"], answer=state["answer"], context=ctx,
        )
        raw = await LLMClient.complete(prompt, name="critic")
        try:
            cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
            critique = json.loads(cleaned)
        except Exception:
            logger.warning(f"Critic parsing failed, raw: {raw}")
            critique = {"score": 4, "reasoning": "parse_failed", "retry_query": None}
        return {**state, "critique": critique, "iteration": state.get("iteration", 0) + 1}

    def clarify_node(self, state: AgentState) -> AgentState:
        return {**state, "answer": _CLARIFY_MSG}

    def _after_critic(self, state: AgentState) -> str:
        score = state.get("critique", {}).get("score", 5)
        iteration = state.get("iteration", 0)
        if score < 3 and iteration < self.MAX_ITERATIONS:
            logger.info(f"Retry (iteration {iteration}, score {score})")
            return "retry"
        return "done"

    # ── Background critic ──────────────────────────────────────────────────────

    async def _run_critic_bg(self, state: dict) -> None:
        """Run critic asynchronously after the response has been sent."""
        try:
            result = await self.critic_node(AgentState(**state))
            score = result.get("critique", {}).get("score", "?")
            logger.info(f"[bg critic] score={score}")
        except Exception as exc:
            logger.warning(f"[bg critic] failed: {exc}")

    # ── Public API ─────────────────────────────────────────────────────────────

    async def run(self, question: str, context_id: str | None = None, background_tasks=None) -> dict:
        """Run the agent. Critic is off the critical path when background_tasks is provided."""
        action = _route_heuristic(question, context_id)
        logger.info(f"Route: {action}")

        state: AgentState = {
            "question": question,
            "action":   action,
            "context":  [],
            "answer":   "",
            "critique": {},
            "iteration": 0,
            "messages": [],
            "context_id": context_id,
        }

        if action == "CLARIFY":
            return {
                "question":     question,
                "answer":       _CLARIFY_MSG,
                "action_taken": "CLARIFY",
                "sources":      [],
                "critique":     {},
                "iterations":   0,
            }

        if action == "SEARCH":
            state = await self.retrieve_node(state)

        state = await self.answer_node(state)

        if background_tasks is not None:
            # Schedule critic after the response — does not block
            background_tasks.add_task(self._run_critic_bg, dict(state))
            critique = {}
        else:
            state = await self.critic_node(state)
            critique = state.get("critique", {})

        return {
            "question":     question,
            "answer":       state["answer"],
            "action_taken": action,
            "sources":      state.get("context", []),
            "critique":     critique,
            "iterations":   state.get("iteration", 0),
        }

    async def stream_run(
        self, question: str, context_id: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream the agent response as SSE lines. Critic skipped; router uses heuristic."""
        action = _route_heuristic(question, context_id)
        logger.info(f"[stream] Route: {action}")

        if action == "CLARIFY":
            msg = _CLARIFY_MSG
            yield f'data: {json.dumps({"type": "chunk", "text": msg})}\n\n'
            yield f'data: {json.dumps({"type": "done", "answer": msg, "sources": [], "action_taken": "CLARIFY"})}\n\n'
            return

        context: list[dict] = []
        if action == "SEARCH":
            loop = asyncio.get_event_loop()
            vec = await loop.run_in_executor(_embed_executor, self.embedder.embed_one, question)
            filters = {"context_id": context_id} if context_id else None
            hits = await self.store.search_async(vec, top_k=5, filters=filters)
            context = [
                {
                    "text":        h.payload.get("text"),
                    "source":      h.payload.get("source", "unknown"),
                    "source_type": h.payload.get("source_type"),
                    "score":       h.score,
                }
                for h in hits
            ]
            logger.info(f"[stream] Retrieved {len(context)} chunks")

        ctx_str = (
            "\n\n".join(f"[{i+1}] Źródło: {c['source']}\n{c['text']}" for i, c in enumerate(context))
            if context else "(brak kontekstu — odpowiadasz z wiedzy ogólnej)"
        )

        chunks: list[str] = []
        async for token in LLMClient.stream(
            ANSWER_PROMPT.format(context=ctx_str, question=question),
            temperature=0.2,
            name="generate",
        ):
            chunks.append(token)
            yield f'data: {json.dumps({"type": "chunk", "text": token})}\n\n'

        full_answer = "".join(chunks)
        yield f'data: {json.dumps({"type": "done", "answer": full_answer, "sources": context, "action_taken": action})}\n\n'
