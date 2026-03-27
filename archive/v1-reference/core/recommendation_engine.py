"""
Wadjet AI — Hybrid Recommendation Engine.

**Phase 3.8 upgrade:** Combines embedding-based semantic similarity
(from ``EmbeddingService``) with tag-based heuristics (type, era, city,
proximity) for smarter recommendations.

When an ``EmbeddingService`` is available the final score is a **weighted
blend** of the embedding cosine similarity (primary) and the tag-based
bonus (secondary).  When embeddings are unavailable the engine falls back
to the original tag-only scoring.

Usage::

    from app.core.recommendation_engine import RecommendationEngine

    engine = RecommendationEngine(embedding_service=emb)
    recs = engine.recommend("Great Pyramids of Giza", limit=5)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.attractions_data import (
    Attraction,
    get_all,
    get_by_name,
    get_by_slug,
)
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.core.gemini_embeddings import EmbeddingService

logger = get_logger("wadjet.recommendations")

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

# Embedding weight - primary signal (0.0-1.0 cosine similarity normalised)
WEIGHT_EMBEDDING: float = 6.0

# Tag-based bonuses — secondary signals
WEIGHT_TYPE: float = 3.0  # Same heritage type (Pharaonic, Islamic, ...)
WEIGHT_ERA: float = 2.0  # Same historical era
WEIGHT_CITY: float = 1.5  # Same city / nearby
WEIGHT_PROXIMITY: float = 1.0  # Geo-distance bonus (if coords available)
PROXIMITY_THRESHOLD_KM: float = 50.0  # Max km for proximity bonus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance (km) between two GPS points."""
    r = 6_371.0  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _era_tokens(era: str) -> set[str]:
    """Split an era string into lowercase tokens for partial matching.

    ``"New Kingdom (18th Dynasty)"`` → ``{"new", "kingdom", "18th", "dynasty"}``.
    """
    return {t.strip("(),.") for t in era.lower().split() if t.strip("(),.")}


# ---------------------------------------------------------------------------
# Recommendation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Recommendation:
    """A single recommendation with its similarity score."""

    attraction: Attraction
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class RecommendationEngine:
    """Hybrid recommendation engine: embeddings + tag heuristics.

    When an ``EmbeddingService`` is provided, each candidate's score is::

        score = WEIGHT_EMBEDDING * cosine_sim + tag_bonus + pref_boost

    Without embeddings, the score reduces to the original tag-only formula.

    Scoring factors:
        - **Embedding similarity** (*6 max): cosine similarity between
          the seed and candidate attraction embeddings.
        - **Type match** (+3): same heritage type.
        - **Era overlap** (+2): shared era keywords.
        - **City match** (+1.5): same city.
        - **Proximity bonus** (+1 max): geo-distance within threshold.
    """

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self._attractions: list[Attraction] = get_all()
        self._embedding_service = embedding_service
        mode = "hybrid (embedding + tags)" if embedding_service else "tag-only"
        logger.info("recommendation_engine_init", mode=mode)

    # ── Properties ──────────────────────────────────────

    @property
    def has_embeddings(self) -> bool:
        """Whether the engine has an embedding service available."""
        return self._embedding_service is not None

    # ── Public API ──────────────────────────────────────────

    def recommend(
        self,
        attraction_name: str,
        *,
        limit: int = 5,
        preferred_types: list[str] | None = None,
        preferred_eras: list[str] | None = None,
    ) -> list[Recommendation]:
        """Return up to *limit* recommendations similar to the named attraction.

        Args:
            attraction_name: Exact attraction name **or** URL slug.
            limit: Maximum number of results (default 5).
            preferred_types: Optional list of preferred heritage types to boost.
            preferred_eras: Optional list of preferred eras to boost.

        Returns:
            Sorted list of ``Recommendation`` objects (highest score first).
            Returns an empty list if the seed attraction is not found.
        """
        seed = get_by_name(attraction_name) or get_by_slug(attraction_name)
        if seed is None:
            logger.warning("recommendation_seed_not_found", name=attraction_name)
            return []

        # Get seed embedding (if available)
        seed_vec: list[float] | None = None
        if self._embedding_service:
            seed_vec = self._embedding_service.get_attraction_embedding(seed.name)

        scored: list[Recommendation] = []
        seed_era_tokens = _era_tokens(seed.era)

        for candidate in self._attractions:
            if candidate.name == seed.name:
                continue  # Don't recommend itself

            score = 0.0
            reasons: list[str] = []

            # ── Embedding similarity (primary) ──────
            if seed_vec and self._embedding_service:
                cand_vec = self._embedding_service.get_attraction_embedding(candidate.name)
                if cand_vec:
                    from app.core.gemini_embeddings import cosine_similarity

                    cos_sim = cosine_similarity(seed_vec, cand_vec)
                    emb_score = WEIGHT_EMBEDDING * max(0.0, cos_sim)  # clamp negatives
                    score += emb_score
                    reasons.append(f"Semantic similarity ({cos_sim:.3f})")

            # ── Type similarity ─────────────────────
            if candidate.type == seed.type:
                score += WEIGHT_TYPE
                reasons.append(f"Same type ({seed.type.value})")

            # ── Era overlap ─────────────────────────
            cand_era_tokens = _era_tokens(candidate.era)
            if seed_era_tokens and cand_era_tokens:
                overlap = seed_era_tokens & cand_era_tokens
                if overlap:
                    score += WEIGHT_ERA
                    reasons.append(f"Era overlap ({', '.join(sorted(overlap))})")

            # ── City match ──────────────────────────
            if candidate.city == seed.city:
                score += WEIGHT_CITY
                reasons.append(f"Same city ({seed.city.value})")

            # ── Proximity bonus ─────────────────────
            if seed.coordinates and candidate.coordinates:
                dist = _haversine_km(
                    seed.coordinates[0],
                    seed.coordinates[1],
                    candidate.coordinates[0],
                    candidate.coordinates[1],
                )
                if dist <= PROXIMITY_THRESHOLD_KM:
                    # Linear decay: full bonus at 0 km -> 0 at threshold
                    prox_score = WEIGHT_PROXIMITY * (1.0 - dist / PROXIMITY_THRESHOLD_KM)
                    score += prox_score
                    reasons.append(f"Nearby ({dist:.0f} km)")

            # ── Preference boosts ───────────────────
            if preferred_types and candidate.type.value in preferred_types:
                score += 1.0
                reasons.append("Matches preferred type")

            if preferred_eras:
                for pref_era in preferred_eras:
                    if pref_era.lower() in candidate.era.lower():
                        score += 0.5
                        reasons.append(f"Matches preferred era ({pref_era})")
                        break

            if score > 0:
                scored.append(
                    Recommendation(
                        attraction=candidate,
                        score=round(score, 2),
                        reasons=reasons,
                    )
                )

        # Sort by score descending, then by popularity descending as tiebreaker
        scored.sort(key=lambda r: (r.score, r.attraction.popularity), reverse=True)

        mode = "hybrid" if seed_vec else "tag-only"
        logger.info(
            "recommendations_generated",
            seed=seed.name,
            mode=mode,
            total_scored=len(scored),
            returned=min(limit, len(scored)),
        )

        return scored[:limit]

    def recommend_by_class_name(
        self,
        class_name: str,
        *,
        limit: int = 5,
    ) -> list[Recommendation]:
        """Recommend attractions similar to the one identified by an ML class label.

        Convenience wrapper that resolves an ML class name to an attraction
        name and delegates to :meth:`recommend`.

        Args:
            class_name: ML classifier label (e.g. ``"Great Pyramids of Giza"``).
            limit: Maximum number of results.

        Returns:
            Sorted list of recommendations, or empty if class name unknown.
        """
        from app.core.attractions_data import get_by_class_name

        attraction = get_by_class_name(class_name)
        if attraction is None:
            logger.warning("recommendation_class_not_found", class_name=class_name)
            return []
        return self.recommend(attraction.name, limit=limit)
