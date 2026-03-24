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


# ── Visual annotation helpers ──

_GOLD = (55, 175, 212)      # BGR for #D4AF37
_RED = (60, 60, 220)        # BGR for low-confidence highlight
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)
_CROP_PAD = 8               # px padding around each crop


def _annotate_image(
    image: np.ndarray,
    glyphs: list,
    highlight_indices: set[int] | None = None,
) -> bytes:
    """Draw numbered bounding boxes on the image for AI verification.

    Each glyph gets a rectangle + circled number label so the vision model
    can visually match "Glyph #3" to a specific region.  Low-confidence
    glyphs in *highlight_indices* get a red box; others get gold.

    Returns: JPEG bytes of the annotated image.
    """
    annotated = image.copy()
    h, w = annotated.shape[:2]
    # Scale line thickness + font relative to image size
    scale = max(0.5, min(w, h) / 600)
    thickness = max(1, int(scale * 2))
    font_scale = max(0.4, scale * 0.6)
    label_pad = max(12, int(scale * 16))

    for i, g in enumerate(glyphs):
        x1, y1, x2, y2 = int(g.x1), int(g.y1), int(g.x2), int(g.y2)
        is_low = highlight_indices and i in highlight_indices
        color = _RED if is_low else _GOLD

        # Draw box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

        # Draw label background + number
        label = str(i)
        (tw, th), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness,
        )
        lx = max(0, x1)
        ly = max(th + label_pad, y1 - 4)
        cv2.rectangle(
            annotated,
            (lx, ly - th - 6),
            (lx + tw + 10, ly + 4),
            color, cv2.FILLED,
        )
        cv2.putText(
            annotated, label,
            (lx + 5, ly - 2),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, _WHITE, thickness,
        )

        # Also draw gardiner code + confidence below the box
        info = f"{g.gardiner_code} ({g.class_confidence:.0%})"
        (iw, ih), _ = cv2.getTextSize(
            info, cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.7, max(1, thickness - 1),
        )
        iy = min(h - 4, y2 + ih + 6)
        cv2.rectangle(
            annotated, (x1, iy - ih - 4), (x1 + iw + 6, iy + 2),
            _BLACK, cv2.FILLED,
        )
        cv2.putText(
            annotated, info,
            (x1 + 3, iy - 2),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.7, color,
            max(1, thickness - 1),
        )

    _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return bytes(buf)


def _crop_glyph(image: np.ndarray, g, pad: int = _CROP_PAD) -> bytes:
    """Crop a single glyph from the image with padding. Returns JPEG bytes."""
    h, w = image.shape[:2]
    x1 = max(0, int(g.x1) - pad)
    y1 = max(0, int(g.y1) - pad)
    x2 = min(w, int(g.x2) + pad)
    y2 = min(h, int(g.y2) + pad)
    crop = image[y1:y2, x1:x2]
    # Resize small crops up so the vision model can see detail
    ch, cw = crop.shape[:2]
    if max(ch, cw) < 128:
        factor = 128 / max(ch, cw)
        crop = cv2.resize(
            crop, None, fx=factor, fy=factor,
            interpolation=cv2.INTER_CUBIC,
        )
    _, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return bytes(buf)


# ── AI verification ──

async def _verify_glyphs_gemini(
    gemini,
    original_image: np.ndarray,
    glyphs: list,
    onnx_glyph_dicts: list[dict],
) -> dict[int, str]:
    """Ask Gemini to verify low-confidence ONNX classifications.

    Sends an annotated image with numbered bboxes + individual crops for
    each low-confidence glyph so Gemini can visually identify them.
    Returns: {glyph_index: corrected_gardiner_code} for disagreements only.
    """
    if not gemini or not gemini.available or not glyphs:
        return {}

    low_conf = [
        (i, g, d) for i, (g, d) in enumerate(zip(glyphs, onnx_glyph_dicts))
        if d.get("class_confidence", 1.0) < LOW_CONF_THRESHOLD
    ]
    if not low_conf:
        return {}

    low_indices = {i for i, _, _ in low_conf}

    # Build annotated full image with numbered boxes
    annotated_bytes = _annotate_image(original_image, glyphs, low_indices)

    # Build individual crops for each low-confidence glyph
    crop_parts = []
    glyph_descriptions = []
    for i, g, d in low_conf:
        crop_bytes = _crop_glyph(original_image, g)
        crop_parts.append((i, crop_bytes))
        glyph_descriptions.append(
            f"  Glyph #{i}: ONNX classified as '{d['gardiner_code']}' "
            f"(confidence={d['class_confidence']:.0%})"
        )

    system = (
        "You are an expert Egyptologist specializing in hieroglyphic classification. "
        "You know the Gardiner Sign List exhaustively.\n\n"
        "You will receive:\n"
        "1. An annotated image showing ALL detected hieroglyphs with numbered boxes\n"
        "   - Red boxes = low-confidence glyphs that need your verification\n"
        "   - Gold boxes = high-confidence glyphs (for spatial context only)\n"
        "   - Each box has a number label matching the glyph index\n"
        "2. Individual cropped close-ups of each low-confidence glyph\n\n"
        "Respond ONLY with valid JSON."
    )

    glyph_list = "\n".join(glyph_descriptions)
    prompt = (
        f"The ONNX classifier detected hieroglyphs but is uncertain about these:\n"
        f"{glyph_list}\n\n"
        f"First image: full inscription with numbered bounding boxes.\n"
        f"Following images: individual close-ups of each uncertain glyph "
        f"(in the same order as listed above).\n\n"
        f"For each glyph, examine both the close-up AND its position in the "
        f"full inscription for context. Consider the surrounding glyphs.\n\n"
        f"Return JSON: {{\"corrections\": {{\"<glyph_index>\": \"correct_gardiner_code\"}}}}\n"
        f"Only include glyphs you want to CHANGE. If ONNX is correct, omit it."
    )

    try:
        from google.genai import types as genai_types

        # Build multi-part content: [prompt, annotated_image, crop_0, crop_1, ...]
        contents: list = [prompt]
        contents.append(genai_types.Part.from_bytes(
            data=annotated_bytes, mime_type="image/jpeg",
        ))
        for idx, crop_bytes in crop_parts:
            contents.append(genai_types.Part.from_bytes(
                data=crop_bytes, mime_type="image/jpeg",
            ))

        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.1,
            max_output_tokens=512,
            response_mime_type="application/json",
        )
        response = await gemini._generate_with_retry(
            model=gemini.default_model,
            contents=contents,
            config=config,
        )
        data = json.loads(response.text or "{}")
        corrections = data.get("corrections", {})
        # Only accept corrections for indices we actually asked about
        return {
            int(k): v for k, v in corrections.items()
            if v and int(k) in low_indices
        }
    except Exception:
        logger.warning("Gemini glyph verification failed", exc_info=True)
        return {}


async def _verify_glyphs_grok(
    grok,
    original_image: np.ndarray,
    glyphs: list,
    disputed: list[tuple[int, str, str]],
) -> dict[int, str]:
    """Grok tiebreaker for disputed glyphs (ONNX vs Gemini disagree).

    Sends annotated image + individual crops for each disputed glyph.
    Args:
        disputed: list of (index, onnx_code, gemini_code) tuples
    Returns: {glyph_index: chosen_code}
    """
    if not grok or not grok.available or not disputed:
        return {}

    disputed_indices = {i for i, _, _ in disputed}

    # Annotated image highlighting disputed glyphs
    annotated_bytes = _annotate_image(original_image, glyphs, disputed_indices)

    # Individual crops + description
    crop_messages = []
    glyph_descriptions = []
    for i, onnx_code, gemini_code in disputed:
        if i < len(glyphs):
            crop_bytes = _crop_glyph(original_image, glyphs[i])
            b64_crop = base64.b64encode(crop_bytes).decode("ascii")
            crop_messages.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_crop}"},
            })
        glyph_descriptions.append(
            f"  Glyph #{i}: Model A says '{onnx_code}', Model B says '{gemini_code}'"
        )

    system = (
        "You are an expert Egyptologist and the tiebreaker between two "
        "hieroglyph classification models.\n\n"
        "You will receive:\n"
        "1. An annotated image with numbered bounding boxes (red = disputed)\n"
        "2. Individual cropped close-ups of each disputed glyph\n\n"
        "Respond ONLY with valid JSON."
    )

    glyph_list = "\n".join(glyph_descriptions)
    prompt = (
        f"Two classifiers disagree on these hieroglyphs:\n{glyph_list}\n\n"
        f"First image: full inscription with numbered boxes.\n"
        f"Following images: close-ups of each disputed glyph.\n\n"
        f"Examine both the close-up and the context in the full inscription.\n"
        f"Pick the correct Gardiner code for each.\n"
        f"Return JSON: {{\"votes\": {{\"<glyph_index>\": \"correct_gardiner_code\"}}}}"
    )

    b64_annotated = base64.b64encode(annotated_bytes).decode("ascii")
    content_parts: list[dict] = [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_annotated}"}},
        *crop_messages,
        {"type": "text", "text": prompt},
    ]

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": content_parts},
    ]

    try:
        resp = await grok._chat_completion(
            messages, temperature=0.1, max_tokens=512,
            response_format={"type": "json_object"},
        )
        text = grok._extract_text(resp)
        data = json.loads(text) if text else {}
        return {
            int(k): v for k, v in data.get("votes", {}).items()
            if v and int(k) in disputed_indices
        }
    except Exception:
        logger.warning("Grok glyph tiebreak failed", exc_info=True)
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
            gemini, image, result.glyphs, onnx_glyph_dicts,
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
                    grok, image, result.glyphs, disputed,
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
