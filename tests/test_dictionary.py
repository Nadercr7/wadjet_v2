"""Dictionary API tests — search, categories, alphabet, lookup."""

from __future__ import annotations

from httpx import AsyncClient


async def test_dictionary_list(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary")
    assert resp.status_code == 200


async def test_dictionary_categories(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/categories")
    assert resp.status_code == 200


async def test_dictionary_alphabet(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/alphabet")
    assert resp.status_code == 200


async def test_dictionary_lookup_a1(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/A1")
    assert resp.status_code == 200
    body = resp.json()
    # Should contain the glyph code
    assert "A1" in str(body)


async def test_dictionary_lookup_not_found(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/ZZ999")
    assert resp.status_code == 404


async def test_dictionary_search(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary?search=man")
    assert resp.status_code == 200


async def test_dictionary_pagination(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary?page=1&per_page=10")
    assert resp.status_code == 200


async def test_dictionary_lesson_valid(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/lesson/1")
    assert resp.status_code == 200


async def test_dictionary_lesson_invalid(test_client: AsyncClient):
    resp = await test_client.get("/api/dictionary/lesson/0")
    assert resp.status_code == 404
