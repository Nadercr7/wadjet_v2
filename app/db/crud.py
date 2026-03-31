"""Database CRUD operations."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import case, func, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmailToken, Favorite, RefreshToken, ScanHistory, StoryProgress, User


# ── Users ──

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_google_id(db: AsyncSession, google_id: str) -> User | None:
    result = await db.execute(select(User).where(User.google_id == google_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password_hash: str | None = None,
    display_name: str | None = None,
    google_id: str | None = None,
    auth_provider: str = "email",
    email_verified: bool = False,
    avatar_url: str | None = None,
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        display_name=display_name,
        google_id=google_id,
        auth_provider=auth_provider,
        email_verified=email_verified,
        avatar_url=avatar_url,
    )
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


async def get_all_story_progress(db: AsyncSession, user_id: str) -> list[StoryProgress]:
    result = await db.execute(
        select(StoryProgress).where(StoryProgress.user_id == user_id).order_by(StoryProgress.updated_at.desc())
    )
    return list(result.scalars().all())


async def upsert_story_progress(
    db: AsyncSession,
    user_id: str,
    story_id: str,
    chapter_index: int,
    glyphs_learned: str = "[]",
    score: int = 0,
    completed: bool = False,
) -> StoryProgress:
    existing = await get_story_progress(db, user_id, story_id)
    if existing:
        existing.chapter_index = chapter_index
        existing.glyphs_learned = glyphs_learned
        existing.score = score
        existing.completed = completed
        await db.commit()
        await db.refresh(existing)
        return existing
    sp = StoryProgress(
        user_id=user_id,
        story_id=story_id,
        chapter_index=chapter_index,
        glyphs_learned=glyphs_learned,
        score=score,
        completed=completed,
    )
    try:
        db.add(sp)
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # Race condition: another request inserted first — update instead
        existing = await get_story_progress(db, user_id, story_id)
        if existing:
            existing.chapter_index = chapter_index
            existing.glyphs_learned = glyphs_learned
            existing.score = score
            existing.completed = completed
            await db.commit()
            await db.refresh(existing)
            return existing
    await db.commit()
    await db.refresh(sp)
    return sp


# ── User Profile Updates ──

async def update_user_profile(db: AsyncSession, user_id: str, display_name: str | None = None, preferred_lang: str | None = None) -> User | None:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    if display_name is not None:
        user.display_name = display_name
    if preferred_lang is not None:
        user.preferred_lang = preferred_lang
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_password(db: AsyncSession, user_id: str, new_password_hash: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    user.password_hash = new_password_hash
    await db.commit()
    return True


async def link_google_account(db: AsyncSession, user: User, google_id: str, avatar_url: str | None = None) -> User:
    """Link a Google account to an existing email user (becomes 'both' provider)."""
    user.google_id = google_id
    user.auth_provider = "both"
    user.email_verified = True
    if avatar_url and not user.avatar_url:
        user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)
    return user


async def verify_user_email(db: AsyncSession, user_id: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    user.email_verified = True
    await db.commit()
    return True


# ── Email Tokens ──

async def create_email_token(db: AsyncSession, user_id: str, token_hash: str, token_type: str, expires_at: datetime) -> EmailToken:
    # Delete existing tokens of the same type for this user
    await db.execute(
        delete(EmailToken).where(EmailToken.user_id == user_id, EmailToken.token_type == token_type)
    )
    et = EmailToken(user_id=user_id, token_hash=token_hash, token_type=token_type, expires_at=expires_at)
    db.add(et)
    await db.commit()
    return et


async def validate_email_token(db: AsyncSession, token_hash: str, token_type: str) -> EmailToken | None:
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token_hash == token_hash,
            EmailToken.token_type == token_type,
            EmailToken.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def delete_email_token(db: AsyncSession, token_id: int) -> None:
    await db.execute(delete(EmailToken).where(EmailToken.id == token_id))
    await db.commit()


# ── Stats ──

async def get_user_stats(db: AsyncSession, user_id: str) -> dict:
    # Combined query 1: scan stats (count, total glyphs, today's scans) — 1 round trip
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    scan_row = await db.execute(
        select(
            func.count().label("scan_count"),
            func.coalesce(func.sum(ScanHistory.glyph_count), 0).label("total_glyphs"),
            func.coalesce(func.sum(case((ScanHistory.created_at >= today_start, 1), else_=0)), 0).label("scans_today"),
        ).where(ScanHistory.user_id == user_id)
    )
    s = scan_row.one()

    # Combined query 2: favorites count — 1 round trip
    fav_count = await db.execute(
        select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
    )

    # Combined query 3: story stats (started + completed) — 1 round trip
    story_row = await db.execute(
        select(
            func.count().label("story_count"),
            func.coalesce(func.sum(case((StoryProgress.completed == True, 1), else_=0)), 0).label("completed_count"),  # noqa: E712
        ).where(StoryProgress.user_id == user_id)
    )
    st = story_row.one()

    return {
        "scans": s.scan_count or 0,
        "favorites": fav_count.scalar() or 0,
        "stories_started": st.story_count or 0,
        "stories_completed": st.completed_count or 0,
        "total_glyphs_scanned": s.total_glyphs or 0,
        "scans_today": s.scans_today or 0,
    }
