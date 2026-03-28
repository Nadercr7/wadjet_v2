"""
Wadjet v2 — Audio API (TTS + STT via Groq)
Optional server-side high-quality TTS and speech-to-text.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["audio"])

# ── Groq TTS ──────────────────────────────────────────────────────────────
# Model: playai-tts (PlayAI voices) — free tier on Groq
# Endpoint: POST https://api.groq.com/openai/v1/audio/speech
# Returns: audio/wav

# Voice mapping per language
_VOICE_MAP = {
    "en": "Fritz-PlayAI",       # English male — clear, natural
    "ar": "Arista-PlayAI",      # Arabic-friendly female voice
}

_TTS_MODEL = "playai-tts"


@router.post("/tts")
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
        resp = await groq._client.post(
            "/audio/speech",
            headers=groq._headers(),
            json={
                "model": _TTS_MODEL,
                "input": text[:2000],
                "voice": voice,
                "response_format": "wav",
            },
            timeout=30.0,
        )
        resp.raise_for_status()

        return Response(
            content=resp.content,
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

    # Read file (limit 25MB — Groq's limit)
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large (max 25 MB)")

    try:
        # Use only Authorization header — httpx needs to set multipart Content-Type
        auth_header = {"Authorization": f"Bearer {groq._current_key()}"}
        resp = await groq._client.post(
            "/audio/transcriptions",
            headers=auth_header,
            files={"file": (file.filename or "audio.wav", data, base_type)},
            data={
                "model": _STT_MODEL,
                "language": lang[:2],
                "response_format": "json",
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        result = resp.json()

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
    context: str = Field(default="default", max_length=30)


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
            resp = await groq._client.post(
                "/audio/speech",
                headers=groq._headers(),
                json={
                    "model": _TTS_MODEL,
                    "input": body.text[:2000],
                    "voice": voice,
                    "response_format": "wav",
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            return Response(
                content=resp.content,
                media_type="audio/wav",
                headers={"Cache-Control": "public, max-age=3600"},
            )
        except Exception as e:
            logger.warning("Groq TTS fallback failed: %s", e)

    # No server TTS available — 204 tells frontend to use browser SpeechSynthesis
    return Response(status_code=204)
