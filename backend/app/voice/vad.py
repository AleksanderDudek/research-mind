"""Silero VAD wrapper — lazy singleton model, numpy ↔ torch bridge.

The model is downloaded once on first use (~1.8 MB ONNX).
All public functions accept 16 kHz mono float32 numpy arrays.
"""
from __future__ import annotations

import numpy as np
import torch
from loguru import logger

from app.voice.settings import voice_settings

_model = None


def _get_model():
    global _model
    if _model is None:
        logger.info("Loading Silero VAD model (first use)…")
        from silero_vad import load_silero_vad
        _model = load_silero_vad()
        _model.eval()
        logger.info("Silero VAD ready")
    return _model


def _to_tensor(samples: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(samples.astype(np.float32))


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_speech_segments(
    samples: np.ndarray,
    sr: int = 16000,
) -> list[tuple[float, float]]:
    """Return list of (start_s, end_s) speech segments detected by Silero VAD."""
    from silero_vad import get_speech_timestamps

    model = _get_model()
    timestamps = get_speech_timestamps(
        _to_tensor(samples),
        model,
        threshold=voice_settings.vad_threshold,
        sampling_rate=sr,
        min_speech_duration_ms=voice_settings.vad_min_speech_ms,
        min_silence_duration_ms=voice_settings.vad_min_silence_ms,
        return_seconds=True,
    )
    return [(t["start"], t["end"]) for t in timestamps]


def has_speech(
    samples: np.ndarray,
    sr: int = 16000,
    min_speech_ms: int | None = None,
) -> bool:
    """True when at least one segment of >= min_speech_ms duration is detected."""
    min_ms = min_speech_ms if min_speech_ms is not None else voice_settings.vad_min_speech_ms
    segments = detect_speech_segments(samples, sr)
    min_s = min_ms / 1000.0
    return any((end - start) >= min_s for start, end in segments)


def trim_to_speech(
    samples: np.ndarray,
    sr: int = 16000,
    pad_ms: int = 200,
) -> np.ndarray:
    """Crop from first speech onset to last speech offset + pad_ms padding.

    Returns the original array unchanged when no speech is detected —
    the quality gate will then reject it as LIKELY_NOISE.
    """
    segments = detect_speech_segments(samples, sr)
    if not segments:
        logger.debug("VAD found no speech; returning original clip for gate rejection")
        return samples

    first_start = segments[0][0]
    last_end    = segments[-1][1]
    pad_s       = pad_ms / 1000.0

    start_idx = max(0, int((first_start - pad_s) * sr))
    end_idx   = min(len(samples), int((last_end + pad_s) * sr))

    logger.debug(
        f"VAD trim: {first_start:.2f}s–{last_end:.2f}s "
        f"({len(segments)} segment(s)), pad={pad_ms}ms"
    )
    return samples[start_idx:end_idx]
