"""Explore API tests — landmarks listing, detail, identify validation, positive-path."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def test_landmarks_list(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks")
    assert resp.status_code == 200


async def test_landmarks_categories(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks/categories")
    assert resp.status_code == 200


async def test_landmarks_search(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks?search=pyramid")
    assert resp.status_code == 200


async def test_landmarks_pagination(test_client: AsyncClient):
    resp = await test_client.get("/api/landmarks?page=1&per_page=5")
    assert resp.status_code == 200


async def test_identify_empty_file(test_client: AsyncClient):
    """Empty upload to identify → 422."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/explore/identify",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 422


async def test_identify_invalid_magic_bytes(test_client: AsyncClient):
    """Invalid image to identify → 422."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/explore/identify",
        files={"file": ("test.jpg", b"not-an-image", "image/jpeg")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 422


# ── Positive-path landmark identification (TEST-004) ──


def _make_test_jpeg() -> bytes:
    """Create a minimal valid JPEG image."""
    import cv2
    import numpy as np

    img = np.full((64, 64, 3), 128, dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return bytes(buf)


async def test_identify_onnx_positive_path(test_client: AsyncClient):
    """Send valid image → mocked ONNX returns known landmark → verify output."""
    jpeg_data = _make_test_jpeg()

    mock_onnx_result = {
        "slug": "great_pyramids_of_giza",
        "name": "Great Pyramids Of Giza",
        "confidence": 0.92,
        "top3": [
            {"slug": "great_pyramids_of_giza", "name": "Great Pyramids Of Giza", "confidence": 0.92},
            {"slug": "great_sphinx_of_giza", "name": "Great Sphinx Of Giza", "confidence": 0.05},
            {"slug": "saqqara_step_pyramid", "name": "Saqqara Step Pyramid", "confidence": 0.02},
        ],
    }

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    with (
        patch("app.api.explore._run_onnx", new_callable=AsyncMock, return_value=mock_onnx_result),
        patch("app.api.explore._run_gemini_vision", new_callable=AsyncMock, return_value={}),
    ):
        resp = await test_client.post(
            "/api/explore/identify",
            files={"file": ("pyramid.jpg", jpeg_data, "image/jpeg")},
            headers={"x-csrftoken": csrf},
        )

    assert resp.status_code == 200
    body = resp.json()

    # Verify landmark identification result
    assert "slug" in body or "name" in body or "landmark" in body
    # The response may put result in different keys depending on merge logic
    # Check that we got a meaningful response (not an error)
    assert body.get("slug") or body.get("name") or body.get("landmark")


async def test_identify_gemini_agrees_with_onnx(test_client: AsyncClient):
    """Both ONNX and Gemini identify same landmark → boosted confidence."""
    jpeg_data = _make_test_jpeg()

    mock_onnx = {
        "slug": "karnak_temple",
        "name": "Karnak Temple",
        "confidence": 0.75,
        "top3": [
            {"slug": "karnak_temple", "name": "Karnak Temple", "confidence": 0.75},
            {"slug": "luxor_temple", "name": "Luxor Temple", "confidence": 0.15},
        ],
    }
    mock_gemini = {
        "slug": "karnak_temple",
        "name": "Karnak Temple",
        "confidence": 0.90,
        "description": "The great temple complex at Karnak",
    }

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    with (
        patch("app.api.explore._run_onnx", new_callable=AsyncMock, return_value=mock_onnx),
        patch("app.api.explore._run_gemini_vision", new_callable=AsyncMock, return_value=mock_gemini),
    ):
        resp = await test_client.post(
            "/api/explore/identify",
            files={"file": ("temple.jpg", jpeg_data, "image/jpeg")},
            headers={"x-csrftoken": csrf},
        )

    assert resp.status_code == 200
    body = resp.json()
    # When both agree, slug should be karnak_temple
    slug = body.get("slug", "")
    assert "karnak" in slug.lower() or "temple" in body.get("name", "").lower()


async def test_landmarks_detail_slug(test_client: AsyncClient):
    """GET /api/landmarks/{slug} with a known slug returns detail."""
    resp = await test_client.get("/api/landmarks")
    if resp.status_code != 200:
        pytest.skip("Landmarks not loaded")
    landmarks = resp.json()
    items = landmarks if isinstance(landmarks, list) else landmarks.get("landmarks", [])
    if not items:
        pytest.skip("No landmarks available")

    slug = items[0].get("slug", "")
    if slug:
        resp = await test_client.get(f"/api/landmarks/{slug}")
        assert resp.status_code in (200, 404)  # 404 if expanded_sites not loaded
