"""Transcriber Service using Faster Whisper.

Implements Voice-to-Brief (stenographer) transcription.
"""

from __future__ import annotations

from typing import BinaryIO, Optional

from junior.core import get_logger, settings

logger = get_logger(__name__)

class TranscriberService:
    """
    Service for transcribing audio to text using Faster Whisper.
    This powers the "Voice-to-Brief" stenographer feature.
    """

    def __init__(self, model_size: Optional[str] = None):
        self.model_size = model_size or settings.whisper_model_size
        self._model = None

    @property
    def model(self):
        """Lazy load the Whisper model"""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                # Run on CPU with INT8 quantization for broad compatibility
                # In production with GPU, use device="cuda", compute_type="float16"
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                logger.info(f"Faster Whisper model '{self.model_size}' loaded successfully")
            except ImportError:
                logger.error("faster-whisper not installed. Please install it via requirements.txt")
                raise
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise
        return self._model

    def transcribe(self, audio_file: BinaryIO) -> str:
        """
        Transcribe audio stream to text
        """
        if not self.model:
            return "Transcription unavailable."

        try:
            # faster-whisper accepts a file-like object or path
            try:
                audio_file.seek(0)
            except Exception:
                pass

            segments, info = self.model.transcribe(audio_file, beam_size=5)

            logger.info(f"Detected language '{info.language}' with probability {info.language_probability}")

            text_segments = []
            for segment in segments:
                text_segments.append(segment.text)

            return " ".join(text_segments).strip()
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
