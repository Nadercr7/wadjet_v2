"""
Wadjet AI — In-Memory Response Cache.

Provides a simple TTL-based cache backed by a plain ``dict``.
Designed for:
    - Attraction data (long TTL — data rarely changes)
    - Gemini descriptions per landmark (1 h TTL)
    - Embedding vectors (persistent — no expiry)

Features:
    - O(1) get / set
    - Per-key TTL with lazy expiration (checked on access)
    - Background sweep to prune expired entries (optional)
    - Cache hit / miss structured logging
    - Thread-safe via asyncio (single-threaded event loop)
    - Max-size eviction (LRU-style oldest-first when capacity reached)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger("wadjet.cache")

# ---------------------------------------------------------------------------
# Default TTLs (seconds)
# ---------------------------------------------------------------------------

TTL_ATTRACTION: int = 3600 * 24  # 24 hours — attraction data rarely changes
TTL_GEMINI_DESCRIPTION: int = 3600  # 1 hour — Gemini content
TTL_EMBEDDING: int = 0  # 0 = persistent (never expires)

# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _CacheEntry:
    """Internal wrapper that tracks value, creation time, and TTL."""

    value: Any
    created_at: float
    ttl: int  # 0 = never expires
    last_accessed: float = 0.0

    def __post_init__(self) -> None:
        self.last_accessed = self.created_at

    @property
    def is_expired(self) -> bool:
        """Return ``True`` when the entry has exceeded its TTL."""
        if self.ttl == 0:
            return False
        return (time.monotonic() - self.created_at) >= self.ttl


# ---------------------------------------------------------------------------
# ResponseCache
# ---------------------------------------------------------------------------


@dataclass
class ResponseCache:
    """Simple in-memory TTL cache with hit/miss logging.

    Parameters
    ----------
    max_size:
        Maximum number of entries.  When exceeded the oldest entry
        (by ``last_accessed``) is evicted.  ``0`` means unlimited.
    default_ttl:
        Default time-to-live in seconds for new entries.  ``0``
        means entries never expire.
    namespace:
        Human-readable label used in log messages to distinguish
        multiple cache instances (e.g. ``"attractions"``, ``"gemini"``).
    """

    max_size: int = 0
    default_ttl: int = 3600
    namespace: str = "default"

    # internal storage
    _store: dict[str, _CacheEntry] = field(default_factory=dict, init=False, repr=False)

    # stats
    _hits: int = field(default=0, init=False, repr=False)
    _misses: int = field(default=0, init=False, repr=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Retrieve a cached value by *key*.

        Returns ``None`` on miss **or** if the entry has expired
        (lazy expiration — the stale entry is removed on access).
        """
        entry = self._store.get(key)

        if entry is None:
            self._misses += 1
            logger.debug(
                "cache_miss",
                namespace=self.namespace,
                key=key,
            )
            return None

        if entry.is_expired:
            del self._store[key]
            self._misses += 1
            logger.debug(
                "cache_expired",
                namespace=self.namespace,
                key=key,
            )
            return None

        entry.last_accessed = time.monotonic()
        self._hits += 1
        logger.debug(
            "cache_hit",
            namespace=self.namespace,
            key=key,
        )
        return entry.value

    def set(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        """Store *value* under *key* with an optional per-key *ttl*.

        If *ttl* is ``None`` the instance's ``default_ttl`` is used.
        Pass ``ttl=0`` for a persistent (never-expiring) entry.
        """
        effective_ttl = ttl if ttl is not None else self.default_ttl

        # Evict oldest if at capacity
        if self.max_size > 0 and len(self._store) >= self.max_size and key not in self._store:
            self._evict_oldest()

        self._store[key] = _CacheEntry(
            value=value,
            created_at=time.monotonic(),
            ttl=effective_ttl,
        )
        logger.debug(
            "cache_set",
            namespace=self.namespace,
            key=key,
            ttl=effective_ttl,
        )

    def delete(self, key: str) -> bool:
        """Remove a single entry.  Returns ``True`` if the key existed."""
        if key in self._store:
            del self._store[key]
            logger.debug("cache_delete", namespace=self.namespace, key=key)
            return True
        return False

    def clear(self) -> int:
        """Drop **all** entries.  Returns the number of entries removed."""
        count = len(self._store)
        self._store.clear()
        self._hits = 0
        self._misses = 0
        logger.info("cache_cleared", namespace=self.namespace, removed=count)
        return count

    def has(self, key: str) -> bool:
        """Check whether a non-expired entry exists for *key*."""
        entry = self._store.get(key)
        if entry is None:
            return False
        if entry.is_expired:
            del self._store[key]
            return False
        return True

    def sweep(self) -> int:
        """Remove **all** expired entries in a single pass.

        Returns the number of entries purged.  Useful as a periodic
        maintenance task (e.g. via BackgroundTasks or a scheduled job).
        """
        expired_keys = [k for k, v in self._store.items() if v.is_expired]
        for k in expired_keys:
            del self._store[k]
        if expired_keys:
            logger.info(
                "cache_sweep",
                namespace=self.namespace,
                purged=len(expired_keys),
            )
        return len(expired_keys)

    # ------------------------------------------------------------------
    # Stats / introspection
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Return the current number of entries (including potentially expired)."""
        return len(self._store)

    @property
    def hits(self) -> int:
        """Total cache hits since creation or last ``clear()``."""
        return self._hits

    @property
    def misses(self) -> int:
        """Total cache misses since creation or last ``clear()``."""
        return self._misses

    @property
    def hit_rate(self) -> float:
        """Hit rate as a float 0.0-1.0.  Returns 0.0 when no lookups have been made."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Return a snapshot of cache statistics."""
        return {
            "namespace": self.namespace,
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_oldest(self) -> None:
        """Remove the entry with the oldest ``last_accessed`` timestamp."""
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k].last_accessed)
        del self._store[oldest_key]
        logger.debug(
            "cache_evicted",
            namespace=self.namespace,
            key=oldest_key,
        )


# ---------------------------------------------------------------------------
# Pre-configured cache instances
# ---------------------------------------------------------------------------

attraction_cache = ResponseCache(
    max_size=200,
    default_ttl=TTL_ATTRACTION,
    namespace="attractions",
)

gemini_cache = ResponseCache(
    max_size=1000,
    default_ttl=TTL_GEMINI_DESCRIPTION,
    namespace="gemini",
)

embedding_cache = ResponseCache(
    max_size=1000,
    default_ttl=TTL_EMBEDDING,
    namespace="embeddings",
)
