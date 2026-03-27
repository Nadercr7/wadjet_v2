"""
Wadjet AI — Fallback Chain.

Provides a multi-level degradation strategy so users **always** get
a response, even when upstream AI services fail.

Fallback levels (tried in order)
---------------------------------
1. **Gemini Flash**      — full Gemini 2.5 Flash (default model)
2. **Gemini Flash-Lite** — cheaper/faster Gemini 2.5 Flash-Lite
3. **Cached response**   — previously cached Gemini response
4. **Keras-only**        — on-device classifier with static text
5. **Static data**       — curated attraction data (always available)

Each helper function in this module wraps a specific use-case
(identification, description, etc.) and walks the chain, logging
which level ultimately served the request.

Phase 3.16 — Implement Fallback Chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import structlog

from app.core.exceptions import GeminiError, GeminiRateLimitError

if TYPE_CHECKING:
    from app.core.classifier import ClassificationResult
    from app.core.gemini_service import GeminiService

logger = structlog.get_logger("wadjet.fallback")


# ---------------------------------------------------------------------------
# Fallback level enum & result wrapper
# ---------------------------------------------------------------------------


class FallbackLevel(StrEnum):
    """Which service tier actually served the response."""

    GEMINI_FLASH = "gemini_flash"
    GEMINI_LITE = "gemini_lite"
    CACHED = "cached"
    KERAS_ONLY = "keras_only"
    STATIC_DATA = "static_data"


@dataclass(slots=True)
class FallbackResult:
    """Wraps any response with metadata about which fallback level was used."""

    data: Any
    level: FallbackLevel
    degraded: bool  # True if NOT served by the primary tier


# ---------------------------------------------------------------------------
# Generic text generation with fallback
# ---------------------------------------------------------------------------


async def generate_text_with_fallback(
    gemini_service: GeminiService | None,
    prompt: str,
    *,
    system_instruction: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    static_fallback: str = "",
    use_cache: bool = True,
) -> FallbackResult:
    """Generate text walking: Flash → Lite → Cache → Static.

    Parameters
    ----------
    gemini_service:
        The injected ``GeminiService`` (may be ``None`` if unavailable).
    prompt:
        User/system prompt.
    static_fallback:
        Text returned as the last resort (level 5).

    Returns
    -------
    FallbackResult
        Always succeeds (never raises).
    """
    # Level 1 — Gemini Flash
    if gemini_service is not None:
        try:
            text = await gemini_service.generate_text(
                prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                use_cache=use_cache,
            )
            if text:
                logger.debug("fallback_served", level=FallbackLevel.GEMINI_FLASH)
                return FallbackResult(data=text, level=FallbackLevel.GEMINI_FLASH, degraded=False)
        except (GeminiError, GeminiRateLimitError) as exc:
            logger.warning("fallback_flash_failed", error=str(exc))
        except Exception as exc:
            logger.warning("fallback_flash_unexpected", error=str(exc))

    # Level 2 — Gemini Flash-Lite
    if gemini_service is not None:
        try:
            text = await gemini_service.generate_text(
                prompt,
                model=gemini_service.lite_model,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                use_cache=use_cache,
            )
            if text:
                logger.debug("fallback_served", level=FallbackLevel.GEMINI_LITE)
                return FallbackResult(data=text, level=FallbackLevel.GEMINI_LITE, degraded=True)
        except (GeminiError, GeminiRateLimitError) as exc:
            logger.warning("fallback_lite_failed", error=str(exc))
        except Exception as exc:
            logger.warning("fallback_lite_unexpected", error=str(exc))

    # Level 3 — Check service-level response cache directly
    if gemini_service is not None:
        cached = gemini_service.response_cache.lookup(
            method="generate_text",
            prompt=prompt,
            model=gemini_service.default_model,
            system_instruction=system_instruction or "",
            temperature=str(temperature) if temperature is not None else "",
        )
        if cached is not None:
            logger.debug("fallback_served", level=FallbackLevel.CACHED)
            return FallbackResult(data=cached, level=FallbackLevel.CACHED, degraded=True)

    # Level 4 — Static / hardcoded fallback
    if static_fallback:
        logger.debug("fallback_served", level=FallbackLevel.STATIC_DATA)
        return FallbackResult(data=static_fallback, level=FallbackLevel.STATIC_DATA, degraded=True)

    # Absolute last resort
    logger.warning("fallback_all_levels_exhausted")
    return FallbackResult(
        data="Information temporarily unavailable. Please try again shortly.",
        level=FallbackLevel.STATIC_DATA,
        degraded=True,
    )


# ---------------------------------------------------------------------------
# JSON generation with fallback
# ---------------------------------------------------------------------------


async def generate_json_with_fallback(
    gemini_service: GeminiService | None,
    prompt: str,
    *,
    system_instruction: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    response_schema: dict[str, Any] | None = None,
    static_fallback: str = "{}",
    use_cache: bool = True,
) -> FallbackResult:
    """Generate JSON walking: Flash → Lite → Cache → Static."""

    # Level 1 — Gemini Flash
    if gemini_service is not None:
        try:
            text = await gemini_service.generate_json(
                prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_schema=response_schema,
                use_cache=use_cache,
            )
            if text and text != "{}":
                logger.debug("fallback_json_served", level=FallbackLevel.GEMINI_FLASH)
                return FallbackResult(data=text, level=FallbackLevel.GEMINI_FLASH, degraded=False)
        except (GeminiError, GeminiRateLimitError) as exc:
            logger.warning("fallback_json_flash_failed", error=str(exc))
        except Exception as exc:
            logger.warning("fallback_json_flash_unexpected", error=str(exc))

    # Level 2 — Gemini Flash-Lite
    if gemini_service is not None:
        try:
            text = await gemini_service.generate_json(
                prompt,
                model=gemini_service.lite_model,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_schema=response_schema,
                use_cache=use_cache,
            )
            if text and text != "{}":
                logger.debug("fallback_json_served", level=FallbackLevel.GEMINI_LITE)
                return FallbackResult(data=text, level=FallbackLevel.GEMINI_LITE, degraded=True)
        except (GeminiError, GeminiRateLimitError) as exc:
            logger.warning("fallback_json_lite_failed", error=str(exc))
        except Exception as exc:
            logger.warning("fallback_json_lite_unexpected", error=str(exc))

    # Level 3 — Cache probe
    if gemini_service is not None:
        cached = gemini_service.response_cache.lookup(
            method="generate_json",
            prompt=prompt,
            model=gemini_service.default_model,
            system_instruction=system_instruction or "",
            temperature=str(temperature) if temperature is not None else "",
        )
        if cached is not None:
            logger.debug("fallback_json_served", level=FallbackLevel.CACHED)
            return FallbackResult(data=cached, level=FallbackLevel.CACHED, degraded=True)

    # Level 4 — Static JSON
    logger.debug("fallback_json_served", level=FallbackLevel.STATIC_DATA)
    return FallbackResult(data=static_fallback, level=FallbackLevel.STATIC_DATA, degraded=True)


# ---------------------------------------------------------------------------
# Vision (image) analysis with fallback
# ---------------------------------------------------------------------------


async def analyze_image_with_fallback(
    gemini_service: GeminiService | None,
    image_bytes: bytes,
    *,
    language: str = "en",
    mime_type: str = "image/jpeg",
    classifier_result: ClassificationResult | None = None,
) -> FallbackResult:
    """Analyze an image walking: Flash Vision → Lite Vision → Keras → Static.

    Parameters
    ----------
    classifier_result:
        When provided, used as the Keras-only fallback (level 4).
    """
    from app.core.gemini_vision import GeminiVisionResult, analyze_image

    # Level 1 — Gemini Flash Vision
    if gemini_service is not None:
        try:
            result = await analyze_image(
                gemini_service=gemini_service,
                image_bytes=image_bytes,
                language=language,
                mime_type=mime_type,
            )
            logger.debug("fallback_vision_served", level=FallbackLevel.GEMINI_FLASH)
            return FallbackResult(data=result, level=FallbackLevel.GEMINI_FLASH, degraded=False)
        except (GeminiError, GeminiRateLimitError) as exc:
            logger.warning("fallback_vision_flash_failed", error=str(exc))
        except Exception as exc:
            logger.warning("fallback_vision_flash_unexpected", error=str(exc))

    # Level 2 — Gemini Lite Vision
    if gemini_service is not None:
        try:
            import json

            from app.core.gemini_vision import _SYSTEM_PROMPTS, _vision_response_schema

            system_prompt = _SYSTEM_PROMPTS.get(language, _SYSTEM_PROMPTS["en"])
            user_prompt = (
                "Analyze this image and identify the Egyptian landmark or monument shown. "
                "Return ONLY a valid JSON object following the specified schema."
            )
            raw_json = await gemini_service.generate_with_image(
                prompt=user_prompt,
                image_bytes=image_bytes,
                mime_type=mime_type,
                model=gemini_service.lite_model,
                system_instruction=system_prompt,
                temperature=0.2,
                max_output_tokens=1024,
                response_mime_type="application/json",
                response_schema=_vision_response_schema(),
            )
            parsed = json.loads(raw_json)
            result = GeminiVisionResult.model_validate(parsed)
            logger.debug("fallback_vision_served", level=FallbackLevel.GEMINI_LITE)
            return FallbackResult(data=result, level=FallbackLevel.GEMINI_LITE, degraded=True)
        except Exception as exc:
            logger.warning("fallback_vision_lite_failed", error=str(exc))

    # Level 3 — Cached vision response (via image hash)
    if gemini_service is not None:
        img_hash = gemini_service.response_cache.hash_image(image_bytes)
        cached = gemini_service.response_cache.lookup(
            method="generate_with_image",
            prompt="Analyze this image and identify the Egyptian landmark or monument shown. "
            "Return ONLY a valid JSON object following the specified schema.",
            model=gemini_service.default_model,
            image_hash=img_hash,
        )
        if cached is not None:
            try:
                import json

                parsed = json.loads(cached)
                result = GeminiVisionResult.model_validate(parsed)
                logger.debug("fallback_vision_served", level=FallbackLevel.CACHED)
                return FallbackResult(data=result, level=FallbackLevel.CACHED, degraded=True)
            except Exception:
                pass  # Cache entry was text, not parseable — skip

    # Level 4 — Keras-only (classifier result as-is)
    if classifier_result is not None:
        logger.debug("fallback_vision_served", level=FallbackLevel.KERAS_ONLY)
        return FallbackResult(
            data=classifier_result,
            level=FallbackLevel.KERAS_ONLY,
            degraded=True,
        )

    # Level 5 — Static fallback
    from app.core.attractions_data import get_top_rated

    top = get_top_rated(1)
    static_msg = (
        f"Unable to analyze image. Visit {top[0].name} — {top[0].description}"
        if top
        else "Unable to analyze image. Please try again."
    )
    logger.warning("fallback_vision_all_exhausted")
    return FallbackResult(data=static_msg, level=FallbackLevel.STATIC_DATA, degraded=True)


# ---------------------------------------------------------------------------
# Description generation with fallback
# ---------------------------------------------------------------------------


async def generate_description_with_fallback(
    gemini_service: GeminiService | None,
    landmark_name: str,
    *,
    language: str = "en",
) -> FallbackResult:
    """Rich description: Flash → Lite → Cache → Static attraction data.

    Falls back to the static ``Attraction.description`` /
    ``Attraction.highlights`` from attractions_data.
    """
    from app.core.gemini_descriptions import generate_description

    # Level 1 — Gemini Flash (default)
    if gemini_service is not None:
        try:
            result = await generate_description(
                gemini_service=gemini_service,
                landmark_name=landmark_name,
                language=language,
            )
            logger.debug("fallback_desc_served", level=FallbackLevel.GEMINI_FLASH)
            return FallbackResult(data=result, level=FallbackLevel.GEMINI_FLASH, degraded=False)
        except (GeminiError, GeminiRateLimitError) as exc:
            logger.warning("fallback_desc_flash_failed", error=str(exc))
        except Exception as exc:
            logger.warning("fallback_desc_flash_unexpected", error=str(exc))

    # Level 2 — Gemini Lite description
    if gemini_service is not None:
        try:
            import json

            from app.core.gemini_descriptions import _SYSTEM_PROMPTS, _description_response_schema

            system_prompt = _SYSTEM_PROMPTS.get(language, _SYSTEM_PROMPTS["en"])
            user_prompt = (
                f"Generate a rich description for the Egyptian landmark: {landmark_name}\n\n"
                f"Return ONLY a valid JSON object following the specified schema."
            )
            raw_json = await gemini_service.generate_json(
                prompt=user_prompt,
                model=gemini_service.lite_model,
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=4096,
                response_schema=_description_response_schema(),
            )
            parsed = json.loads(raw_json)
            from app.core.gemini_descriptions import RichDescription

            result = RichDescription(landmark_name=landmark_name, language=language, **parsed)
            logger.debug("fallback_desc_served", level=FallbackLevel.GEMINI_LITE)
            return FallbackResult(data=result, level=FallbackLevel.GEMINI_LITE, degraded=True)
        except Exception as exc:
            logger.warning("fallback_desc_lite_failed", error=str(exc))

    # Level 3 — Cached description
    if gemini_service is not None:
        from app.core.cache import gemini_cache

        cache_key = f"desc:{landmark_name.lower().strip()}:{language}"
        cached = gemini_cache.get(cache_key)
        if cached is not None:
            logger.debug("fallback_desc_served", level=FallbackLevel.CACHED)
            return FallbackResult(data=cached, level=FallbackLevel.CACHED, degraded=True)

    # Level 4 — Static attraction data
    from app.core.attractions_data import get_by_class_name, get_by_name

    attraction = get_by_name(landmark_name) or get_by_class_name(landmark_name)
    if attraction is not None:
        from app.core.gemini_descriptions import RichDescription

        static_desc = RichDescription(
            landmark_name=attraction.name,
            language=language,
            summary=attraction.description,
            history=attraction.historical_significance,
            architectural_significance=attraction.highlights,
            interesting_facts=[],
            visiting_tips=attraction.visiting_tips,
            nearby_attractions=[],
        )
        logger.debug("fallback_desc_served", level=FallbackLevel.STATIC_DATA)
        return FallbackResult(data=static_desc, level=FallbackLevel.STATIC_DATA, degraded=True)

    # Absolute last resort
    from app.core.gemini_descriptions import RichDescription

    logger.warning("fallback_desc_all_exhausted", landmark=landmark_name)
    return FallbackResult(
        data=RichDescription(
            landmark_name=landmark_name,
            language=language,
            summary=f"Information about {landmark_name} is temporarily unavailable.",
            history="",
            architectural_significance="",
            interesting_facts=[],
            visiting_tips="",
            nearby_attractions=[],
        ),
        level=FallbackLevel.STATIC_DATA,
        degraded=True,
    )
