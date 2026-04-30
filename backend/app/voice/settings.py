from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VoiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VOICE_",
        env_file=".env",
        extra="ignore",
    )

    # ── Whisper ────────────────────────────────────────────────────────────────
    whisper_model_size: Literal["tiny", "base", "small", "medium", "large-v3"] = "small"
    whisper_device: Literal["cpu", "cuda", "auto"] = "auto"
    whisper_compute_type: str = "int8"        # int8 on CPU, float16 on GPU
    whisper_beam_size: int = 5
    whisper_language: str | None = None       # None = autodetect first turn, then lock

    # ── VAD ────────────────────────────────────────────────────────────────────
    vad_threshold: float = 0.5                # Silero speech-probability threshold
    vad_min_speech_ms: int = 250
    vad_min_silence_ms: int = 1500            # trailing silence to end a turn
    min_audio_duration_ms: int = 400          # discard clips shorter than this

    # ── Quality gate ───────────────────────────────────────────────────────────
    no_speech_prob_threshold: float = 0.6
    avg_logprob_threshold: float = -1.0
    low_confidence_logprob: float = -0.7      # between this and threshold → LOW_CONFIDENCE
    min_words_per_second: float = 1.0
    max_words_per_second: float = 5.0
    llm_arbiter_enabled: bool = True
    llm_arbiter_model: str = "gpt-4o-mini"

    # ── TTS ────────────────────────────────────────────────────────────────────
    tts_model: Literal["tts-1", "tts-1-hd"] = "tts-1"
    tts_voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "nova"
    tts_speed: float = 1.0

    # ── UX ─────────────────────────────────────────────────────────────────────
    push_to_talk: bool = False
    show_interim_transcript: bool = True
    audio_retention_hours: int = 24
    persist_audio: bool = False               # False = process in memory only


voice_settings = VoiceSettings()
