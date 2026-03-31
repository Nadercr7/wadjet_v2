"""Scan API endpoints — hieroglyph detection, classification, translation.

POST /api/scan       — Full pipeline with mode selection (ai/onnx/auto)
POST /api/detect     — Detection only: returns bounding boxes
POST /api/read       — AI-only reading (lightweight, no ONNX)

Classification ensemble: ONNX first, then Gemini verifies low-confidence
glyphs, Grok tiebreaks disagreements.

NOTE (CQ-008): This file exceeds the 300-line convention. Candidate split:
  - scan_helpers.py: _annotate_image, _crop_glyph, _needs_ai_fallback,
    _apply_ai_results, _build_result_from_ai_reading, _merge_ai_and_onnx,
    _map_ai_codes_to_onnx_bboxes, _detect_only, _enrich_response
  - scan.py: Endpoints and async orchestration only
  Deferred to avoid regression risk across 23+ tests.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from collections import Counter

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scan"])

MAX_FILE_SIZE = 10 * 1024 * 1024
LOW_CONF_THRESHOLD = 0.5  # glyphs below this get AI verification

# AI call budget per scan request (HIERO-015)
MAX_AI_CALLS_PER_SCAN = 5  # ai_reading + fresh_reading + verify + tiebreak + translate

# When ONNX avg classification confidence is below this, try a fresh AI reading
# instead of just verifying individual codes. This catches the case where ONNX
# found many detections but classified them all wrong.
FRESH_AI_READING_THRESHOLD = 0.50

# Magic byte signatures for image validation (not just Content-Type header)
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG': 'image/png',
    b'RIFF': 'image/webp',  # WebP starts with RIFF....WEBP
}


def _get_pipeline():
    """Lazy-load the pipeline singleton (heavy imports on first call)."""
    from app.dependencies import get_pipeline
    return get_pipeline()


MAX_IMAGE_DIM = 1024  # Resize images larger than this (longest side)


async def _read_image_bytes(file: UploadFile) -> tuple[bytes, np.ndarray, str]:
    """Read an uploaded file into raw bytes + BGR numpy array + detected MIME type.

    Handles HEIC conversion, WebP decoding, and resizes images whose longest
    side exceeds MAX_IMAGE_DIM to avoid OOM on large camera photos.
    """
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10 MB.")

    # Validate magic bytes (not just content-type header which can be spoofed)
    detected_mime = ""
    for magic, mime in MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            if magic == b'RIFF' and data[8:12] != b'WEBP':
                continue  # RIFF but not WebP
            detected_mime = mime
            break

    # Try HEIC/HEIF detection (magic: 'ftyp' at offset 4)
    if not detected_mime and len(data) >= 12 and data[4:8] == b'ftyp':
        ftyp_brand = data[8:12]
        if ftyp_brand in (b'heic', b'heix', b'hevc', b'mif1'):
            detected_mime = "image/heic"

    if not detected_mime:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use JPEG, PNG, WebP, or HEIC.",
        )

    # Convert HEIC → JPEG via Pillow (pillow-heif registers automatically if installed)
    if detected_mime == "image/heic":
        try:
            import io

            from PIL import Image as PILImage
            pil_img = PILImage.open(io.BytesIO(data))
            pil_img = pil_img.convert("RGB")
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=92)
            data = buf.getvalue()
            detected_mime = "image/jpeg"
        except Exception as e:
            logger.warning("HEIC conversion failed: %s", e)
            raise HTTPException(
                status_code=400,
                detail="Could not decode HEIC image. Please convert to JPEG or PNG.",
            ) from None

    arr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")

    # Resize large images to prevent OOM and speed up ONNX inference
    h, w = image.shape[:2]
    if max(h, w) > MAX_IMAGE_DIM:
        scale = MAX_IMAGE_DIM / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        # Re-encode to keep raw_bytes consistent with the resized image
        _, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        data = bytes(buf)
        detected_mime = "image/jpeg"
        logger.info("Resized %dx%d → %dx%d for scan", w, h, new_w, new_h)

    return data, image, detected_mime


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
AI_FALLBACK_MIN_CLASS_CONF = 0.35  # Trigger if avg classification confidence below this


def _needs_ai_fallback(result) -> bool:
    """Check if ONNX detection was poor enough to warrant AI fallback."""
    if result.num_detections == 0:
        return True
    if not result.glyphs:
        return True
    if result.num_detections <= AI_FALLBACK_MAX_DETECTIONS:
        avg_conf = sum(g.confidence for g in result.glyphs) / len(result.glyphs)
        if avg_conf < AI_FALLBACK_MIN_AVG_CONF:
            return True
    # Also trigger when many detections but classification is terrible
    avg_class_conf = sum(g.class_confidence for g in result.glyphs) / len(result.glyphs)
    return avg_class_conf < AI_FALLBACK_MIN_CLASS_CONF


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
        response_text = await gemini.generate_vision_json(
            contents=[prompt, image_part],
            system_instruction=system,
            temperature=0.1,
            max_output_tokens=2048,
        )
        data = json.loads(response_text or "{}")
        if data.get("glyphs"):
            logger.info("AI full reading: found %d glyphs", len(data["glyphs"]))
            return data
        return None
    except Exception:
        logger.warning("AI full reading failed", exc_info=True)
        return None


async def _ai_fresh_reading(
    ai_service,
    gemini,
    image_bytes: bytes,
    mime: str,
    image: np.ndarray,
) -> dict | None:
    """Fresh AI reading using the unified AIService (multi-provider fallback).

    This is a higher-quality alternative to _ai_full_reading:
    - Uses AIService (Gemini → Groq → Grok) instead of Gemini-only
    - Has a more detailed Egyptologist prompt with cartouche awareness
    - Asks for translation in addition to transliteration
    - Falls back to _ai_full_reading (Gemini-only) if AIService unavailable

    Returns dict with: glyphs, gardiner_sequence, transliteration,
    translation_en, translation_ar, direction, notes
    or None on failure.
    """
    h, w = image.shape[:2]

    system = (
        "You are a world-class Egyptologist who reads ancient Egyptian hieroglyphic "
        "inscriptions from photographs. You read WORDS and PHRASES, not just "
        "individual signs.\n\n"
        "KEY RULES:\n"
        "- Standard Gardiner codes: uppercase letter + number (A1, D21, N5)\n"
        "- CARTOUCHES (oval frames) = royal names. Read as NAMES, not sign lists.\n"
        "  Two cartouches = prenomen (throne name) + nomen (birth name)\n"
        "- Transliterate as WORDS (e.g., 'wsr-mAat-ra' not 'U-s-r-m-A-a-t-R-a')\n"
        "- Translate the MEANING (e.g., 'Ramesses II' not 'strong-truth-sun')\n"
        "- Respond ONLY with valid JSON."
    )

    prompt = (
        f"This photograph ({w}×{h}px) contains Egyptian hieroglyphs.\n\n"
        f"PRIORITY: Read the inscription as WORDS and NAMES, not individual signs.\n\n"
        f"1. If cartouches are present, identify the PHARAOH'S NAME(S)\n"
        f"2. Transliterate as words (e.g., 'mn-xpr-ra' for Menkheperra)\n"
        f"3. Translate naturally (e.g., 'Thutmose III' not 'enduring-form-of-Ra')\n"
        f"4. For each glyph: Gardiner code + bounding box [x1%, y1%, x2%, y2%]\n\n"
        f"Return ONLY valid JSON:\n"
        f'{{\n'
        f'  "glyphs": [{{"gardiner_code": "N5", "bbox_pct": [10,20,25,45], "confidence": 0.9}}],\n'
        f'  "direction": "right-to-left",\n'
        f'  "gardiner_sequence": "N5-L1-M23-X1",\n'
        f'  "transliteration": "mn-xpr-ra",\n'
        f'  "translation_en": "Menkheperra (Thutmose III)",\n'
        f'  "translation_ar": "من خبر رع (تحتمس الثالث)",\n'
        f'  "notes": "Royal cartouche, New Kingdom"\n'
        f'}}'
    )

    # Try unified AIService first (supports Gemini → Groq → Grok fallback)
    if ai_service and ai_service.available:
        try:
            data, provider = await ai_service.vision_json(
                image_bytes, mime, system, prompt, max_tokens=4096,
            )
            if data and data.get("glyphs"):
                data["_provider"] = provider
                logger.info(
                    "AI fresh reading (%s): found %d glyphs, seq=%s",
                    provider, len(data["glyphs"]),
                    str(data.get("gardiner_sequence", ""))[:60],
                )
                return data
            logger.info("AI fresh reading via AIService returned empty")
        except Exception:
            logger.warning("AI fresh reading via AIService failed", exc_info=True)

    # Fallback to legacy Gemini-only reading
    return await _ai_full_reading(gemini, image_bytes, mime, image)


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

        response_text = await gemini.generate_vision_json(
            contents=contents,
            system_instruction=system,
            temperature=0.1,
            max_output_tokens=1024,
        )
        data = json.loads(response_text or "{}")

        accuracy = data.get("accuracy_assessment", "").lower()
        ai_full_seq = data.get("your_full_sequence", [])
        gemini_corrections = {
            int(k): v for k, v in data.get("corrections", {}).items()
            if v and int(k) < len(glyphs)
        }

        # When AI says the ONNX reading is "poor" and provides its own
        # full sequence, replace ALL glyph codes with AI's reading.
        # This handles the case where ONNX got everything wrong.
        if accuracy == "poor" and ai_full_seq and len(ai_full_seq) >= len(glyphs) // 2:
            logger.info(
                "Sequence verify: AI says 'poor' accuracy, replacing with AI sequence (%d codes)",
                len(ai_full_seq),
            )
            for i, g in enumerate(glyphs):
                if i < len(ai_full_seq):
                    new_code = ai_full_seq[i].upper().strip()
                    if new_code and new_code != g.gardiner_code.upper():
                        g.gardiner_code = new_code
                        g.class_confidence = 0.65
            return glyphs, True

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

    # Annotated image highlighting disputed glyphs — compress for Grok
    annotated_bytes = _annotate_image(original_image, glyphs, disputed_indices)

    # Compress annotated image if too large (Grok has payload limits)
    MAX_IMAGE_BYTES = 500_000  # 500KB
    if len(annotated_bytes) > MAX_IMAGE_BYTES:
        h, w = original_image.shape[:2]
        scale = min(1.0, 1024 / max(h, w))
        if scale < 1.0:
            small = cv2.resize(original_image, None, fx=scale, fy=scale)
            # Re-annotate on smaller image
            from app.core.hieroglyph_pipeline import GlyphResult
            scaled_glyphs = []
            for g in glyphs:
                sg = GlyphResult(
                    x1=g.x1 * scale, y1=g.y1 * scale,
                    x2=g.x2 * scale, y2=g.y2 * scale,
                    confidence=g.confidence, class_id=g.class_id,
                    gardiner_code=g.gardiner_code,
                    class_confidence=g.class_confidence,
                )
                scaled_glyphs.append(sg)
            annotated_bytes = _annotate_image(small, scaled_glyphs, disputed_indices)

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
        resp = await grok.chat_completion(
            messages, temperature=0.1, max_tokens=512,
            response_format={"type": "json_object"},
        )
        text = grok.extract_text(resp)
        data = json.loads(text) if text else {}
        return {
            int(k): v for k, v in data.get("votes", {}).items()
            if v and int(k) in disputed_indices
        }
    except Exception:
        logger.warning("Grok glyph tiebreak failed", exc_info=True)
        return {}


def _enrich_response(response_data: dict, image: np.ndarray) -> dict:
    """Add image_size and confidence_summary to a scan response dict."""
    h, w = image.shape[:2]
    response_data["image_size"] = {"width": w, "height": h}
    glyphs = response_data.get("glyphs", [])
    if glyphs:
        confs = [g.get("class_confidence", 0) for g in glyphs]
        response_data["confidence_summary"] = {
            "avg": round(sum(confs) / len(confs), 3),
            "min": round(min(confs), 3),
            "max": round(max(confs), 3),
            "low_count": sum(1 for c in confs if c < LOW_CONF_THRESHOLD),
        }
    return response_data


@router.post("/scan")
@limiter.limit("30/minute")
async def scan_image(
    request: Request,
    file: UploadFile = File(...),
    translate: bool = True,
    mode: str = Form("auto"),
):
    """Full scan pipeline with mode selection.

    Modes:
    - "ai"   : AI Vision reads inscription directly (best quality, needs internet)
    - "onnx" : ONNX detect→classify only (fast, works offline, lower quality)
    - "auto" : AI-first with ONNX bboxes for visualization (default, recommended)

    Auto flow:
    1. Start ONNX detection (for bounding boxes + visualization)
    2. Send image to AI Vision Reader (primary reading)
    3. If AI succeeds → use AI reading + ONNX bboxes
    4. If AI fails → fall back to full ONNX pipeline
    """
    raw_bytes, image, mime = await _read_image_bytes(file)
    pipeline = _get_pipeline()

    # Normalize mode
    mode = mode.strip().lower()
    if mode not in ("ai", "onnx", "auto"):
        mode = "auto"

    ai_reader = getattr(request.app.state, "ai_reader", None)
    gemini = getattr(request.app.state, "gemini", None)
    grok = getattr(request.app.state, "grok", None)
    ai_service = getattr(request.app.state, "ai_service", None)

    # ── AI-only mode ──
    if mode == "ai":
        response = await _scan_ai_mode(
            ai_reader, pipeline, raw_bytes, mime, image, translate,
        )
    # ── ONNX-only mode ──
    elif mode == "onnx":
        response = await _scan_onnx_mode(
            pipeline, gemini, grok, raw_bytes, mime, image, translate,
        )
    # ── Auto mode (default): AI-first with ONNX assist ──
    else:
        response = await _scan_auto_mode(
            ai_reader, pipeline, gemini, grok, ai_service,
            raw_bytes, mime, image, translate,
        )

    # Save scan history for authenticated users (fire-and-forget)
    await _save_scan_history(request, response)

    return response


async def _save_scan_history(request: Request, response: JSONResponse):
    """Save scan result to user's history if authenticated."""
    try:
        from app.auth.dependencies import get_optional_user
        from app.db.crud import add_scan_history
        from app.db.database import get_db

        # Get user from auth header
        async for db in get_db():
            user = await get_optional_user(request, db)
            if not user:
                return
            # Extract data from response body
            body = json.loads(response.body.decode())
            glyph_count = body.get("glyph_count", 0)
            glyphs = body.get("glyphs", [])
            if glyphs:
                conf_avg = sum(g.get("class_confidence", 0) for g in glyphs) / len(glyphs)
            else:
                conf_avg = 0.0
            results_json = json.dumps(body.get("glyphs", []))
            await add_scan_history(db, user.id, results_json, conf_avg, glyph_count)
            break
    except Exception:
        logger.debug("Scan history save failed (non-critical)", exc_info=True)


async def _scan_ai_mode(ai_reader, pipeline, raw_bytes, mime, image, translate):
    """AI Vision reads inscription directly. ONNX only for bboxes."""

    t0 = time.perf_counter()

    # Run ONNX detection in parallel for bbox visualization
    onnx_bboxes_task = asyncio.to_thread(_detect_only, pipeline, image)

    # AI reading (primary)
    reading = None
    if ai_reader and ai_reader.available:
        reading = await ai_reader.read_inscription(raw_bytes, mime)

    onnx_detections = await onnx_bboxes_task

    if reading and reading.success:
        result = _build_result_from_ai_reading(
            reading, image, onnx_detections, pipeline, translate,
        )
        result.total_ms = (time.perf_counter() - t0) * 1000
        response_data = result.to_dict()
        response_data["detection_source"] = f"ai_vision ({reading.provider})"
        response_data["mode"] = "ai"
        response_data["ai_reading"] = reading.to_dict()
        return JSONResponse(content=_enrich_response(response_data, image))

    # AI failed → ONNX fallback
    logger.warning("AI mode: all vision providers failed, falling back to ONNX")
    try:
        result = await asyncio.to_thread(pipeline.process_image, image, translate=translate)
    except Exception:
        logger.exception("ONNX fallback failed in AI mode")
        raise HTTPException(status_code=500, detail="An error occurred processing your request.") from None

    result.total_ms = (time.perf_counter() - t0) * 1000
    response_data = result.to_dict()
    response_data["detection_source"] = "onnx_fallback"
    response_data["mode"] = "ai"
    return JSONResponse(content=_enrich_response(response_data, image))


async def _scan_onnx_mode(pipeline, gemini, grok, raw_bytes, mime, image, translate):
    """ONNX pipeline with existing AI verification (legacy behavior)."""
    t0 = time.perf_counter()

    try:
        result = await asyncio.to_thread(pipeline.process_image, image, translate=translate)
    except Exception:
        logger.exception("Scan pipeline failed")
        # Provide hints based on common failure modes
        h, w = image.shape[:2]
        if h < 32 or w < 32:
            detail = "Image is too small for detection. Please use a larger, clearer photo."
        else:
            detail = "An error occurred processing your image. Please try a different photo."
        raise HTTPException(status_code=500, detail=detail) from None

    # AI fallback if ONNX detection was poor
    ai_fallback_used = False
    if _needs_ai_fallback(result):
        ai_data = await _ai_full_reading(gemini, raw_bytes, mime, image)
        if ai_data and ai_data.get("glyphs"):
            _apply_ai_results(result, ai_data, image)
            ai_fallback_used = True
            await _onnx_reclassify_and_retranslate(
                pipeline, result, image, ai_data, translate,
            )

    # Full-sequence verification (when ONNX succeeded)
    VERIFY_CONFIDENCE_THRESHOLD = 0.6
    if not ai_fallback_used and result.glyphs:
        avg_class_conf = sum(g.class_confidence for g in result.glyphs) / len(result.glyphs)
        if avg_class_conf < VERIFY_CONFIDENCE_THRESHOLD:
            corrected_glyphs, corrections_applied = await _full_sequence_verify(
                gemini, grok, image, result.glyphs,
            )
            result.glyphs = corrected_glyphs
            if corrections_applied:
                await _retransliterate_and_translate(pipeline, result, translate)

    result.total_ms = (time.perf_counter() - t0) * 1000
    response_data = result.to_dict()
    response_data["detection_source"] = "ai_vision" if ai_fallback_used else "onnx"
    response_data["mode"] = "onnx"
    return JSONResponse(content=_enrich_response(response_data, image))


async def _scan_auto_mode(
    ai_reader, pipeline, gemini, grok, ai_service,
    raw_bytes, mime, image, translate,
):
    """Auto mode: AI-first with ONNX bboxes. Best quality.

    Strategy:
    1. Run AI reader + ONNX in parallel
    2. If AI reader succeeds → merge AI text + ONNX bboxes (best path)
    3. If AI reader fails:
       a. If ONNX confidence is very low (< FRESH_AI_READING_THRESHOLD):
          try a fresh AI reading via AIService → use it directly
       b. If ONNX confidence is moderate (< VERIFY_THRESHOLD):
          verify individual codes with Gemini + Grok tiebreak
       c. If ONNX detection itself failed: try AI full reading fallback
    """
    from app.core.hieroglyph_pipeline import PipelineResult

    t0 = time.perf_counter()
    ai_calls_used = 0  # Track AI call budget (HIERO-015)

    # Run ONNX full pipeline and AI reading concurrently
    onnx_task = asyncio.to_thread(pipeline.process_image, image, translate=translate)

    ai_reading = None
    if ai_reader and ai_reader.available:
        ai_task = asyncio.create_task(
            ai_reader.read_inscription(raw_bytes, mime),
        )
        ai_calls_used += 1
    else:
        ai_task = None

    # Wait for ONNX
    try:
        onnx_result = await onnx_task
    except Exception:
        logger.exception("ONNX pipeline failed in auto mode")
        onnx_result = PipelineResult()

    # Wait for AI
    if ai_task:
        try:
            ai_reading = await ai_task
        except Exception:
            logger.warning("AI reading failed in auto mode", exc_info=True)

    # ── Path A: AI reader succeeded — best quality path ──
    if ai_reading and ai_reading.success:
        result = _merge_ai_and_onnx(ai_reading, onnx_result, image, pipeline, translate)
        result.total_ms = (time.perf_counter() - t0) * 1000
        response_data = result.to_dict()
        response_data["detection_source"] = f"ai_vision ({ai_reading.provider})"
        response_data["mode"] = "auto"
        response_data["ai_calls_used"] = ai_calls_used
        response_data["ai_reading"] = ai_reading.to_dict()
        return JSONResponse(content=_enrich_response(response_data, image))

    # ── Path B: AI reader failed — improve ONNX results ──
    detection_source = "onnx"

    if onnx_result.glyphs:
        avg_class_conf = sum(g.class_confidence for g in onnx_result.glyphs) / len(onnx_result.glyphs)
        VERIFY_CONFIDENCE_THRESHOLD = 0.6

        # B1: Very low confidence — ONNX classification is unreliable.
        # Try a fresh AI reading using AIService (multi-provider fallback).
        if avg_class_conf < FRESH_AI_READING_THRESHOLD and ai_calls_used < MAX_AI_CALLS_PER_SCAN:
            logger.info(
                "Auto mode: ONNX avg confidence %.1f%% < threshold %.0f%%, trying fresh AI reading",
                avg_class_conf * 100, FRESH_AI_READING_THRESHOLD * 100,
            )
            ai_calls_used += 1
            fresh_data = await _ai_fresh_reading(ai_service, gemini, raw_bytes, mime, image)
            if fresh_data and fresh_data.get("glyphs"):
                # AI reading succeeded — use it directly (don't re-classify with weak ONNX)
                _apply_ai_results(onnx_result, fresh_data, image)
                detection_source = f"ai_fresh ({fresh_data.get('_provider', 'ai')})"
                # Prefer AI-provided translation (reads as words/names, not individual signs)
                if fresh_data.get("translation_en"):
                    onnx_result.translation_en = fresh_data["translation_en"]
                if fresh_data.get("translation_ar"):
                    onnx_result.translation_ar = fresh_data["translation_ar"]
                # Only use RAG translator if AI didn't provide translation
                if translate and not onnx_result.translation_en and onnx_result.transliteration:
                    try:
                        translator = pipeline._get_translator()
                        if translator and hasattr(translator, 'translate_async'):
                            raw = await translator.translate_async(onnx_result.transliteration)
                            onnx_result.translation_en = raw.get("english", "")
                            onnx_result.translation_ar = raw.get("arabic", "")
                    except Exception:
                        logger.warning("RAG translation after fresh AI reading failed")
            else:
                # Fresh AI also failed — fall through to verification
                logger.info("Fresh AI reading failed, trying sequence verification")
                if avg_class_conf < VERIFY_CONFIDENCE_THRESHOLD and gemini and ai_calls_used < MAX_AI_CALLS_PER_SCAN:
                    ai_calls_used += 1
                    corrected_glyphs, corrections_applied = await _full_sequence_verify(
                        gemini, grok if ai_calls_used < MAX_AI_CALLS_PER_SCAN else None,
                        image, onnx_result.glyphs,
                    )
                    if grok and corrections_applied:
                        ai_calls_used += 1
                    onnx_result.glyphs = corrected_glyphs
                    if corrections_applied:
                        await _retransliterate_and_translate(pipeline, onnx_result, translate)

        # B2: Moderate confidence — verify individual codes with AI
        elif avg_class_conf < VERIFY_CONFIDENCE_THRESHOLD and gemini and ai_calls_used < MAX_AI_CALLS_PER_SCAN:
            ai_calls_used += 1
            corrected_glyphs, corrections_applied = await _full_sequence_verify(
                gemini, grok if ai_calls_used < MAX_AI_CALLS_PER_SCAN else None,
                image, onnx_result.glyphs,
            )
            if grok and corrections_applied:
                ai_calls_used += 1
            onnx_result.glyphs = corrected_glyphs
            if corrections_applied:
                await _retransliterate_and_translate(pipeline, onnx_result, translate)

    elif _needs_ai_fallback(onnx_result) and ai_calls_used < MAX_AI_CALLS_PER_SCAN:
        # B3: ONNX detection itself was poor — try AI full reading
        ai_calls_used += 1
        ai_data = await _ai_fresh_reading(ai_service, gemini, raw_bytes, mime, image)
        if ai_data and ai_data.get("glyphs"):
            _apply_ai_results(onnx_result, ai_data, image)
            detection_source = f"ai_fresh ({ai_data.get('_provider', 'ai')})"
            # Prefer AI translation (reads words/names, not individual signs)
            if ai_data.get("translation_en"):
                onnx_result.translation_en = ai_data["translation_en"]
            if ai_data.get("translation_ar"):
                onnx_result.translation_ar = ai_data["translation_ar"]
            if translate and not onnx_result.translation_en and onnx_result.transliteration:
                try:
                    translator = pipeline._get_translator()
                    if translator and hasattr(translator, 'translate_async'):
                        raw = await translator.translate_async(onnx_result.transliteration)
                        onnx_result.translation_en = raw.get("english", "")
                        onnx_result.translation_ar = raw.get("arabic", "")
                except Exception:
                    logger.warning("RAG translation after AI fallback failed")

    onnx_result.total_ms = (time.perf_counter() - t0) * 1000
    response_data = onnx_result.to_dict()
    response_data["detection_source"] = detection_source
    response_data["mode"] = "auto"
    response_data["ai_calls_used"] = ai_calls_used
    return JSONResponse(content=_enrich_response(response_data, image))


# ── Helper: Build PipelineResult from AI reading ──

def _build_result_from_ai_reading(reading, image, onnx_detections, pipeline, translate):
    """Build a PipelineResult using AI reading data, optionally overlaying ONNX bboxes."""
    from app.core.hieroglyph_pipeline import GlyphResult, PipelineResult

    h, w = image.shape[:2]
    result = PipelineResult()

    # Build glyphs from AI reading
    ai_glyphs = []
    for g in reading.glyphs:
        bbox = g.get("bbox_pct", [0, 0, 100, 100])
        x1 = max(0.0, bbox[0] * w / 100.0)
        y1 = max(0.0, bbox[1] * h / 100.0)
        x2 = min(float(w), bbox[2] * w / 100.0)
        y2 = min(float(h), bbox[3] * h / 100.0)
        conf = float(g.get("confidence", 0.8))
        ai_glyphs.append(GlyphResult(
            x1=x1, y1=y1, x2=x2, y2=y2,
            confidence=conf,
            class_id=0,
            gardiner_code=g.get("gardiner_code", ""),
            class_confidence=conf,
        ))

    # Prefer ONNX bboxes if available (more precise pixel coordinates)
    if onnx_detections and len(onnx_detections) >= len(ai_glyphs) // 2:
        result.glyphs = [
            GlyphResult(
                x1=d.x1, y1=d.y1, x2=d.x2, y2=d.y2,
                confidence=d.confidence,
                class_id=0,
                gardiner_code="",
                class_confidence=0.0,
            )
            for d in onnx_detections
        ]
    else:
        result.glyphs = ai_glyphs

    result.num_detections = len(result.glyphs)

    # Use AI text fields directly
    result.gardiner_sequence = reading.gardiner_sequence
    result.transliteration = reading.transliteration
    result.reading_direction = reading.direction
    result.translation_en = reading.translation_en
    result.translation_ar = reading.translation_ar

    # If we used ONNX bboxes, map AI Gardiner codes onto them by position
    if onnx_detections and result.glyphs != ai_glyphs and ai_glyphs:
        _map_ai_codes_to_onnx_bboxes(result.glyphs, ai_glyphs)

    return result


def _merge_ai_and_onnx(ai_reading, onnx_result, image, pipeline, translate):
    """Merge AI reading (for text) with ONNX result (for bboxes).

    ONNX provides precise pixel-level bounding boxes for visualization.
    AI provides the correct Gardiner codes, transliteration, and translation.

    Strategy:
    - If ONNX and AI glyph counts are close (within 50%), use ONNX bboxes
      with AI codes mapped onto them (best visualization).
    - If counts diverge (ONNX found way more/fewer), use AI's glyph list
      directly (AI's detection is more reliable than noisy ONNX).
    """
    from app.core.hieroglyph_pipeline import GlyphResult, PipelineResult

    result = PipelineResult()

    # Build AI glyph objects (for spatial mapping or direct use)
    h, w = image.shape[:2]
    ai_glyphs = []
    for g in ai_reading.glyphs:
        bbox = g.get("bbox_pct", [0, 0, 100, 100])
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0, 0, 100, 100]
        conf = float(g.get("confidence", 0.8))
        ai_glyphs.append(GlyphResult(
            x1=max(0.0, bbox[0] * w / 100.0),
            y1=max(0.0, bbox[1] * h / 100.0),
            x2=min(float(w), bbox[2] * w / 100.0),
            y2=min(float(h), bbox[3] * h / 100.0),
            confidence=conf,
            class_id=0,
            gardiner_code=g.get("gardiner_code", ""),
            class_confidence=conf,
        ))

    n_onnx = len(onnx_result.glyphs) if onnx_result.glyphs else 0
    n_ai = len(ai_glyphs)

    # Decide: use ONNX bboxes (precise pixels) or AI glyphs (correct codes)?
    # Use ONNX only when counts are compatible — otherwise ONNX is noisy.
    use_onnx_bboxes = (
        n_onnx > 0
        and n_ai > 0
        and n_onnx <= n_ai * 1.5  # ONNX didn't detect too many ghosts
        and n_onnx >= n_ai * 0.5  # ONNX didn't miss too many
    )

    if use_onnx_bboxes:
        result.glyphs = onnx_result.glyphs
        result.num_detections = onnx_result.num_detections
        result.detection_ms = onnx_result.detection_ms
        result.classification_ms = onnx_result.classification_ms

        # Map AI codes onto ONNX bboxes by spatial proximity
        _map_ai_codes_to_onnx_bboxes(result.glyphs, ai_glyphs)
    elif ai_glyphs:
        # AI reading is the authority — use AI glyphs directly
        result.glyphs = ai_glyphs
        result.num_detections = len(ai_glyphs)
        logger.info(
            "Merge: using AI glyphs (%d) over ONNX (%d) — count mismatch",
            n_ai, n_onnx,
        )
    elif onnx_result.glyphs:
        # No AI glyphs but have ONNX — map sequence if available
        result.glyphs = onnx_result.glyphs
        result.num_detections = onnx_result.num_detections
        result.detection_ms = onnx_result.detection_ms
        if ai_reading.gardiner_sequence:
            _map_sequence_to_glyphs(result.glyphs, ai_reading.gardiner_sequence)
    else:
        result.num_detections = 0

    # Use AI reading for text fields (superior accuracy)
    result.gardiner_sequence = ai_reading.gardiner_sequence
    result.transliteration = ai_reading.transliteration
    result.reading_direction = ai_reading.direction
    result.translation_en = ai_reading.translation_en
    result.translation_ar = ai_reading.translation_ar

    return result


def _map_ai_codes_to_onnx_bboxes(onnx_glyphs, ai_glyphs):
    """Map AI Gardiner codes to ONNX bboxes by spatial proximity.

    Uses nearest-neighbor matching, but each AI glyph can only be matched
    once (prevents multiple ONNX boxes from getting the same code).
    """
    used_ai = set()
    # Sort ONNX glyphs by reading order (top-to-bottom, right-to-left)
    indexed = list(enumerate(onnx_glyphs))

    for _idx, og in indexed:
        best_dist = float("inf")
        best_ai_idx = -1
        ox = (og.x1 + og.x2) / 2
        oy = (og.y1 + og.y2) / 2
        for ai_idx, ag in enumerate(ai_glyphs):
            if ai_idx in used_ai:
                continue
            ax = (ag.x1 + ag.x2) / 2
            ay = (ag.y1 + ag.y2) / 2
            dist = ((ox - ax) ** 2 + (oy - ay) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_ai_idx = ai_idx
        if best_ai_idx >= 0:
            ag = ai_glyphs[best_ai_idx]
            og.gardiner_code = ag.gardiner_code
            og.class_confidence = ag.class_confidence
            used_ai.add(best_ai_idx)


def _map_sequence_to_glyphs(glyphs, gardiner_sequence: str):
    """Map a Gardiner sequence string onto glyphs sorted by reading order.

    When AI provides gardiner_sequence (e.g. "N5-L1-M23-X1") but no
    per-glyph bboxes, we parse the codes and assign them to glyphs
    sorted by spatial position (reading order).
    """
    import re
    # Parse codes from sequence: handle hyphens, colons (vertical), stars (horizontal)
    codes = [c.strip() for c in re.split(r'[-:*\s]+', gardiner_sequence) if c.strip()]
    if not codes:
        return

    # Sort glyphs by reading order: group by rows (Y), then right-to-left (X desc)
    sorted_glyphs = sorted(glyphs, key=lambda g: (round(g.y1 / 30) * 30, -g.x1))

    for i, g in enumerate(sorted_glyphs):
        if i < len(codes):
            g.gardiner_code = codes[i]
            g.class_confidence = 0.75  # AI-assigned confidence


def _detect_only(pipeline, image):
    """Run ONNX detector only (no classification). Returns detection list."""
    try:
        detector = pipeline._get_detector()
        return detector.detect(image)
    except Exception:
        logger.warning("ONNX detection failed", exc_info=True)
        return []


async def _onnx_reclassify_and_retranslate(
    pipeline, result, image, ai_data, translate,
):
    """Re-classify AI-detected bboxes with ONNX, then re-transliterate."""
    ONNX_RECLASSIFY_THRESHOLD = 0.30
    if result.glyphs:
        ai_glyphs_backup = [
            (g.gardiner_code, g.class_confidence) for g in result.glyphs
        ]
        try:
            onnx_glyphs = await asyncio.to_thread(
                pipeline._classify_crops, image, result.glyphs,
            )
            if onnx_glyphs:
                for i, og in enumerate(onnx_glyphs):
                    og.confidence = 0.8
                    if og.class_confidence < ONNX_RECLASSIFY_THRESHOLD and i < len(ai_glyphs_backup):
                        ai_code, ai_conf = ai_glyphs_backup[i]
                        og.gardiner_code = ai_code
                        og.class_confidence = ai_conf
                        og.low_confidence = True
                result.glyphs = onnx_glyphs
                result.num_detections = len(onnx_glyphs)
        except Exception:
            logger.warning("ONNX re-classification after AI fallback failed")

    await _retransliterate_and_translate(pipeline, result, translate)


async def _retransliterate_and_translate(pipeline, result, translate):
    """Re-run transliteration and (async) translation on corrected glyphs."""
    if result.glyphs:
        try:
            trans = pipeline._transliterate(result.glyphs)
            result.transliteration = trans["transliteration"]
            result.gardiner_sequence = trans["gardiner_sequence"]
            result.reading_direction = trans["direction"]
            result.layout_mode = trans["layout"]
        except Exception:
            logger.warning("Re-transliteration failed")

    if translate and result.transliteration:
        try:
            translator = pipeline._get_translator()
            if translator and hasattr(translator, 'translate_async'):
                raw = await translator.translate_async(result.transliteration)
                result.translation_en = raw.get("english", "")
                result.translation_ar = raw.get("arabic", "")
                result.translation_error = raw.get("error", "")
            else:
                translation = await asyncio.to_thread(
                    pipeline._translate, result.transliteration,
                )
                result.translation_en = translation["en"]
                result.translation_ar = translation["ar"]
                result.translation_error = translation["error"]
        except Exception:
            logger.warning("Translation failed")


@router.post("/detect")
@limiter.limit("30/minute")
async def detect_glyphs(request: Request, file: UploadFile = File(...)):
    """Detection only — returns bounding boxes without classification."""
    _, image, _mime = await _read_image_bytes(file)
    pipeline = _get_pipeline()

    def _run_detection():
        detector = pipeline._get_detector()
        return detector.detect(image)

    try:
        detections = await asyncio.to_thread(_run_detection)
    except Exception:
        logger.exception("Detection failed")
        raise HTTPException(status_code=500, detail="An error occurred processing your request.") from None

    h, w = image.shape[:2]
    return JSONResponse(content={
        "num_detections": len(detections),
        "image_size": {"width": w, "height": h},
        "detections": [d.to_dict() for d in detections],
    })


@router.post("/read")
@limiter.limit("30/minute")
async def read_inscription(request: Request, file: UploadFile = File(...)):
    """AI-only inscription reading — lightweight, no ONNX.

    Sends image directly to AI Vision (Gemini→Groq→Grok).
    Used by client-side JS pipeline for AI reading after local detection.
    Returns the AI reading result as JSON.
    """
    raw_bytes, _, mime = await _read_image_bytes(file)

    ai_reader = getattr(request.app.state, "ai_reader", None)
    if not ai_reader or not ai_reader.available:
        raise HTTPException(
            status_code=503,
            detail="AI vision not available. No API keys configured.",
        )

    reading = await ai_reader.read_inscription(raw_bytes, mime)
    if not reading.success:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "error": reading.notes or "AI could not read the inscription",
                "provider": reading.provider,
                "elapsed_ms": round(reading.elapsed_ms, 1),
            },
        )

    return JSONResponse(content={
        "success": True,
        **reading.to_dict(),
    })
