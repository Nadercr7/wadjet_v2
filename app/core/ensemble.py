"""Ensemble — collaborative merge/vote logic for multi-model identification.

Shared by both landmark and hieroglyph pipelines.

Strategies:
  - Agreement: both models agree → boosted confidence
  - Partial match: vision model matches ONNX top2/3 → use vision pick
  - Disagreement: call tiebreaker (Grok) → majority vote
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """A single identification candidate from any source."""
    slug: str
    name: str
    confidence: float
    source: str  # "onnx", "gemini", "grok"
    description: str = ""


@dataclass
class EnsembleResult:
    """Final merged identification result."""
    slug: str
    name: str
    confidence: float
    source: str  # "ensemble", "onnx", "gemini", "grok"
    description: str = ""
    agreement: str = ""  # "full", "partial", "tiebreak", "single"
    votes: dict[str, str] = field(default_factory=dict)  # source → slug voted


def _normalize(slug: str) -> str:
    """Lowercase + underscore-normalize a slug for comparison."""
    return slug.lower().strip().replace("-", "_")


def merge_landmark(
    onnx: Candidate | None,
    gemini: Candidate | None,
    grok: Candidate | None = None,
    onnx_top3: list[dict[str, Any]] | None = None,
) -> EnsembleResult:
    """Merge landmark identifications from up to 3 sources.

    Priority logic:
    1. ONNX + Gemini agree → "full" agreement, boosted confidence
    2. Gemini matches ONNX top2/top3 → "partial", use Gemini's pick
    3. Total disagree + Grok available → majority vote
    4. Fallback → highest confidence wins
    """
    candidates = [c for c in (onnx, gemini, grok) if c and c.slug]
    if not candidates:
        return EnsembleResult(
            slug="", name="", confidence=0.0,
            source="none", agreement="none",
        )

    if len(candidates) == 1:
        c = candidates[0]
        return EnsembleResult(
            slug=c.slug, name=c.name, confidence=c.confidence,
            source=c.source, description=c.description,
            agreement="single",
            votes={c.source: c.slug},
        )

    votes = {c.source: c.slug for c in candidates}
    top3_slugs = [_normalize(m.get("slug", "")) for m in (onnx_top3 or [])]

    # Case 1: ONNX + Gemini agree
    if onnx and gemini and _normalize(onnx.slug) == _normalize(gemini.slug):
        boosted = min(1.0, max(onnx.confidence, gemini.confidence) * 1.15)
        desc = gemini.description or onnx.description
        return EnsembleResult(
            slug=onnx.slug, name=gemini.name or onnx.name,
            confidence=boosted, source="ensemble",
            description=desc, agreement="full", votes=votes,
        )

    # Case 2: Gemini matches ONNX top2/3
    if gemini and top3_slugs and _normalize(gemini.slug) in top3_slugs:
        return EnsembleResult(
            slug=gemini.slug, name=gemini.name,
            confidence=gemini.confidence,
            source="ensemble", description=gemini.description,
            agreement="partial", votes=votes,
        )

    # Case 3: Grok tiebreaker — majority vote
    if grok and grok.slug:
        slug_counts: dict[str, list[Candidate]] = {}
        for c in candidates:
            key = _normalize(c.slug)
            slug_counts.setdefault(key, []).append(c)

        # Find the slug with most votes
        winner_slug = max(slug_counts, key=lambda k: len(slug_counts[k]))
        winners = slug_counts[winner_slug]

        if len(winners) >= 2:
            # Majority (2/3 or 3/3)
            best = max(winners, key=lambda c: c.confidence)
            return EnsembleResult(
                slug=best.slug, name=best.name,
                confidence=best.confidence,
                source="ensemble", description=best.description,
                agreement="tiebreak",
                votes=votes,
            )

    # Case 4: No agreement — highest confidence wins
    best = max(candidates, key=lambda c: c.confidence)
    return EnsembleResult(
        slug=best.slug, name=best.name,
        confidence=best.confidence,
        source=best.source, description=best.description,
        agreement="best_confidence",
        votes=votes,
    )


def merge_hieroglyph(
    onnx_code: str,
    onnx_confidence: float,
    gemini: Candidate | None,
    grok: Candidate | None = None,
    onnx_top3: list[tuple[str, float]] | None = None,
) -> tuple[str, float, str]:
    """Merge hieroglyph classifications. Returns (gardiner_code, confidence, source).

    Simpler than landmark: just slug = gardiner code.
    """
    candidates: list[Candidate] = []
    if onnx_code:
        candidates.append(Candidate(
            slug=onnx_code, name=onnx_code,
            confidence=onnx_confidence, source="onnx",
        ))
    if gemini and gemini.slug:
        candidates.append(gemini)
    if grok and grok.slug:
        candidates.append(grok)

    # Filter out candidates with empty slugs (HIERO-013)
    candidates = [c for c in candidates if c.slug]

    if not candidates:
        return "", 0.0, "none"

    if len(candidates) == 1:
        c = candidates[0]
        return c.slug, c.confidence, c.source

    # Normalize codes for comparison (case-insensitive)
    def _norm_code(c: str) -> str:
        return c.strip().upper()

    # Check agreement between first two
    c1, c2 = candidates[0], candidates[1]
    if _norm_code(c1.slug) == _norm_code(c2.slug):
        boosted = min(1.0, max(c1.confidence, c2.confidence) * 1.15)
        return c1.slug, boosted, "ensemble"

    # Check if vision model matches ONNX top3
    if onnx_top3 and len(candidates) >= 2:
        vision = candidates[1]  # gemini
        top3_codes = [_norm_code(code) for code, _ in onnx_top3]
        if _norm_code(vision.slug) in top3_codes:
            return vision.slug, vision.confidence, "ensemble"

    # Tiebreaker with 3rd model
    if len(candidates) == 3:
        code_counts: dict[str, list[Candidate]] = {}
        for c in candidates:
            key = _norm_code(c.slug)
            code_counts.setdefault(key, []).append(c)

        winner = max(code_counts, key=lambda k: len(code_counts[k]))
        winners = code_counts[winner]
        if len(winners) >= 2:
            best = max(winners, key=lambda c: c.confidence)
            return best.slug, best.confidence, "ensemble"

    # No agreement — highest confidence
    best = max(candidates, key=lambda c: c.confidence)
    return best.slug, best.confidence, best.source
