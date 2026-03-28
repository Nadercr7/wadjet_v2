"""
Wadjet AI — Image Captioning Service.

Generates tourist-friendly, natural-language captions for uploaded
images of Egyptian heritage sites using Gemini Vision.

Phase 3.13 — Image Captioning.

Example output:
    "The magnificent Great Pyramid of Giza, built during the reign of
     Pharaoh Khufu, stands against a blue desert sky."
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.exceptions import GeminiError

logger = structlog.get_logger("wadjet.captioning")


# ---------------------------------------------------------------------------
# System prompts per language
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS: dict[str, str] = {
    "en": (
        "You are an expert travel writer and Egyptologist. "
        "Generate a single, vivid, tourist-friendly caption for the image. "
        "The caption should be descriptive, engaging, and suitable for social media sharing. "
        "Include the landmark name and a brief historical or cultural context. "
        "Keep it between 1-3 sentences. Do not use hashtags. "
        "Return ONLY the caption text — no quotes, no labels, no JSON."
    ),
    "ar": (
        "أنت كاتب سفر خبير وعالم آثار مصري. "
        "أنشئ تعليقًا واحدًا حيويًا ومناسبًا للسياح للصورة. "
        "يجب أن يكون التعليق وصفيًا وجذابًا ومناسبًا للمشاركة على وسائل التواصل الاجتماعي. "
        "أضف اسم المعلم وسياقًا تاريخيًا أو ثقافيًا موجزًا. "
        "اجعله من 1-3 جمل. لا تستخدم الهاشتاغات. "
        "أعد نص التعليق فقط — بدون علامات اقتباس أو تسميات أو JSON."
    ),
    "fr": (
        "Vous êtes un rédacteur de voyage expert et égyptologue. "
        "Générez une légende unique, vivante et adaptée aux touristes pour l'image. "
        "La légende doit être descriptive, engageante et adaptée au partage sur les réseaux sociaux. "
        "Incluez le nom du monument et un bref contexte historique ou culturel. "
        "Gardez-la entre 1 et 3 phrases. N'utilisez pas de hashtags. "
        "Retournez UNIQUEMENT le texte de la légende — pas de guillemets, pas d'étiquettes, pas de JSON."
    ),
    "de": (
        "Sie sind ein erfahrener Reiseschriftsteller und Ägyptologe. "
        "Erstellen Sie eine einzige, lebhafte, touristenfreundliche Bildunterschrift für das Bild. "
        "Die Bildunterschrift sollte beschreibend, ansprechend und für Social-Media-Sharing geeignet sein. "
        "Erwähnen Sie den Namen des Wahrzeichens und einen kurzen historischen oder kulturellen Kontext. "
        "Halten Sie sie zwischen 1-3 Sätzen. Verwenden Sie keine Hashtags. "
        "Geben Sie NUR den Bildunterschrift-Text zurück — keine Anführungszeichen, keine Labels, kein JSON."
    ),
}


# ---------------------------------------------------------------------------
# Core captioning function
# ---------------------------------------------------------------------------


async def caption_image(
    gemini_service: Any,
    image_bytes: bytes,
    *,
    language: str = "en",
    mime_type: str = "image/jpeg",
) -> str:
    """Generate a tourist-friendly caption for an image.

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
    str
        A natural-language caption suitable for social sharing.

    Raises
    ------
    GeminiError
        If the Gemini API call fails.
    """
    system_prompt = _SYSTEM_PROMPTS.get(language, _SYSTEM_PROMPTS["en"])

    user_prompt = (
        "Look at this image of an Egyptian heritage site. "
        "Write a single captivating caption for it."
    )

    logger.info(
        "caption_image_start",
        language=language,
        mime_type=mime_type,
        image_size_kb=round(len(image_bytes) / 1024, 1),
    )

    try:
        caption = await gemini_service.generate_with_image(
            prompt=user_prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
            system_instruction=system_prompt,
            temperature=0.7,  # slightly creative for engaging captions
            max_output_tokens=256,
        )
    except GeminiError:
        raise
    except Exception as exc:
        logger.error("caption_image_api_error", error=str(exc))
        raise GeminiError(f"Image captioning failed: {exc}") from exc

    # Clean up: strip leading/trailing quotes and whitespace
    caption = caption.strip().strip('"').strip("'").strip()

    if not caption:
        raise GeminiError("Gemini returned an empty caption")

    logger.info(
        "caption_image_complete",
        language=language,
        caption_length=len(caption),
        caption_preview=caption[:80],
    )

    return caption
