"""
Wadjet AI - Confidence Threshold Logic.

Multi-tier confidence system that determines how to handle a
classifier prediction based on the model's reported confidence:

- **HIGH** (>= 0.80): Trust the Keras result outright.
- **MEDIUM** (>= 0.50): Show Keras result, suggest Gemini validation.
- **LOW** (>= 0.30): Mandatory Gemini validation required.
- **REJECT** (< 0.30): Not an Egyptian landmark -- reject.

The thresholds are defined as module constants but the ``HIGH``
boundary is overridable via ``Settings.confidence_threshold``.
"""

from __future__ import annotations

from enum import StrEnum

# ── Decision enum ───────────────────────────────


class ConfidenceDecision(StrEnum):
    """Action to take based on classifier confidence."""

    HIGH = "high"
    """Trust Keras result without further validation."""

    MEDIUM = "medium"
    """Show Keras result & suggest Gemini cross-validation."""

    LOW = "low"
    """Mandatory Gemini validation required."""

    REJECT = "reject"
    """Confidence too low -- not an Egyptian landmark."""


# ── Threshold constants ─────────────────────────
# These are the *default* boundaries; the HIGH boundary can be
# overridden via Settings.confidence_threshold at runtime.

CONFIDENCE_HIGH: float = 0.80
"""Minimum confidence to fully trust the Keras model."""

CONFIDENCE_MEDIUM: float = 0.50
"""Minimum confidence for the medium tier (show + suggest Gemini)."""

CONFIDENCE_LOW: float = 0.30
"""Minimum confidence for the low tier (mandatory Gemini)."""

# Below CONFIDENCE_LOW is REJECT territory.


# ── Evaluation function ─────────────────────────


def evaluate_confidence(
    confidence: float,
    *,
    high_threshold: float = CONFIDENCE_HIGH,
) -> ConfidenceDecision:
    """Classify a confidence score into a decision tier.

    Args:
        confidence: Model confidence in [0.0, 1.0].
        high_threshold: Override for the HIGH boundary (from
            ``Settings.confidence_threshold``). Defaults to 0.80.

    Returns:
        The appropriate ``ConfidenceDecision``.

    Examples:
        >>> evaluate_confidence(0.92)
        <ConfidenceDecision.HIGH: 'high'>
        >>> evaluate_confidence(0.65)
        <ConfidenceDecision.MEDIUM: 'medium'>
        >>> evaluate_confidence(0.35)
        <ConfidenceDecision.LOW: 'low'>
        >>> evaluate_confidence(0.15)
        <ConfidenceDecision.REJECT: 'reject'>
    """
    if confidence >= high_threshold:
        return ConfidenceDecision.HIGH
    if confidence >= CONFIDENCE_MEDIUM:
        return ConfidenceDecision.MEDIUM
    if confidence >= CONFIDENCE_LOW:
        return ConfidenceDecision.LOW
    return ConfidenceDecision.REJECT
