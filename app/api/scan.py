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


# ── AI detection fallback ──

AI_FALLBACK_MAX_DETECTIONS = 2    # Trigger AI if ONNX finds this many or fewer
AI_FALLBACK_MIN_AVG_CONF = 0.30   # Trigger AI if avg ONNX confidence below this


def _needs_ai_fallback(result) -> bool:
    """Check if ONNX detection was poor enough to warrant AI fallback."""
    if result.num_detections == 0:
        return True
    if result.num_detections <= AI_FALLBACK_MAX_DETECTIONS:
        if not result.glyphs:
            return True
        avg_conf = sum(g.confidence for g in result.glyphs) / len(result.glyphs)
        return avg_conf < AI_FALLBACK_MIN_AVG_CONF
    return False


async def _ai_full_reading(
    gemini,
    image_bytes: bytes,
    mime: str,
    image: np.ndarray,
) -> dict | None:
    """Have Gemini read the full inscription when ONNX detection fails.

    Returns dict with: glyphs, gardiner_sequence, transliteration, direction
    or None on failure.
    """
    if not gemini or not gemini.available:
        return None

    h, w = image.shape[:2]
    system = (
        "You are an expert Egyptologist. You can identify and read ancient Egyptian "
        "hieroglyphic inscriptions with high accuracy. You know the Gardiner Sign List "
        "exhaustively. Respond ONLY with valid JSON."
    )

    prompt = (
        f"This image ({w}×{h}px) contains Egyptian hieroglyphs. "
        f"The automatic detector could not find them, so I need you to read the inscription.\n\n"
        f"Please:\n"
        f"1. Identify EVERY hieroglyph you can see in the image\n"
        f"2. For each hieroglyph, provide its Gardiner code and approximate bounding box "
        f"as percentages of image dimensions [x1%, y1%, x2%, y2%]\n"
        f"3. Read the inscription in the correct order\n"
        f"4. Provide the MdC (Manuel de Codage) transliteration\n\n"
        f"Return JSON:\n"
        f'{{\n'
        f'  "glyphs": [\n'
        f'    {{"gardiner_code": "G1", "bbox_pct": [10.0, 20.0, 25.0, 45.0], "confidence": 0.9}},\n'
        f'    ...\n'
        f'  ],\n'
        f'  "gardiner_sequence": "G1-D21-M17-N35",\n'
        f'  "transliteration": "MdC transliteration string",\n'
        f'  "direction": "right-to-left or left-to-right",\n'
        f'  "notes": "brief inscription description"\n'
        f'}}'
    )

    try:
        from google.genai import types as genai_types

        image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime)
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.1,
            max_output_tokens=2048,
            response_mime_type="application/json",
        )
        response = await gemini._generate_with_retry(
            model=gemini.default_model,
            contents=[prompt, image_part],
            config=config,
        )
        data = json.loads(response.text or "{}")
        if data.get("glyphs"):
            logger.info("AI full reading: found %d glyphs", len(data["glyphs"]))
            return data
        return None
    except Exception:
        logger.warning("AI full reading failed", exc_info=True)
        return None


def _apply_ai_results(result, ai_data: dict, image: np.ndarray) -> None:
    """Overwrite PipelineResult with AI-detected glyphs and reading."""
    from app.core.hieroglyph_pipeline import GlyphResult

    h, w = image.shape[:2]
    glyphs = []

    for g in ai_data.get("glyphs", []):
        code = g.get("gardiner_code", "")
        if not code:
            continue

        # Convert percentage bboxes to pixel coordinates
        bbox_pct = g.get("bbox_pct", [0, 0, 100, 100])
        if len(bbox_pct) == 4:
            x1 = max(0.0, bbox_pct[0] * w / 100.0)
            y1 = max(0.0, bbox_pct[1] * h / 100.0)
            x2 = min(float(w), bbox_pct[2] * w / 100.0)
            y2 = min(float(h), bbox_pct[3] * h / 100.0)
        else:
            x1, y1, x2, y2 = 0.0, 0.0, float(w), float(h)

        conf = float(g.get("confidence", 0.8))
        glyphs.append(GlyphResult(
            x1=x1, y1=y1, x2=x2, y2=y2,
            confidence=conf,
            class_id=0,
            gardiner_code=code.upper(),
            class_confidence=conf,
            low_confidence=False,
        ))

    if not glyphs:
        return

    result.glyphs = glyphs
    result.num_detections = len(glyphs)

    # Use AI-provided reading data
    result.gardiner_sequence = ai_data.get("gardiner_sequence", "")
    result.transliteration = ai_data.get("transliteration", "")
    result.reading_direction = ai_data.get("direction", "")
    result.layout_mode = "AI_DETECTED"


# ── Full-sequence AI verification ──

async def _full_sequence_verify(
    gemini,
    grok,
    original_image: np.ndarray,
    glyphs: list,
) -> tuple[list, bool]:
    """Full-sequence verification: AI reads the entire inscription independently.

    Instead of only verifying low-confidence glyphs, Gemini reads the whole
    inscription and we diff its reading against ONNX's classification.
    Grok tiebreaks disagreements.

    Returns: (corrected_glyphs, corrections_applied)
    """
    if not gemini or not gemini.available or not glyphs:
        return glyphs, False

    # Build ONNX reading description
    glyph_descriptions = []
    for i, g in enumerate(glyphs):
        glyph_descriptions.append(
            f"  #{i}: {g.gardiner_code} (conf={g.class_confidence:.0%})"
        )

    # Annotated image with numbered boxes + crops of uncertain glyphs
    low_indices = {i for i, g in enumerate(glyphs) if g.class_confidence < LOW_CONF_THRESHOLD}
    annotated_bytes = _annotate_image(original_image, glyphs, low_indices or None)

    system = (
        "You are an expert Egyptologist specializing in hieroglyphic classification. "
        "You know the Gardiner Sign List exhaustively.\n\n"
        "Verify a machine-learning model's reading of an inscription.\n"
        "You will receive an annotated image with numbered bounding boxes.\n"
        "Red boxes = low-confidence. Gold boxes = high-confidence.\n"
        "Respond ONLY with valid JSON."
    )

    glyph_list = "\n".join(glyph_descriptions)
    prompt = (
        f"An ONNX model classified these hieroglyphs:\n{glyph_list}\n\n"
        f"The annotated image shows numbered bounding boxes around each detection.\n\n"
        f"Please:\n"
        f"1. Verify EVERY classification (including high-confidence ones)\n"
        f"2. If any classification is wrong, provide the correct Gardiner code\n"
        f"3. Note if any hieroglyphs were MISSED by the detector\n\n"
        f"Return JSON:\n"
        f'{{\n'
        f'  "corrections": {{"<glyph_index>": "correct_gardiner_code"}},\n'
        f'  "your_full_sequence": ["G1", "D21", ...],\n'
        f'  "accuracy_assessment": "good|fair|poor"\n'
        f'}}\n'
        f"Only include corrections for glyphs you want to CHANGE."
    )

    try:
        from google.genai import types as genai_types

        contents: list = [prompt]
        contents.append(genai_types.Part.from_bytes(
            data=annotated_bytes, mime_type="image/jpeg",
        ))

        # Add individual crops for low-confidence glyphs
        for i in sorted(low_indices):
            if i < len(glyphs):
                crop_bytes = _crop_glyph(original_image, glyphs[i])
                contents.append(genai_types.Part.from_bytes(
                    data=crop_bytes, mime_type="image/jpeg",
                ))

        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.1,
            max_output_tokens=1024,
            response_mime_type="application/json",
        )
        response = await gemini._generate_with_retry(
            model=gemini.default_model,
            contents=contents,
            config=config,
        )
        data = json.loads(response.text or "{}")
        gemini_corrections = {
            int(k): v for k, v in data.get("corrections", {}).items()
            if v and int(k) < len(glyphs)
        }

        if not gemini_corrections:
            return glyphs, False

        # Tiebreak with Grok where Gemini disagrees with ONNX
        grok_votes: dict[int, str] = {}
        if grok and grok.available:
            disputed = [
                (i, glyphs[i].gardiner_code, gemini_code)
                for i, gemini_code in gemini_corrections.items()
                if gemini_code.upper() != glyphs[i].gardiner_code.upper()
            ]
            if disputed:
                grok_votes = await _verify_glyphs_grok(
                    grok, original_image, glyphs, disputed,
                )

        # Apply corrections via majority vote
        was_corrected = False
        for i, gemini_code in gemini_corrections.items():
            onnx_code = glyphs[i].gardiner_code
            grok_code = grok_votes.get(i, "")
            onnx_conf = glyphs[i].class_confidence

            # Don't override high-confidence ONNX predictions unless
            # at least one AI model agrees with ONNX
            if onnx_conf >= 0.85:
                ai_codes = [gemini_code.upper()]
                if grok_code:
                    ai_codes.append(grok_code.upper())
                if onnx_code.upper() not in ai_codes and all(
                    c != onnx_code.upper() for c in ai_codes
                ):
                    logger.info(
                        "Glyph #%d: keeping ONNX %s (%.0f%%) — AI disagreed (%s/%s) "
                        "but ONNX confidence too high to override",
                        i, onnx_code, onnx_conf * 100,
                        gemini_code, grok_code or "N/A",
                    )
                    continue

            codes = [onnx_code.upper(), gemini_code.upper()]
            if grok_code:
                codes.append(grok_code.upper())

            counts = Counter(codes)
            winner, _ = counts.most_common(1)[0]

            if winner != onnx_code.upper():
                logger.info(
                    "Glyph #%d corrected: %s → %s (Gemini=%s, Grok=%s)",
                    i, onnx_code, winner, gemini_code, grok_code or "N/A",
                )
                glyphs[i].gardiner_code = winner
                glyphs[i].class_confidence = 0.7
                was_corrected = True

        return glyphs, was_corrected

    except Exception:
        logger.warning("Full sequence verification failed", exc_info=True)
        return glyphs, False


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
    """Full scan pipeline with AI detection fallback and ensemble verification.

    Flow:
    1. ONNX pipeline: detect → classify → transliterate → translate
    2. If ONNX detection poor (≤2 glyphs or low confidence):
       → AI full reading via Gemini Vision (detects + classifies in one shot)
    3. If ONNX succeeded:
       → Full-sequence verification (Gemini reads whole inscription, Grok tiebreaks)
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

    gemini = getattr(request.app.state, "gemini", None)
    grok = getattr(request.app.state, "grok", None)

    # Step 2: AI fallback if ONNX detection was poor
    ai_fallback_used = False
    if _needs_ai_fallback(result):
        logger.info(
            "AI fallback triggered: ONNX found %d detections (avg_conf=%.2f)",
            result.num_detections,
            sum(g.confidence for g in result.glyphs) / max(1, len(result.glyphs))
            if result.glyphs else 0.0,
        )
        ai_data = await _ai_full_reading(gemini, raw_bytes, mime, image)
        if ai_data and ai_data.get("glyphs"):
            _apply_ai_results(result, ai_data, image)
            ai_fallback_used = True

            # Re-classify AI-detected regions with ONNX classifier
            # Gemini provides bounding boxes but often misidentifies the
            # Gardiner code. The ONNX classifier (98% accuracy) is more
            # reliable for classification, so we use AI boxes + ONNX labels.
            # However, if ONNX confidence is very low (e.g. line drawings
            # on white backgrounds), keep Gemini's per-glyph classification.
            ONNX_RECLASSIFY_THRESHOLD = 0.30
            if result.glyphs:
                ai_glyphs_backup = [
                    (g.gardiner_code, g.class_confidence) for g in result.glyphs
                ]
                try:
                    onnx_glyphs = await loop.run_in_executor(
                        None, partial(pipeline._classify_crops, image, result.glyphs)
                    )
                    if onnx_glyphs:
                        any_used_onnx = False
                        for i, og in enumerate(onnx_glyphs):
                            og.confidence = 0.8  # AI-detected box confidence
                            if og.class_confidence < ONNX_RECLASSIFY_THRESHOLD and i < len(ai_glyphs_backup):
                                # ONNX not confident → keep Gemini's code
                                ai_code, ai_conf = ai_glyphs_backup[i]
                                logger.info(
                                    "Glyph #%d: ONNX=%s (%.0f%%) too low, keeping AI=%s",
                                    i, og.gardiner_code, og.class_confidence * 100, ai_code,
                                )
                                og.gardiner_code = ai_code
                                og.class_confidence = ai_conf
                                og.low_confidence = True
                            else:
                                any_used_onnx = True
                        result.glyphs = onnx_glyphs
                        result.num_detections = len(onnx_glyphs)
                        logger.info(
                            "AI fallback: final classification %s",
                            [(g.gardiner_code, f"{g.class_confidence:.0%}") for g in onnx_glyphs],
                        )
                except Exception:
                    logger.warning("ONNX re-classification after AI fallback failed")

            # Re-transliterate with pipeline (instead of using Gemini's)
            if result.glyphs:
                try:
                    trans = pipeline._transliterate(result.glyphs)
                    result.transliteration = trans["transliteration"]
                    result.gardiner_sequence = trans["gardiner_sequence"]
                    result.reading_direction = trans["direction"]
                    result.layout_mode = trans["layout"]
                except Exception:
                    logger.warning("Re-transliteration after AI fallback failed")

            # Run translation on the corrected sequence
            if translate and result.transliteration:
                try:
                    translation = pipeline._translate(result.transliteration)
                    result.translation_en = translation["en"]
                    result.translation_ar = translation["ar"]
                    result.translation_error = translation["error"]
                except Exception:
                    logger.warning("Translation after AI fallback failed")

    # Step 3: Full-sequence verification (when ONNX succeeded)
    if not ai_fallback_used and result.glyphs:
        corrected_glyphs, corrections_applied = await _full_sequence_verify(
            gemini, grok, image, result.glyphs,
        )
        result.glyphs = corrected_glyphs

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

    # Build response
    response_data = result.to_dict()
    response_data["detection_source"] = "ai_vision" if ai_fallback_used else "onnx"
    return JSONResponse(content=response_data)


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
