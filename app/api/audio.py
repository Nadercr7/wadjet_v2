"""
Wadjet v3 — Audio API (TTS + STT)
Server-side TTS (Gemini → Groq fallback) and speech-to-text.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["audio"])

# ── Constants ─────────────────────────────────────────────────────────────
_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB (Groq limit)

# Magic bytes for audio format validation
_AUDIO_MAGIC: dict[str, list[bytes]] = {
    "audio/wav": [b"RIFF"],
    "audio/mpeg": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"],
    "audio/ogg": [b"OggS"],
    "audio/flac": [b"fLaC"],
    "audio/webm": [b"\x1a\x45\xdf\xa3"],
    "video/webm": [b"\x1a\x45\xdf\xa3"],
    "audio/mp4": [b"\x00\x00\x00"],  # ftyp box (variable offset)
    "audio/x-m4a": [b"\x00\x00\x00"],
}

# Voice mapping per language
_VOICE_MAP = {
    "en": "Fritz-PlayAI",
    "ar": "Arista-PlayAI",
}

_TTS_MODEL = "playai-tts"
_STT_MODEL = "whisper-large-v3-turbo"


def _validate_audio_magic(data: bytes, mime_type: str) -> bool:
    """Check if audio data starts with expected magic bytes for the MIME type."""
    magic_options = _AUDIO_MAGIC.get(mime_type)
    if not magic_options:
        return True  # unknown type — skip check
    return any(data[:len(m)] == m for m in magic_options)


@router.post("/tts")
@limiter.limit("20/minute")
async def text_to_speech(
    request: Request,
    text: str = Form(..., min_length=1, max_length=2000),
    lang: str = Form("en"),
):
    """Convert text to speech audio via Groq PlayAI TTS.

    Returns audio/wav. Falls back to 404 if Groq unavailable.
    """
    groq = getattr(request.app.state, "groq", None)
    if not groq:
        raise HTTPException(status_code=404, detail="Groq TTS not available")

    voice = _VOICE_MAP.get(lang, _VOICE_MAP["en"])

    try:
        audio_bytes = await groq.tts(
            text[:2000],
            model=_TTS_MODEL,
            voice=voice,
            response_format="wav",
        )
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    except Exception as e:
        logger.warning("Groq TTS failed: %s", e)
        raise HTTPException(status_code=502, detail="TTS generation failed")


# ── Groq STT ──────────────────────────────────────────────────────────────
# Model: whisper-large-v3-turbo — free tier on Groq
# Endpoint: POST https://api.groq.com/openai/v1/audio/transcriptions

_STT_MODEL = "whisper-large-v3-turbo"


@router.post("/stt")
@limiter.limit("10/minute")
async def speech_to_text(
    request: Request,
    file: UploadFile = File(...),
    lang: str = Form("en"),
):
    """Transcribe audio to text via Groq Whisper.

    Accepts audio files (wav, mp3, webm, m4a). Returns JSON with transcription.
    """
    groq = getattr(request.app.state, "groq", None)
    if not groq:
        raise HTTPException(status_code=404, detail="Groq STT not available")

    # Validate file type (strip codecs suffix: "audio/webm;codecs=opus" → "audio/webm")
    allowed = {"audio/wav", "audio/mpeg", "audio/webm", "audio/mp4", "audio/x-m4a",
               "audio/ogg", "video/webm"}
    content_type = file.content_type or ""
    base_type = content_type.split(";")[0].strip()
    if base_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {content_type}",
        )

    # Pre-check Content-Length before reading full file
    cl = request.headers.get("content-length")
    if cl and int(cl) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 25 MB)")

    # Read file
    data = await file.read()
    if len(data) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 25 MB)")

    # Validate magic bytes
    if not _validate_audio_magic(data, base_type):
        raise HTTPException(status_code=400, detail="File content does not match declared audio format")

    try:
        result = await groq.stt(
            data,
            file.filename or "audio.wav",
            base_type,
            model=_STT_MODEL,
            language=lang,
        )
        return {
            "text": result.get("text", ""),
            "language": lang,
        }

    except Exception as e:
        logger.warning("Groq STT failed: %s", e)
        raise HTTPException(status_code=502, detail="Speech-to-text failed")


# ── Gemini TTS (Smart Fallback Primary) ───────────────────────────────────
# Model: gemini-2.5-flash-preview-tts (30 voices, 73+ langs, FREE)
# Fallback: Groq PlayAI → 204 (browser SpeechSynthesis)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    lang: str = Field(default="en", max_length=5)
    context: str = Field(default="default", pattern=r"^[a-z_]{1,30}$")


@router.post("/audio/speak")
@limiter.limit("20/minute")
async def speak(request: Request, body: SpeakRequest):
    """Generate TTS audio via Gemini (primary) → Groq (fallback) → 204 (browser).

    Returns WAV audio on success, or 204 if no server TTS available.
    """
    from app.core.tts_service import speak as tts_speak

    audio_path = await tts_speak(body.text, lang=body.lang, context=body.context)
    if audio_path:
        return FileResponse(
            audio_path,
            media_type="audio/wav",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # Fallback: try existing Groq TTS
    groq = getattr(request.app.state, "groq", None)
    if groq:
        voice = _VOICE_MAP.get(body.lang, _VOICE_MAP["en"])
        try:
            audio_bytes = await groq.tts(
                body.text[:2000],
                model=_TTS_MODEL,
                voice=voice,
                response_format="wav",
            )
            return Response(
                content=audio_bytes,
                media_type="audio/wav",
                headers={"Cache-Control": "public, max-age=3600"},
            )
        except Exception as e:
            logger.warning("Groq TTS fallback failed: %s", e)

    # No server TTS available — 204 tells frontend to use browser SpeechSynthesis
    return Response(status_code=204)
