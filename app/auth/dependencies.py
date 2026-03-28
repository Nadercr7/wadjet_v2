"""FastAPI auth dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.db.crud import get_user_by_id
from app.db.database import get_db
from app.db.models import User


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Require authentication. Returns User or raises 401."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload or payload.get("type") == "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    """Optional auth. Returns User or None (for guest mode)."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") == "refresh":
        return None
    return await get_user_by_id(db, payload["sub"])
