"""Groq Service — async client with key rotation (OpenAI-compatible API).

Vision via Llama 4 Scout, text via Llama 3.3 70B.
Free tier per key: 30 RPM, 1000 req/day.
Multiple keys multiply effective rate limits.
"""

from __future__ import annotations

import asyncio
import base64
import itertools
import json
import logging
from typing import Any

import cv2
import httpx
import numpy as np

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

    async def chat_completion(
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

    def extract_text(self, response: dict) -> str:
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
            resp = await self.chat_completion(
                messages,
                model=self.vision_model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            text = self.extract_text(resp)
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
            resp = await self.chat_completion(
                messages,
                model=self.text_model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            text = self.extract_text(resp)
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
        resp = await self.chat_completion(
            messages,
            model=self.text_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self.extract_text(resp)

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

    async def tts(
        self,
        text: str,
        *,
        model: str = "playai-tts",
        voice: str = "Fritz-PlayAI",
        response_format: str = "wav",
        timeout: float = 30.0,
    ) -> bytes:
        """Generate speech audio via Groq TTS. Returns raw audio bytes."""
        resp = await self._client.post(
            "/audio/speech",
            headers=self._headers(),
            json={
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": response_format,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.content

    async def stt(
        self,
        audio_data: bytes,
        filename: str,
        mime_type: str,
        *,
        model: str = "whisper-large-v3-turbo",
        language: str = "en",
        timeout: float = 60.0,
    ) -> dict:
        """Transcribe audio via Groq Whisper. Returns JSON result."""
        auth_header = {"Authorization": f"Bearer {self._current_key()}"}
        resp = await self._client.post(
            "/audio/transcriptions",
            headers=auth_header,
            files={"file": (filename, audio_data, mime_type)},
            data={
                "model": model,
                "language": language[:2],
                "response_format": "json",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
