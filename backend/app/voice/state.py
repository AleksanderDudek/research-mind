"""LangGraph-based FSM for a single voice turn.

Pipeline
--------
audio_bytes
  → PREPROCESSING  decode + energy gate
  → VAD            speech detection + trim
  → TRANSCRIBING   faster-whisper
  → GATING         quality gate + optional LLM arbiter
       ↓
       GateDecision.VALID         → THINKING  (ResearchAgent) → SPEAKING → done
       GateDecision.LOW_CONFIDENCE → return turn with confirmation prompt
       GateDecision.LIKELY_NOISE  → return turn with toast flag
       GateDecision.HALLUCINATION → return turn silently
       GateDecision.EMPTY         → return turn silently

Each stage records elapsed milliseconds in VoiceTurn.latency_ms.

Barge-in
--------
`interrupt_event` is a module-level threading.Event.  The UI sets it when
new speech is detected during playback.  The TTS streaming loop checks it
between chunks and aborts cleanly.  Always cleared at the start of SPEAKING.
"""
from __future__ import annotations

import asyncio
import time
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from loguru import logger
from langgraph.graph import END, StateGraph

from app.config import settings as _app_settings
from app.voice.capture import decode_audio_bytes, is_too_quiet, is_too_short
from app.voice.intents import is_cancel
from app.voice.quality_gate import evaluate_with_arbiter
from app.voice.schemas import GateDecision, VoiceTurn
from app.voice.settings import voice_settings
from app.voice.transcribe import transcribe
from app.voice.vad import has_speech, trim_to_speech

# ── Barge-in event (set by UI during SPEAKING to abort TTS) ──────────────────
interrupt_event: threading.Event = threading.Event()


# ── Langfuse observability helpers ────────────────────────────────────────────

def _lf_enabled() -> bool:
    return bool(_app_settings.langfuse_public_key and _app_settings.langfuse_secret_key)


def _lf_span(**kwargs) -> None:
    """Update the current Langfuse span with metadata/output. No-op if disabled."""
    if not _lf_enabled():
        return
    try:
        from langfuse import get_client
        get_client().update_current_span(**{k: v for k, v in kwargs.items() if v is not None})
    except Exception:
        pass  # Never let observability break the voice pipeline


def _lf_observe(name: str):
    """Return the langfuse @observe decorator or identity if Langfuse is off."""
    if _lf_enabled():
        try:
            from langfuse import observe
            return observe(name=name)
        except Exception:
            pass
    return lambda f: f  # identity


# ── FSM state ─────────────────────────────────────────────────────────────────

class VoiceFSMState(TypedDict):
    turn:       VoiceTurn
    fsm_state:  str
    language:   str | None
    context_id: str | None
    error:      str | None


# ── Shared utilities ──────────────────────────────────────────────────────────

def _adapt_rag_result(result: dict) -> tuple[str, list[dict]]:
    """Thin adapter from ResearchAgent.run() output → (answer, sources)."""
    return result.get("answer", ""), result.get("sources", [])


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


# ── Pipeline steps (each decorated for Langfuse span) ─────────────────────────

@_lf_observe("preprocess")
async def _step_preprocess(
    audio_bytes: bytes,
    turn: VoiceTurn,
) -> tuple[bytes | None, int]:
    """Decode audio and run energy gates. Returns (samples, sr) or None."""
    samples, sr = await asyncio.to_thread(decode_audio_bytes, audio_bytes)
    turn.audio_duration_s = len(samples) / sr

    _lf_span(metadata={
        "audio_bytes": len(audio_bytes),
        "duration_s":  round(turn.audio_duration_s, 2),
    })

    if is_too_short(samples, sr, voice_settings.min_audio_duration_ms):
        logger.info(f"Turn {turn.turn_id}: too short ({turn.audio_duration_s:.2f}s), skipping")
        return None, sr

    if is_too_quiet(samples):
        logger.info(f"Turn {turn.turn_id}: too quiet (energy gate), skipping")
        return None, sr

    return samples, sr


@_lf_observe("vad")
async def _step_vad(samples, sr: int, turn: VoiceTurn):
    """VAD: detect speech and trim. Returns trimmed samples or None."""
    t = time.perf_counter()
    detected = await asyncio.to_thread(has_speech, samples, sr, voice_settings.vad_min_speech_ms)
    trimmed  = await asyncio.to_thread(trim_to_speech, samples, sr) if detected else samples
    turn.latency_ms["vad"] = _ms(t)

    _lf_span(metadata={
        "speech_detected":  detected,
        "duration_ms":      turn.latency_ms["vad"],
        "min_speech_ms":    voice_settings.vad_min_speech_ms,
        "vad_threshold":    voice_settings.vad_threshold,
    })

    if not detected:
        logger.info(f"Turn {turn.turn_id}: VAD found no speech")
        return None

    return trimmed


@_lf_observe("transcribe")
async def _step_transcribe(trimmed, sr: int, language: str | None,
                            initial_prompt: str | None, turn: VoiceTurn):
    """faster-whisper transcription. Returns (TranscriptionResult, locked_language)."""
    t = time.perf_counter()
    result = await asyncio.to_thread(transcribe, trimmed, sr, language, initial_prompt)
    turn.transcription = result
    turn.latency_ms["stt"] = _ms(t)

    segs = result.segments
    mean_lp  = sum(s.avg_logprob    for s in segs) / len(segs) if segs else 0.0
    mean_nsp = sum(s.no_speech_prob for s in segs) / len(segs) if segs else 0.0
    _lf_span(metadata={
        "model_size":        voice_settings.whisper_model_size,
        "duration_s":        round(result.duration_s, 2),
        "language":          result.language,
        "word_count":        result.word_count,
        "mean_avg_logprob":  round(mean_lp,  3),
        "mean_no_speech_prob": round(mean_nsp, 3),
        "initial_prompt_len": len(initial_prompt) if initial_prompt else 0,
        "duration_ms":       turn.latency_ms["stt"],
    }, output=result.text[:500] if result.text else None)

    locked = language or result.language
    logger.info(
        f"Turn {turn.turn_id}: transcribed {result.duration_s:.1f}s "
        f"lang={result.language!r} words={result.word_count} "
        f"text={result.text!r:.80}"
    )
    return result, locked


@_lf_observe("quality_gate")
async def _step_gate(transcription, turn: VoiceTurn):
    """Quality gate + optional LLM arbiter. Returns GateResult."""
    t = time.perf_counter()
    gate = await evaluate_with_arbiter(transcription)
    turn.gate_result = gate
    turn.latency_ms["gate"] = _ms(t)

    arbiter_used = any("arbiter override" in r for r in gate.reasons)
    rejected     = gate.decision != GateDecision.VALID
    _lf_span(metadata={
        "decision":      gate.decision.value,
        "confidence":    gate.confidence,
        "reasons":       gate.reasons,
        "arbiter_used":  arbiter_used,
        "gate_rejected": rejected,
        "duration_ms":   turn.latency_ms["gate"],
    })

    logger.info(f"Turn {turn.turn_id}: gate={gate.decision!r} reasons={gate.reasons}")
    return gate


@_lf_observe("llm")
async def _step_thinking(text: str, context_id: str | None, turn: VoiceTurn) -> str | None:
    """Call the existing RAG chain. Returns the answer string or None on failure."""
    from app.agents.research_agent import ResearchAgent

    t = time.perf_counter()
    try:
        result = await ResearchAgent().run(text, context_id=context_id)
        answer, _sources = _adapt_rag_result(result)
        turn.response_text = answer
        turn.final_text    = text
        turn.latency_ms["llm"] = _ms(t)
        _lf_span(
            metadata={"context_id": context_id, "duration_ms": turn.latency_ms["llm"]},
            input=text,
            output=answer[:500] if answer else None,
        )
        return answer
    except Exception as exc:
        logger.error(f"Turn {turn.turn_id}: RAG chain error: {exc}")
        turn.latency_ms["llm"] = _ms(t)
        return None


@_lf_observe("tts")
async def _step_speaking(answer: str, turn: VoiceTurn) -> None:
    """Stream TTS to a temp file; abort on barge-in."""
    from app.voice.tts import TTSUnavailable, synthesize_stream

    interrupt_event.clear()

    tmp_dir = Path(".cache/tts/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{turn.turn_id}.mp3"

    t = time.perf_counter()
    ttfb_ms: float | None = None
    bytes_written = 0

    try:
        with tmp_path.open("wb") as fh:
            async for chunk in synthesize_stream(
                answer,
                voice=voice_settings.tts_voice,
                speed=voice_settings.tts_speed,
            ):
                if ttfb_ms is None:
                    ttfb_ms = _ms(t)   # time-to-first-byte
                if interrupt_event.is_set():
                    logger.info(f"Turn {turn.turn_id}: TTS interrupted by barge-in")
                    break
                fh.write(chunk)
                bytes_written += len(chunk)

        turn.response_audio_path = str(tmp_path)
    except TTSUnavailable:
        logger.warning(f"Turn {turn.turn_id}: TTS unavailable — text-only response")
    except Exception as exc:
        logger.error(f"Turn {turn.turn_id}: TTS error: {exc}")
    finally:
        turn.latency_ms["tts"] = _ms(t)
        _lf_span(metadata={
            "model":          voice_settings.tts_model,
            "voice":          voice_settings.tts_voice,
            "speed":          voice_settings.tts_speed,
            "char_count":     len(answer),
            "bytes_written":  bytes_written,
            "ttfb_ms":        ttfb_ms,
            "duration_ms":    turn.latency_ms["tts"],
            "interrupted":    interrupt_event.is_set(),
        })


# ── Main entry point (top-level Langfuse trace) ───────────────────────────────

@_lf_observe("voice_turn")
async def run_turn(
    audio_bytes: bytes,
    context_id: str | None,
    language: str | None = None,
    initial_prompt: str | None = None,
) -> VoiceTurn:
    """Process one voice turn end-to-end and return a populated VoiceTurn.

    The returned turn's gate_result indicates the outcome:
      VALID          — response_text and (optionally) response_audio_path populated
      LOW_CONFIDENCE — suggested_confirmation populated; send to UI for confirm card
      LIKELY_NOISE   — show toast, discard
      HALLUCINATION  — discard silently
      EMPTY          — discard silently
      None           — preprocessing/VAD/STT failure
    """
    turn = VoiceTurn(
        turn_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        audio_duration_s=0.0,
    )

    # PREPROCESSING
    try:
        samples, sr = await _step_preprocess(audio_bytes, turn)
    except Exception as exc:
        logger.error(f"Turn {turn.turn_id}: decode error: {exc}")
        return turn

    if samples is None:
        return turn

    # VAD
    trimmed = await _step_vad(samples, sr, turn)
    if trimmed is None:
        return turn

    # TRANSCRIBING
    try:
        transcription, language = await _step_transcribe(
            trimmed, sr, language, initial_prompt, turn
        )
    except Exception as exc:
        logger.error(f"Turn {turn.turn_id}: transcription error: {exc}")
        return turn

    # GATING
    gate = await _step_gate(transcription, turn)

    # Intent check before sending to LLM
    if gate.decision == GateDecision.VALID and is_cancel(transcription.text, language):
        logger.info(f"Turn {turn.turn_id}: cancel intent — aborting before LLM")
        return turn

    if gate.decision != GateDecision.VALID:
        return turn  # caller inspects gate_result.decision for toast/confirmation

    # THINKING
    answer = await _step_thinking(transcription.text, context_id, turn)
    if not answer:
        return turn

    # SPEAKING
    await _step_speaking(answer, turn)
    return turn


# ── LangGraph graph (wraps run_turn for Langfuse / graph tracing) ─────────────

def build_graph():
    """Build a single-node StateGraph that delegates to run_turn.

    The graph is provided for Langfuse tracing and future FSM expansion.
    Individual pipeline steps are implemented in the pipeline helpers above.
    """
    async def _run_node(state: VoiceFSMState) -> VoiceFSMState:
        # This node is called by the graph; audio_bytes passed via state extras
        audio_bytes = state.get("_audio_bytes", b"")  # type: ignore[misc]
        turn = await run_turn(
            audio_bytes=audio_bytes,
            context_id=state.get("context_id"),
            language=state.get("language"),
        )
        return {**state, "turn": turn, "fsm_state": "done"}

    g = StateGraph(VoiceFSMState)
    g.add_node("voice_turn", _run_node)
    g.set_entry_point("voice_turn")
    g.add_edge("voice_turn", END)
    return g.compile()
