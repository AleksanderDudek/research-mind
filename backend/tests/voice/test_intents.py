"""Unit tests for intent detection — no audio fixtures needed."""
import pytest

from app.voice.intents import is_acknowledgment, is_cancel, is_repeat_request


# ── Cancel ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,lang", [
    ("cancel", "en"),
    ("nevermind", "en"),
    ("never mind", "en"),
    ("scratch that", "en"),
    ("anuluj", "pl"),
    ("nieważne", "pl"),
])
def test_cancel_detected(text, lang):
    assert is_cancel(text, lang) is True, f"cancel not detected: {text!r} ({lang})"


@pytest.mark.parametrize("text,lang", [
    ("what is the capital of France?", "en"),
    ("I cannot cancel the subscription", "en"),  # "cancel" in context
    ("tell me about RAG", "pl"),
])
def test_cancel_not_false_positive(text, lang):
    assert is_cancel(text, lang) is False


# ── Acknowledgment ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,lang", [
    ("yes", "en"),
    ("yeah", "en"),
    ("ok", "en"),
    ("okay", "en"),
    ("mhm", "en"),
    ("tak", "pl"),
    ("dobrze", "pl"),
    ("okej", "pl"),
])
def test_ack_detected(text, lang):
    assert is_acknowledgment(text, lang) is True, f"ack not detected: {text!r} ({lang})"


@pytest.mark.parametrize("text,lang", [
    ("yes I think RAG is better", "en"),   # "yes" but not standalone
    ("okay so tell me more about that topic", "en"),
])
def test_ack_not_false_positive(text, lang):
    assert is_acknowledgment(text, lang) is False


# ── Repeat request ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,lang", [
    ("say that again", "en"),
    ("repeat", "en"),
    ("repeat that", "en"),
    ("pardon", "en"),
    ("powtórz", "pl"),
    ("powtórz to", "pl"),
])
def test_repeat_detected(text, lang):
    assert is_repeat_request(text, lang) is True


@pytest.mark.parametrize("text,lang", [
    ("do not repeat yourself", "en"),
    ("I repeat, what is the answer?", "en"),
])
def test_repeat_not_false_positive(text, lang):
    assert is_repeat_request(text, lang) is False
