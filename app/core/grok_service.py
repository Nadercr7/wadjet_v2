"""Grok Service — async vision + text client with key rotation.

Uses the OpenAI-compatible xAI API (https://api.x.ai/v1).
Provides landmark identification, hieroglyph classification, text chat,
and streaming chat — all as tiebreaker/fallback to Gemini.
"""

from __future__ import annotations

import asyncio
import base64
import itertools
import json
import logging
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

_API_BASE = "https://api.x.ai/v1"
_MAX_RETRIES = 3
_BASE_BACKOFF_S = 1.0
_TIMEOUT = 60.0


class GrokService:
    """Async Grok client with round-robin key rotation."""

    def __init__(
        self,
        api_keys: list[str],
        *,
        default_model: str = "grok-4-latest",
    ) -> None:
        if not api_keys:
            raise ValueError("At least one Grok API key is required.")
        self._api_keys = api_keys
        self._key_cycle = itertools.cycle(range(len(api_keys)))
        self._current_key_idx: int = next(self._key_cycle)
        self.default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=_API_BASE,
            timeout=httpx.Timeout(_TIMEOUT, connect=10.0),
        )
        logger.info("GrokService init: %d keys, model=%s", len(api_keys), default_model)

    @property
    def available(self) -> bool:
        return len(self._api_keys) > 0

    def _current_key(self) -> str:
        return self._api_keys[self._current_key_idx]

    def _rotate_key(self) -> None:
        prev = self._current_key_idx
        self._current_key_idx = next(self._key_cycle)
        logger.warning("Rotated Grok key %d -> %d", prev + 1, self._current_key_idx + 1)

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
        temperature: float = 0.3,
        max_tokens: int = 512,
        response_format: dict | None = None,
    ) -> dict:
        """Core chat completions call with retry + key rotation."""
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
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
                        "Rate limited", request=resp.request, response=resp
                    )
                    await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    self._rotate_key()
                    last_error = exc
                    await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                    continue
                raise
            except httpx.TimeoutException as exc:
                last_error = exc
                await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                continue
        raise RuntimeError("Grok unavailable after retries") from last_error

    def _extract_text(self, response: dict) -> str:
        """Extract text from chat completion response."""
        choices = response.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    # ── Vision helpers ─────────────────────────────────────────────

    def _image_message(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
    ) -> list[dict]:
        """Build messages with inline base64 image for vision."""
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64}",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

    # ── Landmark identification ────────────────────────────────────

    async def identify_landmark(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> dict:
        """Identify an Egyptian landmark from an image.

        Returns: {name, slug, confidence, description} or empty dict.
        """
        system = (
            "You are an expert on Egyptian landmarks and archaeological sites. "
            "Identify the Egyptian landmark in the photo. Respond ONLY with valid JSON."
        )
        prompt = (
            "Identify the Egyptian landmark in this image. "
            "Return JSON with these exact keys:\n"
            '{"name": "display name", "slug": "snake_case_id", '
            '"confidence": 0.0-1.0, "description": "1-2 sentence description"}\n'
            "If this is not an Egyptian landmark, return "
            '{"name": "", "slug": "", "confidence": 0.0, '
            '"description": "Not an Egyptian landmark"}'
        )
        messages = [
            {"role": "system", "content": system},
            *self._image_message(image_bytes, mime_type, prompt),
        ]
        try:
            resp = await self._chat_completion(
                messages,
                temperature=0.2,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
            text = self._extract_text(resp)
            return json.loads(text) if text else {}
        except Exception:
            logger.exception("Grok identify_landmark failed")
            return {}

    # ── Hieroglyph classification ──────────────────────────────────

    async def classify_hieroglyph(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        known_classes: list[str] | None = None,
    ) -> dict:
        """Classify a cropped hieroglyph image.

        Returns: {gardiner_code, name, confidence} or empty dict.
        """
        class_hint = ""
        if known_classes:
            class_hint = (
                f"\nThe valid Gardiner codes are: {', '.join(known_classes[:50])}... "
                f"({len(known_classes)} total). Only return codes from this set."
            )

        system = (
            "You are an expert Egyptologist specializing in hieroglyphic classification. "
            "You know the Gardiner Sign List exhaustively. Respond ONLY with valid JSON."
        )
        prompt = (
            "Classify the hieroglyph in this image using the Gardiner Sign List. "
            "Return JSON with these exact keys:\n"
            '{"gardiner_code": "e.g. A1", "name": "glyph name/description", '
            '"confidence": 0.0-1.0}\n'
            "If this is not a recognizable hieroglyph, return "
            '{"gardiner_code": "", "name": "Unknown", "confidence": 0.0}'
            + class_hint
        )
        messages = [
            {"role": "system", "content": system},
            *self._image_message(image_bytes, mime_type, prompt),
        ]
        try:
            resp = await self._chat_completion(
                messages,
                temperature=0.1,
                max_tokens=256,
                response_format={"type": "json_object"},
            )
            text = self._extract_text(resp)
            return json.loads(text) if text else {}
        except Exception:
            logger.exception("Grok classify_hieroglyph failed")
            return {}

    # ── Text generation (chat fallback) ────────────────────────────

    async def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Simple text generation — used as Thoth chat fallback."""
        messages: list[dict[str, Any]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = await self._chat_completion(
                messages, temperature=temperature, max_tokens=max_tokens,
            )
            return self._extract_text(resp)
        except Exception:
            logger.exception("Grok generate_text failed")
            return ""

    # ── Streaming text (chat fallback) ─────────────────────────────

    async def generate_text_stream(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Streaming text generation with retry + key rotation."""
        messages: list[dict[str, Any]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.default_model,
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
                        await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                        continue
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            text = delta.get("content", "")
                            if text:
                                yield text
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                    return  # stream completed successfully
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    self._rotate_key()
                    last_error = exc
                    await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                    continue
                raise
            except httpx.TimeoutException as exc:
                last_error = exc
                await asyncio.sleep(_BASE_BACKOFF_S * (2 ** attempt))
                continue
        logger.error("Grok streaming failed after %d retries", _MAX_RETRIES)
        if last_error:
            raise last_error

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
