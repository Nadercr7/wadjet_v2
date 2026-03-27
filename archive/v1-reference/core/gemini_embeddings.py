"""
Wadjet AI — Gemini Embedding Service.

Generates and caches semantic embeddings for Egyptian heritage attractions
via ``gemini-embedding-001``.  Core capabilities:

* **Pre-compute** embeddings for all 20 attractions on startup.
* **Cache-first** — embeddings are stored in the persistent
  ``embedding_cache`` and never re-fetched unless the cache is cleared.
* **Cosine similarity** — lightweight math using only the stdlib
  ``math`` module (no numpy required at runtime).
* **Query embedding** — embed arbitrary user text for semantic search.
* **find_similar()** — rank all attractions by cosine distance to a
  query vector.

Phase 3.7 — lays the foundation for Phase 3.8 (embedding-based
recommendation engine upgrade).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from app.core.attractions_data import Attraction, get_all
from app.core.cache import embedding_cache
from app.core.exceptions import GeminiError

if TYPE_CHECKING:
    from app.core.gemini_service import GeminiService

logger = structlog.get_logger("wadjet.embeddings")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CACHE_PREFIX = "emb:"
_ATTRACTION_PREFIX = "attr:"
_BATCH_SIZE = 5  # embed up to 5 texts per API call to reduce round trips


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SimilarityResult:
    """A single similarity match with its score."""

    attraction: Attraction
    score: float  # cosine similarity 0.0 - 1.0
    rank: int = 0


@dataclass(slots=True)
class EmbeddingStats:
    """Runtime statistics for the embedding service."""

    total_attractions: int = 0
    cached_embeddings: int = 0
    api_calls: int = 0
    avg_embed_ms: float = 0.0
    cache_hit_rate: float = 0.0


# ---------------------------------------------------------------------------
# Cosine similarity (pure Python — no numpy dependency)
# ---------------------------------------------------------------------------


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute the cosine similarity between two vectors.

    Returns a float in ``[-1.0, 1.0]``.  Identical vectors → ``1.0``,
    orthogonal → ``0.0``, opposite → ``-1.0``.
    """
    if len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Embedding Service
# ---------------------------------------------------------------------------


@dataclass
class EmbeddingService:
    """Manages embedding generation, caching, and similarity search.

    Parameters
    ----------
    gemini:
        An initialised ``GeminiService`` instance.
    """

    gemini: GeminiService
    _ready: bool = field(default=False, init=False, repr=False)
    _embed_times: list[float] = field(default_factory=list, init=False, repr=False)

    # ------------------------------------------------------------------
    # Startup — pre-compute attraction embeddings
    # ------------------------------------------------------------------

    async def precompute_attractions(self) -> int:
        """Generate embeddings for every attraction and cache them.

        Skips attractions that already have a cached embedding.
        Returns the number of **new** embeddings generated.

        This is designed to be called once during the FastAPI lifespan
        so the embedding index is ready before the first request.
        """
        attractions = get_all()
        generated = 0
        skipped = 0

        logger.info(
            "embedding_precompute_start",
            total_attractions=len(attractions),
        )

        # Build texts for attractions that need embedding
        to_embed: list[tuple[Attraction, str]] = []
        for attr in attractions:
            cache_key = f"{_ATTRACTION_PREFIX}{attr.name}"
            if embedding_cache.has(cache_key):
                skipped += 1
                continue
            text = _attraction_to_text(attr)
            to_embed.append((attr, text))

        # Batch embed to reduce API calls
        for batch_start in range(0, len(to_embed), _BATCH_SIZE):
            batch = to_embed[batch_start : batch_start + _BATCH_SIZE]
            texts = [text for _, text in batch]

            try:
                start = time.perf_counter()
                vectors = await self.gemini.embed(texts)
                elapsed_ms = (time.perf_counter() - start) * 1000
                self._embed_times.append(elapsed_ms)

                for i, (attr, _text) in enumerate(batch):
                    if i < len(vectors) and vectors[i]:
                        cache_key = f"{_ATTRACTION_PREFIX}{attr.name}"
                        embedding_cache.set(cache_key, vectors[i], ttl=0)
                        generated += 1

                logger.info(
                    "embedding_batch_done",
                    batch_size=len(batch),
                    latency_ms=round(elapsed_ms, 1),
                )
            except GeminiError as exc:
                logger.error(
                    "embedding_batch_error",
                    batch_size=len(batch),
                    error=str(exc),
                )
                # Continue with next batch — partial results are fine
                continue

        self._ready = True
        logger.info(
            "embedding_precompute_done",
            generated=generated,
            skipped=skipped,
            total=len(attractions),
        )
        return generated

    # ------------------------------------------------------------------
    # Public API: embed arbitrary text
    # ------------------------------------------------------------------

    async def get_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for arbitrary text.

        Uses cache to avoid redundant API calls for repeated queries.

        Returns
        -------
        list[float]
            The embedding vector, or an empty list on failure.
        """
        cache_key = f"{_CACHE_PREFIX}{text[:200]}"  # truncate long keys
        cached = embedding_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            start = time.perf_counter()
            vectors = await self.gemini.embed(text)
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._embed_times.append(elapsed_ms)

            if vectors and vectors[0]:
                embedding_cache.set(cache_key, vectors[0], ttl=3600)  # 1h for queries
                logger.debug(
                    "embedding_generated",
                    text_length=len(text),
                    dim=len(vectors[0]),
                    latency_ms=round(elapsed_ms, 1),
                )
                return vectors[0]
            return []
        except GeminiError as exc:
            logger.error("embedding_error", error=str(exc), text_length=len(text))
            return []

    # ------------------------------------------------------------------
    # Public API: get attraction embedding (from cache)
    # ------------------------------------------------------------------

    def get_attraction_embedding(self, attraction_name: str) -> list[float] | None:
        """Retrieve the cached embedding for a named attraction.

        Returns ``None`` if the attraction has not been pre-computed.
        """
        cache_key = f"{_ATTRACTION_PREFIX}{attraction_name}"
        return embedding_cache.get(cache_key)

    # ------------------------------------------------------------------
    # Public API: find similar attractions
    # ------------------------------------------------------------------

    async def find_similar(
        self,
        text: str,
        *,
        top_n: int = 5,
        exclude_names: set[str] | None = None,
    ) -> list[SimilarityResult]:
        """Find the most similar attractions to the given text.

        Parameters
        ----------
        text:
            A user query or description to compare against attractions.
        top_n:
            Maximum number of results to return.
        exclude_names:
            Attraction names to exclude (e.g. the current attraction).

        Returns
        -------
        list[SimilarityResult]
            Ranked list of similar attractions, highest score first.
        """
        query_vec = await self.get_embedding(text)
        if not query_vec:
            logger.warning("find_similar_no_query_vec", text_length=len(text))
            return []

        return self.find_similar_by_vector(
            query_vec,
            top_n=top_n,
            exclude_names=exclude_names,
        )

    def find_similar_by_vector(
        self,
        query_vec: list[float],
        *,
        top_n: int = 5,
        exclude_names: set[str] | None = None,
    ) -> list[SimilarityResult]:
        """Find similar attractions given a pre-computed vector.

        Useful when the query embedding is already available (e.g.
        the recommendation engine has cached the current attraction's
        embedding).
        """
        exclude = exclude_names or set()
        attractions = get_all()
        scored: list[SimilarityResult] = []

        for attr in attractions:
            if attr.name in exclude:
                continue
            attr_vec = self.get_attraction_embedding(attr.name)
            if attr_vec is None:
                continue
            score = cosine_similarity(query_vec, attr_vec)
            scored.append(SimilarityResult(attraction=attr, score=score))

        # Sort by similarity descending
        scored.sort(key=lambda r: r.score, reverse=True)

        # Assign ranks and truncate
        results = []
        for i, item in enumerate(scored[:top_n]):
            results.append(
                SimilarityResult(
                    attraction=item.attraction,
                    score=round(item.score, 6),
                    rank=i + 1,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Stats / health
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """Whether pre-computation has completed at least once."""
        return self._ready

    def stats(self) -> EmbeddingStats:
        """Return current embedding service statistics."""
        attractions = get_all()
        cached = sum(1 for a in attractions if embedding_cache.has(f"{_ATTRACTION_PREFIX}{a.name}"))
        avg_ms = sum(self._embed_times) / len(self._embed_times) if self._embed_times else 0.0
        return EmbeddingStats(
            total_attractions=len(attractions),
            cached_embeddings=cached,
            api_calls=len(self._embed_times),
            avg_embed_ms=round(avg_ms, 1),
            cache_hit_rate=round(embedding_cache.hit_rate, 4),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _attraction_to_text(attr: Attraction) -> str:
    """Build a rich text representation of an attraction for embedding.

    Combines name, city, type, era, description, and highlights into
    a single string that captures the attraction's semantic identity.
    """
    parts = [
        f"{attr.name} in {attr.city.value}, Egypt.",
        f"Type: {attr.type.value}.",
    ]

    if attr.era:
        parts.append(f"Era: {attr.era}.")
    if attr.period:
        parts.append(f"Period: {attr.period}.")
    if attr.dynasty:
        parts.append(f"Dynasty: {attr.dynasty}.")

    parts.append(attr.description)

    if attr.historical_significance:
        parts.append(attr.historical_significance)

    if attr.notable_pharaohs:
        parts.append(f"Associated pharaohs: {', '.join(attr.notable_pharaohs)}.")
    if attr.key_artifacts:
        parts.append(f"Key artifacts: {', '.join(attr.key_artifacts)}.")
    if attr.architectural_features:
        parts.append(f"Architecture: {', '.join(attr.architectural_features)}.")

    return " ".join(parts)
