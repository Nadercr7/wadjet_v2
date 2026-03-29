"""Security tests — CSRF, rate limiting, path traversal, CSP headers, timing."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── CSRF ──


async def test_csrf_blocks_unprotected_post(test_client: AsyncClient):
    """POST to a CSRF-protected route without token → 403."""
    # /api/user/favorites requires CSRF + auth.
    # The CSRF check happens before auth, so even without auth we should get 403
    # (unless the middleware skips when there are no sensitive cookies).
    # With starlette_csrf and sensitive_cookies=None, _has_sensitive_cookies returns True always.
    resp = await test_client.post(
        "/api/user/favorites",
        json={"item_type": "landmark", "item_id": "test"},
    )
    assert resp.status_code == 403


async def test_csrf_allows_exempt_routes(test_client: AsyncClient):
    """Auth routes are exempt from CSRF — returns auth error, not 403."""
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": "csrf-test@wadjet.app", "password": "short"},
    )
    # 422 = validation ran (not blocked by CSRF 403)
    assert resp.status_code == 422


# ── Security Headers ──


async def test_csp_header_present(test_client: AsyncClient):
    resp = await test_client.get("/api/health")
    assert "content-security-policy" in resp.headers
    csp = resp.headers["content-security-policy"]
    assert "default-src 'self'" in csp


async def test_security_headers_present(test_client: AsyncClient):
    resp = await test_client.get("/api/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert "strict-origin" in resp.headers.get("referrer-policy", "")


# ── OpenAPI hidden in production ──


async def test_openapi_available_in_dev(test_client: AsyncClient):
    """In dev mode, /docs should be accessible."""
    resp = await test_client.get("/docs")
    # It either returns 200 (docs page) or 307 redirect to /docs/
    assert resp.status_code in (200, 307)


# ── Path Traversal ──


async def test_path_traversal_blocked():
    """load_story with path traversal attempt returns None."""
    from app.core.stories_engine import load_story

    result = load_story("../../etc/passwd")
    assert result is None


async def test_path_traversal_dotdot():
    """load_story with ../ sequences returns None."""
    from app.core.stories_engine import load_story

    result = load_story("../../../etc/shadow")
    assert result is None


# ── Input Validation ──


async def test_oversized_message_rejected(test_client: AsyncClient):
    """Chat message exceeding max_length → 422."""
    resp = await test_client.post(
        "/api/auth/register",
        json={
            "email": "size@wadjet.app",
            "password": "a" * 200,  # way over max_length=128
        },
    )
    assert resp.status_code == 422


async def test_password_complexity_enforced(test_client: AsyncClient):
    """Password without uppercase → 422."""
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": "complex@wadjet.app", "password": "alllowercase1"},
    )
    assert resp.status_code == 422


async def test_password_no_digit_rejected(test_client: AsyncClient):
    """Password without digit → 422."""
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": "digit@wadjet.app", "password": "NoDigitHere"},
    )
    assert resp.status_code == 422
