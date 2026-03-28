"""Database CRUD operations."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Favorite, RefreshToken, ScanHistory, StoryProgress, User


# ── Users ──

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password_hash: str, display_name: str | None = None) -> User:
    user = User(email=email, password_hash=password_hash, display_name=display_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ── Refresh Tokens ──

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def store_refresh_token(db: AsyncSession, user_id: str, token: str, expires_at: datetime) -> None:
    rt = RefreshToken(user_id=user_id, token_hash=_hash_token(token), expires_at=expires_at)
    db.add(rt)
    await db.commit()


async def validate_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    token_hash = _hash_token(token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token: str) -> None:
    token_hash = _hash_token(token)
    await db.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))
    await db.commit()


async def delete_user_refresh_tokens(db: AsyncSession, user_id: str) -> None:
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.commit()


# ── Scan History ──

async def add_scan_history(db: AsyncSession, user_id: str, results_json: str, confidence_avg: float, glyph_count: int) -> ScanHistory:
    entry = ScanHistory(user_id=user_id, results_json=results_json, confidence_avg=confidence_avg, glyph_count=glyph_count)
    db.add(entry)
    await db.commit()
    return entry


async def get_scan_history(db: AsyncSession, user_id: str, limit: int = 20) -> list[ScanHistory]:
    result = await db.execute(
        select(ScanHistory).where(ScanHistory.user_id == user_id).order_by(ScanHistory.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ── Favorites ──

async def add_favorite(db: AsyncSession, user_id: str, item_type: str, item_id: str) -> Favorite:
    fav = Favorite(user_id=user_id, item_type=item_type, item_id=item_id)
    db.add(fav)
    await db.commit()
    return fav


async def remove_favorite(db: AsyncSession, user_id: str, item_type: str, item_id: str) -> None:
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.item_type == item_type,
            Favorite.item_id == item_id,
        )
    )
    await db.commit()


async def get_favorites(db: AsyncSession, user_id: str) -> list[Favorite]:
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user_id).order_by(Favorite.created_at.desc())
    )
    return list(result.scalars().all())


# ── Story Progress ──

async def get_story_progress(db: AsyncSession, user_id: str, story_id: str) -> StoryProgress | None:
    result = await db.execute(
        select(StoryProgress).where(StoryProgress.user_id == user_id, StoryProgress.story_id == story_id)
    )
    return result.scalar_one_or_none()
