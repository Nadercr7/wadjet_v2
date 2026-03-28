"""
Wadjet AI - Supported languages data module.

Provides the static list of languages supported by the application.
Language detection via Gemini will be added in Phase 3.

Public helpers
--------------
``get_all()``
    Return all supported languages.
``get_by_code(code)``
    O(1) lookup by ISO 639-1 code.
``get_default()``
    Return the default language (English).
``get_codes()``
    Return list of supported language codes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Language:
    """A supported language."""

    code: str  # ISO 639-1 (e.g. "en")
    name: str  # English name
    native_name: str  # Name in the language itself
    direction: str  # "ltr" or "rtl"
    enabled: bool  # Whether active in the current release


# ---------------------------------------------------------------------------
# Static language list
# ---------------------------------------------------------------------------

_LANGUAGES: list[Language] = [
    Language(
        code="en",
        name="English",
        native_name="English",
        direction="ltr",
        enabled=True,
    ),
    Language(
        code="ar",
        name="Arabic",
        native_name="العربية",
        direction="rtl",
        enabled=True,
    ),
    Language(
        code="fr",
        name="French",
        native_name="Français",
        direction="ltr",
        enabled=True,
    ),
    Language(
        code="de",
        name="German",
        native_name="Deutsch",
        direction="ltr",
        enabled=True,
    ),
]

_CODE_INDEX: dict[str, Language] = {lang.code: lang for lang in _LANGUAGES}

DEFAULT_LANGUAGE_CODE: str = "en"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_all() -> list[Language]:
    """Return all supported languages."""
    return list(_LANGUAGES)


def get_by_code(code: str) -> Language | None:
    """O(1) lookup by ISO 639-1 code.  Returns ``None`` if not found."""
    return _CODE_INDEX.get(code.lower())


def get_default() -> Language:
    """Return the default language (English)."""
    return _CODE_INDEX[DEFAULT_LANGUAGE_CODE]


def get_codes() -> list[str]:
    """Return sorted list of supported language codes."""
    return sorted(_CODE_INDEX.keys())
