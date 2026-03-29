"""Scan API tests — upload validation, magic bytes, MIME check."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_scan_empty_file(test_client: AsyncClient):
    """Empty upload → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/scan",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_scan_invalid_magic_bytes(test_client: AsyncClient):
    """File with wrong magic bytes → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/scan",
        files={"file": ("test.jpg", b"not an image content", "image/jpeg")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_scan_oversized_file(test_client: AsyncClient):
    """File > 10MB → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    # Create minimal JPEG header + padding to exceed 10MB
    fake_large = b"\xff\xd8\xff" + b"\x00" * (10 * 1024 * 1024 + 1)
    resp = await test_client.post(
        "/api/scan",
        files={"file": ("big.jpg", fake_large, "image/jpeg")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_detect_empty_file(test_client: AsyncClient):
    """Detect with empty file → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/detect",
        files={"file": ("empty.png", b"", "image/png")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_read_empty_file(test_client: AsyncClient):
    """Read with empty file → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/read",
        files={"file": ("empty.png", b"", "image/png")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400
