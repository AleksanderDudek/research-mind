"""Transcription quality classifier: heuristics + optional LLM arbiter.

Rules, applied in strict order
-------------------------------
1. EMPTY        — text is blank after stripping.
2. HALLUCINATION — matches blocklist OR is_repetitive.
3. LIKELY_NOISE  — ANY of: all-silent segments, out-of-range word rate,
                   all-bad logprobs.
4. LOW_CONFIDENCE — borderline logprob / no_speech_prob / very short clip.
5. VALID

When the heuristic yields LOW_CONFIDENCE and llm_arbiter_enabled is True,
evaluate_with_arbiter() calls _llm_arbiter() which may promote to VALID or
demote to LIKELY_NOISE.  On any failure the heuristic result is kept.
"""
from __future__ import annotations

import json

from loguru import logger
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential

from app.voice.hallucinations import is_hallucination, is_repetitive
from app.voice.schemas import GateDecision, GateResult, TranscriptionResult
from app.voice.settings import voice_settings

_ARBITER_PROMPT = """\
You are a transcription quality classifier. Given a transcription from an \
automatic speech recognition system, decide whether it is a coherent message \
from a user OR likely noise/garbled audio.

Transcription: "{text}"
Audio duration: {duration_s}s
Language: {language}

Respond with JSON only: {{"coherent": true|false, "reason": "<short>"}}
A transcription is coherent if it could plausibly be something a person said \
to an assistant, even if short or grammatically loose. It is not coherent if \
it is gibberish, a fragment of unrelated speech, or a known ASR artifact.\
"""


# ── Aggregate helpers ─────────────────────────────────────────────────────────

def _mean_logprob(result: TranscriptionResult) -> float:
    segs = result.segments
    return sum(s.avg_logprob for s in segs) / len(segs) if segs else float("-inf")


def _mean_no_speech(result: TranscriptionResult) -> float:
    segs = result.segments
    return sum(s.no_speech_prob for s in segs) / len(segs) if segs else 1.0


# ── Heuristic classifier (synchronous, no I/O) ───────────────────────────────

def evaluate(result: TranscriptionResult) -> GateResult:
    """Apply heuristic rules and return a GateResult — no network calls."""
    s    = voice_settings
    text = result.text.strip()
    segs = result.segments

    # Rule 1: EMPTY
    if not text:
        logger.debug("Gate → EMPTY")
        return GateResult(
            decision=GateDecision.EMPTY,
            confidence=1.0,
            reasons=["transcript is empty after stripping"],
        )

    # Rule 2: HALLUCINATION
    hall, pattern = is_hallucination(text)
    if hall:
        logger.debug(f"Gate → HALLUCINATION: blocklist {pattern!r}")
        return GateResult(
            decision=GateDecision.HALLUCINATION,
            confidence=1.0,
            reasons=[f"known Whisper artefact (pattern: {pattern!r})"],
        )
    if is_repetitive(text):
        logger.debug("Gate → HALLUCINATION: repetition")
        return GateResult(
            decision=GateDecision.HALLUCINATION,
            confidence=0.95,
            reasons=["repetitive n-gram loop"],
        )

    # Aggregate scores for rules 3 & 4
    mean_lp  = _mean_logprob(result)
    mean_nsp = _mean_no_speech(result)
    wps      = result.words_per_second

    # Rule 3: LIKELY_NOISE
    noise_reasons: list[str] = []
    if segs and all(seg.no_speech_prob > s.no_speech_prob_threshold for seg in segs):
        noise_reasons.append(
            f"all segments no_speech_prob > {s.no_speech_prob_threshold} "
            f"(mean={mean_nsp:.3f})"
        )
    if wps < s.min_words_per_second or wps > s.max_words_per_second:
        noise_reasons.append(
            f"words_per_second={wps:.2f} outside "
            f"[{s.min_words_per_second}, {s.max_words_per_second}]"
        )
    if segs and all(seg.avg_logprob < s.avg_logprob_threshold for seg in segs):
        noise_reasons.append(
            f"all segments avg_logprob < {s.avg_logprob_threshold} "
            f"(mean={mean_lp:.3f})"
        )
    if noise_reasons:
        logger.debug(f"Gate → LIKELY_NOISE: {noise_reasons}")
        return GateResult(
            decision=GateDecision.LIKELY_NOISE,
            confidence=0.85,
            reasons=noise_reasons,
        )

    # Rule 4: LOW_CONFIDENCE
    lc_reasons: list[str] = []
    if s.avg_logprob_threshold < mean_lp < s.low_confidence_logprob:
        lc_reasons.append(
            f"avg_logprob={mean_lp:.3f} in borderline range "
            f"({s.avg_logprob_threshold}, {s.low_confidence_logprob})"
        )
    if 0.4 < mean_nsp < s.no_speech_prob_threshold:
        lc_reasons.append(
            f"no_speech_prob={mean_nsp:.3f} elevated"
        )
    if result.word_count <= 2 and mean_lp < s.low_confidence_logprob:
        lc_reasons.append(
            f"short utterance ({result.word_count} word(s)) "
            f"with avg_logprob={mean_lp:.3f}"
        )
    if lc_reasons:
        logger.debug(f"Gate → LOW_CONFIDENCE: {lc_reasons}")
        return GateResult(
            decision=GateDecision.LOW_CONFIDENCE,
            confidence=0.45,
            reasons=lc_reasons,
            suggested_confirmation=f'Did you say "{text}"?',
        )

    # Rule 5: VALID
    lc_gap     = abs(s.low_confidence_logprob)
    above_lc   = mean_lp - s.low_confidence_logprob
    confidence = min(1.0, 0.8 + 0.2 * min(1.0, above_lc / lc_gap))
    logger.debug(f"Gate → VALID (lp={mean_lp:.3f} nsp={mean_nsp:.3f} wps={wps:.2f})")
    return GateResult(
        decision=GateDecision.VALID,
        confidence=round(confidence, 3),
        reasons=[],
    )


# ── LLM arbiter ───────────────────────────────────────────────────────────────

async def _llm_arbiter(
    text: str,
    duration_s: float,
    language: str,
) -> GateDecision | None:
    """Call a small LLM to resolve LOW_CONFIDENCE cases.

    Returns:
        VALID        — LLM considers the text coherent.
        LIKELY_NOISE — LLM considers it noise/garbage.
        None         — all retries exhausted; caller keeps heuristic result.

    Retries: 3 attempts, exponential backoff (0.5 s → 4 s).
    """
    from app.llm.client import LLMClient  # lazy — avoids circular import at module load

    prompt = _ARBITER_PROMPT.format(
        text=text[:500],           # cap to avoid huge prompts
        duration_s=f"{duration_s:.1f}",
        language=language,
    )

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
            reraise=False,
        ):
            with attempt:
                client   = LLMClient.get()
                response = await client.chat.completions.create(
                    model=voice_settings.llm_arbiter_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=80,
                    temperature=0.0,
                )
                raw  = response.choices[0].message.content or "{}"
                data = json.loads(raw)
                coherent = bool(data.get("coherent", False))
                reason   = data.get("reason", "")
                logger.debug(f"Arbiter: coherent={coherent} reason={reason!r}")
                return GateDecision.VALID if coherent else GateDecision.LIKELY_NOISE

    except RetryError as exc:
        logger.warning(f"LLM arbiter exhausted retries: {exc}; using heuristic result")
    except Exception as exc:
        logger.warning(f"LLM arbiter unexpected error: {exc}; using heuristic result")

    return None   # signals caller to keep the heuristic GateResult unchanged


# ── Combined entry point (async) ──────────────────────────────────────────────

async def evaluate_with_arbiter(result: TranscriptionResult) -> GateResult:
    """Run heuristics; if LOW_CONFIDENCE, consult the LLM arbiter.

    Always safe to call — on arbiter failure the heuristic result is returned.
    """
    gate = evaluate(result)

    if (
        gate.decision == GateDecision.LOW_CONFIDENCE
        and voice_settings.llm_arbiter_enabled
    ):
        arbiter_decision = await _llm_arbiter(
            text=result.text,
            duration_s=result.duration_s,
            language=result.language,
        )
        if arbiter_decision is not None:
            logger.info(
                f"Arbiter overrode {gate.decision!r} → {arbiter_decision!r}"
            )
            return GateResult(
                decision=arbiter_decision,
                confidence=0.75,
                reasons=gate.reasons + ["arbiter override"],
                suggested_confirmation=(
                    gate.suggested_confirmation
                    if arbiter_decision == GateDecision.LOW_CONFIDENCE
                    else None
                ),
            )

    return gate
