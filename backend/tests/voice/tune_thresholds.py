"""Threshold tuning script for the voice quality gate.

Usage (from backend/):
    python tests/voice/tune_thresholds.py

For each fixture in tests/voice/fixtures/, runs the full pipeline
(decode → VAD → transcribe → quality gate) and prints a report showing
the gate decision and raw Whisper scores.  Missing fixtures are skipped.

After reviewing the output, update the defaults in app/voice/settings.py
and re-run until all acceptance criteria are met:

  • silence / noise  → VAD no-speech or gate LIKELY_NOISE/EMPTY  (target ≥ 90 %)
  • real utterances  → gate VALID                                  (target ≥ 95 %)
  • hallucinations   → gate HALLUCINATION                          (always)
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# Make sure the project is importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

FIXTURES = Path(__file__).parent / "fixtures"

# Expected outcomes for the standard fixture set
_EXPECTED: dict[str, str | set[str]] = {
    "silence_3s.wav":       {"likely_noise", "empty"},   # no speech / gate rejects
    "clear_speech.wav":     "valid",
    "noisy_speech.wav":     {"valid", "low_confidence"},
    "mumbled.wav":          {"low_confidence", "likely_noise"},
    "single_yes.wav":       "valid",
    "polish_question.wav":  "valid",
}


def _load(filename: str):
    path = FIXTURES / filename
    if not path.exists():
        return None
    return path.read_bytes()


def _expected_ok(decision: str, filename: str) -> bool:
    exp = _EXPECTED.get(filename)
    if exp is None:
        return True          # unknown fixture — just report
    if isinstance(exp, str):
        return decision == exp
    return decision in exp


async def _run_fixture(name: str, audio_bytes: bytes) -> dict:
    from app.voice.capture import decode_audio_bytes, is_too_quiet, is_too_short
    from app.voice.vad import has_speech, trim_to_speech
    from app.voice.transcribe import transcribe
    from app.voice.quality_gate import evaluate

    t0 = time.perf_counter()

    # 1. Decode
    samples, sr = decode_audio_bytes(audio_bytes)
    duration_s = len(samples) / sr

    if is_too_short(samples, sr, 400):
        return {"fixture": name, "decision": "too_short", "duration_s": duration_s,
                "ok": True, "ms": 0}
    if is_too_quiet(samples):
        return {"fixture": name, "decision": "too_quiet", "duration_s": duration_s,
                "ok": True, "ms": 0}

    # 2. VAD
    t_vad = time.perf_counter()
    detected = has_speech(samples, sr)
    vad_ms   = (time.perf_counter() - t_vad) * 1000
    trimmed  = trim_to_speech(samples, sr) if detected else samples

    if not detected:
        return {"fixture": name, "decision": "no_speech (VAD)", "duration_s": duration_s,
                "vad_ms": round(vad_ms, 1), "ok": _expected_ok("no_speech", name), "ms": 0}

    # 3. Transcribe (sync — wrapped in thread for tuning script)
    t_stt = time.perf_counter()
    result = await asyncio.to_thread(transcribe, trimmed, sr)
    stt_ms = (time.perf_counter() - t_stt) * 1000

    # 4. Gate (heuristic only — skip arbiter for speed)
    gate = evaluate(result)

    total_ms = (time.perf_counter() - t0) * 1000
    segs = result.segments
    mean_lp  = sum(s.avg_logprob    for s in segs) / len(segs) if segs else 0.0
    mean_nsp = sum(s.no_speech_prob for s in segs) / len(segs) if segs else 0.0

    return {
        "fixture":       name,
        "decision":      gate.decision.value,
        "ok":            _expected_ok(gate.decision.value, name),
        "confidence":    round(gate.confidence, 2),
        "reasons":       gate.reasons,
        "text":          result.text[:60],
        "language":      result.language,
        "duration_s":    round(duration_s, 2),
        "word_count":    result.word_count,
        "mean_logprob":  round(mean_lp,  3),
        "mean_nsp":      round(mean_nsp, 3),
        "wps":           round(result.words_per_second, 2),
        "vad_ms":        round(vad_ms, 1) if detected else 0,
        "stt_ms":        round(stt_ms, 1),
        "total_ms":      round(total_ms, 1),
    }


async def main() -> None:
    print("=" * 70)
    print("VOICE QUALITY GATE — THRESHOLD TUNING REPORT")
    print("=" * 70)

    from app.voice.settings import voice_settings
    print(f"\nCurrent thresholds:")
    print(f"  no_speech_prob_threshold : {voice_settings.no_speech_prob_threshold}")
    print(f"  avg_logprob_threshold    : {voice_settings.avg_logprob_threshold}")
    print(f"  low_confidence_logprob   : {voice_settings.low_confidence_logprob}")
    print(f"  min/max_words_per_second : {voice_settings.min_words_per_second} / {voice_settings.max_words_per_second}")
    print(f"  vad_threshold            : {voice_settings.vad_threshold}")
    print(f"  whisper_model_size       : {voice_settings.whisper_model_size!r}")
    print()

    results = []
    for name in sorted(p.name for p in FIXTURES.glob("*.wav")):
        audio = _load(name)
        if audio is None:
            continue
        print(f"Running: {name} ...", end=" ", flush=True)
        try:
            r = await _run_fixture(name, audio)
            results.append(r)
            ok_mark = "✓" if r["ok"] else "✗"
            print(f"{ok_mark}  {r['decision']} "
                  f"({r.get('total_ms', 0):.0f} ms)")
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append({"fixture": name, "decision": "error", "ok": False,
                            "error": str(exc)})

    if not results:
        print("No fixtures found.  Add .wav files to tests/voice/fixtures/")
        print("See tests/voice/fixtures/README.md for the full list.\n")
        return

    print()
    print("─" * 70)
    print(f"{'Fixture':<30} {'Decision':<20} {'LP':>6} {'NSP':>6} {'WPS':>5} {'ms':>6} {'OK'}")
    print("─" * 70)
    for r in results:
        if "error" in r:
            print(f"{r['fixture']:<30} ERROR")
            continue
        print(
            f"{r['fixture']:<30} "
            f"{r['decision']:<20} "
            f"{r.get('mean_logprob', 0):>6.3f} "
            f"{r.get('mean_nsp', 0):>6.3f} "
            f"{r.get('wps', 0):>5.1f} "
            f"{r.get('total_ms', 0):>6.0f}  "
            f"{'✓' if r['ok'] else '✗'}"
        )
        if r.get("text"):
            print(f"  → {r['text']!r}")
        if r.get("reasons"):
            print(f"  ⚠ {r['reasons']}")

    passed = sum(1 for r in results if r.get("ok"))
    total  = len(results)
    print("─" * 70)
    print(f"Passed: {passed}/{total}")

    if passed < total:
        print("\nFailed fixtures suggest threshold adjustment:")
        print("  • If VALID is expected but got LOW_CONFIDENCE → lower low_confidence_logprob")
        print("  • If silence got VALID → raise no_speech_prob_threshold or lower avg_logprob_threshold")
        print("  • If real speech got LIKELY_NOISE → widen min/max_words_per_second")
    print()


if __name__ == "__main__":
    asyncio.run(main())
