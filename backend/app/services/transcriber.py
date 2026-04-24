"""
Audio transcription via faster-whisper (local, CPU-optimised, no ffmpeg system dep).
Model is loaded once on first use (lazy singleton).
"""

import os
import tempfile

from loguru import logger

from app.config import settings


class Transcriber:
    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper model: {settings.whisper_model!r}")
            cls._model = WhisperModel(
                settings.whisper_model,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Whisper model loaded")
        return cls._model

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        model = self._get_model()
        ext = os.path.splitext(filename)[1].lower() or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            segments, info = model.transcribe(tmp_path, beam_size=5)
            text = " ".join(s.text.strip() for s in segments)
            logger.info(f"Transcribed {filename!r}: {info.duration:.1f}s → {len(text)} chars")
            return text
        finally:
            os.unlink(tmp_path)
