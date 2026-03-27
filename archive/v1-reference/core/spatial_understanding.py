"""
Wadjet AI — Spatial Understanding Service.

Multi-landmark detection in a single image using Gemini Vision.
Returns each detected landmark with a normalised bounding box.

Phase 3.12 — Spatial Understanding (Bonus).

Gemini returns bounding boxes as ``[y_min, x_min, y_max, x_max]``
normalised to 0-1000.  This module converts them to 0.0-1.0 floats
before returning ``SpatialResult``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.exceptions import GeminiError

logger = structlog.get_logger("wadjet.spatial")


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Normalised bounding box (0.0-1.0)."""

    y_min: float
    x_min: float
    y_max: float
    x_max: float


@dataclass(frozen=True, slots=True)
class DetectedLandmark:
    """A single landmark detected in the image."""

    landmark_name: str
    landmark_name_ar: str
    confidence: str  # "High", "Medium", "Low"
    bounding_box: BoundingBox
    historical_period: str = ""
    brief_description: str = ""
    is_egyptian: bool = True


@dataclass(frozen=True, slots=True)
class SpatialResult:
    """Full spatial analysis result."""

    total_landmarks: int
    landmarks: list[DetectedLandmark] = field(default_factory=list)
    scene_description: str = ""


# ---------------------------------------------------------------------------
# JSON Schema for Gemini structured output
# ---------------------------------------------------------------------------


def _spatial_response_schema() -> dict[str, Any]:
    """JSON Schema that Gemini must follow for spatial analysis."""
    return {
        "type": "object",
        "properties": {
            "scene_description": {"type": "string"},
            "landmarks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "landmark_name": {"type": "string"},
                        "landmark_name_ar": {"type": "string"},
                        "confidence": {
                            "type": "string",
                            "enum": ["High", "Medium", "Low"],
                        },
                        "bounding_box": {
                            "type": "object",
                            "properties": {
                                "y_min": {"type": "integer"},
                                "x_min": {"type": "integer"},
                                "y_max": {"type": "integer"},
                                "x_max": {"type": "integer"},
                            },
                            "required": ["y_min", "x_min", "y_max", "x_max"],
                        },
                        "historical_period": {"type": "string"},
                        "brief_description": {"type": "string"},
                        "is_egyptian": {"type": "boolean"},
                    },
                    "required": [
                        "landmark_name",
                        "landmark_name_ar",
                        "confidence",
                        "bounding_box",
                        "historical_period",
                        "brief_description",
                        "is_egyptian",
                    ],
                },
            },
        },
        "required": ["scene_description", "landmarks"],
    }


# ---------------------------------------------------------------------------
# System prompts per language
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS: dict[str, str] = {
    "en": (
        "You are an expert Egyptologist with advanced spatial analysis skills. "
        "Examine the provided image and detect ALL Egyptian landmarks, monuments, "
        "temples, tombs, pyramids, or artifacts visible.\n\n"
        "For EACH detected landmark:\n"
        "1. Provide its English name (landmark_name) and Arabic name (landmark_name_ar).\n"
        "2. Assign a detection confidence: 'High', 'Medium', or 'Low'.\n"
        "3. Provide a bounding box as integer coordinates normalised to 0-1000 "
        "(where 0 is the top/left edge and 1000 is the bottom/right edge of the image). "
        "Format: {y_min, x_min, y_max, x_max}.\n"
        "4. State the historical period (dynasty / era / approximate dates).\n"
        "5. Write a brief one-sentence description.\n"
        "6. Set is_egyptian to true if it is an Egyptian heritage site, false otherwise.\n\n"
        "Also provide a scene_description summarising the overall image.\n\n"
        "If the image contains only one landmark, return an array with a single entry. "
        "If no Egyptian landmarks are detected, return an empty array and describe "
        "what you see in scene_description."
    ),
    "ar": (
        "أنت عالم آثار مصري خبير مع مهارات متقدمة في التحليل المكاني. "
        "افحص الصورة المقدمة واكتشف جميع المعالم المصرية والنصب التذكارية "
        "والمعابد والمقابر والأهرامات أو الآثار المرئية.\n\n"
        "لكل معلم مكتشف:\n"
        "1. قدم اسمه بالإنجليزية (landmark_name) والعربية (landmark_name_ar).\n"
        "2. حدد ثقة الاكتشاف: 'High' أو 'Medium' أو 'Low'.\n"
        "3. قدم مربع إحاطة كإحداثيات صحيحة مُعَيَّرة من 0 إلى 1000. "
        "الشكل: {y_min, x_min, y_max, x_max}.\n"
        "4. حدد الفترة التاريخية.\n"
        "5. اكتب وصفًا موجزًا من جملة واحدة بالعربية.\n"
        "6. اضبط is_egyptian على true إذا كان موقعًا تراثيًا مصريًا.\n\n"
        "قدم أيضًا scene_description يلخص الصورة بالكامل بالعربية."
    ),
    "fr": (
        "Vous êtes un égyptologue expert avec des compétences avancées en analyse spatiale. "
        "Examinez l'image fournie et détectez TOUS les monuments, temples, tombeaux, "
        "pyramides ou artefacts égyptiens visibles.\n\n"
        "Pour CHAQUE monument détecté:\n"
        "1. Fournissez son nom anglais (landmark_name) et arabe (landmark_name_ar).\n"
        "2. Attribuez une confiance: 'High', 'Medium' ou 'Low'.\n"
        "3. Fournissez une bo\u00eete englobante en coordonn\u00e9es enti\u00e8res normalis\u00e9es 0-1000. "
        "Format: {y_min, x_min, y_max, x_max}.\n"
        "4. Indiquez la période historique.\n"
        "5. Écrivez une brève description d'une phrase en français.\n"
        "6. Mettez is_egyptian à true si c'est un site patrimonial égyptien.\n\n"
        "Fournissez aussi une scene_description résumant l'image en français."
    ),
    "de": (
        "Sie sind ein erfahrener Ägyptologe mit fortgeschrittenen Fähigkeiten "
        "in der räumlichen Analyse. Untersuchen Sie das bereitgestellte Bild und "
        "erkennen Sie ALLE sichtbaren ägyptischen Wahrzeichen, Denkmäler, Tempel, "
        "Gräber, Pyramiden oder Artefakte.\n\n"
        "Für JEDES erkannte Wahrzeichen:\n"
        "1. Geben Sie den englischen (landmark_name) und arabischen Namen (landmark_name_ar) an.\n"
        "2. Weisen Sie eine Erkennung zu: 'High', 'Medium' oder 'Low'.\n"
        "3. Geben Sie eine Bounding Box als ganzzahlige Koordinaten normalisiert auf 0-1000 an. "
        "Format: {y_min, x_min, y_max, x_max}.\n"
        "4. Nennen Sie die historische Periode.\n"
        "5. Schreiben Sie eine kurze Beschreibung in einem Satz auf Deutsch.\n"
        "6. Setzen Sie is_egyptian auf true für ägyptische Kulturerbestätten.\n\n"
        "Geben Sie auch eine scene_description an, die das Bild zusammenfasst (auf Deutsch)."
    ),
}


# ---------------------------------------------------------------------------
# Helper: convert 0-1000 box -> 0.0-1.0 box
# ---------------------------------------------------------------------------


def _normalise_box(raw: dict[str, int | float]) -> BoundingBox:
    """Convert Gemini's 0-1000 integer coordinates to 0.0-1.0 floats."""
    return BoundingBox(
        y_min=max(0.0, min(1.0, raw.get("y_min", 0) / 1000.0)),
        x_min=max(0.0, min(1.0, raw.get("x_min", 0) / 1000.0)),
        y_max=max(0.0, min(1.0, raw.get("y_max", 0) / 1000.0)),
        x_max=max(0.0, min(1.0, raw.get("x_max", 0) / 1000.0)),
    )


# ---------------------------------------------------------------------------
# Core spatial analysis function
# ---------------------------------------------------------------------------


async def detect_landmarks(
    gemini_service: Any,
    image_bytes: bytes,
    *,
    language: str = "en",
    mime_type: str = "image/jpeg",
) -> SpatialResult:
    """Detect multiple landmarks in an image with bounding boxes.

    Parameters
    ----------
    gemini_service:
        An initialised ``GeminiService`` instance.
    image_bytes:
        Raw image data.
    language:
        ISO 639-1 code (``en``, ``ar``, ``fr``, ``de``).
    mime_type:
        MIME type of the image.

    Returns
    -------
    SpatialResult
        All detected landmarks with normalised bounding boxes.

    Raises
    ------
    GeminiError
        If the Gemini API call or response parsing fails.
    """
    system_prompt = _SYSTEM_PROMPTS.get(language, _SYSTEM_PROMPTS["en"])

    user_prompt = (
        "Analyze this image and detect ALL Egyptian landmarks or monuments visible. "
        "For each one, provide identification details and a bounding box (0-1000 coordinates). "
        "Return ONLY a valid JSON object following the specified schema."
    )

    logger.info(
        "spatial_analysis_start",
        language=language,
        mime_type=mime_type,
        image_size_kb=round(len(image_bytes) / 1024, 1),
    )

    # ── Call Gemini Vision ──────────────────────
    try:
        raw_json = await gemini_service.generate_with_image(
            prompt=user_prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
            system_instruction=system_prompt,
            temperature=0.2,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_schema=_spatial_response_schema(),
        )
    except GeminiError:
        raise
    except Exception as exc:
        logger.error("spatial_analysis_api_error", error=str(exc))
        raise GeminiError(f"Gemini spatial analysis failed: {exc}") from exc

    # ── Parse JSON ─────────────────────────────
    try:
        parsed: dict[str, Any] = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error(
            "spatial_analysis_json_error",
            raw_response=raw_json[:500],
            error=str(exc),
        )
        raise GeminiError(f"Gemini returned invalid JSON: {exc}") from exc

    # ── Build result ───────────────────────────
    raw_landmarks = parsed.get("landmarks", [])
    landmarks: list[DetectedLandmark] = []

    for item in raw_landmarks:
        try:
            box = _normalise_box(item.get("bounding_box", {}))
            landmarks.append(
                DetectedLandmark(
                    landmark_name=item.get("landmark_name", "Unknown"),
                    landmark_name_ar=item.get("landmark_name_ar", ""),
                    confidence=item.get("confidence", "Low"),
                    bounding_box=box,
                    historical_period=item.get("historical_period", ""),
                    brief_description=item.get("brief_description", ""),
                    is_egyptian=item.get("is_egyptian", True),
                )
            )
        except Exception as exc:
            logger.warning(
                "spatial_landmark_parse_skip",
                item=item,
                error=str(exc),
            )
            continue

    result = SpatialResult(
        total_landmarks=len(landmarks),
        landmarks=landmarks,
        scene_description=parsed.get("scene_description", ""),
    )

    logger.info(
        "spatial_analysis_complete",
        total_landmarks=result.total_landmarks,
        landmark_names=[lm.landmark_name for lm in landmarks],
    )

    return result
