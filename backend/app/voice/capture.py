"""Audio capture helpers: decode bytes → 16 kHz mono float32 PCM.

Decoding strategy
-----------------
soundfile handles WAV / FLAC / OGG / MP3.
WebM (browser MediaRecorder default) is not supported by libsndfile, so we
fall back to an in-process ffmpeg pipe which is already required by faster-whisper.

Resampling uses numpy linear interpolation — no librosa dependency.
"""
from __future__ import annotations

import io
import re
import subprocess
from collections import Counter

import numpy as np
import soundfile as sf
from loguru import logger

_TARGET_SR = 16_000


# ── Resampling ─────────────────────────────────────────────────────────────────

def _resample_numpy(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return samples
    n_target = int(round(len(samples) * target_sr / orig_sr))
    x_orig = np.arange(len(samples), dtype=np.float64)
    x_new  = np.linspace(0, len(samples) - 1, n_target)
    return np.interp(x_new, x_orig, samples).astype(np.float32)


# ── WebM / unknown-format fallback ────────────────────────────────────────────

def _decode_with_ffmpeg(raw: bytes) -> tuple[np.ndarray, int]:
    """Pipe raw bytes through ffmpeg → 16 kHz mono WAV → numpy array."""
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0",
            "-ar", str(_TARGET_SR),
            "-ac", "1",
            "-f", "wav",
            "pipe:1",
        ],
        input=raw,
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg decoding failed: {result.stderr.decode(errors='replace')[:400]}"
        )
    samples, sr = sf.read(io.BytesIO(result.stdout), dtype="float32", always_2d=False)
    return samples, sr


# ── Public API ─────────────────────────────────────────────────────────────────

def decode_audio_bytes(raw: bytes) -> tuple[np.ndarray, int]:
    """Decode WAV/WebM/OGG/MP3/FLAC bytes → (samples float32 16 kHz mono, 16000).

    1. Try soundfile (handles WAV, FLAC, OGG, MP3).
    2. Fall back to ffmpeg pipe (handles WebM/Opus from browser MediaRecorder).
    Always returns 16 kHz mono float32 normalised to [-1, 1].
    """
    try:
        samples, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    except Exception as sf_err:
        logger.debug(f"soundfile failed ({sf_err}); trying ffmpeg")
        samples, sr = _decode_with_ffmpeg(raw)

    # Stereo → mono
    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    # Resample to 16 kHz if needed
    if sr != _TARGET_SR:
        logger.debug(f"Resampling {sr} Hz → {_TARGET_SR} Hz")
        samples = _resample_numpy(samples, sr, _TARGET_SR)

    return samples.astype(np.float32), _TARGET_SR


def compute_rms(samples: np.ndarray) -> float:
    """Return root-mean-square amplitude (normalised, range 0..1 for float32 PCM)."""
    if len(samples) == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def is_too_short(samples: np.ndarray, sr: int, min_ms: int) -> bool:
    """True when clip duration < min_ms milliseconds."""
    return len(samples) < (sr * min_ms / 1000)


def is_too_quiet(samples: np.ndarray, threshold: float = 0.005) -> bool:
    """True when RMS is below threshold (near-silence energy gate)."""
    return compute_rms(samples) < threshold


# ── Domain vocabulary biasing ─────────────────────────────────────────────────

# Regex for valid term tokens: 3–25 Unicode word chars (covers EN + PL).
_TERM_RE = re.compile(r"[a-zA-ZÀ-ɏ]{3,25}")

# Common English and Polish stop words — filtered before counting.
_STOP_WORDS: frozenset[str] = frozenset({
    # English
    "the","a","an","and","or","but","in","on","at","to","for","of","with","by",
    "from","up","about","into","through","during","is","are","was","were","be",
    "been","being","have","has","had","do","does","did","will","would","shall",
    "should","may","might","must","can","could","this","that","these","those",
    "it","its","they","them","their","he","she","we","you","i","me","my","our",
    "your","his","her","which","who","what","when","where","how","why","all",
    "any","both","each","more","most","other","some","such","no","not","only",
    "same","than","too","very","also","as","if","so","then","there","here",
    "now","just","one","two","three","four","five","six","seven","eight","nine",
    "ten","new","old","first","last","long","great","little","own","right",
    "big","high","large","small","next","early","young","important","public",
    "private","real","best","free","used","good","bad","well","able","just",
    "make","way","see","get","use","look","come","could","still","many","much",
    # Polish
    "się","że","to","jest","nie","jak","ale","czy","przez","po","przy","za",
    "przed","tak","co","już","go","jej","jego","ich","tym","tego","tej","tych",
    "tej","temu","który","która","które","którzy","więc","oraz","tutaj","tam",
    "nad","pod","przy","też","tylko","bez","kiedy","gdzie","kto","ma","być",
})


def get_domain_prompt(context_id: str | None, max_tokens: int = 200) -> str | None:
    """Query Qdrant for the ~50 most frequent domain terms in the active context.

    Returns a string like "Topics may include: RAG, Qdrant, embeddings, ..."
    capped at approximately max_tokens Whisper tokens (~4 chars each).
    Returns None when context_id is absent, Qdrant is unreachable, or the
    collection contains no usable text.

    Algorithm
    ---------
    1. Scroll up to 500 chunk payloads from qdrant_collection filtered by context_id.
    2. Tokenise each chunk text with a regex that matches 3–25-char word tokens.
    3. Remove stop words (EN + PL).
    4. Rank by frequency, take the top 50.
    5. Build "Topics may include: <term1>, <term2>, …" and truncate to max_tokens.
    """
    if not context_id:
        return None

    try:
        from qdrant_client import models as qm
        from app.config import settings
        from app.services._qdrant import get_client

        client = get_client()
        results, _ = client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=qm.Filter(must=[
                qm.FieldCondition(
                    key="context_id",
                    match=qm.MatchValue(value=context_id),
                )
            ]),
            limit=500,
            with_payload=True,
            with_vectors=False,
        )
        texts = [r.payload.get("text", "") for r in results if r.payload.get("text")]
    except Exception as exc:
        logger.debug(f"get_domain_prompt: Qdrant query failed ({exc}); skipping prompt")
        return None

    if not texts:
        return None

    # Count tokens across all chunks
    counter: Counter[str] = Counter()
    for text in texts:
        tokens = _TERM_RE.findall(text.lower())
        counter.update(t for t in tokens if t not in _STOP_WORDS)

    if not counter:
        return None

    # Build prompt, trimming terms until it fits within max_tokens characters
    top_terms = [term for term, _ in counter.most_common(50)]
    max_chars  = max_tokens * 4           # 1 Whisper token ≈ 4 chars (rough)
    prompt     = "Topics may include: " + ", ".join(top_terms) + "."

    while len(prompt) > max_chars and top_terms:
        top_terms.pop()
        prompt = "Topics may include: " + ", ".join(top_terms) + "."

    if not top_terms:
        return None

    logger.debug(f"Domain prompt: {len(top_terms)} terms, {len(prompt)} chars")
    return prompt
