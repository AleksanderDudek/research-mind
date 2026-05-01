from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class GateDecision(str, Enum):
    VALID          = "valid"
    LOW_CONFIDENCE = "low_confidence"
    LIKELY_NOISE   = "likely_noise"
    EMPTY          = "empty"
    HALLUCINATION  = "hallucination"


class TranscriptionSegment(BaseModel):
    start:             float
    end:               float
    text:              str
    avg_logprob:       float
    no_speech_prob:    float
    compression_ratio: float


class TranscriptionResult(BaseModel):
    text:       str
    language:   str
    duration_s: float
    segments:   list[TranscriptionSegment]
    word_count: int

    @property
    def words_per_second(self) -> float:
        return self.word_count / self.duration_s if self.duration_s > 0 else 0.0


class GateResult(BaseModel):
    decision:               GateDecision
    confidence:             float          # 0..1
    reasons:                list[str]
    suggested_confirmation: str | None = None   # populated for LOW_CONFIDENCE


class VoiceTurn(BaseModel):
    turn_id:             str
    timestamp:           datetime
    audio_duration_s:    float
    transcription:       TranscriptionResult | None = None
    gate_result:         GateResult | None = None
    final_text:          str | None = None       # text actually sent to the LLM
    response_text:       str | None = None
    response_audio_path: str | None = None
    latency_ms:          dict[str, float] = Field(default_factory=dict)  # vad/stt/llm/tts
