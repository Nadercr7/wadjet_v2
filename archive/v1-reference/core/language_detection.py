"""
Wadjet AI — Language Detection Service.

Detects the ISO 639-1 language of arbitrary text using Gemini.

Phase 3.10 — multi-language support auto-detection.

Supported language codes: en, ar, fr, de
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.core.gemini_service import GeminiService

logger = structlog.get_logger("wadjet.lang_detect")

# ---------------------------------------------------------------------------
# Supported codes
# ---------------------------------------------------------------------------

SUPPORTED_CODES: frozenset[str] = frozenset({"en", "ar", "fr", "de"})
"""ISO 639-1 codes Wadjet actively supports."""

# Language names for display
LANG_NAMES: dict[str, str] = {
    "en": "English",
    "ar": "Arabic",
    "fr": "French",
    "de": "German",
}

# ---------------------------------------------------------------------------
# Internal prompt
# ---------------------------------------------------------------------------

_DETECT_PROMPT = """\
What language is the following text written in?

Return ONLY a 2-letter ISO 639-1 language code (lowercase).
Valid answers: en, ar, fr, de
If the text is English (or unclear / unrecognised), return: en

Text:
\"\"\"
{text}
\"\"\"

Language code (2 letters only):"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def detect_language(
    gemini_service: GeminiService,
    text: str,
    fallback: str = "en",
) -> str:
    """Detect the language of *text* via Gemini.

    Uses only the first 300 characters — enough for reliable detection and
    minimises token cost.

    Parameters
    ----------
    gemini_service:
        Injected ``GeminiService`` instance.
    text:
        The text to classify.
    fallback:
        Returned when detection fails or the result is unsupported.

    Returns
    -------
    str
        One of ``{"en", "ar", "fr", "de"}``.
    """
    if not text or not text.strip():
        return fallback

    excerpt = text.strip()[:300]
    prompt = _DETECT_PROMPT.format(text=excerpt)

    try:
        raw: str = await gemini_service.generate_text(
            prompt,
            temperature=0.0,  # fully deterministic
            max_output_tokens=8,  # just the 2-letter code
        )

        code = raw.strip().lower()

        # Accept just the first token if the model adds punctuation
        code = code[:2]

        if code in SUPPORTED_CODES:
            logger.debug(
                "language_detected",
                code=code,
                language=LANG_NAMES.get(code, code),
                excerpt=excerpt[:60],
            )
            return code

        logger.debug(
            "language_detection_unsupported",
            raw=raw.strip(),
            fallback=fallback,
        )
        return fallback

    except Exception as exc:
        logger.warning(
            "language_detection_error",
            error=str(exc),
            fallback=fallback,
        )
        return fallback


def is_supported(code: str) -> bool:
    """Return *True* if *code* is a supported language code."""
    return code.lower() in SUPPORTED_CODES


def language_name(code: str) -> str:
    """Return the English name of a language code, or the code itself."""
    return LANG_NAMES.get(code.lower(), code)
