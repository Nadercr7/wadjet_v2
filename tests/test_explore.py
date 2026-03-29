"""Explore API tests — landmarks listing, detail, identify validation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_landmarks_list(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks")
    assert resp.status_code == 200


async def test_landmarks_categories(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks/categories")
    assert resp.status_code == 200


async def test_landmarks_search(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks?search=pyramid")
    assert resp.status_code == 200


async def test_landmarks_pagination(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks?page=1&per_page=5")
    assert resp.status_code == 200


async def test_identify_empty_file(test_client: AsyncClient):
    """Empty upload to identify → 422."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/explore/identify",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 422


async def test_identify_invalid_magic_bytes(test_client: AsyncClient):
    """Invalid image to identify → 422."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/explore/identify",
        files={"file": ("test.jpg", b"not-an-image", "image/jpeg")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 422
