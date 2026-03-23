"""Scan API endpoints — hieroglyph detection, classification, translation.

POST /api/scan       — Full pipeline: detect → classify → transliterate → translate
POST /api/detect     — Detection only: returns bounding boxes
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scan"])

# Maximum upload size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _get_pipeline():
    """Lazy-load the pipeline singleton (heavy imports on first call)."""
    from app.dependencies import get_pipeline
    return get_pipeline()


async def _read_image(file: UploadFile) -> np.ndarray:
    """Read an uploaded file into a BGR numpy array."""
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Use JPEG, PNG, or WebP.",
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10 MB.")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # Decode image
    arr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image. Check format.")
    return image


@router.post("/scan")
async def scan_image(file: UploadFile = File(...), translate: bool = True):
    """Full scan pipeline: detect → classify → transliterate → (optionally) translate.

    Returns JSON with glyphs, transliteration, and translation.
    Pipeline runs in a thread pool to avoid blocking the event loop.
    """
    image = await _read_image(file)
    pipeline = _get_pipeline()

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, partial(pipeline.process_image, image, translate=translate)
        )
    except Exception as e:
        logger.exception("Scan pipeline failed")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}") from e

    return JSONResponse(content=result.to_dict())


@router.post("/detect")
async def detect_glyphs(file: UploadFile = File(...)):
    """Detection only — returns bounding boxes without classification.

    Lighter endpoint for quick preview / bounding box overlay.
    Runs in a thread pool to avoid blocking the event loop.
    """
    image = await _read_image(file)
    pipeline = _get_pipeline()

    def _run_detection():
        detector = pipeline._get_detector()
        return detector.detect(image)

    loop = asyncio.get_event_loop()
    try:
        detections = await loop.run_in_executor(None, _run_detection)
    except Exception as e:
        logger.exception("Detection failed")
        raise HTTPException(status_code=500, detail=f"Detection error: {e}") from e

    h, w = image.shape[:2]
    return JSONResponse(content={
        "num_detections": len(detections),
        "image_size": {"width": w, "height": h},
        "detections": [d.to_dict() for d in detections],
    })
