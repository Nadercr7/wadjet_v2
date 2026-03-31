"""Chat API tests — stream, clear, session management."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient


async def test_chat_stream_is_post_only(test_client: AsyncClient):
    """GET /api/chat/stream → 405 Method Not Allowed."""
    resp = await test_client.get("/api/chat/stream")
    assert resp.status_code == 405


async def test_chat_requires_gemini(test_client: AsyncClient):
    """POST /api/chat without Gemini service → 503."""
    # Get CSRF token
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/chat",
        json={"message": "hello", "session_id": "test-session"},
        headers={"x-csrftoken": csrf},
    )
    # 503 if gemini not in app state, or 403 if CSRF fails
    assert resp.status_code in (503, 403)


async def test_chat_clear_no_auth_requires_uuid(test_client: AsyncClient):
    """POST /api/chat/clear without auth needs UUID session_id."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/chat/clear",
        json={"session_id": "not-a-uuid"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_chat_clear_with_valid_uuid(test_client: AsyncClient):
    """POST /api/chat/clear with valid UUID format → succeeds."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/chat/clear",
        json={"session_id": "12345678-1234-1234-1234-123456789abc"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"


async def test_chat_message_too_long(test_client: AsyncClient):
    """Message exceeding 2000 chars → 422."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/chat",
        json={"message": "a" * 2001, "session_id": "test"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 422


async def test_chat_message_success(test_client: AsyncClient):
    """POST /api/chat with mocked gemini → 200 with reply."""
    from types import SimpleNamespace

    gemini_mock = MagicMock()
    test_client._transport.app.state.gemini = gemini_mock  # type: ignore[attr-defined]

    mock_result = SimpleNamespace(reply="Hello from Thoth", sources=[])

    with patch("app.core.thoth_chat.chat", new_callable=AsyncMock, return_value=mock_result):
        await test_client.get("/api/health")
        csrf = test_client.cookies.get("csrftoken", "")

        resp = await test_client.post(
            "/api/chat",
            json={"message": "Hello Thoth", "session_id": "test-session-1"},
            headers={"x-csrftoken": csrf},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Hello from Thoth"
    assert body["sources"] == []


async def test_chat_message_error_returns_500(test_client: AsyncClient):
    """POST /api/chat when chat() raises → 500."""
    gemini_mock = MagicMock()
    test_client._transport.app.state.gemini = gemini_mock  # type: ignore[attr-defined]

    with patch("app.core.thoth_chat.chat", new_callable=AsyncMock, side_effect=RuntimeError("AI broke")):
        await test_client.get("/api/health")
        csrf = test_client.cookies.get("csrftoken", "")

        resp = await test_client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": "test-session-2"},
            headers={"x-csrftoken": csrf},
        )
    assert resp.status_code == 500


async def test_chat_stream_success(test_client: AsyncClient):
    """POST /api/chat/stream with mocked gemini → SSE stream."""

    gemini_mock = MagicMock()
    test_client._transport.app.state.gemini = gemini_mock  # type: ignore[attr-defined]

    async def fake_stream(*args, **kwargs):
        yield "Hello "
        yield "World"

    with patch("app.core.thoth_chat.chat_stream", return_value=fake_stream()):
        await test_client.get("/api/health")
        csrf = test_client.cookies.get("csrftoken", "")

        resp = await test_client.post(
            "/api/chat/stream",
            json={"message": "Tell me about Egypt", "session_id": "stream-1"},
            headers={"x-csrftoken": csrf},
        )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "Hello " in body
    assert "[DONE]" in body


async def test_chat_stream_error_sends_error_event(test_client: AsyncClient):
    """POST /api/chat/stream when generator raises → error SSE event."""
    gemini_mock = MagicMock()
    test_client._transport.app.state.gemini = gemini_mock  # type: ignore[attr-defined]

    async def broken_stream(*args, **kwargs):
        yield "start"
        raise RuntimeError("stream broke")

    with patch("app.core.thoth_chat.chat_stream", return_value=broken_stream()):
        await test_client.get("/api/health")
        csrf = test_client.cookies.get("csrftoken", "")

        resp = await test_client.post(
            "/api/chat/stream",
            json={"message": "Hello", "session_id": "stream-2"},
            headers={"x-csrftoken": csrf},
        )
    assert resp.status_code == 200
    assert "error" in resp.text or "Generation failed" in resp.text


async def test_chat_clear_authenticated_user(authenticated_client: AsyncClient):
    """Authenticated users can clear with any session_id format."""
    resp = await authenticated_client.post(
        "/api/chat/clear",
        json={"session_id": "not-a-uuid-but-ok"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"
