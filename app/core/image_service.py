"""Image Generation Service — AI scene illustrations for stories.

Fallback chain: Cloudflare FLUX.1 schnell → Cloudflare SDXL → None (UI shows placeholder).
Images are cached to disk by content hash for instant reload.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "static" / "cache" / "images"

_CF_API_BASE = "https://api.cloudflare.com/client/v4/accounts"
_FLUX_MODEL = "@cf/black-forest-labs/FLUX-1-schnell"
_SDXL_MODEL = "@cf/stabilityai/stable-diffusion-xl-base-1.0"

EGYPTIAN_STYLE_SUFFIX = (
    ", ancient Egyptian art style, golden tones, hieroglyphs on walls, "
    "dramatic warm lighting, detailed oil painting, museum quality"
)


def _cache_key(story_id: str, chapter_idx: int, prompt: str) -> str:
    """Generate a deterministic filename from story + chapter + prompt."""
    h = hashlib.sha256(f"{story_id}-{chapter_idx}-{prompt}".encode()).hexdigest()[:16]
    return f"story_{story_id}_{chapter_idx}_{h}"


async def generate_story_image(
    prompt: str,
    story_id: str,
    chapter_idx: int,
) -> str | None:
    """Generate scene image for a story chapter. Returns static URL path or None."""
    if not settings.cloudflare_api_token or not settings.cloudflare_account_id:
        return None

    await asyncio.to_thread(CACHE_DIR.mkdir, parents=True, exist_ok=True)

    key = _cache_key(story_id, chapter_idx, prompt)
    cache_path = CACHE_DIR / f"{key}.png"

    # Check cache first
    if await asyncio.to_thread(cache_path.exists):
        return f"/static/cache/images/{key}.png"

    full_prompt = prompt + EGYPTIAN_STYLE_SUFFIX

    # Try FLUX.1 schnell first (fastest, free)
    image_bytes = await _try_cloudflare(_FLUX_MODEL, full_prompt, num_steps=4)
    if not image_bytes:
        # Fallback to SDXL (more detailed, free)
        image_bytes = await _try_cloudflare(_SDXL_MODEL, full_prompt, num_steps=20)

    if image_bytes:
        # Atomic write: .tmp → rename
        tmp_path = cache_path.with_suffix(".tmp")
        await asyncio.to_thread(tmp_path.write_bytes, image_bytes)
        await asyncio.to_thread(tmp_path.rename, cache_path)
        logger.info("Image cached: %s (%d bytes)", cache_path.name, len(image_bytes))
        return f"/static/cache/images/{key}.png"

    return None


async def _try_cloudflare(model: str, prompt: str, num_steps: int = 4) -> bytes | None:
    """Attempt image generation via Cloudflare Workers AI."""
    url = f"{_CF_API_BASE}/{settings.cloudflare_account_id}/ai/run/{model}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
                json={"prompt": prompt, "num_steps": num_steps},
            )
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content
            logger.warning("Cloudflare %s returned status=%d len=%d", model, resp.status_code, len(resp.content))
    except Exception as e:
        logger.warning("Cloudflare image gen (%s) failed: %s", model, e)
    return None
