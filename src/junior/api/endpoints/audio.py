"""Audio endpoints for Voice-to-Brief features."""

from __future__ import annotations

import os

from fastapi import APIRouter, File, HTTPException, UploadFile

try:  # python-multipart provides `multipart`
    import multipart  # type: ignore
    _HAS_MULTIPART = True
except ModuleNotFoundError:  # pragma: no cover
    _HAS_MULTIPART = False

from junior.core import get_logger, settings

router = APIRouter()
logger = get_logger(__name__)

_ALLOWED_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".webm", ".mp4", ".flac"}

def _is_likely_audio_upload(upload: UploadFile) -> bool:
    ct = (upload.content_type or "").lower().strip()
    if ct.startswith("audio/"):
        return True
    # Browser recordings are commonly video/webm even if it only contains audio
    if ct.startswith("video/"):
        return True
    if ct in {"application/octet-stream", "application/x-www-form-urlencoded", "multipart/form-data", ""}:
        # fall back to extension check
        pass

    name = upload.filename or ""
    ext = os.path.splitext(name)[1].lower()
    return ext in _ALLOWED_EXTS

if _HAS_MULTIPART:

    @router.post("/transcribe")
    async def transcribe_audio(file: UploadFile = File(...)):
        """
        Transcribe uploaded audio file to text.
        Used for the 'Stenographer' feature.
        """
        logger.info(f"Received audio file: {file.filename}, content_type: {file.content_type}")

        # Validate file type (browser recordings are often `video/webm`)
        if not _is_likely_audio_upload(file):
            raise HTTPException(
                status_code=400,
                detail="Unsupported upload type. Please upload audio (e.g., .wav/.mp3) or a browser recording (.webm).",
            )

        try:
            from junior.services.transcriber import TranscriberService

            # Enforce a max size (UploadFile doesn't expose size, so we measure stream)
            try:
                file.file.seek(0, 2)
                size = int(file.file.tell() or 0)
                file.file.seek(0)
            except Exception:
                size = 0

            if size and size > settings.audio_max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Audio file too large ({size} bytes). Max is {settings.audio_max_bytes} bytes.",
                )

            transcriber = TranscriberService()

            text = transcriber.transcribe(file.file)
            if not text:
                raise HTTPException(
                    status_code=422,
                    detail="No speech detected. Try a clearer recording or upload a .wav file.",
                )

            return {
                "text": text,
                "filename": file.filename,
                "status": "success",
            }
        except Exception as e:
            msg = str(e)
            logger.error(f"Transcription failed: {msg}")

            # Common local-decode failure: ffmpeg missing or unsupported format
            lowered = msg.lower()
            if "ffmpeg" in lowered or "could not decode" in lowered or "invalid data found" in lowered:
                raise HTTPException(
                    status_code=422,
                    detail="Could not decode this audio. If you recorded in-browser, try exporting WAV. Local decoding may require FFmpeg installed.",
                )
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail="Transcription failed")

else:

    @router.post("/transcribe")
    async def transcribe_audio_unavailable():
        raise HTTPException(
            status_code=503,
            detail='File upload requires "python-multipart". Install it with: pip install python-multipart',
        )
