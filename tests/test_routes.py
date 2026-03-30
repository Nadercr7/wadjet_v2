"""API route tests — health check, page rendering, 404s, validation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Health Check ──


async def test_health_check(test_client: AsyncClient):
    resp = await test_client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "version" in body
    assert "database" in body
    assert "services" in body


# ── Page Routes ──


PAGE_ROUTES = [
    "/welcome",
]

PROTECTED_ROUTES = [
    "/",
    "/hieroglyphs",
    "/landmarks",
    "/scan",
    "/dictionary",
    "/write",
    "/explore",
    "/chat",
    "/stories",
    "/dashboard",
    "/settings",
    "/feedback",
]


@pytest.mark.parametrize("path", PAGE_ROUTES)
async def test_page_renders_html(test_client: AsyncClient, path: str):
    resp = await test_client.get(path)
    assert resp.status_code == 200
    assert "<html" in resp.text.lower()


@pytest.mark.parametrize("path", PROTECTED_ROUTES)
async def test_protected_redirects_to_welcome(test_client: AsyncClient, path: str):
    resp = await test_client.get(path, follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "/welcome" in location


@pytest.mark.parametrize("path", PROTECTED_ROUTES)
async def test_protected_renders_with_session(test_client: AsyncClient, path: str):
    resp = await test_client.get(path, cookies={"wadjet_session": "1"})
    assert resp.status_code == 200
    assert "<html" in resp.text.lower()


async def test_quiz_redirects_to_stories(test_client: AsyncClient):
    resp = await test_client.get("/quiz", follow_redirects=False)
    assert resp.status_code in (301, 307)
    assert "/stories" in resp.headers.get("location", "")


async def test_robots_txt(test_client: AsyncClient):
    resp = await test_client.get("/robots.txt")
    assert resp.status_code == 200
    assert "User-agent" in resp.text


async def test_sitemap_xml(test_client: AsyncClient):
    resp = await test_client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "xml" in resp.headers.get("content-type", "")


# ── 404 Handling ──


async def test_nonexistent_page_404(test_client: AsyncClient):
    resp = await test_client.get("/this-does-not-exist")
    assert resp.status_code == 404


async def test_invalid_story_id_404(test_client: AsyncClient):
    resp = await test_client.get("/stories/../../etc/passwd", cookies={"wadjet_session": "1"})
    assert resp.status_code in (404, 422)


async def test_nonexistent_story_404(test_client: AsyncClient):
    resp = await test_client.get("/stories/nonexistent-story-id", cookies={"wadjet_session": "1"})
    assert resp.status_code == 404


async def test_lesson_out_of_bounds_lower(test_client: AsyncClient):
    resp = await test_client.get("/dictionary/lesson/0", cookies={"wadjet_session": "1"})
    assert resp.status_code == 404


async def test_lesson_out_of_bounds_upper(test_client: AsyncClient):
    resp = await test_client.get("/dictionary/lesson/6", cookies={"wadjet_session": "1"})
    assert resp.status_code == 404


async def test_lesson_valid(test_client: AsyncClient):
    resp = await test_client.get("/dictionary/lesson/1", cookies={"wadjet_session": "1"})
    assert resp.status_code == 200


# ── Dictionary API ──


async def test_dictionary_list(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary")
    assert resp.status_code == 200
    body = resp.json()
    assert "signs" in body or "items" in body or isinstance(body, list) or "results" in body


async def test_dictionary_categories(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/categories")
    assert resp.status_code == 200


async def test_dictionary_alphabet(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/alphabet")
    assert resp.status_code == 200


async def test_dictionary_lookup_valid(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/A1")
    assert resp.status_code == 200
    body = resp.json()
    assert "code" in body or "sign" in body or "transliteration" in body


async def test_dictionary_lookup_not_found(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/ZZ999")
    assert resp.status_code == 404


# ── Landmarks API ──


async def test_landmarks_list(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks")
    assert resp.status_code == 200


async def test_landmarks_categories(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks/categories")
    assert resp.status_code == 200


# ── Write API ──


async def test_write_palette(test_client: AsyncClient):
    resp = await test_client.get("/api/write/palette")
    assert resp.status_code == 200


# ── Stories API ──


async def test_stories_list(test_client: AsyncClient):
    resp = await test_client.get("/api/stories")
    assert resp.status_code == 200


async def test_stories_invalid_id(test_client: AsyncClient):
    resp = await test_client.get("/api/stories/!!invalid!!")
    assert resp.status_code == 400
