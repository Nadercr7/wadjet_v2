"""TTS Service — Smart fallback: Gemini TTS → None (caller handles Groq/browser).

Uses Gemini 2.5 Flash Preview TTS as primary (FREE, 30 voices, 73+ languages).
Returns cached WAV path on success, or None so the caller (audio.py) can try Groq
PlayAI and ultimately return HTTP 204 for browser SpeechSynthesis fallback.
Audio is cached to disk by content hash for instant replay.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import wave
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "static" / "cache" / "audio"
TTS_MODEL = "gemini-2.5-flash-preview-tts"

# Voice presets per context (from constitution.md)
VOICE_PRESETS: dict[str, str] = {
    "thoth_chat": "Orus",        # Firm — authoritative ancient deity
    "landing": "Charon",         # Informative — warm guide
    "dictionary": "Rasalgethi",  # Informative — academic
    "pronunciation": "Rasalgethi",  # Academic — hieroglyphic sounds
    "story_narration": "Aoede",  # Breezy — myths
    "explore": "Charon",         # Informative — landmark descriptions
    "scan": "Charon",            # Informative — scan results
    "scan_pronunciation": "Rasalgethi",  # Academic — scan transliteration
    "default": "Charon",         # Informative — general fallback
}

# Director's notes per context for richer performance
DIRECTOR_NOTES: dict[str, str] = {
    "thoth_chat": (
        "You are Thoth, an ancient Egyptian deity of wisdom and writing. "
        "Speak with gravitas, authority, and warmth. Your tone is that of a wise "
        "teacher sharing sacred knowledge. Measured pace, deep resonance."
    ),
    "landing": (
        "You are a knowledgeable museum guide welcoming visitors to an Egyptian "
        "heritage exhibit. Warm, inviting, and informative. Clear enunciation."
    ),
    "dictionary": (
        "You are an Egyptology professor explaining hieroglyphic signs. "
        "Academic but accessible. Clear, measured, precise pronunciation."
    ),
    "story_narration": (
        "You are a storyteller narrating an ancient Egyptian myth. "
        "Captivating, with dramatic pauses and vivid expression. "
        "Draw the listener into the ancient world."
    ),
    "explore": (
        "You are an expert Egyptologist giving a guided tour of a monument. "
        "Speak with wonder and reverence. Paint vivid scenes of ancient grandeur. "
        "Clear enunciation, warm and engaging."
    ),
    "scan": (
        "You are an Egyptologist examining a hieroglyphic inscription. "
        "Read the translation with scholarly clarity and measured pace. "
        "Precise pronunciation, confident delivery."
    ),
    "pronunciation": (
        "You are an Egyptology professor teaching hieroglyphic pronunciation. "
        "Speak clearly, slowly, and precisely with academic authority. "
        "Pronounce this ancient Egyptian sound:"
    ),
    "scan_pronunciation": (
        "You are an Egyptology professor reading an ancient Egyptian word aloud. "
        "Speak clearly, slowly, and precisely with academic authority. "
        "Pronounce this ancient Egyptian sound:"
    ),
}


def _cache_key(text: str, voice: str) -> str:
    """Generate a deterministic filename from text + voice."""
    h = hashlib.sha256(f"{voice}:{text}".encode()).hexdigest()[:16]
    return f"{voice.lower()}_{h}.wav"


def _pcm_to_wav(pcm_data: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
    """Wrap raw PCM data in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


async def speak(
    text: str,
    *,
    lang: str = "en",
    context: str = "default",
) -> Path | None:
    """Generate TTS audio, return path to cached WAV file or None.

    Fallback chain: Gemini TTS → None (caller handles Groq/browser fallback).
    """
    if not text or not text.strip():
        return None

    text = text[:5000]  # Limit length
    voice = VOICE_PRESETS.get(context, VOICE_PRESETS["default"])

    # Check cache first (offload blocking I/O to thread)
    await asyncio.to_thread(CACHE_DIR.mkdir, parents=True, exist_ok=True)
    cache_file = CACHE_DIR / _cache_key(text, voice)
    if await asyncio.to_thread(lambda: cache_file.exists() and cache_file.stat().st_size > 0):
        return cache_file

    # Try Gemini TTS
    keys = settings.gemini_keys_list
    if keys:
        try:
            audio_path = await _gemini_tts(text, voice, context, cache_file, keys, lang=lang)
            if audio_path:
                return audio_path
        except Exception as e:
            logger.warning("Gemini TTS failed: %s", e)

    return None


async def _gemini_tts(
    text: str,
    voice: str,
    context: str,
    cache_file: Path,
    api_keys: list[str],
    lang: str = "en",
) -> Path | None:
    """Generate audio via Gemini 2.5 Flash TTS."""
    # Build the prompt with optional director's notes and language hint
    notes = DIRECTOR_NOTES.get(context, "")
    lang_hint = f"Speak in {'Arabic' if lang == 'ar' else 'English'}." if lang else ""
    parts = [p for p in (notes, lang_hint, text) if p]
    prompt = "\n\n".join(parts)

    # Try keys from the pool (randomized to distribute quota)
    import random as _rng
    keys_to_try = _rng.sample(api_keys, min(5, len(api_keys)))
    last_error: Exception | None = None
    for key in keys_to_try:
        try:
            client = genai.Client(api_key=key)
            response = await client.aio.models.generate_content(
                model=TTS_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=genai_types.SpeechConfig(
                        voice_config=genai_types.VoiceConfig(
                            prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                                voice_name=voice,
                            )
                        )
                    ),
                ),
            )

            # Extract PCM audio data
            pcm_data = response.candidates[0].content.parts[0].inline_data.data
            if not pcm_data:
                continue

            # Wrap in WAV and cache atomically (write to .tmp, then rename)
            wav_data = _pcm_to_wav(pcm_data)
            tmp_file = cache_file.with_suffix(".tmp")
            await asyncio.to_thread(tmp_file.write_bytes, wav_data)
            await asyncio.to_thread(tmp_file.rename, cache_file)
            logger.info("Gemini TTS: cached %s (%d bytes)", cache_file.name, len(wav_data))
            return cache_file

        except Exception as e:
            last_error = e
            logger.warning("Gemini TTS key failed: %s", e)
            continue

    if last_error:
        raise last_error
    return None
