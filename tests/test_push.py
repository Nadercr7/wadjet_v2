"""Tests for E-P9 (POST /api/push/send) and E-P8 (/.well-known/assetlinks.json)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.core.push_service import _chunk, _should_prune


# ── E-P9: endpoint ──


async def test_push_requires_auth(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/push/send", json={"title": "t", "body": "b", "broadcast": True}
    )
    assert resp.status_code == 401


async def test_push_rejects_non_admin(authenticated_client: AsyncClient):
    resp = await authenticated_client.post(
        "/api/push/send", json={"title": "t", "body": "b", "broadcast": True}
    )
    assert resp.status_code == 403


async def test_push_requires_target(admin_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "firebase_project_id", "test-project")
    resp = await admin_client.post("/api/push/send", json={"title": "t", "body": "b"})
    assert resp.status_code == 400


async def test_push_unconfigured_returns_503(admin_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "firebase_project_id", "")
    resp = await admin_client.post(
        "/api/push/send", json={"title": "t", "body": "b", "broadcast": True}
    )
    assert resp.status_code == 503


async def test_push_broadcast_sends_and_reports(admin_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "firebase_project_id", "test-project")
    fake = AsyncMock(return_value={"tokens": 3, "sent": 2, "failed": 1, "pruned": 1})
    with patch("app.core.push_service.send_push", fake):
        resp = await admin_client.post(
            "/api/push/send",
            json={
                "title": "New story!",
                "body": "The Eye of Ra awaits",
                "broadcast": True,
                "story_id": "eye-of-ra",
            },
        )
    assert resp.status_code == 200
    assert resp.json() == {"tokens": 3, "sent": 2, "failed": 1, "pruned": 1}
    kwargs = fake.await_args.kwargs
    assert kwargs["broadcast"] is True
    assert kwargs["data"] == {"story_id": "eye-of-ra"}


async def test_push_single_user_target(admin_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "firebase_project_id", "test-project")
    fake = AsyncMock(return_value={"tokens": 1, "sent": 1, "failed": 0, "pruned": 0})
    with patch("app.core.push_service.send_push", fake):
        resp = await admin_client.post(
            "/api/push/send",
            json={"title": "t", "body": "b", "uid": "user-1", "landmark_slug": "giza"},
        )
    assert resp.status_code == 200
    kwargs = fake.await_args.kwargs
    assert kwargs["uid"] == "user-1"
    assert kwargs["data"] == {"landmark_slug": "giza"}


async def test_push_sdk_failure_maps_to_503(admin_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "firebase_project_id", "test-project")
    fake = AsyncMock(side_effect=RuntimeError("no credentials"))
    with patch("app.core.push_service.send_push", fake):
        resp = await admin_client.post(
            "/api/push/send", json={"title": "t", "body": "b", "broadcast": True}
        )
    assert resp.status_code == 503


# ── E-P9: sender internals ──


def test_chunk_respects_fcm_batch_limit():
    items = list(range(1203))
    batches = _chunk(items)
    assert [len(b) for b in batches] == [500, 500, 203]
    assert [x for b in batches for x in b] == items


def test_should_prune_unregistered_and_invalid_only():
    from firebase_admin import messaging

    assert _should_prune(None) is False
    assert _should_prune(messaging.UnregisteredError("gone")) is True

    class FakeInvalid(Exception):
        code = "invalid-argument"

    class FakeTransient(Exception):
        code = "unavailable"

    assert _should_prune(FakeInvalid()) is True
    assert _should_prune(FakeTransient()) is False


# ── E-P8: assetlinks ──


async def test_assetlinks_404_when_unconfigured(test_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "android_cert_sha256", "")
    resp = await test_client.get("/.well-known/assetlinks.json")
    assert resp.status_code == 404


async def test_assetlinks_statement_shape(test_client: AsyncClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(
        settings,
        "android_cert_sha256",
        "aa:bb:cc, 11:22:33",
    )
    resp = await test_client.get("/.well-known/assetlinks.json")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["relation"] == ["delegate_permission/common.handle_all_urls"]
    target = body[0]["target"]
    assert target["namespace"] == "android_app"
    assert target["package_name"] == "com.wadjet.app"
    assert target["sha256_cert_fingerprints"] == ["AA:BB:CC", "11:22:33"]
