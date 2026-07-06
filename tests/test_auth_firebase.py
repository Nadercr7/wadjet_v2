"""Tests for POST /api/auth/firebase — Firebase ID-token exchange (Android app)."""

from __future__ import annotations

from unittest.mock import patch

from httpx import AsyncClient


def _info(**overrides) -> dict:
    base = {
        "uid": "firebase-uid-1",
        "email": "fb@wadjet.app",
        "email_verified": True,
        "name": "Firebase User",
        "picture": None,
        "provider": "password",
        "google_sub": None,
    }
    base.update(overrides)
    return base


def _exchange(client: AsyncClient, token: str = "fake-firebase-token"):
    return client.post("/api/auth/firebase", json={"id_token": token})


async def test_firebase_new_user_created(test_client: AsyncClient):
    with patch("app.auth.firebase.verify_firebase_token", return_value=_info()):
        resp = await _exchange(test_client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "fb@wadjet.app"
    assert body["user"]["auth_provider"] == "firebase"
    assert body["user"]["email_verified"] is True
    # Session cookie contract matches /login
    assert "wadjet_refresh" in resp.cookies


async def test_firebase_existing_user_signs_in(test_client: AsyncClient):
    with patch("app.auth.firebase.verify_firebase_token", return_value=_info()):
        first = await _exchange(test_client)
        assert first.status_code == 201
        second = await _exchange(test_client)
    assert second.status_code == 200
    assert second.json()["user"]["email"] == "fb@wadjet.app"


async def test_firebase_invalid_token_rejected(test_client: AsyncClient):
    with patch("app.auth.firebase.verify_firebase_token", return_value=None):
        resp = await _exchange(test_client, "garbage")
    assert resp.status_code == 401


async def test_firebase_unverified_email_rejected(test_client: AsyncClient):
    with patch(
        "app.auth.firebase.verify_firebase_token",
        return_value=_info(email_verified=False),
    ):
        resp = await _exchange(test_client)
    assert resp.status_code == 403


async def test_firebase_unverified_google_provider_allowed(test_client: AsyncClient):
    """google.com sign-ins are trusted even if email_verified is missing."""
    with patch(
        "app.auth.firebase.verify_firebase_token",
        return_value=_info(email_verified=False, provider="google.com", google_sub="g-sub-9"),
    ):
        resp = await _exchange(test_client)
    assert resp.status_code == 201
    assert resp.json()["user"]["auth_provider"] == "google"


async def test_firebase_links_existing_email_account(test_client: AsyncClient):
    """A verified Firebase token signs into an account created via /register."""
    reg = await test_client.post(
        "/api/auth/register",
        json={"email": "linked@wadjet.app", "password": "StrongPass1"},
    )
    assert reg.status_code == 201

    with patch(
        "app.auth.firebase.verify_firebase_token",
        return_value=_info(email="linked@wadjet.app"),
    ):
        resp = await _exchange(test_client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "linked@wadjet.app"
    # Firebase verified the address; backend mirrors it
    assert body["user"]["email_verified"] is True


async def test_firebase_google_sub_links_google_id(test_client: AsyncClient):
    """Google-backed Firebase token links google_id on an existing email account."""
    reg = await test_client.post(
        "/api/auth/register",
        json={"email": "google-link@wadjet.app", "password": "StrongPass1"},
    )
    assert reg.status_code == 201

    info = _info(email="google-link@wadjet.app", provider="google.com", google_sub="g-sub-42")
    with patch("app.auth.firebase.verify_firebase_token", return_value=info):
        first = await _exchange(test_client)
        assert first.status_code == 200
        assert first.json()["user"]["auth_provider"] == "both"
        # Second exchange must match by google_id (branch 1)
        second = await _exchange(test_client)
    assert second.status_code == 200


async def test_firebase_missing_email_rejected(test_client: AsyncClient):
    with patch("app.auth.firebase.verify_firebase_token", return_value=_info(email="")):
        resp = await _exchange(test_client)
    assert resp.status_code == 400


async def test_firebase_issued_token_works_on_protected_endpoint(test_client: AsyncClient):
    """The exchanged access token authenticates normal API calls."""
    with patch("app.auth.firebase.verify_firebase_token", return_value=_info()):
        resp = await _exchange(test_client)
    token = resp.json()["access_token"]

    profile = await test_client.get(
        "/api/user/profile", headers={"Authorization": f"Bearer {token}"}
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "fb@wadjet.app"


async def test_firebase_refresh_cookie_rotates(test_client: AsyncClient):
    """The refresh cookie issued by the exchange works at /api/auth/refresh."""
    with patch("app.auth.firebase.verify_firebase_token", return_value=_info()):
        resp = await _exchange(test_client)
    assert resp.status_code == 201

    refreshed = await test_client.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


async def test_firebase_not_configured_returns_401(test_client: AsyncClient, monkeypatch):
    """Without FIREBASE_PROJECT_ID the endpoint fails closed (401), not 500."""
    from app.config import settings

    monkeypatch.setattr(settings, "firebase_project_id", "")
    # Real verifier path (no patch): must return None because config is missing
    resp = await _exchange(test_client, "any-token")
    assert resp.status_code == 401
