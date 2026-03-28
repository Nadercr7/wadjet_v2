"""User API — profile, history, favorites, stats, progress, and settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.password import hash_password, verify_password
from app.db.crud import (
    add_favorite,
    get_all_story_progress,
    get_favorites,
    get_scan_history,
    get_user_stats,
    remove_favorite,
    update_user_password,
    update_user_profile,
    upsert_story_progress,
)
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import (
    ChangePasswordRequest,
    FavoriteRequest,
    StoryProgressRequest,
    UpdateProfileRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile")
async def profile(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return JSONResponse(content=UserResponse.model_validate(user).model_dump(mode="json"))


@router.patch("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's display name and/or language."""
    updated = await update_user_profile(
        db,
        user.id,
        display_name=body.display_name,
        preferred_lang=body.preferred_lang,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse(content=UserResponse.model_validate(updated).model_dump(mode="json"))


@router.patch("/password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password (requires current password)."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    new_hash = hash_password(body.new_password)
    await update_user_password(db, user.id, new_hash)
    return JSONResponse(content={"ok": True})


@router.get("/history")
async def history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get the current user's scan history."""
    entries = await get_scan_history(db, user.id)
    return JSONResponse(content=[
        {
            "id": e.id,
            "results_json": e.results_json,
            "confidence_avg": e.confidence_avg,
            "glyph_count": e.glyph_count,
            "created_at": str(e.created_at),
        }
        for e in entries
    ])


@router.get("/favorites")
async def favorites(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get the current user's favorites."""
    favs = await get_favorites(db, user.id)
    return JSONResponse(content=[
        {
            "id": f.id,
            "item_type": f.item_type,
            "item_id": f.item_id,
            "created_at": str(f.created_at),
        }
        for f in favs
    ])


@router.post("/favorites")
async def add_fav(
    body: FavoriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a favorite item."""
    try:
        fav = await add_favorite(db, user.id, body.item_type, body.item_id)
    except Exception:
        raise HTTPException(status_code=409, detail="Already favorited")
    return JSONResponse(content={"id": fav.id, "item_type": fav.item_type, "item_id": fav.item_id}, status_code=201)


@router.delete("/favorites/{item_type}/{item_id}")
async def remove_fav(
    item_type: str,
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a favorite item."""
    if item_type not in ("landmark", "glyph", "story"):
        raise HTTPException(status_code=400, detail="Invalid item_type")
    await remove_favorite(db, user.id, item_type, item_id)
    return JSONResponse(content={"ok": True})


@router.get("/stats")
async def stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get aggregated stats for the dashboard."""
    data = await get_user_stats(db, user.id)
    return JSONResponse(content=data)


@router.get("/progress")
async def progress(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all story progress for the dashboard."""
    entries = await get_all_story_progress(db, user.id)
    return JSONResponse(content=[
        {
            "id": sp.id,
            "story_id": sp.story_id,
            "chapter_index": sp.chapter_index,
            "glyphs_learned": sp.glyphs_learned,
            "score": sp.score,
            "completed": sp.completed,
            "updated_at": str(sp.updated_at),
        }
        for sp in entries
    ])


@router.post("/progress")
async def save_progress(
    body: StoryProgressRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save/update story progress."""
    sp = await upsert_story_progress(
        db,
        user.id,
        body.story_id,
        body.chapter_index,
        body.glyphs_learned,
        body.score,
        body.completed,
    )
    return JSONResponse(content={
        "id": sp.id,
        "story_id": sp.story_id,
        "chapter_index": sp.chapter_index,
        "completed": sp.completed,
    })
