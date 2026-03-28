"""User API — profile and history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.crud import get_favorites, get_scan_history
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import UserResponse

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile")
async def profile(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return JSONResponse(content=UserResponse.model_validate(user).model_dump(mode="json"))


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
