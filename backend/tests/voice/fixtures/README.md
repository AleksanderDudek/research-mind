# Audio Fixtures

These files are **not committed to git** (add `tests/voice/fixtures/*.wav` to `.gitignore`).
Tests that require them use `conftest.require_fixture()` which calls `pytest.skip` gracefully
when the file is absent, so CI never fails on a fresh checkout.

## Required files

| Filename | Description | Expected outcome |
|---|---|---|
| `silence_3s.wav` | 3 seconds of room tone, no speech | VAD: no speech; Gate: LIKELY_NOISE or EMPTY |
| `clear_speech.wav` | "What is the capital of France?" — clear recording | Gate: VALID |
| `noisy_speech.wav` | Same phrase with background noise | Gate: VALID or LOW_CONFIDENCE |
| `mumbled.wav` | Unclear single word or phrase | Gate: LOW_CONFIDENCE |
| `single_yes.wav` | Just "yes" — clear | Gate: VALID; Intent: acknowledgment |
| `polish_question.wav` | "Jaka jest stolica Polski?" | Gate: VALID; Language: pl |

## Recording guidelines

- Sample rate: 16 kHz (or any rate — `capture.decode_audio_bytes` will resample)
- Channels: mono preferred, stereo acceptable (will be down-mixed)
- Format: WAV (PCM 16-bit) or WebM
- Duration: keep under 10 s to keep test runtime short
- No PII — use generic phrases only

## Generating silence for CI

```python
import numpy as np, soundfile as sf
sf.write("silence_3s.wav", np.zeros(48000), 16000, subtype="PCM_16")
```
