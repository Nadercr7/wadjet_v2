"""
Wadjet AI — Analytics Service (Phase 7.16).

Privacy-friendly, server-side analytics — **no cookies, no PII, no
tracking scripts**.  Counts are kept in-memory with periodic flush
to a single JSONL file:

    data/analytics/events.jsonl

Each event is a one-line JSON record with:
    type, route/class/feature/language, timestamp

A companion ``get_stats()`` method reads events and returns aggregate
counters suitable for the ``/admin/stats`` dashboard.

Design goals:
  • Zero external dependencies (file I/O via aiofiles)
  • Hot-path writes are in-memory append → async flush
  • No personally-identifiable information stored
  • Survives server restarts (persistent JSONL)
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from app.core.logging import get_logger

logger = get_logger("wadjet.analytics")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ANALYTICS_DIR = Path("data/analytics")
_EVENTS_FILE = _ANALYTICS_DIR / "events.jsonl"

# Recognised page routes (for filtering noise from bots / scanners)
_TRACKED_ROUTES: set[str] = {
    "/",
    "/result",
    "/chat",
    "/history",
    "/itinerary",
    "/explore",
    "/learn",
    "/quiz",
    "/timeline",
    "/translator",
    "/achievements",
    "/compare",
    "/about",
    "/feedback",
    "/admin/stats",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _append_jsonl(record: dict) -> None:
    """Append a single JSON line, creating dirs if needed."""
    _ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    async with aiofiles.open(_EVENTS_FILE, "a", encoding="utf-8") as fh:
        await fh.write(line)


async def _read_events() -> list[dict]:
    """Read all events from the JSONL file.  Returns [] if missing."""
    if not _EVENTS_FILE.exists():
        return []
    records: list[dict] = []
    async with aiofiles.open(_EVENTS_FILE, encoding="utf-8") as fh:
        async for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError:
                continue  # skip corrupt lines silently
    return records


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class AnalyticsService:
    """Privacy-friendly analytics collector & aggregator.

    Instantiated once at app startup; shared via middleware and API.
    """

    def __init__(self) -> None:
        self._start_time: float = time.monotonic()
        logger.info("analytics_service_init", storage=str(_ANALYTICS_DIR))

    # ── Recording (called from middleware / endpoints) ────────────

    async def record_page_view(self, route: str) -> None:
        """Record a page view for a tracked route."""
        if route not in _TRACKED_ROUTES:
            return
        await _append_jsonl({"type": "page_view", "route": route, "ts": _utcnow_iso()})

    async def record_identification(
        self,
        class_name: str,
        confidence: float,
        source: str = "keras",
    ) -> None:
        """Record a landmark identification event."""
        await _append_jsonl(
            {
                "type": "identification",
                "class_name": class_name,
                "confidence": round(confidence, 4),
                "source": source,
                "ts": _utcnow_iso(),
            }
        )

    async def record_language(self, language: str) -> None:
        """Record the language used in a request."""
        await _append_jsonl({"type": "language", "language": language, "ts": _utcnow_iso()})

    async def record_feature(self, feature: str) -> None:
        """Record feature usage (chat, quiz, translation, etc.)."""
        await _append_jsonl({"type": "feature", "feature": feature, "ts": _utcnow_iso()})

    # ── Aggregation ──────────────────────────────────────────────

    async def get_stats(self) -> dict:
        """Read all events and return aggregated stats dict.

        Returns a dict matching ``AnalyticsStatsData`` fields.
        """
        events = await _read_events()

        # Counters
        page_counter: Counter[str] = Counter()
        landmark_counter: Counter[str] = Counter()
        landmark_conf: defaultdict[str, list[float]] = defaultdict(list)
        lang_counter: Counter[str] = Counter()
        feature_counter: Counter[str] = Counter()
        total_conf: list[float] = []

        for ev in events:
            etype = ev.get("type", "")
            if etype == "page_view":
                page_counter[ev.get("route", "?")] += 1
            elif etype == "identification":
                cls = ev.get("class_name", "unknown")
                conf = ev.get("confidence", 0.0)
                landmark_counter[cls] += 1
                landmark_conf[cls].append(conf)
                total_conf.append(conf)
            elif etype == "language":
                lang_counter[ev.get("language", "?")] += 1
            elif etype == "feature":
                feature_counter[ev.get("feature", "?")] += 1

        # Build response-shaped dict
        page_views = [{"route": r, "views": c} for r, c in page_counter.most_common()]

        top_landmarks = [
            {
                "class_name": cls,
                "count": cnt,
                "avg_confidence": round(sum(landmark_conf[cls]) / len(landmark_conf[cls]), 4),
            }
            for cls, cnt in landmark_counter.most_common(15)
        ]

        languages = [{"language": lang, "count": cnt} for lang, cnt in lang_counter.most_common()]

        features = [{"feature": feat, "count": cnt} for feat, cnt in feature_counter.most_common()]

        uptime_s = time.monotonic() - self._start_time

        return {
            "total_page_views": sum(page_counter.values()),
            "total_identifications": sum(landmark_counter.values()),
            "avg_confidence": (round(sum(total_conf) / len(total_conf), 4) if total_conf else 0.0),
            "page_views": page_views,
            "top_landmarks": top_landmarks,
            "languages": languages,
            "features": features,
            "uptime_hours": round(uptime_s / 3600, 2),
        }
