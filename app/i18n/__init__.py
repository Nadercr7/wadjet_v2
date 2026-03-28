"""Wadjet i18n — lightweight bilingual translation (English/Arabic).

Usage in templates:  {{ t('nav.scan', lang) }}
Usage in Python:     from app.i18n import t; t('nav.scan', 'ar')
"""

from __future__ import annotations

import json
from pathlib import Path

I18N_DIR = Path(__file__).parent
SUPPORTED_LANGS = ("en", "ar")

_cache: dict[str, tuple[float, dict]] = {}


def _load(lang: str) -> dict:
    path = I18N_DIR / f"{lang}.json"
    if not path.exists():
        path = I18N_DIR / "en.json"
    mtime = path.stat().st_mtime
    cached = _cache.get(lang)
    if cached and cached[0] == mtime:
        return cached[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    _cache[lang] = (mtime, data)
    return data


def t(key: str, lang: str = "en"):
    """Get translation for a dot-separated key.

    Returns string for simple values, list for arrays.

    >>> t('nav.scan', 'ar')
    'مسح'
    """
    translations = _load(lang if lang in SUPPORTED_LANGS else "en")
    parts = key.split(".")
    value = translations
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return key  # path broken — return key as fallback
        if value is None:
            return key
    if isinstance(value, (str, list)):
        return value
    return key


def get_lang(request) -> str:
    """Determine language from request: ?lang= → cookie → Accept-Language → 'en'."""
    lang = request.query_params.get("lang")
    if lang in SUPPORTED_LANGS:
        return lang
    lang = request.cookies.get("wadjet_lang")
    if lang in SUPPORTED_LANGS:
        return lang
    accept = request.headers.get("accept-language", "")
    if accept.startswith("ar"):
        return "ar"
    return "en"
