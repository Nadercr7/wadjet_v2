"""Stories of the Nile — story loader and progress tracker.

Loads bilingual Egyptian mythology stories from data/stories/*.json.
Provides metadata listing and full chapter retrieval.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STORIES_DIR = Path(__file__).parent.parent.parent / "data" / "stories"

# Cache: maps file mtime to parsed data so we reload on change (dev-friendly)
_cache: dict[str, tuple[float, dict]] = {}


def _load_json(path: Path) -> dict | None:
    """Load a JSON file with mtime-based caching."""
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None

    cached = _cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _cache[key] = (mtime, data)
        return data
    except Exception as e:
        logger.warning("Failed to load story %s: %s", path.name, e)
        return None


def load_all_stories() -> list[dict]:
    """Load all story metadata (without full chapters) for listing."""
    stories = []
    if not STORIES_DIR.exists():
        return stories

    for f in sorted(STORIES_DIR.glob("*.json")):
        data = _load_json(f)
        if not data:
            continue
        stories.append({
            "id": data["id"],
            "title": data["title"],
            "subtitle": data["subtitle"],
            "cover_glyph": data["cover_glyph"],
            "difficulty": data["difficulty"],
            "estimated_minutes": data["estimated_minutes"],
            "chapter_count": len(data.get("chapters", [])),
            "glyphs_taught": data.get("glyphs_taught", []),
        })
    return stories


def load_story(story_id: str) -> dict | None:
    """Load full story with all chapters."""
    path = STORIES_DIR / f"{story_id}.json"
    return _load_json(path)


def get_chapter(story_id: str, chapter_index: int) -> dict | None:
    """Load a specific chapter from a story."""
    story = load_story(story_id)
    if not story:
        return None
    chapters = story.get("chapters", [])
    if chapter_index < 0 or chapter_index >= len(chapters):
        return None
    return chapters[chapter_index]


def get_story_ids() -> list[str]:
    """Return list of all valid story IDs."""
    return [s["id"] for s in load_all_stories()]
