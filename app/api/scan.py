"""Scan API endpoints — hieroglyph detection, classification, translation.

POST /api/scan       — Full pipeline: detect → classify → transliterate → translate
POST /api/detect     — Detection only: returns bounding boxes

Classification ensemble: ONNX first, then Gemini verifies low-confidence
glyphs, Grok tiebreaks disagreements.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from functools import partial

import cv2
import numpy as np
from collections import Counter
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scan"])

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
LOW_CONF_THRESHOLD = 0.5  # glyphs below this get AI verification


def _get_pipeline():
    """Lazy-load the pipeline singleton (heavy imports on first call)."""
    from app.dependencies import get_pipeline
    return get_pipeline()


async def _read_image_bytes(file: UploadFile) -> tuple[bytes, np.ndarray]:
    """Read an uploaded file into raw bytes + BGR numpy array."""
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

    arr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image. Check format.")
    return data, image


async def _verify_glyphs_gemini(
    gemini, image_bytes: bytes, mime: str, onnx_glyphs: list[dict],
) -> dict[int, str]:
    """Ask Gemini to verify low-confidence ONNX classifications.

    Sends the full image + the ONNX results, asks Gemini to confirm or correct.
    Returns: {glyph_index: corrected_gardiner_code} for disagreements only.
    """
    if not gemini or not gemini.available or not onnx_glyphs:
        return {}

    low_conf = [
        (i, g) for i, g in enumerate(onnx_glyphs)
        if g.get("class_confidence", 1.0) < LOW_CONF_THRESHOLD
    ]
    if not low_conf:
        return {}

    glyph_list = "\n".join(
        f"  Glyph #{i}: ONNX says '{g['gardiner_code']}' (conf={g['class_confidence']:.2f})"
        for i, g in low_conf
    )

    system = (
        "You are an expert Egyptologist specializing in hieroglyphic classification. "
        "You know the Gardiner Sign List exhaustively. Respond ONLY with valid JSON."
    )
    prompt = (
        f"This image contains hieroglyphs. The ONNX classifier found these "
        f"low-confidence classifications:\n{glyph_list}\n\n"
        f"Look at the image and verify or correct each glyph. "
        f"Return JSON: {{\"corrections\": {{\"<glyph_index>\": \"correct_gardiner_code\"}}}}\n"
        f"Only include glyphs you want to CHANGE. If ONNX is correct, don't include it."
    )

    try:
        from google.genai import types as genai_types
        image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime)
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.1,
            max_output_tokens=512,
            response_mime_type="application/json",
        )
        response = await gemini._generate_with_retry(
            model=gemini.default_model,
            contents=[prompt, image_part],
            config=config,
        )
        data = json.loads(response.text or "{}")
        corrections = data.get("corrections", {})
        return {int(k): v for k, v in corrections.items() if v}
    except Exception:
        logger.warning("Gemini glyph verification failed")
        return {}


async def _verify_glyphs_grok(
    grok, image_bytes: bytes, mime: str,
    disputed: list[tuple[int, str, str]],
) -> dict[int, str]:
    """Grok tiebreaker for disputed glyphs (ONNX vs Gemini disagree).

    Args:
        disputed: list of (index, onnx_code, gemini_code) tuples
    Returns: {glyph_index: chosen_code}
    """
    if not grok or not grok.available or not disputed:
        return {}

    glyph_list = "\n".join(
        f"  Glyph #{i}: Model A says '{onnx_code}', Model B says '{gemini_code}'"
        for i, onnx_code, gemini_code in disputed
    )

    system = (
        "You are an expert Egyptologist. You are the tiebreaker between two "
        "classification models. Respond ONLY with valid JSON."
    )
    prompt = (
        f"This image has hieroglyphs where two classifiers disagree:\n{glyph_list}\n\n"
        f"Look at the image and pick the correct Gardiner code for each. "
        f"Return JSON: {{\"votes\": {{\"<glyph_index>\": \"correct_gardiner_code\"}}}}"
    )

    b64 = base64.b64encode(image_bytes).decode("ascii")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": prompt},
        ]},
    ]

    try:
        resp = await grok._chat_completion(
            messages, temperature=0.1, max_tokens=512,
            response_format={"type": "json_object"},
        )
        text = grok._extract_text(resp)
        data = json.loads(text) if text else {}
        return {int(k): v for k, v in data.get("votes", {}).items() if v}
    except Exception:
        logger.warning("Grok glyph tiebreak failed")
        return {}


@router.post("/scan")
async def scan_image(request: Request, file: UploadFile = File(...), translate: bool = True):
    """Full scan pipeline with ensemble verification.

    1. ONNX pipeline: detect → classify → transliterate → translate
    2. Gemini verifies low-confidence glyphs (parallel-safe)
    3. Grok tiebreaks if ONNX and Gemini disagree
    4. Re-transliterate/translate if corrections were made
    """
    raw_bytes, image = await _read_image_bytes(file)
    pipeline = _get_pipeline()
    mime = file.content_type or "image/jpeg"

    # Step 1: Run full ONNX pipeline
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, partial(pipeline.process_image, image, translate=translate)
        )
    except Exception as e:
        logger.exception("Scan pipeline failed")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}") from e

    # Step 2: Ensemble verification for low-confidence glyphs
    if result.glyphs:
        gemini = getattr(request.app.state, "gemini", None)
        grok = getattr(request.app.state, "grok", None)

        onnx_glyph_dicts = [
            {
                "gardiner_code": g.gardiner_code,
                "class_confidence": g.class_confidence,
            }
            for g in result.glyphs
        ]

        # Ask Gemini to verify low-confidence ones
        gemini_corrections = await _verify_glyphs_gemini(
            gemini, raw_bytes, mime, onnx_glyph_dicts,
        )

        # If Gemini disagrees with ONNX on any, ask Grok to tiebreak
        grok_votes: dict[int, str] = {}
        if gemini_corrections and grok and grok.available:
            disputed = [
                (i, result.glyphs[i].gardiner_code, gemini_corrections[i])
                for i in gemini_corrections
                if i < len(result.glyphs)
                and gemini_corrections[i].upper() != result.glyphs[i].gardiner_code.upper()
            ]
            if disputed:
                grok_votes = await _verify_glyphs_grok(
                    grok, raw_bytes, mime, disputed,
                )

        # Apply corrections (majority vote: ONNX vs Gemini vs Grok)
        corrections_applied = False
        for i, gemini_code in gemini_corrections.items():
            if i >= len(result.glyphs):
                continue
            onnx_code = result.glyphs[i].gardiner_code
            grok_code = grok_votes.get(i, "")

            # Votes
            codes = [onnx_code.upper(), gemini_code.upper()]
            if grok_code:
                codes.append(grok_code.upper())

            # Majority wins
            counts = Counter(codes)
            winner, _ = counts.most_common(1)[0]

            if winner != onnx_code.upper():
                logger.info(
                    "Glyph #%d corrected: %s → %s (votes: ONNX=%s, Gemini=%s, Grok=%s)",
                    i, onnx_code, winner, onnx_code, gemini_code, grok_code or "N/A",
                )
                result.glyphs[i].gardiner_code = winner
                result.glyphs[i].class_confidence = 0.7  # synthetic confidence for corrected
                corrections_applied = True

        # Re-run transliteration + translation if glyphs were corrected
        if corrections_applied:
            try:
                trans = pipeline._transliterate(result.glyphs)
                result.transliteration = trans["transliteration"]
                result.gardiner_sequence = trans["gardiner_sequence"]
                result.reading_direction = trans["direction"]
                result.layout_mode = trans["layout"]

                if translate and result.transliteration:
                    translation = pipeline._translate(result.transliteration)
                    result.translation_en = translation["en"]
                    result.translation_ar = translation["ar"]
                    result.translation_error = translation["error"]
            except Exception:
                logger.warning("Re-transliteration after corrections failed")

    return JSONResponse(content=result.to_dict())


@router.post("/detect")
async def detect_glyphs(file: UploadFile = File(...)):
    """Detection only — returns bounding boxes without classification."""
    _, image = await _read_image_bytes(file)
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
