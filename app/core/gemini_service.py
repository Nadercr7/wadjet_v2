"""Gemini Service — async wrapper with key rotation.

Provides text generation, JSON generation, and streaming via
the google-genai library with round-robin key rotation on 429 errors.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
from typing import TYPE_CHECKING, Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_BACKOFF_S = 1.0


class GeminiService:
    """Async Gemini client with round-robin key rotation."""

    def __init__(
        self,
        api_keys: list[str],
        *,
        default_model: str = "gemini-2.5-flash",
    ) -> None:
        if not api_keys:
            raise ValueError("At least one Gemini API key is required.")
        self._api_keys = api_keys
        self._key_cycle = itertools.cycle(range(len(api_keys)))
        self._current_key_idx: int = next(self._key_cycle)
        self._clients = [genai.Client(api_key=k) for k in api_keys]
        self.default_model = default_model
        logger.info("GeminiService init: %d keys, model=%s", len(api_keys), default_model)

    @property
    def available(self) -> bool:
        return len(self._api_keys) > 0

    @property
    def api_keys(self) -> list[str]:
        """Public read-only access to API keys (for embedding clients etc.)."""
        return self._api_keys

    @property
    def _client(self) -> genai.Client:
        return self._clients[self._current_key_idx]

    def _rotate_key(self) -> None:
        prev = self._current_key_idx
        self._current_key_idx = next(self._key_cycle)
        logger.warning("Rotated Gemini key %d -> %d", prev + 1, self._current_key_idx + 1)

    async def _generate_with_retry(
        self,
        *,
        model: str,
        contents: Any,
        config: genai_types.GenerateContentConfig | None = None,
    ) -> genai_types.GenerateContentResponse:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return await self._client.aio.models.generate_content(
                    model=model, contents=contents, config=config,
                )
            except genai_errors.ClientError as exc:
                exc_str = str(exc)
                if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                    self._rotate_key()
                    last_error = exc
                    await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                    continue
                raise
            except genai_errors.ServerError as exc:
                last_error = exc
                await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                continue
        raise RuntimeError("Gemini unavailable after retries") from last_error

    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        response = await self._generate_with_retry(
            model=model or self.default_model, contents=prompt, config=config,
        )
        return response.text or ""

    async def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        config_kwargs: dict[str, Any] = {
            "system_instruction": system_instruction,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": "application/json",
        }
        if response_schema is not None:
            config_kwargs["response_json_schema"] = response_schema
        config = genai_types.GenerateContentConfig(**config_kwargs)
        response = await self._generate_with_retry(
            model=model or self.default_model, contents=prompt, config=config,
        )
        return response.text or "{}"

    async def generate_text_stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                stream = await self._client.aio.models.generate_content_stream(
                    model=model or self.default_model, contents=prompt, config=config,
                )
                async for chunk in stream:
                    if chunk.text:
                        yield chunk.text
                return
            except genai_errors.ClientError as exc:
                exc_str = str(exc)
                if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                    self._rotate_key()
                    last_error = exc
                    await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                    continue
                raise
            except genai_errors.ServerError as exc:
                last_error = exc
                await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                continue
        raise RuntimeError("Gemini streaming unavailable after retries") from last_error

    # ── Landmark identification (Gemini Vision) ────────────────────

    async def identify_landmark(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> dict:
        """Use Gemini Vision to identify an Egyptian landmark in an image.

        Returns dict: {name, slug, confidence, description} or empty on failure.
        """
        system = (
            "You are an expert on Egyptian landmarks and archaeological sites. "
            "Identify the Egyptian landmark in the photo. Respond ONLY with valid JSON."
        )
        prompt_text = (
            "Identify the Egyptian landmark in this image. "
            "Return JSON with these exact keys:\n"
            '{"name": "display name", "slug": "snake_case_id", '
            '"confidence": 0.0-1.0, "description": "1-2 sentence description"}\n'
            "If this is not an Egyptian landmark, return "
            '{"name": "", "slug": "", "confidence": 0.0, '
            '"description": "Not an Egyptian landmark"}'
        )

        image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        try:
            config = genai_types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.2,
                max_output_tokens=512,
                response_mime_type="application/json",
            )
            response = await self._generate_with_retry(
                model=self.default_model,
                contents=[prompt_text, image_part],
                config=config,
            )
            import json
            return json.loads(response.text or "{}")
        except Exception:
            logger.exception("Gemini identify_landmark failed")
            return {}

    async def describe_landmark(
        self,
        slug: str,
        name: str = "",
    ) -> str:
        """Generate a brief description for a known landmark.

        Text-only call (no image needed) — used for high-confidence enrichment.
        """
        display = name or slug.replace("_", " ").title()
        prompt = (
            f"Write a 2-3 sentence description of the Egyptian landmark "
            f'"{display}". Include its era, significance, and one interesting fact. '
            f"Be concise and informative."
        )
        try:
            return await self.generate_text(
                prompt,
                system_instruction="You are an expert Egyptian history guide.",
                temperature=0.4,
                max_output_tokens=256,
            )
        except Exception:
            logger.exception("Gemini describe_landmark failed")
            return ""

    # ── Text-to-Speech (Gemini TTS) ────────────────────────────────

    _TTS_MODEL = "gemini-2.5-flash-preview-tts"

    async def generate_tts(self, text: str) -> bytes | None:
        """Generate natural speech audio for a pronunciation string.

        Returns raw PCM audio bytes (L16, 24kHz, mono) or None on failure.
        """
        try:
            config = genai_types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai_types.SpeechConfig(
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                            voice_name="Rasalgethi",
                        ),
                    ),
                ),
            )
            prompt = (
                "You are an Egyptology professor teaching hieroglyphic pronunciation. "
                "Speak clearly and precisely, with academic authority. "
                f"Pronounce this ancient Egyptian sound slowly and clearly: {text}"
            )
            response = await self._generate_with_retry(
                model=self._TTS_MODEL,
                contents=prompt,
                config=config,
            )
            if (
                response.candidates
                and response.candidates[0].content.parts
            ):
                return response.candidates[0].content.parts[0].inline_data.data
            return None
        except Exception:
            logger.exception("Gemini TTS failed for text=%r", text)
            return None
