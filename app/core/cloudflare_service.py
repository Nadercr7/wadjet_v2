"""Cloudflare Workers AI Service — vision + text via Cloudflare REST API.

Free tier: 10,000 neurons/day. No key rotation needed (single token).
Vision model: @cf/meta/llama-3.2-11b-vision-instruct
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_CF_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
_TIMEOUT = 60.0
_MAX_IMAGE_BYTES = 500_000


def _compress_for_cf(image_bytes: bytes, max_bytes: int = _MAX_IMAGE_BYTES) -> bytes:
    """Compress image if too large for Cloudflare."""
    if len(image_bytes) <= max_bytes:
        return image_bytes
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes
        h, w = img.shape[:2]
        scale = min(1.0, 1024 / max(h, w))
        if scale < 1.0:
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return bytes(buf)
    except Exception:
        return image_bytes


class CloudflareService:
    """Async Cloudflare Workers AI client for vision tasks."""

    def __init__(
        self,
        api_token: str,
        account_id: str,
        *,
        vision_model: str = "@cf/meta/llama-3.2-11b-vision-instruct",
    ) -> None:
        self._api_token = api_token
        self._account_id = account_id
        self.vision_model = vision_model
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(_TIMEOUT, connect=10.0),
        )
        logger.info("CloudflareService init: model=%s", vision_model)

    @property
    def available(self) -> bool:
        return bool(self._api_token and self._account_id)

    def _url(self, model: str) -> str:
        return f"{_CF_API_BASE}/{self._account_id}/ai/run/{model}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    async def _run_model(
        self,
        model: str,
        payload: dict[str, Any],
    ) -> dict:
        """Call a Cloudflare Workers AI model."""
        resp = await self._client.post(
            self._url(model),
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            errors = data.get("errors", [])
            raise RuntimeError(f"Cloudflare AI error: {errors}")
        return data.get("result", {})

    async def vision_json(
        self,
        image_bytes: bytes,
        mime_type: str,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 512,
    ) -> dict | None:
        """Send image to Cloudflare vision model and parse JSON response."""
        compressed = _compress_for_cf(image_bytes)
        b64 = base64.b64encode(compressed).decode("ascii")
        payload = {
            "messages": [
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
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        try:
            result = await self._run_model(self.vision_model, payload)
            text = result.get("response", "")
            if not text:
                return None
            # Try to extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            return None
        except Exception:
            logger.warning("Cloudflare vision_json failed", exc_info=True)
            return None

    async def identify_landmark(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> dict:
        """Identify an Egyptian landmark from an image."""
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
        result = await self.vision_json(
            image_bytes, mime_type, system, prompt, max_tokens=512,
        )
        return result or {}

    async def close(self) -> None:
        await self._client.aclose()
