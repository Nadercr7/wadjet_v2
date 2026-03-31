"""Audio API tests — TTS and STT endpoint validation, positive-path."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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


# ── TTS Success-Path Tests (TEST-006) ──


async def test_speak_gemini_tts_success(test_client: AsyncClient):
    """POST /api/audio/speak with mocked Gemini TTS → returns WAV audio."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    # Create a temporary WAV file to simulate TTS output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # Minimal WAV header (44 bytes) + 100 bytes of silence
        wav_header = (
            b"RIFF"
            + (144).to_bytes(4, "little")  # file size - 8
            + b"WAVE"
            + b"fmt "
            + (16).to_bytes(4, "little")  # chunk size
            + (1).to_bytes(2, "little")   # PCM
            + (1).to_bytes(2, "little")   # mono
            + (22050).to_bytes(4, "little")  # sample rate
            + (22050).to_bytes(4, "little")  # byte rate
            + (1).to_bytes(2, "little")   # block align
            + (8).to_bytes(2, "little")   # bits per sample
            + b"data"
            + (100).to_bytes(4, "little")  # data size
            + b"\x80" * 100              # silence samples
        )
        f.write(wav_header)
        tmp_path = f.name

    try:
        with patch("app.core.tts_service.speak", new_callable=AsyncMock, return_value=tmp_path):
            resp = await test_client.post(
                "/api/audio/speak",
                json={"text": "Welcome to ancient Egypt", "lang": "en", "context": "story"},
                headers={"x-csrftoken": csrf},
            )

        assert resp.status_code == 200
        assert "audio" in resp.headers.get("content-type", "")
        assert len(resp.content) > 44  # More than just a WAV header
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def test_speak_groq_fallback_success(test_client: AsyncClient):
    """When Gemini TTS fails, Groq fallback returns audio bytes."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    # Minimal WAV bytes from Groq
    fake_wav = b"RIFF" + b"\x00" * 40 + b"WAVE" + b"\x00" * 100

    mock_groq = MagicMock()
    mock_groq.tts = AsyncMock(return_value=fake_wav)
    test_client._transport.app.state.groq = mock_groq  # type: ignore[attr-defined]

    with patch("app.core.tts_service.speak", new_callable=AsyncMock, return_value=None):
        resp = await test_client.post(
            "/api/audio/speak",
            json={"text": "Praise be to Amun-Ra", "lang": "en", "context": "default"},
            headers={"x-csrftoken": csrf},
        )

    assert resp.status_code == 200
    assert "audio" in resp.headers.get("content-type", "")
