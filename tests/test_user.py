"""User API tests — profile, favorites, history, stats, progress."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Profile ──


async def test_get_profile(authenticated_client: AsyncClient):
    resp = await authenticated_client.get("/api/user/profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "test@wadjet.app"
    assert body["display_name"] == "Test User"


async def test_get_profile_unauthenticated(test_client: AsyncClient):
    resp = await test_client.get("/api/user/profile")
    assert resp.status_code == 401


async def test_update_profile(authenticated_client: AsyncClient):
    resp = await authenticated_client.patch(
        "/api/user/profile",
        json={"display_name": "Updated Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated Name"


# ── Password ──


async def test_change_password(authenticated_client: AsyncClient):
    resp = await authenticated_client.patch(
        "/api/user/password",
        json={"current_password": "TestPass123", "new_password": "NewPass456"},
    )
    assert resp.status_code == 200


async def test_change_password_wrong_current(authenticated_client: AsyncClient):
    resp = await authenticated_client.patch(
        "/api/user/password",
        json={"current_password": "WrongOldPass1", "new_password": "NewPass456"},
    )
    assert resp.status_code == 400


# ── Favorites ──


async def test_add_favorite(authenticated_client: AsyncClient):
    resp = await authenticated_client.post(
        "/api/user/favorites",
        json={"item_type": "landmark", "item_id": "pyramids-of-giza"},
    )
    assert resp.status_code == 201


async def test_get_favorites(authenticated_client: AsyncClient):
    # Add one first
    await authenticated_client.post(
        "/api/user/favorites",
        json={"item_type": "glyph", "item_id": "A1"},
    )
    resp = await authenticated_client.get("/api/user/favorites")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_delete_favorite_invalid_type(authenticated_client: AsyncClient):
    resp = await authenticated_client.delete("/api/user/favorites/invalid_type/item1")
    assert resp.status_code == 400


async def test_delete_favorite(authenticated_client: AsyncClient):
    # Add then delete
    await authenticated_client.post(
        "/api/user/favorites",
        json={"item_type": "story", "item_id": "isis"},
    )
    resp = await authenticated_client.delete("/api/user/favorites/story/isis")
    assert resp.status_code == 200


# ── History ──


async def test_get_history(authenticated_client: AsyncClient):
    resp = await authenticated_client.get("/api/user/history")
    assert resp.status_code == 200


# ── Stats ──


async def test_get_stats(authenticated_client: AsyncClient):
    resp = await authenticated_client.get("/api/user/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "scans" in body
    assert "favorites" in body


# ── Progress ──


async def test_get_progress(authenticated_client: AsyncClient):
    resp = await authenticated_client.get("/api/user/progress")
    assert resp.status_code == 200


async def test_post_progress(authenticated_client: AsyncClient):
    resp = await authenticated_client.post(
        "/api/user/progress",
        json={
            "story_id": "isis-and-osiris",
            "chapter_index": 2,
            "score": 10,
            "completed": False,
        },
    )
    assert resp.status_code == 200


# ── Limits ──


async def test_get_limits(authenticated_client: AsyncClient):
    resp = await authenticated_client.get("/api/user/limits")
    assert resp.status_code == 200
    body = resp.json()
    # limits are nested under "limits" key
    assert "limits" in body
    assert "scans_per_day" in body["limits"]
