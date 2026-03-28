"""
Wadjet AI — Gemini Response Cache.

Provides a unified, hash-keyed caching layer that sits **inside**
``GeminiService`` and transparently caches responses for:

* Text generation (``generate_text``)
* JSON generation (``generate_json``)
* Multimodal / vision (``generate_with_image``)
* Embeddings (``embed``)

Cache keys are deterministic SHA-256 hashes of the call parameters
so identical requests always resolve to the same slot.

TTL categories
--------------
* ``description``  — 1 hour  (dynamic content, worthwhile to refresh)
* ``embedding``    — 24 hours (stable across model version)
* ``default``      — 1 hour  (general text / JSON responses)

Phase 3.15 — Gemini Response Caching.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import structlog

from app.core.cache import ResponseCache

logger = structlog.get_logger("wadjet.gemini.cache")

# ---------------------------------------------------------------------------
# TTL presets (seconds)
# ---------------------------------------------------------------------------

TTL_DEFAULT: int = 3600  # 1 hour — general responses
TTL_DESCRIPTION: int = 3600  # 1 hour — rich descriptions
TTL_EMBEDDING: int = 86_400  # 24 hours — embedding vectors
TTL_VISION: int = 3600  # 1 hour — image analysis results

# ---------------------------------------------------------------------------
# Cache key builder
# ---------------------------------------------------------------------------


def _build_cache_key(
    *,
    method: str,
    prompt: str,
    model: str = "",
    system_instruction: str = "",
    language: str = "",
    image_hash: str = "",
    temperature: str = "",
    extra: str = "",
) -> str:
    """Build a deterministic SHA-256 cache key from call parameters.

    The key is a hex-digest prefixed with ``gemini:<method>:`` for
    easy identification in logs and debugging.

    Parameters are joined with a null-byte separator to avoid
    collisions between concatenated strings.
    """
    parts = [
        method,
        prompt,
        model,
        system_instruction,
        language,
        image_hash,
        temperature,
        extra,
    ]
    raw = "\0".join(parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:16]  # 16 hex chars = 64 bits
    return f"gemini:{method}:{digest}"


def _hash_image(image_bytes: bytes) -> str:
    """Return a short hash of raw image bytes for cache-key inclusion."""
    return hashlib.sha256(image_bytes).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Gemini Response Cache
# ---------------------------------------------------------------------------


class GeminiResponseCache:
    """Unified response cache for all GeminiService calls.

    Wraps a ``ResponseCache`` (LRU, TTL, hit/miss logging) and adds:
    - Deterministic hash-based key generation
    - Per-category TTL selection
    - Convenience ``lookup`` / ``store`` / ``lookup_embedding`` helpers
    - Aggregate statistics with hit-rate logging

    Parameters
    ----------
    max_size:
        Maximum number of cached entries (LRU eviction beyond this).
    """

    def __init__(self, *, max_size: int = 1000) -> None:
        self._cache = ResponseCache(
            max_size=max_size,
            default_ttl=TTL_DEFAULT,
            namespace="gemini_responses",
        )
        self._last_log_time: float = 0.0
        logger.info("gemini_response_cache_init", max_size=max_size)

    # ── Key helpers (public for testing) ────────

    @staticmethod
    def make_key(
        *,
        method: str,
        prompt: str,
        model: str = "",
        system_instruction: str = "",
        language: str = "",
        image_hash: str = "",
        temperature: str = "",
        extra: str = "",
    ) -> str:
        """Build a cache key.  Exposed for testing / external use."""
        return _build_cache_key(
            method=method,
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
            language=language,
            image_hash=image_hash,
            temperature=temperature,
            extra=extra,
        )

    @staticmethod
    def hash_image(image_bytes: bytes) -> str:
        """Hash raw image bytes (16-char hex)."""
        return _hash_image(image_bytes)

    # ── Lookup / store ──────────────────────────

    def lookup(
        self,
        *,
        method: str,
        prompt: str,
        model: str = "",
        system_instruction: str = "",
        language: str = "",
        image_hash: str = "",
        temperature: str = "",
        extra: str = "",
    ) -> Any | None:
        """Look up a cached response.  Returns ``None`` on miss."""
        key = _build_cache_key(
            method=method,
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
            language=language,
            image_hash=image_hash,
            temperature=temperature,
            extra=extra,
        )
        result = self._cache.get(key)
        self._maybe_log_stats()
        return result

    def store(
        self,
        value: Any,
        *,
        method: str,
        prompt: str,
        model: str = "",
        system_instruction: str = "",
        language: str = "",
        image_hash: str = "",
        temperature: str = "",
        extra: str = "",
        ttl: int | None = None,
    ) -> str:
        """Store a response in the cache.  Returns the cache key used."""
        key = _build_cache_key(
            method=method,
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
            language=language,
            image_hash=image_hash,
            temperature=temperature,
            extra=extra,
        )
        effective_ttl = ttl if ttl is not None else self._ttl_for(method)
        self._cache.set(key, value, ttl=effective_ttl)
        return key

    def lookup_embedding(
        self,
        text: str,
        *,
        model: str = "",
    ) -> list[list[float]] | None:
        """Convenience: look up cached embedding vectors."""
        return self.lookup(method="embed", prompt=text, model=model)

    def store_embedding(
        self,
        text: str,
        vectors: list[list[float]],
        *,
        model: str = "",
    ) -> str:
        """Convenience: store embedding vectors (24h TTL)."""
        return self.store(
            vectors,
            method="embed",
            prompt=text,
            model=model,
            ttl=TTL_EMBEDDING,
        )

    # ── Stats ───────────────────────────────────

    @property
    def size(self) -> int:
        return self._cache.size

    @property
    def hit_rate(self) -> float:
        return self._cache.hit_rate

    @property
    def hits(self) -> int:
        return self._cache.hits

    @property
    def misses(self) -> int:
        return self._cache.misses

    def stats(self) -> dict[str, Any]:
        """Return cache statistics snapshot."""
        base = self._cache.stats()
        base["ttl_default"] = TTL_DEFAULT
        base["ttl_embedding"] = TTL_EMBEDDING
        return base

    def clear(self) -> int:
        """Clear all cached responses.  Returns count of removed entries."""
        return self._cache.clear()

    def sweep(self) -> int:
        """Purge expired entries."""
        return self._cache.sweep()

    # ── Internal helpers ────────────────────────

    @staticmethod
    def _ttl_for(method: str) -> int:
        """Select the appropriate TTL based on the method category."""
        if method == "embed":
            return TTL_EMBEDDING
        if method in ("generate_with_image", "vision"):
            return TTL_VISION
        if method in ("generate_text", "generate_json", "description"):
            return TTL_DESCRIPTION
        return TTL_DEFAULT

    def _maybe_log_stats(self) -> None:
        """Log cache hit-rate at most once every 60 seconds."""
        now = time.monotonic()
        if now - self._last_log_time >= 60.0:
            total = self._cache.hits + self._cache.misses
            if total > 0:
                logger.info(
                    "gemini_cache_stats",
                    size=self._cache.size,
                    hits=self._cache.hits,
                    misses=self._cache.misses,
                    hit_rate=round(self._cache.hit_rate, 4),
                )
            self._last_log_time = now
