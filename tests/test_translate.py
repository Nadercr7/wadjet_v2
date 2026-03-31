"""Translation API tests — input validation, service availability, mock translate."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient


async def test_translate_empty_text(test_client: AsyncClient):
    """POST /api/translate with empty text → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/translate",
        json={"transliteration": "", "gardiner_sequence": ""},
        headers={"x-csrftoken": csrf},
    )
    # Empty string fails min_length or the explicit check
    assert resp.status_code in (400, 422)


async def test_translate_whitespace_only(test_client: AsyncClient):
    """POST /api/translate with whitespace-only text → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/translate",
        json={"transliteration": "   ", "gardiner_sequence": ""},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_translate_no_translator_service(test_client: AsyncClient):
    """POST /api/translate without translator in app state → returns fallback."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/translate",
        json={"transliteration": "nfr", "gardiner_sequence": "F35"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transliteration"] == "nfr"
    assert "error" in body


async def test_translate_with_mock_translator(test_client: AsyncClient):
    """POST /api/translate with mocked translator → success."""
    mock_translator = MagicMock()
    mock_translator.translate_async = AsyncMock(return_value={
        "english": "beautiful",
        "arabic": "جميل",
        "context": "Adjective meaning beautiful/good",
        "provider": "gemini",
        "latency_ms": 150,
        "from_cache": False,
    })
    test_client._transport.app.state.translator = mock_translator  # type: ignore[attr-defined]

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/translate",
        json={"transliteration": "nfr", "gardiner_sequence": "F35"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["english"] == "beautiful"
    assert body["arabic"] == "جميل"
    assert body["provider"] == "gemini"


async def test_translate_error_returns_500(test_client: AsyncClient):
    """POST /api/translate when translator raises → 500."""
    mock_translator = MagicMock()
    mock_translator.translate_async = AsyncMock(side_effect=RuntimeError("AI broke"))
    test_client._transport.app.state.translator = mock_translator  # type: ignore[attr-defined]

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/translate",
        json={"transliteration": "nfr", "gardiner_sequence": ""},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 500
