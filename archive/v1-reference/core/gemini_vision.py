"""
Wadjet AI — Gemini Vision Service.

High-level image analysis powered by Gemini multimodal capabilities.
Wraps ``GeminiService.generate_with_image`` with an expert Egyptologist
system prompt and returns a structured ``GeminiVisionResult``.

Phase 3.2 — Gemini Vision (Image Analysis).
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.core.exceptions import GeminiError

logger = structlog.get_logger("wadjet.gemini.vision")

# ---------------------------------------------------------------------------
# Structured result model
# ---------------------------------------------------------------------------


class GeminiVisionResult(BaseModel):
    """Structured result from Gemini Vision image analysis.

    Returned by ``analyze_image()`` — contains the identified landmark,
    a natural-language confidence description, the historical period,
    and a list of key facts about the location.
    """

    landmark_name: str = Field(
        ...,
        description="Name of the identified Egyptian landmark, monument, or artifact",
    )
    landmark_name_ar: str = Field(
        default="",
        description="Arabic name of the landmark (if available)",
    )
    confidence_description: str = Field(
        ...,
        description=(
            "Human-readable confidence assessment, e.g. "
            "'Very confident', 'Fairly confident', 'Uncertain'"
        ),
    )
    historical_period: str = Field(
        ...,
        description="Historical era or dynasty the landmark belongs to",
    )
    key_facts: list[str] = Field(
        default_factory=list,
        description="3-5 concise facts about the landmark",
    )
    description: str = Field(
        default="",
        description="One-paragraph description of the landmark",
    )
    location: str = Field(
        default="",
        description="Geographic location (city / governorate)",
    )
    is_egyptian: bool = Field(
        default=True,
        description="Whether the image depicts an Egyptian heritage site",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "landmark_name": "Great Pyramid of Giza",
                    "landmark_name_ar": "هرم خوفو الأكبر",
                    "confidence_description": "Very confident",
                    "historical_period": "Old Kingdom, Fourth Dynasty (c. 2580-2560 BC)",
                    "key_facts": [
                        "Built as a tomb for Pharaoh Khufu (Cheops)",
                        "Originally stood 146.6 metres tall",
                        "The only surviving Wonder of the Ancient World",
                        "Constructed with approximately 2.3 million stone blocks",
                    ],
                    "description": (
                        "The Great Pyramid of Giza is the oldest and largest "
                        "of the three pyramids on the Giza plateau."
                    ),
                    "location": "Giza, Egypt",
                    "is_egyptian": True,
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# JSON schema for Gemini structured output
# ---------------------------------------------------------------------------


def _vision_response_schema() -> dict[str, Any]:
    """Return the JSON Schema that Gemini must follow."""
    return {
        "type": "object",
        "properties": {
            "landmark_name": {"type": "string"},
            "landmark_name_ar": {"type": "string"},
            "confidence_description": {
                "type": "string",
                "enum": [
                    "Very confident",
                    "Fairly confident",
                    "Uncertain",
                    "Not an Egyptian landmark",
                ],
            },
            "historical_period": {"type": "string"},
            "key_facts": {
                "type": "array",
                "items": {"type": "string"},
            },
            "description": {"type": "string"},
            "location": {"type": "string"},
            "is_egyptian": {"type": "boolean"},
        },
        "required": [
            "landmark_name",
            "landmark_name_ar",
            "confidence_description",
            "historical_period",
            "key_facts",
            "description",
            "location",
            "is_egyptian",
        ],
    }


# ---------------------------------------------------------------------------
# System prompts (keyed by language code)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS: dict[str, str] = {
    "en": (
        "You are an expert Egyptologist and heritage specialist. "
        "Identify the Egyptian landmark, monument, temple, tomb, or artifact "
        "shown in the provided image. "
        "Return your analysis as a JSON object with the following fields:\n"
        "- landmark_name: the most commonly used English name\n"
        "- landmark_name_ar: the Arabic name\n"
        "- confidence_description: one of 'Very confident', 'Fairly confident', "
        "'Uncertain', or 'Not an Egyptian landmark'\n"
        "- historical_period: the dynasty / era / approximate dates\n"
        "- key_facts: a list of 3-5 interesting facts\n"
        "- description: a concise one-paragraph description\n"
        "- location: the geographic location in Egypt\n"
        "- is_egyptian: true if the image shows an Egyptian heritage site, false otherwise\n\n"
        "If you cannot identify the landmark or it is not Egyptian, set "
        "is_egyptian to false and provide your best guess or state that you "
        "cannot identify it."
    ),
    "ar": (
        "أنت عالم آثار مصري خبير ومتخصص في التراث. "
        "حدد المعلم المصري أو النصب التذكاري أو المعبد أو المقبرة أو الأثر "
        "الظاهر في الصورة المقدمة. "
        "أعد تحليلك ككائن JSON بالحقول التالية:\n"
        "- landmark_name: الاسم الإنجليزي الأكثر شيوعًا\n"
        "- landmark_name_ar: الاسم بالعربية\n"
        "- confidence_description: أحد 'Very confident', 'Fairly confident', "
        "'Uncertain', أو 'Not an Egyptian landmark'\n"
        "- historical_period: الأسرة / العصر / التواريخ التقريبية\n"
        "- key_facts: قائمة من 3-5 حقائق مثيرة للاهتمام (بالعربية)\n"
        "- description: وصف موجز في فقرة واحدة (بالعربية)\n"
        "- location: الموقع الجغرافي في مصر\n"
        "- is_egyptian: true إذا كانت الصورة تظهر موقعًا تراثيًا مصريًا، false خلاف ذلك"
    ),
    "fr": (
        "Vous êtes un égyptologue expert et spécialiste du patrimoine. "
        "Identifiez le monument, temple, tombeau ou artefact égyptien "
        "montré dans l'image fournie. "
        "Retournez votre analyse sous forme d'objet JSON avec les champs suivants:\n"
        "- landmark_name: le nom anglais le plus couramment utilisé\n"
        "- landmark_name_ar: le nom en arabe\n"
        "- confidence_description: l'un de 'Very confident', 'Fairly confident', "
        "'Uncertain', ou 'Not an Egyptian landmark'\n"
        "- historical_period: la dynastie / époque / dates approximatives\n"
        "- key_facts: une liste de 3-5 faits intéressants (en français)\n"
        "- description: une description concise en un paragraphe (en français)\n"
        "- location: la localisation géographique en Égypte\n"
        "- is_egyptian: true si l'image montre un site patrimonial égyptien, false sinon"
    ),
    "de": (
        "Sie sind ein erfahrener Ägyptologe und Kulturerbe-Spezialist. "
        "Identifizieren Sie das ägyptische Wahrzeichen, Denkmal, den Tempel, "
        "das Grab oder Artefakt auf dem bereitgestellten Bild. "
        "Geben Sie Ihre Analyse als JSON-Objekt mit folgenden Feldern zurück:\n"
        "- landmark_name: der gebräuchlichste englische Name\n"
        "- landmark_name_ar: der arabische Name\n"
        "- confidence_description: einer von 'Very confident', 'Fairly confident', "
        "'Uncertain', oder 'Not an Egyptian landmark'\n"
        "- historical_period: die Dynastie / Epoche / ungefähre Daten\n"
        "- key_facts: eine Liste von 3-5 interessanten Fakten (auf Deutsch)\n"
        "- description: eine prägnante Beschreibung in einem Absatz (auf Deutsch)\n"
        "- location: der geografische Standort in Ägypten\n"
        "- is_egyptian: true wenn das Bild eine ägyptische Kulturerbestätte zeigt, sonst false"
    ),
}


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------


async def analyze_image(
    gemini_service: Any,
    image_bytes: bytes,
    *,
    language: str = "en",
    mime_type: str = "image/jpeg",
) -> GeminiVisionResult:
    """Analyse an image using Gemini Vision and return a structured result.

    Parameters
    ----------
    gemini_service:
        An initialised ``GeminiService`` instance (from DI).
    image_bytes:
        Raw image data.
    language:
        ISO 639-1 language code (``en``, ``ar``, ``fr``, ``de``).
        Controls which system prompt is used.
    mime_type:
        MIME type of the image (default ``image/jpeg``).

    Returns
    -------
    GeminiVisionResult
        Structured analysis with landmark name, confidence, period, facts.

    Raises
    ------
    GeminiError
        If the Gemini API call fails or the response cannot be parsed.
    """
    system_prompt = _SYSTEM_PROMPTS.get(language, _SYSTEM_PROMPTS["en"])

    user_prompt = (
        "Analyze this image and identify the Egyptian landmark or monument shown. "
        "Return ONLY a valid JSON object following the specified schema."
    )

    logger.info(
        "gemini_vision_analyze_start",
        language=language,
        mime_type=mime_type,
        image_size_kb=round(len(image_bytes) / 1024, 1),
    )

    try:
        raw_json = await gemini_service.generate_with_image(
            prompt=user_prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
            system_instruction=system_prompt,
            temperature=0.2,
            max_output_tokens=1024,
            response_mime_type="application/json",
            response_schema=_vision_response_schema(),
        )
    except GeminiError:
        # Re-raise known errors as-is
        raise
    except Exception as exc:
        logger.error("gemini_vision_api_error", error=str(exc))
        raise GeminiError(f"Gemini Vision API call failed: {exc}") from exc

    # ── Parse the JSON response ──────────────────
    try:
        parsed: dict[str, Any] = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error(
            "gemini_vision_json_parse_error",
            raw_response=raw_json[:500],
            error=str(exc),
        )
        raise GeminiError(f"Gemini returned invalid JSON: {exc}") from exc

    # ── Validate with Pydantic ───────────────────
    try:
        result = GeminiVisionResult.model_validate(parsed)
    except Exception as exc:
        logger.error(
            "gemini_vision_validation_error",
            parsed_data=parsed,
            error=str(exc),
        )
        raise GeminiError(f"Gemini response failed validation: {exc}") from exc

    logger.info(
        "gemini_vision_analyze_complete",
        landmark=result.landmark_name,
        confidence=result.confidence_description,
        is_egyptian=result.is_egyptian,
    )

    return result
