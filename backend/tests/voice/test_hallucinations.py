"""Unit tests for hallucination detection.  No audio fixtures needed."""
import pytest

from app.voice.hallucinations import is_hallucination, is_repetitive


# ── is_hallucination ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "thank you",
    "Thank you.",
    "Thanks for watching.",
    "Thanks for watching!",
    "Please subscribe.",
    "bye",
    "[music]",
    "(music)",
    "[silence]",
])
def test_known_hallucination(text):
    result, pattern = is_hallucination(text)
    assert result is True, f"Expected hallucination for {text!r}"
    assert pattern is not None


@pytest.mark.parametrize("text", [
    "I want to thank you for the help",
    "goodbye and thanks",
    "thank you very much for your detailed answer",
    "What is the capital of France?",
    "Tell me about RAG pipelines.",
])
def test_not_a_hallucination(text):
    result, _ = is_hallucination(text)
    assert result is False, f"False positive hallucination for {text!r}"


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "\n\t",
])
def test_empty_is_not_hallucination(text):
    # Empty text is handled by EMPTY gate decision, not hallucination detector
    result, _ = is_hallucination(text)
    assert result is False


# ── is_repetitive ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "thank you. thank you. thank you.",
    "yes yes yes yes",
    "the the the the",
])
def test_repetitive_detected(text):
    assert is_repetitive(text) is True, f"Expected repetitive for {text!r}"


@pytest.mark.parametrize("text", [
    "I want to thank you for the help",
    "yes I agree with that",
    "the quick brown fox jumps over the lazy dog",
])
def test_not_repetitive(text):
    assert is_repetitive(text) is False, f"False positive repetitive for {text!r}"
