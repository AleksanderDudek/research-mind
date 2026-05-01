"""Whisper hallucination blocklist and detector.

Whisper produces well-known artefacts when fed silence or near-silence,
especially with smaller models ("thank you", "Thanks for watching!", etc.).
These must be caught before the quality gate sends garbage to the LLM.

Two complementary checks:
1. Pattern matching against a curated blocklist (regex, case-insensitive).
2. Repetition detection: any n-gram (n=1..5) that repeats >= min_repeats
   times *consecutively* is flagged — catches "thank you. thank you. thank you."
   and similar loops that don't appear in the static blocklist.
"""
from __future__ import annotations

import re

# ── Blocklist ─────────────────────────────────────────────────────────────────

HALLUCINATION_PATTERNS: list[str] = [
    r"^thanks? for watching[.!]?$",
    r"^thank you\.?$",
    r"^thank you for watching\.?$",
    r"^subscribe to my channel\.?$",
    r"^please subscribe\.?$",
    r"^bye\.?$",
    r"^you$",
    r"^\.+$",
    r"^\[music\]$",
    r"^\(music\)$",
    r"^\[silence\]$",
    r"^\[blank_audio\]$",
    r"^\[inaudible\]$",
    r"^\(applause\)$",
    r"^\[noise\]$",
    r"^\[laughter\]$",
]

_COMPILED: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in HALLUCINATION_PATTERNS
]

# Punctuation stripper for normalisation
_STRIP_PUNCT = re.compile(r"[^\w\s]")
_COLLAPSE_WS = re.compile(r"\s+")


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = _STRIP_PUNCT.sub("", text)
    return _COLLAPSE_WS.sub(" ", text).strip()


# ── Public API ─────────────────────────────────────────────────────────────────

def is_hallucination(text: str) -> tuple[bool, str | None]:
    """Return (True, matched_pattern_string) if text is a known hallucination.

    Matches against the original text (preserving punctuation) to catch
    "Thanks for watching!" which normalises to "thanks for watching" but the
    regex already handles the trailing punctuation via `\.?`.

    Empty / whitespace-only text is *not* a hallucination — that is the
    EMPTY gate decision and handled upstream.
    """
    if not text.strip():
        return False, None

    for pattern, compiled in zip(HALLUCINATION_PATTERNS, _COMPILED):
        if compiled.match(text.strip()):
            return True, pattern

    return False, None


def is_repetitive(text: str, min_repeats: int = 3) -> bool:
    """True when any n-gram (n=1..5) repeats >= min_repeats times consecutively.

    Examples that return True:
        "thank you. thank you. thank you."   — bigram repeats 3×
        "yes yes yes yes"                    — unigram repeats 4×
        "the the the the"                    — unigram repeats 4×

    Examples that return False:
        "I want to thank you for the help"   — no consecutive repetition
        "yes I agree with that"              — "yes" appears once
    """
    tokens = _normalise(text).split()
    if not tokens:
        return False

    for n in range(1, 6):
        if _has_consecutive_ngram(tokens, n, min_repeats):
            return True

    return False


def _has_consecutive_ngram(tokens: list[str], n: int, min_repeats: int) -> bool:
    """Return True when any n-gram repeats >= min_repeats times in sequence.

    Uses non-overlapping (stride-n) chunks so that "A B A B A B" is correctly
    seen as three consecutive repetitions of the bigram "A B" rather than
    alternating bigrams "(A,B), (B,A), (A,B), ..." which would never be adjacent.
    """
    if len(tokens) < n * min_repeats:
        return False

    # Non-overlapping chunks of size n
    chunks = [
        tuple(tokens[i : i + n])
        for i in range(0, len(tokens) - n + 1, n)
    ]

    consecutive = 1
    for i in range(1, len(chunks)):
        if chunks[i] == chunks[i - 1]:
            consecutive += 1
            if consecutive >= min_repeats:
                return True
        else:
            consecutive = 1

    return False
