"""TLA (Thesaurus Linguae Aegyptiae) Service — scholarly Egyptian lexicon lookup.

Free public API: https://aaew.bbaw.de/tla/
No authentication required. 90,000+ ancient Egyptian lemmas.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TLA_BASE = "https://aaew.bbaw.de/tla/servlet/GetWcnDetails"
_TLA_SEARCH = "https://aaew.bbaw.de/tla/servlet/s0"
_TIMEOUT = 5.0
_CACHE_MAXSIZE = 256


class TLAService:
    """Async TLA API client for Egyptian lexicon lookups."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(_TIMEOUT, connect=3.0),
        )
        self._cache: OrderedDict[str, Any] = OrderedDict()
        logger.info("TLAService init")

    @property
    def available(self) -> bool:
        return True

    def _cache_put(self, key: str, value: Any) -> None:
        """Insert into bounded LRU cache."""
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > _CACHE_MAXSIZE:
            self._cache.popitem(last=False)

    async def search_lemma(self, term: str, limit: int = 5) -> list[dict]:
        """Search for Egyptian lemmas by transliteration or translation.

        Returns list of {id, transliteration, translation, word_class}.
        """
        cache_key = f"search:{term}:{limit}"
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        try:
            resp = await self._client.get(
                _TLA_SEARCH,
                params={
                    "f": "0",
                    "l": "0",
                    "s": term,
                    "ff": "0",
                    "ex": "1",
                    "lc": str(limit),
                },
            )
            resp.raise_for_status()
            # TLA returns HTML — parse basic results
            results = self._parse_search_html(resp.text, limit)
            self._cache_put(cache_key, results)
            return results
        except Exception:
            logger.debug("TLA search failed for '%s'", term, exc_info=True)
            return []

    async def get_lemma(self, lemma_id: str) -> dict | None:
        """Get full details for a TLA lemma by ID.

        Returns {id, transliteration, translation, word_class, attestations} or None.
        """
        cache_key = f"lemma:{lemma_id}"
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        try:
            resp = await self._client.get(
                _TLA_BASE,
                params={"wn": lemma_id, "db": "0"},
            )
            resp.raise_for_status()
            result = self._parse_lemma_html(resp.text, lemma_id)
            if result:
                self._cache_put(cache_key, result)
            return result
        except Exception:
            logger.debug("TLA lemma lookup failed for '%s'", lemma_id, exc_info=True)
            return None

    @staticmethod
    def _parse_search_html(html: str, limit: int) -> list[dict]:
        """Extract basic lemma info from TLA search HTML response."""
        results = []
        # TLA returns structured HTML; extract what we can
        import re

        # Look for lemma links with IDs and transliterations
        pattern = re.compile(
            r'wn=(\d+).*?<i>([^<]+)</i>.*?(?:"d">([^<]*)</)',
            re.DOTALL,
        )
        for match in pattern.finditer(html):
            if len(results) >= limit:
                break
            results.append({
                "id": match.group(1),
                "transliteration": match.group(2).strip(),
                "translation": match.group(3).strip() if match.group(3) else "",
            })
        return results

    @staticmethod
    def _parse_lemma_html(html: str, lemma_id: str) -> dict | None:
        """Extract lemma details from TLA detail HTML."""
        import re

        translit_match = re.search(r'<i>([^<]+)</i>', html)
        translation_match = re.search(r'"d">([^<]+)</', html)

        if not translit_match:
            return None

        return {
            "id": lemma_id,
            "transliteration": translit_match.group(1).strip(),
            "translation": translation_match.group(1).strip() if translation_match else "",
            "source": "TLA (Thesaurus Linguae Aegyptiae)",
        }

    async def close(self) -> None:
        await self._client.aclose()
