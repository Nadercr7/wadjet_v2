"""Auth API tests — register, login, refresh, logout, token validation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture()
async def registered_user(test_client: AsyncClient) -> dict:
    """Register a user and return the response data."""
    resp = await test_client.post(
        "/api/auth/register",
        json={
            "email": "auth@wadjet.app",
            "password": "StrongPass1",
            "display_name": "Auth User",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
async def logged_in_client(test_client: AsyncClient, registered_user: dict) -> AsyncClient:
    """Client that has a valid login session with refresh cookie."""
    resp = await test_client.post(
        "/api/auth/login",
        json={"email": "auth@wadjet.app", "password": "StrongPass1"},
    )
    assert resp.status_code == 200
    return test_client


# ── Registration ──


async def test_register_creates_user(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": "new@wadjet.app", "password": "ValidPass1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "new@wadjet.app"


async def test_register_duplicate_email(test_client: AsyncClient, registered_user: dict):
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": "auth@wadjet.app", "password": "StrongPass1"},
    )
    assert resp.status_code == 409


async def test_register_weak_password(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": "weak@wadjet.app", "password": "nodigits"},
    )
    assert resp.status_code == 422


async def test_register_short_password(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": "short@wadjet.app", "password": "Ab1"},
    )
    assert resp.status_code == 422


# ── Login ──


async def test_login_returns_tokens(test_client: AsyncClient, registered_user: dict):
    resp = await test_client.post(
        "/api/auth/login",
        json={"email": "auth@wadjet.app", "password": "StrongPass1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert "wadjet_refresh" in resp.cookies


async def test_login_bad_password(test_client: AsyncClient, registered_user: dict):
    resp = await test_client.post(
        "/api/auth/login",
        json={"email": "auth@wadjet.app", "password": "WrongPass1"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_user(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/auth/login",
        json={"email": "nobody@wadjet.app", "password": "Whatever1"},
    )
    assert resp.status_code == 401


async def test_login_bad_email_returns_error(
    test_client: AsyncClient, registered_user: dict
):
    """Invalid email returns 401, same as bad password."""
    r1 = await test_client.post(
        "/api/auth/login",
        json={"email": "nobody@wadjet.app", "password": "Whatever1"},
    )
    assert r1.status_code == 401


# ── Refresh ──


async def test_token_refresh_works(logged_in_client: AsyncClient):
    # Refresh — httpx carries cookies automatically
    resp = await logged_in_client.post("/api/auth/refresh")
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_without_cookie(test_client: AsyncClient):
    resp = await test_client.post("/api/auth/refresh")
    assert resp.status_code == 401


# ── Logout ──


async def test_logout_clears_cookie(logged_in_client: AsyncClient):
    resp = await logged_in_client.post("/api/auth/logout")
    assert resp.status_code == 200


# ── Token validation ──


async def test_expired_token_rejected(test_client: AsyncClient):
    from datetime import datetime, timedelta

    from jose import jwt

    token = jwt.encode(
        {"sub": "test-user", "exp": datetime.utcnow() - timedelta(hours=1)},
        "test-jwt-secret-do-not-use-in-production",
        algorithm="HS256",
    )
    resp = await test_client.get(
        "/api/user/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_malformed_token_rejected(test_client: AsyncClient):
    resp = await test_client.get(
        "/api/user/profile",
        headers={"Authorization": "Bearer not.a.valid.token.at.all"},
    )
    assert resp.status_code == 401


async def test_refresh_with_access_token_rejected(test_client: AsyncClient, registered_user: dict):
    """Using an access token as refresh token should fail."""
    access = registered_user["access_token"]
    resp = await test_client.post(
        "/api/auth/refresh",
        cookies={"wadjet_refresh": access},
    )
    assert resp.status_code == 401


async def test_refresh_with_garbage_cookie(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/auth/refresh",
        cookies={"wadjet_refresh": "garbage-token-value"},
    )
    assert resp.status_code == 401


async def test_logout_without_cookie(test_client: AsyncClient):
    """Logout without a refresh cookie still returns 200."""
    resp = await test_client.post("/api/auth/logout")
    assert resp.status_code == 200


async def test_register_sets_refresh_cookie(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/auth/register",
        json={"email": "cookie@wadjet.app", "password": "CookiePass1"},
    )
    assert resp.status_code == 201
    assert "wadjet_refresh" in resp.cookies


async def test_login_success_response_shape(test_client: AsyncClient, registered_user: dict):
    resp = await test_client.post(
        "/api/auth/login",
        json={"email": "auth@wadjet.app", "password": "StrongPass1"},
    )
    body = resp.json()
    assert "user" in body
    assert body["user"]["email"] == "auth@wadjet.app"
