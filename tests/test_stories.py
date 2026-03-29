"""Stories API tests — listing, chapter access, interactions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def test_stories_list(test_client: AsyncClient):
    resp = await test_client.get("/api/stories")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, (list, dict))


async def test_stories_invalid_id_format(test_client: AsyncClient):
    resp = await test_client.get("/api/stories/!!invalid!!")
    assert resp.status_code == 400


async def test_stories_nonexistent(test_client: AsyncClient):
    resp = await test_client.get("/api/stories/nonexistent-story-xyz")
    assert resp.status_code == 404


async def test_stories_chapter_invalid_story(test_client: AsyncClient):
    resp = await test_client.get("/api/stories/nonexistent-story/chapters/0")
    assert resp.status_code == 404


async def test_stories_valid_story():
    """If stories exist, loading one should work."""
    from app.core.stories_engine import load_all_stories

    stories = load_all_stories()
    if not stories:
        pytest.skip("No story files available")


async def test_stories_chapter_out_of_bounds(test_client: AsyncClient):
    """Accessing chapter beyond last → 404."""
    from app.core.stories_engine import load_all_stories

    stories = load_all_stories()
    if not stories:
        pytest.skip("No story files available")

    story_id = stories[0]["id"]
    resp = await test_client.get(f"/api/stories/{story_id}/chapters/9999")
    assert resp.status_code == 404


async def test_stories_get_story_success(test_client: AsyncClient):
    """GET /api/stories/{id} with a valid story returns full data."""
    from app.core.stories_engine import get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    resp = await test_client.get(f"/api/stories/{ids[0]}")
    assert resp.status_code == 200
    body = resp.json()
    assert "chapters" in body or "title" in body


async def test_stories_get_chapter_success(test_client: AsyncClient):
    """GET /api/stories/{id}/chapters/0 returns chapter data."""
    from app.core.stories_engine import get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    resp = await test_client.get(f"/api/stories/{ids[0]}/chapters/0")
    assert resp.status_code == 200
    body = resp.json()
    assert "chapter" in body
    assert "total_chapters" in body


async def test_stories_chapter_negative_index(test_client: AsyncClient):
    """Negative chapter index → 400."""
    from app.core.stories_engine import get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    resp = await test_client.get(f"/api/stories/{ids[0]}/chapters/-1")
    assert resp.status_code == 400


async def test_stories_interact_invalid_story(test_client: AsyncClient):
    """POST interact on nonexistent story → 404."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stories/nonexistent-story/interact",
        json={"chapter_index": 0, "interaction_index": 0, "answer": "a"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 404


async def test_stories_interact_invalid_id_format(test_client: AsyncClient):
    """POST interact with bad story ID → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stories/!!BAD!!/interact",
        json={"chapter_index": 0, "interaction_index": 0, "answer": "a"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_stories_list_has_count(test_client: AsyncClient):
    """List response includes count field."""
    resp = await test_client.get("/api/stories")
    body = resp.json()
    assert "count" in body
    assert body["count"] >= 0


async def test_stories_image_no_story(test_client: AsyncClient):
    """POST image generate for nonexistent story → 404."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stories/nonexistent-story/chapters/0/image",
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 404


async def test_stories_image_bad_story_id(test_client: AsyncClient):
    """POST image generate with bad story ID → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stories/!!invalid!!/chapters/0/image",
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400
