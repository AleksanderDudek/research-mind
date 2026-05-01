"""faster-whisper wrapper — singleton model, config from VoiceSettings.

Design decisions
----------------
- vad_filter=True always: Whisper's internal VAD removes silence before decoding,
  which reduces hallucinations on quiet clips.
- word_timestamps=True always: word counts come from word lists, not text.split().
- condition_on_previous_text=False always: prevents hallucination cascades where
  the model repeats previous output when it has nothing to say.
- The model is loaded once and reused across requests (lazy singleton).
- Device is auto-detected: CUDA if available, else CPU.
"""
from __future__ import annotations

import dataclasses

import numpy as np
from loguru import logger

from app.voice.schemas import TranscriptionResult, TranscriptionSegment
from app.voice.settings import voice_settings

_model = None


def _resolve_device() -> tuple[str, str]:
    """Return (device, compute_type) based on VoiceSettings and hardware."""
    device = voice_settings.whisper_device
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    compute_type = voice_settings.whisper_compute_type
    # If caller left compute_type as the CPU default but GPU is selected, upgrade it.
    if device == "cuda" and compute_type == "int8":
        compute_type = "float16"

    return device, compute_type


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        device, compute_type = _resolve_device()
        logger.info(
            f"Loading Whisper model: size={voice_settings.whisper_model_size!r} "
            f"device={device!r} compute_type={compute_type!r}"
        )
        _model = WhisperModel(
            voice_settings.whisper_model_size,
            device=device,
            compute_type=compute_type,
        )
        logger.info("Whisper model ready")
    return _model


def transcribe(
    samples: np.ndarray,
    sr: int = 16000,
    language: str | None = None,
    initial_prompt: str | None = None,
) -> TranscriptionResult:
    """Transcribe 16 kHz mono float32 PCM → TranscriptionResult.

    Parameters
    ----------
    samples:        16 kHz mono float32 numpy array.
    sr:             Sample rate (must be 16000; validated for safety).
    language:       ISO-639-1 code to lock language; None = autodetect.
    initial_prompt: Domain-vocabulary hint fed to Whisper's decoder.
                    Populated from active Qdrant collection by the caller.

    Always uses:
        vad_filter=True                 — removes silence before decoding
        word_timestamps=True            — enables word-level word_count
        condition_on_previous_text=False — prevents repetition cascades
    """
    if sr != 16000:
        raise ValueError(f"transcribe() expects 16 kHz audio, got {sr} Hz")

    model = _get_model()

    raw_segments, info = model.transcribe(
        samples,
        language=language or voice_settings.whisper_language,
        initial_prompt=initial_prompt,
        beam_size=voice_settings.whisper_beam_size,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
    )

    # Materialise the generator — faster-whisper is lazy
    raw_segments = list(raw_segments)

    segments: list[TranscriptionSegment] = []
    word_count = 0

    for seg in raw_segments:
        # Word count from word objects, not text.split() (more accurate)
        words = seg.words or []
        word_count += len(words)

        segments.append(TranscriptionSegment(
            start=seg.start,
            end=seg.end,
            text=seg.text,
            avg_logprob=seg.avg_logprob,
            no_speech_prob=seg.no_speech_prob,
            compression_ratio=seg.compression_ratio,
        ))

    full_text = " ".join(s.text.strip() for s in segments).strip()
    duration_s = info.duration if info.duration > 0 else (len(samples) / 16000)

    logger.info(
        f"Transcribed {duration_s:.1f}s | lang={info.language!r} "
        f"| {len(segments)} seg(s) | {word_count} word(s) | {len(full_text)} chars"
        + (f" | prompt={initial_prompt[:40]!r}…" if initial_prompt else "")
    )

    return TranscriptionResult(
        text=full_text,
        language=info.language,
        duration_s=duration_s,
        segments=segments,
        word_count=word_count,
    )
