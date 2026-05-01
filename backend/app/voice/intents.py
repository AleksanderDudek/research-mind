"""Detect special-purpose utterances before they reach the LLM.

All three functions use normalised exact-match comparison against
language-specific phrase lists.  Exact matching is intentional:
  - "yes" → acknowledgment
  - "yes I think RAG is better" → NOT an acknowledgment  (full sentence)
  - "I cannot cancel the subscription" → NOT a cancel intent
  - "do not repeat yourself" → NOT a repeat request

Normalisation: lowercase, strip punctuation, collapse whitespace.
For an unknown language code the English list is used as fallback.
"""
from __future__ import annotations

import re

# ── Phrase lists ───────────────────────────────────────────────────────────────

_CANCEL: dict[str, list[str]] = {
    "en": ["cancel", "nevermind", "never mind", "scratch that", "abort", "stop"],
    "pl": ["anuluj", "nieważne", "cofnij", "zatrzymaj", "porzuć"],
}

_ACKNOWLEDGMENT: dict[str, list[str]] = {
    "en": ["yes", "yeah", "yep", "yup", "ok", "okay", "sure", "mhm", "uh huh",
           "correct", "right"],
    "pl": ["tak", "no tak", "okej", "ok", "dobrze", "zgadza się", "właśnie"],
}

_REPEAT: dict[str, list[str]] = {
    "en": ["say that again", "repeat", "repeat that", "what did you say",
           "pardon", "come again"],
    "pl": ["powtórz", "powtórz to", "co powiedziałeś", "słucham",
           "nie zrozumiałem"],
}

# ── Normalisation ─────────────────────────────────────────────────────────────

_STRIP_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_COLLAPSE_WS = re.compile(r"\s+")


def _normalise(text: str) -> str:
    text = text.lower().strip()
    text = _STRIP_PUNCT.sub("", text)
    return _COLLAPSE_WS.sub(" ", text).strip()


def _phrases_for(table: dict[str, list[str]], language: str) -> list[str]:
    """Return phrases for *language*, falling back to English."""
    lang_key = language.split("-")[0].lower()   # "pl-PL" → "pl"
    return table.get(lang_key, table.get("en", []))


def _exact_match(text: str, phrases: list[str]) -> bool:
    norm = _normalise(text)
    return any(_normalise(p) == norm for p in phrases)


# ── Public API ─────────────────────────────────────────────────────────────────

def is_cancel(text: str, language: str) -> bool:
    """True when the *entire* utterance is a cancel / abort intent.

    Embedded uses ("I cannot cancel the subscription") return False
    because the full normalised string does not match any phrase.
    """
    return _exact_match(text, _phrases_for(_CANCEL, language))


def is_acknowledgment(text: str, language: str) -> bool:
    """True when the utterance is a standalone confirmation (yes / ok / tak …).

    Longer sentences starting with "yes" ("yes I think …") return False.
    """
    return _exact_match(text, _phrases_for(_ACKNOWLEDGMENT, language))


def is_repeat_request(text: str, language: str) -> bool:
    """True when the user asks the assistant to repeat its last response."""
    return _exact_match(text, _phrases_for(_REPEAT, language))
