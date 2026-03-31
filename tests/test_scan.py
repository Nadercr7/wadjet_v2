"""Scan API tests — upload validation, magic bytes, MIME check, positive-path pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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


# ── Positive-path pipeline tests (TEST-003) ──


def _make_test_jpeg() -> bytes:
    """Create a minimal valid JPEG image for testing."""
    import cv2
    import numpy as np

    img = np.full((64, 64, 3), 128, dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return bytes(buf)


def _mock_pipeline_result():
    """Create a realistic PipelineResult with known Gardiner codes."""
    from app.core.hieroglyph_pipeline import GlyphResult, PipelineResult

    glyphs = [
        GlyphResult(
            x1=10.0, y1=10.0, x2=40.0, y2=50.0,
            confidence=0.92, class_id=0,
            gardiner_code="G1", class_confidence=0.88,
        ),
        GlyphResult(
            x1=50.0, y1=10.0, x2=80.0, y2=50.0,
            confidence=0.85, class_id=1,
            gardiner_code="D21", class_confidence=0.82,
        ),
        GlyphResult(
            x1=90.0, y1=10.0, x2=120.0, y2=50.0,
            confidence=0.90, class_id=2,
            gardiner_code="N35", class_confidence=0.87,
        ),
    ]

    return PipelineResult(
        num_detections=3,
        glyphs=glyphs,
        transliteration="A-r-n",
        gardiner_sequence="G1-D21-N35",
        reading_direction="left-to-right",
        layout_mode="horizontal",
        num_groups=1, num_lines=1,
        translation_en="Egyptian vulture - mouth - water",
        translation_ar="نسر مصري - فم - ماء",
        detection_ms=45.0, classification_ms=30.0,
        transliteration_ms=5.0, translation_ms=120.0, total_ms=200.0,
    )


async def test_scan_onnx_positive_path(test_client: AsyncClient):
    """Send valid image through ONNX mode — verify full pipeline output."""
    jpeg_data = _make_test_jpeg()
    mock_result = _mock_pipeline_result()

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    with patch("app.api.scan._get_pipeline") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.process_image.return_value = mock_result
        mock_get_pipeline.return_value = mock_pipeline

        resp = await test_client.post(
            "/api/scan",
            files={"file": ("test.jpg", jpeg_data, "image/jpeg")},
            data={"mode": "onnx"},
            headers={"x-csrftoken": csrf},
        )

    assert resp.status_code == 200
    body = resp.json()

    # Verify output structure
    assert body["num_detections"] == 3
    assert len(body["glyphs"]) == 3

    # Verify Gardiner codes
    codes = [g["gardiner_code"] for g in body["glyphs"]]
    assert "G1" in codes
    assert "D21" in codes
    assert "N35" in codes

    # Verify bounding boxes
    for g in body["glyphs"]:
        assert "bbox" in g
        assert len(g["bbox"]) == 4
        assert g["class_confidence"] > 0

    # Verify transliteration and translation
    assert body["gardiner_sequence"] == "G1-D21-N35"
    assert body["transliteration"] != ""
    assert body["translation_en"] != ""
    assert body["translation_ar"] != ""

    # Verify timing and metadata
    assert body["timing"]["total_ms"] > 0
    assert body["image_size"]["width"] > 0


async def test_scan_auto_mode_onnx_fallback(test_client: AsyncClient):
    """Auto mode falls back to ONNX when AI unavailable — verify output."""
    jpeg_data = _make_test_jpeg()
    mock_result = _mock_pipeline_result()

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    with patch("app.api.scan._get_pipeline") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.process_image.return_value = mock_result
        mock_get_pipeline.return_value = mock_pipeline

        resp = await test_client.post(
            "/api/scan",
            files={"file": ("test.jpg", jpeg_data, "image/jpeg")},
            data={"mode": "auto"},
            headers={"x-csrftoken": csrf},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["num_detections"] == 3
    assert body["translation_en"] != ""


async def test_detect_positive_path(test_client: AsyncClient):
    """POST /api/detect with mocked detector returns bounding boxes."""
    jpeg_data = _make_test_jpeg()

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    # Mock the detector to return detection results
    mock_detection = MagicMock()
    mock_detection.to_dict.return_value = {
        "bbox": [10.0, 10.0, 40.0, 50.0],
        "confidence": 0.91,
    }

    with patch("app.api.scan._get_pipeline") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [mock_detection, mock_detection]
        mock_pipeline._get_detector.return_value = mock_detector
        mock_get_pipeline.return_value = mock_pipeline

        resp = await test_client.post(
            "/api/detect",
            files={"file": ("test.jpg", jpeg_data, "image/jpeg")},
            headers={"x-csrftoken": csrf},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["num_detections"] == 2
    assert "image_size" in body
    assert len(body["detections"]) == 2


async def test_read_ai_unavailable(test_client: AsyncClient):
    """POST /api/read without AI service → 503."""
    jpeg_data = _make_test_jpeg()

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/read",
        files={"file": ("test.jpg", jpeg_data, "image/jpeg")},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 503


async def test_scan_png_accepted(test_client: AsyncClient):
    """PNG files with correct magic bytes are accepted."""
    import cv2
    import numpy as np

    img = np.full((64, 64, 3), 128, dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    png_data = bytes(buf)

    mock_result = _mock_pipeline_result()

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    with patch("app.api.scan._get_pipeline") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.process_image.return_value = mock_result
        mock_get_pipeline.return_value = mock_pipeline

        resp = await test_client.post(
            "/api/scan",
            files={"file": ("test.png", png_data, "image/png")},
            data={"mode": "onnx"},
            headers={"x-csrftoken": csrf},
        )

    assert resp.status_code == 200
    assert resp.json()["num_detections"] == 3


async def test_scan_confidence_summary(test_client: AsyncClient):
    """Scan response includes confidence_summary with avg/min/max."""
    jpeg_data = _make_test_jpeg()
    mock_result = _mock_pipeline_result()

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    with patch("app.api.scan._get_pipeline") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.process_image.return_value = mock_result
        mock_get_pipeline.return_value = mock_pipeline

        resp = await test_client.post(
            "/api/scan",
            files={"file": ("test.jpg", jpeg_data, "image/jpeg")},
            data={"mode": "onnx"},
            headers={"x-csrftoken": csrf},
        )

    body = resp.json()
    assert "confidence_summary" in body
    summary = body["confidence_summary"]
    assert summary["avg"] > 0
    assert summary["min"] > 0
    assert summary["max"] > 0
    assert summary["low_count"] >= 0
