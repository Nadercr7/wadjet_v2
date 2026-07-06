"""Tests for GET /api/images/pexels-search — server-side Pexels proxy."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient

from app.api import images


@pytest.fixture(autouse=True)
def _clear_cache():
    images._cache.clear()
    yield
    images._cache.clear()


def _pexels_response(status_code: int = 200, photos: list | None = None) -> httpx.Response:
    body = {
        "total_results": len(photos or []),
        "page": 1,
        "per_page": 1,
        "photos": photos
        or [
            {
                "id": 123,
                "width": 4000,
                "height": 3000,
                "url": "https://www.pexels.com/photo/123/",
                "photographer": "Jane",
                "photographer_url": "https://www.pexels.com/@jane",
                "alt": "Pyramids",
                "src": {
                    "original": "https://images.pexels.com/123/original.jpg",
                    "large2x": "https://images.pexels.com/123/large2x.jpg",
                    "large": "https://images.pexels.com/123/large.jpg",
                    "medium": "https://images.pexels.com/123/medium.jpg",
                    "small": "https://images.pexels.com/123/small.jpg",
                    "portrait": "x",
                    "landscape": "x",
                    "tiny": "x",
                },
            }
        ],
    }
    return httpx.Response(status_code, json=body, request=httpx.Request("GET", images.PEXELS_SEARCH_URL))


async def test_pexels_search_requires_auth(test_client: AsyncClient):
    resp = await test_client.get("/api/images/pexels-search", params={"query": "giza"})
    assert resp.status_code == 401


async def test_pexels_search_unconfigured_returns_503(authenticated_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pexels_api_keys", "")
    resp = await authenticated_client.get("/api/images/pexels-search", params={"query": "giza"})
    assert resp.status_code == 503


async def test_pexels_search_proxies_and_slims(authenticated_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pexels_api_keys", "key-1")
    with patch.object(images, "_get_client") as get_client:
        get_client.return_value.get = AsyncMock(return_value=_pexels_response())
        resp = await authenticated_client.get(
            "/api/images/pexels-search",
            params={"query": "giza pyramids", "per_page": 1, "orientation": "landscape"},
        )
    assert resp.status_code == 200
    body = resp.json()
    photo = body["photos"][0]
    assert photo["src"]["large"] == "https://images.pexels.com/123/large.jpg"
    assert photo["src"]["medium"] == "https://images.pexels.com/123/medium.jpg"
    assert photo["src"]["original"] == "https://images.pexels.com/123/original.jpg"
    assert photo["photographer"] == "Jane"
    # Slimmed: unconsumed variants dropped
    assert "large2x" not in photo["src"]
    # Upstream call carried the server-side key
    _, kwargs = get_client.return_value.get.call_args
    assert kwargs["headers"]["Authorization"] == "key-1"


async def test_pexels_search_rotates_key_on_429(authenticated_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pexels_api_keys", "key-1,key-2")
    with patch.object(images, "_get_client") as get_client:
        get_client.return_value.get = AsyncMock(
            side_effect=[_pexels_response(429), _pexels_response(200)]
        )
        resp = await authenticated_client.get(
            "/api/images/pexels-search", params={"query": "luxor"}
        )
    assert resp.status_code == 200
    calls = get_client.return_value.get.call_args_list
    assert calls[0].kwargs["headers"]["Authorization"] == "key-1"
    assert calls[1].kwargs["headers"]["Authorization"] == "key-2"


async def test_pexels_search_all_keys_limited_returns_429(authenticated_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pexels_api_keys", "key-1,key-2")
    with patch.object(images, "_get_client") as get_client:
        get_client.return_value.get = AsyncMock(
            side_effect=[_pexels_response(429), _pexels_response(429)]
        )
        resp = await authenticated_client.get(
            "/api/images/pexels-search", params={"query": "aswan"}
        )
    assert resp.status_code == 429


async def test_pexels_search_caches_results(authenticated_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pexels_api_keys", "key-1")
    with patch.object(images, "_get_client") as get_client:
        get_client.return_value.get = AsyncMock(return_value=_pexels_response())
        first = await authenticated_client.get(
            "/api/images/pexels-search", params={"query": "cairo"}
        )
        second = await authenticated_client.get(
            "/api/images/pexels-search", params={"query": "cairo"}
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert get_client.return_value.get.await_count == 1  # second hit served from cache


async def test_pexels_search_upstream_error_returns_502(authenticated_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pexels_api_keys", "key-1")
    with patch.object(images, "_get_client") as get_client:
        get_client.return_value.get = AsyncMock(return_value=_pexels_response(500))
        resp = await authenticated_client.get(
            "/api/images/pexels-search", params={"query": "siwa"}
        )
    assert resp.status_code == 502


async def test_pexels_search_validates_params(authenticated_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pexels_api_keys", "key-1")
    resp = await authenticated_client.get(
        "/api/images/pexels-search", params={"query": "x", "per_page": 99}
    )
    assert resp.status_code == 422
    resp = await authenticated_client.get(
        "/api/images/pexels-search", params={"query": "x", "orientation": "diagonal"}
    )
    assert resp.status_code == 422
