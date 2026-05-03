"""Unit tests for _route_heuristic() and _cache_key() — pure functions, no I/O."""
import pytest

from app.agents.research_agent import _route_heuristic
from app.routers.query import _cache_key


class TestRouteHeuristic:
    # ── CLARIFY ───────────────────────────────────────────────────────────────

    def test_empty_string_is_clarify(self):
        assert _route_heuristic("", None) == "CLARIFY"

    def test_whitespace_only_is_clarify(self):
        assert _route_heuristic("   \t", None) == "CLARIFY"

    def test_single_word_no_punctuation_is_clarify(self):
        assert _route_heuristic("hello", None) == "CLARIFY"

    def test_hello_is_clarify_not_direct(self):
        # "hi" / "hello" start with a direct-starter prefix but are ≤2 words
        # so the CLARIFY guard fires first
        assert _route_heuristic("hi", None) == "CLARIFY"
        assert _route_heuristic("hello there", None) == "CLARIFY"

    def test_two_words_no_punctuation_is_clarify(self):
        assert _route_heuristic("ok sure", None) == "CLARIFY"

    # ── DIRECT (no context_id + known starters) ───────────────────────────────

    @pytest.mark.parametrize("question", [
        "What is RAG?",
        "What is the capital of France?",
        "Who is Alan Turing?",
        "When did World War 2 end?",
        "Define retrieval augmented generation",


    ])
    def test_direct_starters_without_context(self, question):
        result = _route_heuristic(question, None)
        assert result == "DIRECT", f"Expected DIRECT for {question!r}, got {result!r}"

    def test_direct_starter_with_context_id_becomes_search(self):
        """context_id always forces retrieval even for direct-style questions."""
        assert _route_heuristic("What is RAG?", "ctx-abc") == "SEARCH"

    # ── SEARCH (default) ──────────────────────────────────────────────────────

    def test_long_question_without_context_is_search(self):
        assert _route_heuristic("Explain the transformer architecture in depth", None) == "SEARCH"

    def test_question_with_context_id_is_search(self):
        assert _route_heuristic("Summarise my documents", "ctx-123") == "SEARCH"

    def test_question_mark_prevents_two_word_clarify(self):
        result = _route_heuristic("Yes?", None)
        assert result in ("SEARCH", "DIRECT")  # not CLARIFY

    def test_exclamation_prevents_two_word_clarify(self):
        result = _route_heuristic("Go!", None)
        assert result in ("SEARCH", "DIRECT")

    # ── Exhaustive value check ────────────────────────────────────────────────

    @pytest.mark.parametrize("q,ctx", [
        ("", None), ("  ", "abc"), ("yes", None), ("tell me everything about RAG", "ctx"),
        ("What is Python?", None), ("What is Python?", "ctx"),
    ])
    def test_always_returns_valid_action(self, q, ctx):
        assert _route_heuristic(q, ctx) in ("SEARCH", "CLARIFY", "DIRECT")


class TestCacheKey:
    def test_same_inputs_give_same_key(self):
        assert _cache_key("hello", "ctx1") == _cache_key("hello", "ctx1")

    def test_different_question_gives_different_key(self):
        assert _cache_key("hello", "ctx1") != _cache_key("world", "ctx1")

    def test_different_context_gives_different_key(self):
        assert _cache_key("hello", "ctx1") != _cache_key("hello", "ctx2")

    def test_none_context_differs_from_real_context(self):
        assert _cache_key("hello", None) != _cache_key("hello", "some-id")

    def test_none_context_is_stable(self):
        assert _cache_key("test", None) == _cache_key("test", None)

    def test_returns_hex_sha256(self):
        key = _cache_key("anything", "ctx")
        assert isinstance(key, str)
        assert len(key) == 64           # SHA-256 → 32 bytes → 64 hex chars
        int(key, 16)                    # must be valid hex
