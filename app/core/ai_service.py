"""Unified AI Service — multi-provider orchestration with automatic fallback.

Provides vision reading and text generation across:
1. Gemini (17 keys, primary — google-genai library)
2. Groq (Llama 4 Scout vision, free tier — OpenAI-compatible)
3. Grok (8 keys, tiebreaker — OpenAI-compatible)

Each provider handles its own key rotation internally.
This service orchestrates cross-provider fallback.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.gemini_service import GeminiService
    from app.core.grok_service import GrokService

from app.core.groq_service import GroqService, _compress_image_bytes  # noqa: F401

logger = logging.getLogger(__name__)


# ── Unified AI Service ──


class AIService:
    """Unified multi-provider AI service with automatic fallback.

    Provider priority: Gemini → Groq → Grok.
    Each provider has internal key rotation. This service handles
    cross-provider fallback when a provider is unavailable or errors.
    """

    def __init__(
        self,
        gemini: GeminiService | None = None,
        groq: GroqService | None = None,
        grok: GrokService | None = None,
    ) -> None:
        self._gemini = gemini
        self._groq = groq
        self._grok = grok
        providers = []
        if gemini and gemini.available:
            providers.append("gemini")
        if groq and groq.available:
            providers.append("groq")
        if grok and grok.available:
            providers.append("grok")
        logger.info("AIService init: providers=%s", providers)

    @property
    def available(self) -> bool:
        return any([
            self._gemini and self._gemini.available,
            self._groq and self._groq.available,
            self._grok and self._grok.available,
        ])

    @property
    def gemini(self) -> GeminiService | None:
        return self._gemini

    @property
    def groq(self) -> GroqService | None:
        return self._groq

    @property
    def grok(self) -> GrokService | None:
        return self._grok

    async def vision_json(
        self,
        image_bytes: bytes,
        mime_type: str,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 2048,
    ) -> tuple[dict | None, str]:
        """Send image + prompt to vision model, get JSON response.

        Tries providers in order: Gemini → Groq → Grok.
        Returns (parsed_dict_or_None, provider_name).
        """
        # 1. Gemini Vision
        if self._gemini and self._gemini.available:
            try:
                result = await self._gemini_vision_json(
                    image_bytes, mime_type, system, prompt, max_tokens,
                )
                if result:
                    return result, "gemini"
                logger.info("Gemini vision returned empty, trying Groq")
            except Exception:
                logger.warning("Gemini vision failed, trying Groq", exc_info=True)

        # 2. Groq Vision (Llama 4 Scout)
        if self._groq and self._groq.available:
            try:
                result = await self._groq.vision_json(
                    image_bytes, mime_type, system, prompt, max_tokens=max_tokens,
                )
                if result:
                    return result, "groq"
                logger.info("Groq vision returned empty, trying Grok")
            except Exception:
                logger.warning("Groq vision failed, trying Grok", exc_info=True)

        # 3. Grok Vision
        if self._grok and self._grok.available:
            try:
                result = await self._grok_vision_json(
                    image_bytes, mime_type, system, prompt, max_tokens,
                )
                if result:
                    return result, "grok"
                logger.info("Grok vision returned empty")
            except Exception:
                logger.warning("Grok vision failed, all providers exhausted", exc_info=True)

        return None, "none"

    async def text_json(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 1024,
    ) -> tuple[dict | None, str]:
        """Text-only JSON generation with fallback.

        Returns (parsed_dict_or_None, provider_name).
        """
        # 1. Gemini
        if self._gemini and self._gemini.available:
            try:
                result = await self._gemini_text_json(system, prompt, max_tokens)
                if result:
                    return result, "gemini"
            except Exception:
                logger.warning("Gemini text failed, trying Groq", exc_info=True)

        # 2. Groq
        if self._groq and self._groq.available:
            try:
                result = await self._groq.text_json(
                    system, prompt, max_tokens=max_tokens,
                )
                if result:
                    return result, "groq"
            except Exception:
                logger.warning("Groq text failed, trying Grok", exc_info=True)

        # 3. Grok
        if self._grok and self._grok.available:
            try:
                result = await self._grok_text_json(system, prompt, max_tokens)
                if result:
                    return result, "grok"
            except Exception:
                logger.warning("Grok text failed, all providers exhausted", exc_info=True)

        return None, "none"

    # ── Gemini adapters ──

    async def _gemini_vision_json(
        self,
        image_bytes: bytes,
        mime_type: str,
        system: str,
        prompt: str,
        max_tokens: int,
    ) -> dict | None:
        from google.genai import types as genai_types

        image_part = genai_types.Part.from_bytes(
            data=image_bytes, mime_type=mime_type,
        )
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.1,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )
        response = await self._gemini._generate_with_retry(
            model=self._gemini.default_model,
            contents=[prompt, image_part],
            config=config,
        )
        text = response.text or ""
        return json.loads(text) if text.strip() else None

    async def _gemini_text_json(
        self,
        system: str,
        prompt: str,
        max_tokens: int,
    ) -> dict | None:
        text = await self._gemini.generate_json(
            prompt,
            system_instruction=system,
            max_output_tokens=max_tokens,
            temperature=0.1,
        )
        return json.loads(text) if text and text.strip() else None

    # ── Grok adapters ──

    async def _grok_vision_json(
        self,
        image_bytes: bytes,
        mime_type: str,
        system: str,
        prompt: str,
        max_tokens: int,
    ) -> dict | None:
        compressed = _compress_image_bytes(image_bytes)
        b64 = base64.b64encode(compressed).decode("ascii")
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        resp = await self._grok.chat_completion(
            messages,
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        text = self._grok.extract_text(resp)
        return json.loads(text) if text else None

    async def _grok_text_json(
        self,
        system: str,
        prompt: str,
        max_tokens: int,
    ) -> dict | None:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        resp = await self._grok.chat_completion(
            messages,
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        text = self._grok.extract_text(resp)
        return json.loads(text) if text else None

    async def close(self) -> None:
        """Close HTTP clients for providers that own them."""
        if self._groq:
            await self._groq.close()
