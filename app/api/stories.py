"""Stories of the Nile — API endpoints.

Provides story listing, chapter retrieval, interaction checking,
image generation, and progress tracking.
"""

from __future__ import annotations

import asyncio
import logging
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.stories_engine import get_chapter, get_story_ids, load_all_stories, load_story
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stories", tags=["stories"])

# ── Concurrency limiter for image generation (STORY-005) ──
_IMAGE_GEN_SEMAPHORE = asyncio.Semaphore(3)  # max 3 concurrent image gen requests

# ── Story Listing ─────────────────────────────────────────────────────────

_STORY_ID_RE = re.compile(r"^[a-z0-9\-]{1,50}$")


@router.get("")
@limiter.limit("60/minute")
async def list_stories(request: Request):
    """List all stories (metadata only, no chapter content)."""
    stories = load_all_stories()
    return {"stories": stories, "count": len(stories)}


@router.get("/{story_id}")
@limiter.limit("60/minute")
async def get_story(request: Request, story_id: str):
    """Get full story with all chapters."""
    if not _STORY_ID_RE.match(story_id):
        raise HTTPException(status_code=400, detail="Invalid story ID")
    story = load_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.get("/{story_id}/chapters/{index}")
@limiter.limit("60/minute")
async def get_story_chapter(request: Request, story_id: str, index: int):
    """Get a specific chapter from a story."""
    if not _STORY_ID_RE.match(story_id):
        raise HTTPException(status_code=400, detail="Invalid story ID")
    if index < 0:
        raise HTTPException(status_code=400, detail="Invalid chapter index")
    chapter = get_chapter(story_id, index)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    # Include story-level metadata for context
    story = load_story(story_id)
    return {
        "chapter": chapter,
        "story_id": story_id,
        "total_chapters": len(story.get("chapters", [])) if story else 0,
    }


# ── Interaction Checking ──────────────────────────────────────────────────

class InteractionSubmit(BaseModel):
    chapter_index: int = Field(ge=0)
    interaction_index: int = Field(ge=0)
    answer: str = Field(min_length=1, max_length=200)


@router.post("/{story_id}/interact")
@limiter.limit("120/minute")
async def check_interaction(request: Request, story_id: str, body: InteractionSubmit):
    """Check an interaction answer (choose_glyph, write_word)."""
    if not _STORY_ID_RE.match(story_id):
        raise HTTPException(status_code=400, detail="Invalid story ID")

    chapter = get_chapter(story_id, body.chapter_index)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    interactions = chapter.get("interactions", [])
    if body.interaction_index >= len(interactions):
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction = interactions[body.interaction_index]
    itype = interaction["type"]

    if itype == "choose_glyph":
        correct = interaction["correct"]
        is_correct = body.answer == correct
        result = {
            "correct": is_correct,
            "type": itype,
        }
        if is_correct:
            result["explanation"] = interaction.get("explanation", {})
            result["correct_answer"] = correct
        else:
            result["explanation"] = interaction.get("explanation", {})
        return result

    elif itype == "write_word":
        target_code = interaction["gardiner_code"]
        target_glyph = interaction["target_glyph"]
        is_correct = body.answer.strip() in (target_code, target_glyph)
        return {
            "correct": is_correct,
            "type": itype,
            "target_glyph": target_glyph if is_correct else None,
            "gardiner_code": target_code if is_correct else None,
            "hint": interaction.get("hint", {}) if not is_correct else None,
        }

    elif itype == "glyph_discovery":
        # Discovery is always "correct" — just marking as seen
        return {"correct": True, "type": itype}

    elif itype == "story_decision":
        # Branching narrative — all choices are valid (educational, not wrong)
        choices = interaction.get("choices", [])
        selected = next((c for c in choices if c["id"] == body.answer), None)
        if not selected:
            raise HTTPException(status_code=400, detail="Invalid choice")
        return {
            "correct": True,
            "type": itype,
            "choice_id": selected["id"],
            "outcome": {
                "en": selected.get("outcome", {}).get("en", ""),
                "ar": selected.get("outcome", {}).get("ar", ""),
            },
        }

    raise HTTPException(status_code=400, detail="Unknown interaction type")


# ── Image Generation ──────────────────────────────────────────────────────

@router.post("/{story_id}/chapters/{index}/image")
@limiter.limit("10/minute")
async def generate_chapter_image(request: Request, story_id: str, index: int):
    """Generate AI illustration for a story chapter (Cloudflare FLUX → SDXL → None)."""
    if not _STORY_ID_RE.match(story_id):
        raise HTTPException(status_code=400, detail="Invalid story ID")

    chapter = get_chapter(story_id, index)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    prompt = chapter.get("scene_image_prompt", "")
    if not prompt:
        return JSONResponse({"image_url": None, "status": "no_prompt"})

    from app.core.image_service import generate_story_image

    async with _IMAGE_GEN_SEMAPHORE:
        image_url = await generate_story_image(prompt, story_id, index)
    if image_url:
        return {"image_url": image_url, "status": "ok"}

    return JSONResponse({"image_url": None, "status": "generation_failed"})
