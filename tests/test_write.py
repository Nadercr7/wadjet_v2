"""Write API tests — alpha mode, palette."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_write_palette(test_client: AsyncClient):
    resp = await test_client.get("/api/write/palette")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, (list, dict))


async def test_write_alpha_mode(test_client: AsyncClient):
    """Alpha mode converts English letters to hieroglyphs."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "hello", "mode": "alpha"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "glyphs" in body or "signs" in body or "result" in body


async def test_write_mdc_mode(test_client: AsyncClient):
    """MdC mode converts transliteration to hieroglyphs."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "anx", "mode": "mdc"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200


async def test_write_invalid_mode(test_client: AsyncClient):
    """Invalid mode → 422."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "test", "mode": "invalid"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 422


async def test_write_empty_text(test_client: AsyncClient):
    """Empty text → 422."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "", "mode": "alpha"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 422


async def test_write_text_too_long(test_client: AsyncClient):
    """Text > 500 chars → 422."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "a" * 501, "mode": "alpha"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 422
