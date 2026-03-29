"""Database CRUD tests — users, favorites, history, story progress, stats, cascades."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.db.crud import (
    add_favorite,
    add_scan_history,
    create_user,
    get_favorites,
    get_scan_history,
    get_user_by_email,
    get_user_by_id,
    get_user_stats,
    remove_favorite,
    update_user_password,
    update_user_profile,
    upsert_story_progress,
)
from app.db.models import Favorite, ScanHistory, StoryProgress, User


# ── User CRUD ──


async def test_create_user(test_db: AsyncSession):
    user = await create_user(test_db, "create@test.com", hash_password("Test1234"))
    assert user.id
    assert user.email == "create@test.com"


async def test_get_user_by_email(test_db: AsyncSession):
    await create_user(test_db, "find@test.com", hash_password("Test1234"))
    found = await get_user_by_email(test_db, "find@test.com")
    assert found is not None
    assert found.email == "find@test.com"


async def test_get_user_by_email_not_found(test_db: AsyncSession):
    result = await get_user_by_email(test_db, "ghost@test.com")
    assert result is None


async def test_get_user_by_id(test_db: AsyncSession):
    user = await create_user(test_db, "byid@test.com", hash_password("Test1234"))
    found = await get_user_by_id(test_db, user.id)
    assert found is not None
    assert found.email == "byid@test.com"


async def test_update_user_profile(test_db: AsyncSession):
    user = await create_user(test_db, "profile@test.com", hash_password("Test1234"))
    updated = await update_user_profile(test_db, user.id, display_name="New Name", preferred_lang="ar")
    assert updated.display_name == "New Name"
    assert updated.preferred_lang == "ar"


async def test_update_user_password(test_db: AsyncSession):
    user = await create_user(test_db, "pw@test.com", hash_password("OldPass1"))
    new_hash = hash_password("NewPass1")
    result = await update_user_password(test_db, user.id, new_hash)
    assert result is True


# ── Favorites ──


async def test_add_and_get_favorite(test_db: AsyncSession):
    user = await create_user(test_db, "fav@test.com", hash_password("Test1234"))
    fav = await add_favorite(test_db, user.id, "landmark", "pyramids")
    assert fav.item_type == "landmark"

    favs = await get_favorites(test_db, user.id)
    assert len(favs) == 1


async def test_remove_favorite(test_db: AsyncSession):
    user = await create_user(test_db, "rmfav@test.com", hash_password("Test1234"))
    await add_favorite(test_db, user.id, "glyph", "A1")
    await remove_favorite(test_db, user.id, "glyph", "A1")
    favs = await get_favorites(test_db, user.id)
    assert len(favs) == 0


async def test_duplicate_favorite_raises(test_db: AsyncSession):
    from sqlalchemy.exc import IntegrityError

    user = await create_user(test_db, "dupfav@test.com", hash_password("Test1234"))
    await add_favorite(test_db, user.id, "story", "isis")
    with pytest.raises(IntegrityError):
        await add_favorite(test_db, user.id, "story", "isis")


# ── Scan History ──


async def test_add_and_get_scan_history(test_db: AsyncSession):
    user = await create_user(test_db, "scan@test.com", hash_password("Test1234"))
    entry = await add_scan_history(test_db, user.id, '{"glyphs":[]}', 0.85, 5)
    assert entry.glyph_count == 5

    history = await get_scan_history(test_db, user.id)
    assert len(history) == 1


# ── Story Progress ──


async def test_upsert_story_progress_create(test_db: AsyncSession):
    user = await create_user(test_db, "story@test.com", hash_password("Test1234"))
    sp = await upsert_story_progress(test_db, user.id, "isis-and-osiris", 2, score=10)
    assert sp.chapter_index == 2
    assert sp.score == 10


async def test_upsert_story_progress_update(test_db: AsyncSession):
    user = await create_user(test_db, "story2@test.com", hash_password("Test1234"))
    await upsert_story_progress(test_db, user.id, "ra-journey", 1)
    sp = await upsert_story_progress(test_db, user.id, "ra-journey", 3, completed=True)
    assert sp.chapter_index == 3
    assert sp.completed is True


# ── Stats ──


async def test_get_user_stats_empty(test_db: AsyncSession):
    user = await create_user(test_db, "stats@test.com", hash_password("Test1234"))
    stats = await get_user_stats(test_db, user.id)
    assert stats["scans"] == 0
    assert stats["favorites"] == 0
    assert stats["stories_started"] == 0
    assert stats["stories_completed"] == 0


async def test_get_user_stats_with_data(test_db: AsyncSession):
    user = await create_user(test_db, "stats2@test.com", hash_password("Test1234"))
    await add_scan_history(test_db, user.id, "{}", 0.9, 3)
    await add_scan_history(test_db, user.id, "{}", 0.8, 7)
    await add_favorite(test_db, user.id, "landmark", "sphinx")
    await upsert_story_progress(test_db, user.id, "isis", 5, completed=True)
    await upsert_story_progress(test_db, user.id, "ra", 2)

    stats = await get_user_stats(test_db, user.id)
    assert stats["scans"] == 2
    assert stats["total_glyphs_scanned"] == 10
    assert stats["favorites"] == 1
    assert stats["stories_started"] == 2
    assert stats["stories_completed"] == 1


# ── Cascade Delete ──


async def test_cascade_delete_removes_children(test_db: AsyncSession):
    """Deleting a user cascades to all child records."""
    # Enable FK enforcement for SQLite
    await test_db.execute(text("PRAGMA foreign_keys=ON"))

    user = await create_user(test_db, "cascade@test.com", hash_password("Test1234"))
    uid = user.id
    await add_favorite(test_db, uid, "landmark", "karnak")
    await add_scan_history(test_db, uid, "{}", 0.5, 1)
    await upsert_story_progress(test_db, uid, "anubis", 1)

    # Delete user via raw SQL to trigger ON DELETE CASCADE
    await test_db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
    await test_db.commit()

    # Verify all children are gone
    favs = (await test_db.execute(select(Favorite).where(Favorite.user_id == uid))).scalars().all()
    scans = (await test_db.execute(select(ScanHistory).where(ScanHistory.user_id == uid))).scalars().all()
    progress = (await test_db.execute(select(StoryProgress).where(StoryProgress.user_id == uid))).scalars().all()
    assert len(favs) == 0
    assert len(scans) == 0
    assert len(progress) == 0
