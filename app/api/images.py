"""Image proxy API — server-side Pexels search for the Android app.

The Android app uses Pexels photos as a fallback thumbnail source for
landmarks. Proxying the search here keeps the Pexels API keys server-side
(they previously shipped inside the APK via BuildConfig). Responses mirror
the Pexels /v1/search shape for the fields the client consumes
(photos[].src.large/medium/original + attribution fields).
"""

from __future__ import annotations

import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.models import User
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# In-memory TTL cache — Pexels free tier is 200 req/hr and landmark queries
# repeat heavily across users, so a small cache does most of the work.
_CACHE_TTL_SECONDS = 24 * 60 * 60
_CACHE_MAX_ENTRIES = 512
_cache: dict[tuple[str, int, str], tuple[float, dict]] = {}

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=15.0))
    return _client


async def close_images_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _cache_get(key: tuple[str, int, str]) -> dict | None:
    entry = _cache.get(key)
    if not entry:
        return None
    stamp, payload = entry
    if time.monotonic() - stamp > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return payload


def _cache_put(key: tuple[str, int, str], payload: dict) -> None:
    if len(_cache) >= _CACHE_MAX_ENTRIES:
        # Drop the oldest entry (insertion order ≈ age for a TTL cache)
        _cache.pop(next(iter(_cache)), None)
    _cache[key] = (time.monotonic(), payload)


def _slim_photo(photo: dict) -> dict:
    """Keep the fields the clients consume (src URLs + attribution)."""
    src = photo.get("src") or {}
    return {
        "id": photo.get("id"),
        "width": photo.get("width"),
        "height": photo.get("height"),
        "url": photo.get("url"),
        "photographer": photo.get("photographer"),
        "photographer_url": photo.get("photographer_url"),
        "alt": photo.get("alt"),
        "src": {
            "original": src.get("original"),
            "large": src.get("large"),
            "medium": src.get("medium"),
        },
    }


@router.get("/pexels-search")
@limiter.limit("30/minute")
async def pexels_search(
    request: Request,
    query: str = Query(min_length=1, max_length=200),
    per_page: int = Query(default=1, ge=1, le=15),
    orientation: str = Query(default="landscape", pattern="^(landscape|portrait|square)$"),
    user: User = Depends(get_current_user),
):
    """Search Pexels photos server-side (keys never leave the server)."""
    keys = settings.pexels_keys_list
    if not keys:
        raise HTTPException(status_code=503, detail="Image search not configured")

    cache_key = (query.strip().lower(), per_page, orientation)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {"query": query, "per_page": per_page, "orientation": orientation}
    client = _get_client()

    last_status = None
    for key in keys:
        try:
            resp = await client.get(
                PEXELS_SEARCH_URL, params=params, headers={"Authorization": key}
            )
        except httpx.HTTPError as e:
            logger.warning("Pexels request failed: %s", e)
            raise HTTPException(status_code=502, detail="Image search unavailable") from None

        last_status = resp.status_code
        if resp.status_code == 429:
            continue  # rotate to the next key
        if resp.status_code != 200:
            logger.warning("Pexels returned %s for query %r", resp.status_code, query)
            raise HTTPException(status_code=502, detail="Image search unavailable")

        body = resp.json()
        payload = {
            "total_results": body.get("total_results", 0),
            "page": body.get("page", 1),
            "per_page": body.get("per_page", per_page),
            "photos": [_slim_photo(p) for p in body.get("photos", [])],
        }
        _cache_put(cache_key, payload)
        return payload

    logger.warning("All Pexels keys rate-limited (last status %s)", last_status)
    raise HTTPException(status_code=429, detail="Image search rate-limited")
