"""Unified AI Service — multi-provider orchestration with automatic fallback.

Provides vision reading and text generation across:
1. Gemini (17 keys, primary — google-genai library)
2. Groq (Llama 4 Scout vision, free tier — OpenAI-compatible)
3. Grok (8 keys, tiebreaker — OpenAI-compatible)

Each provider handles its own key rotation internally.
This service orchestrates cross-provider fallback.
"""

from __future__ import annotations

import asyncio
import base64
import itertools
import json
import logging
from typing import TYPE_CHECKING, Any

import cv2
import httpx
import numpy as np

if TYPE_CHECKING:
    from app.core.gemini_service import GeminiService
    from app.core.grok_service import GrokService

logger = logging.getLogger(__name__)

_GROQ_API_BASE = "https://api.groq.com/openai/v1"
_GROQ_TIMEOUT = 60.0
_MAX_RETRIES = 2
_BASE_BACKOFF_S = 1.0
_MAX_BASE64_BYTES = 500_000  # Compress images larger than this for base64 APIs


def _compress_image_bytes(image_bytes: bytes, max_bytes: int = _MAX_BASE64_BYTES) -> bytes:
    """Compress image JPEG bytes if they exceed max_bytes."""
    if len(image_bytes) <= max_bytes:
        return image_bytes
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return image_bytes
    h, w = img.shape[:2]
    scale = min(1.0, 1024 / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return bytes(buf)


# ── Groq Service ──


class GroqService:
    """Async Groq client (OpenAI-compatible API) with key rotation.

    Vision via Llama 4 Scout, text via Llama 3.3 70B.
    Free tier per key: 30 RPM, 1000 req/day.
    Multiple keys multiply effective rate limits.
    """

    def __init__(
        self,
        api_keys: list[str],
        *,
        vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct",
        text_model: str = "llama-3.3-70b-versatile",
    ) -> None:
        if not api_keys:
            raise ValueError("At least one Groq API key is required.")
        self._api_keys = api_keys
        self._key_cycle = itertools.cycle(range(len(api_keys)))
        self._current_key_idx: int = next(self._key_cycle)
        self.vision_model = vision_model
        self.text_model = text_model
        self._client = httpx.AsyncClient(
            base_url=_GROQ_API_BASE,
            timeout=httpx.Timeout(_GROQ_TIMEOUT, connect=10.0),
        )
        logger.info("GroqService init: %d keys, vision=%s, text=%s", len(api_keys), vision_model, text_model)

    @property
    def available(self) -> bool:
        return len(self._api_keys) > 0

    def _current_key(self) -> str:
        return self._api_keys[self._current_key_idx]

    def _rotate_key(self) -> None:
        prev = self._current_key_idx
        self._current_key_idx = next(self._key_cycle)
        logger.warning("Rotated Groq key %d -> %d", prev + 1, self._current_key_idx + 1)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._current_key()}",
            "Content-Type": "application/json",
        }

    async def _chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> dict:
        """Core chat completion with retry on rate limits."""
        payload: dict[str, Any] = {
            "model": model or self.text_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await self._client.post(
                    "/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code == 429:
                    self._rotate_key()
                    last_error = httpx.HTTPStatusError(
                        "Rate limited", request=resp.request, response=resp,
                    )
                    await asyncio.sleep(_BASE_BACKOFF_S * (2**attempt))
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    self._rotate_key()
                    last_error = exc
                    await asyncio.sleep(_BASE_BACKOFF_S * (2**attempt))
                    continue
                raise
            except httpx.TimeoutException as exc:
                last_error = exc
                await asyncio.sleep(_BASE_BACKOFF_S * (2**attempt))
                continue
        raise RuntimeError("Groq unavailable after retries") from last_error

    def _extract_text(self, response: dict) -> str:
        choices = response.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    async def vision_json(
        self,
        image_bytes: bytes,
        mime_type: str,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 2048,
    ) -> dict | None:
        """Send image to Groq vision model and parse JSON response."""
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
        try:
            resp = await self._chat_completion(
                messages,
                model=self.vision_model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            text = self._extract_text(resp)
            return json.loads(text) if text else None
        except Exception:
            logger.warning("Groq vision_json failed", exc_info=True)
            return None

    async def text_json(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 1024,
    ) -> dict | None:
        """Text-only JSON generation."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        try:
            resp = await self._chat_completion(
                messages,
                model=self.text_model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            text = self._extract_text(resp)
            return json.loads(text) if text else None
        except Exception:
            logger.warning("Groq text_json failed", exc_info=True)
            return None

    async def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Free-text generation (no JSON forcing)."""
        messages: list[dict[str, Any]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        resp = await self._chat_completion(
            messages,
            model=self.text_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self._extract_text(resp)

    async def generate_text_stream(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        """Streaming free-text generation via SSE."""
        messages: list[dict[str, Any]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.text_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with self._client.stream(
                    "POST",
                    "/chat/completions",
                    headers=self._headers(),
                    json=payload,
                ) as resp:
                    if resp.status_code == 429:
                        self._rotate_key()
                        last_error = RuntimeError("Rate limited")
                        await asyncio.sleep(_BASE_BACKOFF_S * (2**attempt))
                        continue
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            return
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            text = delta.get("content", "")
                            if text:
                                yield text
                        except json.JSONDecodeError:
                            continue
                    return  # stream finished normally
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    self._rotate_key()
                    last_error = exc
                    await asyncio.sleep(_BASE_BACKOFF_S * (2**attempt))
                    continue
                raise
            except httpx.TimeoutException as exc:
                last_error = exc
                await asyncio.sleep(_BASE_BACKOFF_S * (2**attempt))
                continue
        raise RuntimeError("Groq stream unavailable after retries") from last_error

    async def close(self) -> None:
        await self._client.aclose()


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
        resp = await self._grok._chat_completion(
            messages,
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        text = self._grok._extract_text(resp)
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
        resp = await self._grok._chat_completion(
            messages,
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        text = self._grok._extract_text(resp)
        return json.loads(text) if text else None

    async def close(self) -> None:
        """Close HTTP clients for providers that own them."""
        if self._groq:
            await self._groq.close()
