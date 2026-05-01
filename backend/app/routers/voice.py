"""Voice turn endpoint — accepts audio, runs the full pipeline, returns VoiceTurn data."""
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from loguru import logger

from app.voice.state import run_turn
from app.voice.schemas import GateDecision

router = APIRouter(prefix="/voice", tags=["voice"])

_500 = {500: {"description": "Internal server error"}}


@router.post("/interrupt")
async def interrupt_voice_turn() -> dict:
    """Signal any in-progress TTS streaming to stop immediately.

    The frontend calls this when the user starts speaking during playback
    (barge-in).  Sets the module-level interrupt_event checked between chunks
    in _step_speaking; the event is cleared at the start of each new turn.
    """
    from app.voice.state import interrupt_event
    interrupt_event.set()
    logger.info("Voice turn interrupted by barge-in signal")
    return {"interrupted": True}


class VoiceTurnResponse(BaseModel):
    turn_id:                  str
    gate_decision:            str | None = None   # GateDecision value
    transcription_text:       str | None = None
    suggested_confirmation:   str | None = None
    final_text:               str | None = None
    response_text:            str | None = None
    latency_ms:               dict[str, float] = {}


@router.post("/turn", response_model=VoiceTurnResponse, responses=_500)
async def voice_turn_endpoint(
    file:       Annotated[UploadFile, File()],
    context_id: Annotated[str | None, Form()] = None,
    language:   Annotated[str | None, Form()] = None,
) -> dict:
    """Run one complete voice turn: VAD → STT → quality gate → LLM.

    Returns structured turn data.  TTS audio delivery is handled separately
    (the Streamlit UI uses the browser's Web Speech API for basic playback).
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        turn = await run_turn(
            audio_bytes=audio_bytes,
            context_id=context_id or None,
            language=language or None,
        )

        return {
            "turn_id":                turn.turn_id,
            "gate_decision":          turn.gate_result.decision.value if turn.gate_result else None,
            "transcription_text":     turn.transcription.text if turn.transcription else None,
            "suggested_confirmation": (
                turn.gate_result.suggested_confirmation if turn.gate_result else None
            ),
            "final_text":             turn.final_text,
            "response_text":          turn.response_text,
            "latency_ms":             turn.latency_ms,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Voice turn failed")
        raise HTTPException(status_code=500, detail=str(exc))
