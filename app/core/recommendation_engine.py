"""Recommendation Engine — tag-based landmark recommendations.

Scores candidates based on type, era, city, and geo-proximity
relative to a seed attraction. No embedding dependency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.core.landmarks import Attraction, get_all, get_by_name, get_by_slug

# Scoring weights
WEIGHT_TYPE = 3.0
WEIGHT_ERA = 2.0
WEIGHT_CITY = 1.5
WEIGHT_PROXIMITY = 1.0
PROXIMITY_THRESHOLD_KM = 50.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _era_tokens(era: str) -> set[str]:
    return {t.strip("(),.") for t in era.lower().split() if t.strip("(),.")}


@dataclass(frozen=True, slots=True)
class Recommendation:
    attraction: Attraction
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


def recommend(
    attraction_name: str,
    *,
    limit: int = 5,
) -> list[Recommendation]:
    """Return up to *limit* similar landmarks by tag scoring."""
    seed = get_by_name(attraction_name) or get_by_slug(attraction_name)
    if seed is None:
        return []

    attractions = get_all()
    seed_era_tokens = _era_tokens(seed.era)
    scored: list[Recommendation] = []

    for cand in attractions:
        if cand.name == seed.name:
            continue

        score = 0.0
        reasons: list[str] = []

        if cand.type == seed.type:
            score += WEIGHT_TYPE
            reasons.append(f"Same type ({seed.type.value})")

        cand_tokens = _era_tokens(cand.era)
        if seed_era_tokens and cand_tokens:
            overlap = seed_era_tokens & cand_tokens
            if overlap:
                score += WEIGHT_ERA
                reasons.append(f"Era overlap ({', '.join(sorted(overlap))})")

        if cand.city == seed.city:
            score += WEIGHT_CITY
            reasons.append(f"Same city ({seed.city.value})")

        if seed.coordinates and cand.coordinates:
            dist = _haversine_km(
                seed.coordinates[0], seed.coordinates[1],
                cand.coordinates[0], cand.coordinates[1],
            )
            if dist <= PROXIMITY_THRESHOLD_KM:
                prox = WEIGHT_PROXIMITY * (1.0 - dist / PROXIMITY_THRESHOLD_KM)
                score += prox
                reasons.append(f"Nearby ({dist:.0f} km)")

        if score > 0:
            scored.append(Recommendation(cand, round(score, 2), reasons))

    scored.sort(key=lambda r: (r.score, r.attraction.popularity), reverse=True)
    return scored[:limit]
