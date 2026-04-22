from typing import TypedDict, Annotated
import operator
import json
from langgraph.graph import StateGraph, END
from loguru import logger

from app.agents.prompts import ROUTER_PROMPT, ANSWER_PROMPT, CRITIC_PROMPT
from app.llm.client import LLMClient
from app.services.embedder import Embedder
from app.services.vector_store import VectorStore
from app.config import settings


def _observe(func):
    """Wrap with langfuse @observe when Langfuse is configured, else no-op."""
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse import observe
            return observe(name=func.__name__)(func)
        except ImportError:
            pass
    return func


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
    MAX_ITERATIONS = 2

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

        g.add_conditional_edges(
            "router",
            lambda s: s["action"],
            {"SEARCH": "retrieve", "CLARIFY": "clarify", "DIRECT": "generate"},
        )
        g.add_edge("retrieve", "generate")
        g.add_edge("generate", "critic")
        g.add_conditional_edges(
            "critic",
            self._after_critic,
            {"retry": "retrieve", "done": END},
        )
        g.add_edge("clarify", END)

        return g.compile()

    async def router_node(self, state: AgentState) -> AgentState:
        prompt = ROUTER_PROMPT.format(question=state["question"])
        response = await LLMClient.complete(prompt, name="router")
        action = response.strip().upper().split()[0] if response else "SEARCH"
        if action not in ("SEARCH", "CLARIFY", "DIRECT"):
            action = "SEARCH"
        logger.info(f"Router decision: {action}")
        return {**state, "action": action, "iteration": 0}

    def retrieve_node(self, state: AgentState) -> AgentState:
        vec = self.embedder.embed_one(state["question"])
        filters = {"context_id": state["context_id"]} if state.get("context_id") else None
        hits = self.store.search(vec, top_k=5, filters=filters)
        context = [
            {
                "text": h.payload.get("text"),
                "source": h.payload.get("source", "unknown"),
                "source_type": h.payload.get("source_type"),
                "score": h.score,
            }
            for h in hits
        ]
        logger.info(f"Retrieved {len(context)} chunks")
        return {**state, "context": context}

    async def answer_node(self, state: AgentState) -> AgentState:
        ctx = state.get("context", [])
        if not ctx:
            context_str = "(brak kontekstu — odpowiadasz z wiedzy ogólnej)"
        else:
            context_str = "\n\n".join(
                f"[{i+1}] Źródło: {c['source']}\n{c['text']}"
                for i, c in enumerate(ctx)
            )
        prompt = ANSWER_PROMPT.format(context=context_str, question=state["question"])
        answer = await LLMClient.complete(prompt, temperature=0.2, name="generate")
        return {**state, "answer": answer}

    async def critic_node(self, state: AgentState) -> AgentState:
        ctx = "\n\n".join(c["text"] for c in state.get("context", []))
        prompt = CRITIC_PROMPT.format(
            question=state["question"],
            answer=state["answer"],
            context=ctx,
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
        return {
            **state,
            "answer": "Twoje pytanie jest niejasne. Czy mógłbyś doprecyzować, czego dokładnie szukasz?",
        }

    def _after_critic(self, state: AgentState) -> str:
        score = state.get("critique", {}).get("score", 5)
        iteration = state.get("iteration", 0)
        if score < 3 and iteration < self.MAX_ITERATIONS:
            logger.info(f"Retry (iteration {iteration}, score {score})")
            return "retry"
        return "done"

    async def run(self, question: str, context_id: str | None = None) -> dict:
        initial_state: AgentState = {
            "question": question,
            "action": "",
            "context": [],
            "answer": "",
            "critique": {},
            "iteration": 0,
            "messages": [],
            "context_id": context_id,
        }
        final = await self.graph.ainvoke(initial_state)
        return {
            "question": question,
            "answer": final["answer"],
            "action_taken": final["action"],
            "sources": final.get("context", []),
            "critique": final.get("critique", {}),
            "iterations": final.get("iteration", 0),
        }
