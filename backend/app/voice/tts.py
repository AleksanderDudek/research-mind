"""OpenAI TTS synthesis with streaming response and SHA-256 disk cache.

Design
------
synthesize_stream()   — async generator of MP3 chunks for unique responses.
                        Never cached (responses are one-off).
synthesize_to_bytes() — complete bytes for repeated strings (confirmations,
                        error messages).  Cached by SHA-256(text+voice+speed).

Both raise TTSUnavailable on failure so the UI can fall back to text display.

The cache directory is .cache/tts/ relative to the working directory.
OPENAI_API_KEY must be set in the environment; the function raises immediately
when the key is absent so callers get a clear error rather than an auth failure
from the API.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import AsyncIterator

from loguru import logger

from app.voice.settings import voice_settings

_CACHE_DIR = Path(".cache/tts")


# ── Exception ─────────────────────────────────────────────────────────────────

class TTSUnavailable(Exception):
    """Raised when TTS synthesis fails; UI falls back to text-only display."""


# ── Client factories ──────────────────────────────────────────────────────────

def _api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise TTSUnavailable(
            "OPENAI_API_KEY is not set — TTS unavailable. "
            "Set the variable or disable TTS in voice settings."
        )
    return key


def _async_client():
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=_api_key())


def _sync_client():
    from openai import OpenAI
    return OpenAI(api_key=_api_key())


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_key(text: str, voice: str, speed: float) -> str:
    raw = f"{text}\x00{voice}\x00{speed}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_path(text: str, voice: str, speed: float) -> Path:
    return _CACHE_DIR / f"{_cache_key(text, voice, speed)}.mp3"


# ── Public API ────────────────────────────────────────────────────────────────

async def synthesize_stream(
    text: str,
    voice: str,
    speed: float,
) -> AsyncIterator[bytes]:
    """Yield MP3 audio chunks from OpenAI's streaming TTS API.

    No caching — used for unique assistant responses.
    Raises TTSUnavailable on any failure so the caller can degrade gracefully.
    """
    logger.debug(
        f"TTS stream: model={voice_settings.tts_model!r} "
        f"voice={voice!r} speed={speed} chars={len(text)}"
    )
    try:
        client = _async_client()
        async with client.audio.speech.with_streaming_response.create(
            model=voice_settings.tts_model,
            voice=voice,
            input=text,
            speed=speed,
            response_format="mp3",
        ) as response:
            async for chunk in response.iter_bytes(chunk_size=4096):
                yield chunk
    except TTSUnavailable:
        raise
    except Exception as exc:
        raise TTSUnavailable(f"TTS stream error: {exc}") from exc


def synthesize_to_bytes(
    text: str,
    voice: str,
    speed: float,
) -> bytes:
    """Synthesise to complete bytes with SHA-256 disk cache.

    Cache path: .cache/tts/<sha256(text+voice+speed)>.mp3
    Used for repeated strings (error messages, confirmations).
    Raises TTSUnavailable on API failure.
    """
    path = _cache_path(text, voice, speed)

    if path.exists():
        logger.debug(f"TTS cache hit: {path.name}")
        return path.read_bytes()

    logger.debug(
        f"TTS synthesise: model={voice_settings.tts_model!r} "
        f"voice={voice!r} speed={speed} chars={len(text)}"
    )
    try:
        client = _sync_client()
        response = client.audio.speech.create(
            model=voice_settings.tts_model,
            voice=voice,
            input=text,
            speed=speed,
            response_format="mp3",
        )
        data: bytes = response.content
    except TTSUnavailable:
        raise
    except Exception as exc:
        raise TTSUnavailable(f"TTS synthesis error: {exc}") from exc

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    logger.debug(f"TTS cache write: {path.name} ({len(data)} bytes)")
    return data
