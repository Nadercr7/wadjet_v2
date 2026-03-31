"""Write API tests — alpha mode, palette, smart mode."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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


# ── Smart Mode Tests (TEST-007) ──


async def test_write_smart_mode_shortcut(test_client: AsyncClient):
    """Smart mode with a known phrase → instant shortcut, no AI needed."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "life prosperity health", "mode": "smart"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "smart"
    assert body["provider"] == "shortcut"
    assert len(body["glyphs"]) > 0
    assert body["hieroglyphs"] != ""


async def test_write_smart_mode_ai(test_client: AsyncClient):
    """Smart mode with AI-translated text → verify output structure."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    # Mock AI service to return MdC JSON
    mock_ai = MagicMock()
    mock_ai.available = True
    mock_ai.text_json = AsyncMock(return_value=(
        {
            "mdc": "Htp di nsw",
            "glyphs": [
                {"mdc": "Htp", "meaning": "offering"},
                {"mdc": "di", "meaning": "give"},
                {"mdc": "nsw", "meaning": "king"},
            ],
            "explanation": "Offering formula",
        },
        "gemini",
    ))

    test_client._transport.app.state.ai_service = mock_ai  # type: ignore[attr-defined]

    resp = await test_client.post(
        "/api/write",
        json={"text": "an offering which the king gives to osiris", "mode": "smart"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "smart"
    assert len(body["glyphs"]) > 0
    assert body["hieroglyphs"] != ""
    # Glyphs should contain recognized signs
    glyph_types = {g["type"] for g in body["glyphs"]}
    assert "glyph" in glyph_types


async def test_write_smart_mode_mdc_detect(test_client: AsyncClient):
    """Smart mode auto-detects MdC input and parses directly."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "Htp di nsw", "mode": "smart"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "smart"
    assert body["provider"] == "mdc_detect"
    assert len(body["glyphs"]) > 0


async def test_write_smart_mode_alpha_fallback(test_client: AsyncClient):
    """Smart mode without AI falls back to alpha (letter-by-letter)."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    # Use a phrase that's NOT a shortcut and not MdC
    resp = await test_client.post(
        "/api/write",
        json={"text": "cat", "mode": "smart"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "smart"
    assert body["provider"] in ("alpha_fallback", "none")
    assert len(body["glyphs"]) > 0


async def test_write_alpha_output_structure(test_client: AsyncClient):
    """Alpha mode output has correct glyph structure with code and unicode."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "ra", "mode": "alpha"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "alpha"
    assert body["hieroglyphs"] != ""
    for g in body["glyphs"]:
        assert g["type"] in ("glyph", "separator", "unknown")
        if g["type"] == "glyph":
            assert "code" in g
            assert "transliteration" in g


async def test_write_mdc_known_signs(test_client: AsyncClient):
    """MdC mode with known signs produces verified glyphs."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/write",
        json={"text": "anx", "mode": "mdc"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    glyphs = [g for g in body["glyphs"] if g["type"] == "glyph"]
    assert len(glyphs) >= 1
    assert any(g.get("verified") for g in glyphs)
