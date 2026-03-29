"""Audio API tests — TTS and STT endpoint validation."""

from __future__ import annotations

from httpx import AsyncClient


async def test_tts_no_groq_service(test_client: AsyncClient):
    """POST /api/tts without Groq service → 404."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/tts",
        data={"text": "Hello world", "lang": "en"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 404


async def test_stt_no_groq_service(test_client: AsyncClient):
    """POST /api/stt without Groq service → 404."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stt",
        data={"lang": "en"},
        files={"file": ("audio.wav", b"RIFF" + b"\x00" * 100, "audio/wav")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 404


async def test_stt_unsupported_format(test_client: AsyncClient):
    """POST /api/stt with unsupported MIME type → 400."""
    from unittest.mock import MagicMock

    # Inject mock groq so we get past the availability check
    test_client._transport.app.state.groq = MagicMock()  # type: ignore[attr-defined]

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stt",
        data={"lang": "en"},
        files={"file": ("test.txt", b"not audio", "text/plain")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_speak_no_tts_service(test_client: AsyncClient):
    """POST /api/audio/speak without any TTS → 204 (browser fallback)."""
    from unittest.mock import AsyncMock, patch

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    with patch("app.core.tts_service.speak", new_callable=AsyncMock, return_value=None):
        resp = await test_client.post(
            "/api/audio/speak",
            json={"text": "Hello from Thoth", "lang": "en", "context": "default"},
            headers={"x-csrftoken": csrf},
        )
    # 204 means browser should handle TTS
    assert resp.status_code == 204
