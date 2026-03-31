"""AI Hieroglyph Reader — vision-based inscription reading.

Sends photo to AI Vision (Gemini/Groq/Grok) and gets a structured
reading: Gardiner codes, bounding boxes, transliteration, translation,
reading direction.

This is the PRIMARY reader — far more accurate than ONNX detect+classify
on real stone inscriptions (AI ~70-90% vs ONNX ~5-15%).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.ai_service import AIService

logger = logging.getLogger(__name__)


@dataclass
class InscriptionReading:
    """Structured result from AI vision reading."""

    glyphs: list[dict] = field(default_factory=list)
    gardiner_sequence: str = ""
    transliteration: str = ""
    translation_en: str = ""
    translation_ar: str = ""
    direction: str = "right-to-left"
    notes: str = ""
    provider: str = "none"
    elapsed_ms: float = 0.0

    @property
    def success(self) -> bool:
        return bool(self.glyphs) or bool(self.transliteration)

    def to_dict(self) -> dict:
        return {
            "glyphs": self.glyphs,
            "gardiner_sequence": self.gardiner_sequence,
            "transliteration": self.transliteration,
            "translation_en": self.translation_en,
            "translation_ar": self.translation_ar,
            "direction": self.direction,
            "notes": self.notes,
            "provider": self.provider,
            "elapsed_ms": round(self.elapsed_ms, 1),
        }


# ── Egyptologist Expert Prompt ──

_SYSTEM_PROMPT = (
    "You are a world-class Egyptologist who can read ancient Egyptian hieroglyphs "
    "from photographs. You read inscriptions the way a scholar would: identifying "
    "WORDS and PHRASES, not just individual signs.\n\n"
    "KEY KNOWLEDGE:\n"
    "- Standard Gardiner codes: uppercase letter + number (A1, D21, G1, M17, N5)\n"
    "- CARTOUCHES (oval frames) contain ROYAL NAMES. Read the signs inside as a "
    "single name, not individual transliterations. Common royal names:\n"
    "  * mn-xpr-ra = Menkheperra (Thutmose III)\n"
    "  * wsr-mAat-ra stp-n-ra = Usermaatre Setepenre (Ramesses II)\n"
    "  * ra-ms-sw mry-imn = Ramesses Meryamun (Ramesses II birth name)\n"
    "  * twt-anx-imn HqA-iwnw-Sma = Tutankhamun (birth name)\n"
    "  * imn-Htp HqA-wAst = Amenhotep Heqawaset\n"
    "- If TWO cartouches appear together, they are typically the pharaoh's "
    "PRENOMEN (throne name, nsw-bity) and NOMEN (birth name, sA-ra)\n"
    "- Translate the MEANING of the inscription, not individual sign names\n"
    "- MdC: hyphens between signs, colons for vertical stacking, "
    "asterisks for horizontal juxtaposition\n"
    "- Respond ONLY with valid JSON."
)

_USER_PROMPT = """\
Read the hieroglyphic inscription in this photograph.

PRIORITY: Read the inscription as WORDS and SENTENCES, not as a list of individual signs.

STEP 1 — Overall reading:
- Identify cartouches (oval frames = royal names), columns, and registers
- Determine reading direction (signs face INTO the reading direction)
- If cartouches are present: what royal name(s) do they spell?
- If two cartouches: identify prenomen (throne name) and nomen (birth name)

STEP 2 — Translation:
- Provide the MdC transliteration as WORDS (e.g., "wsr-mAat-ra stp.n-ra" NOT "U-s-r-m-A-a-t-R-a")
- Translate into natural English (e.g., "Ramesses II, Strong is the Maat of Ra")
- Translate into Arabic (فصحى)
- Add scholarly notes (pharaoh identified, period, formula type)

STEP 3 — Individual glyphs:
- For each hieroglyph, provide Gardiner code and approximate bounding box [x1%, y1%, x2%, y2%]

Return ONLY valid JSON:
{
  "glyphs": [
    {"gardiner_code": "N5", "bbox_pct": [10, 20, 25, 45], "confidence": 0.9,
     "type": "logogram", "phonetic": "ra", "description": "sun disk"}
  ],
  "direction": "right-to-left",
  "gardiner_sequence": "N5-L1-M23-X1",
  "transliteration": "wsr-mAat-ra stp.n-ra",
  "translation_en": "Usermaatre Setepenre (Ramesses II throne name)",
  "translation_ar": "وسر ماعت رع ستب إن رع (اسم عرش رمسيس الثاني)",
  "notes": "Two cartouches from the royal titulary of Ramesses II, New Kingdom, Dynasty XIX"
}"""

_VALID_DIRECTIONS = frozenset({"right-to-left", "left-to-right", "top-to-bottom"})


class AIHieroglyphReader:
    """Reads hieroglyphic inscriptions using AI vision models.

    Fallback chain (handled by AIService): Gemini → Groq → Grok.
    If all AI providers fail, returns empty InscriptionReading
    and caller should fall back to ONNX pipeline.
    """

    def __init__(self, ai_service: AIService) -> None:
        self._ai = ai_service

    @property
    def available(self) -> bool:
        return self._ai.available

    async def read_inscription(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> InscriptionReading:
        """Read full inscription from image.

        Returns InscriptionReading with glyphs, transliteration,
        translation, direction, and provider info.
        """
        if not self._ai.available:
            return InscriptionReading(notes="No AI providers available")

        t0 = time.perf_counter()
        data, provider = await self._ai.vision_json(
            image_bytes,
            mime_type,
            _SYSTEM_PROMPT,
            _USER_PROMPT,
            max_tokens=4096,
        )
        elapsed = (time.perf_counter() - t0) * 1000

        if not data:
            logger.warning("AI reader: all providers returned empty")
            return InscriptionReading(
                elapsed_ms=elapsed,
                notes="All AI vision providers failed or returned empty",
            )

        reading = self._parse_response(data, provider, elapsed)
        logger.info(
            "AI reader (%s): %d glyphs, seq=%s, dir=%s, %.0fms",
            provider,
            len(reading.glyphs),
            reading.gardiner_sequence[:50],
            reading.direction,
            elapsed,
        )
        return reading

    def _parse_response(
        self,
        data: dict,
        provider: str,
        elapsed_ms: float,
    ) -> InscriptionReading:
        """Parse and validate AI response into InscriptionReading."""
        glyphs = self._parse_glyphs(data.get("glyphs", []))

        direction = data.get("direction", "right-to-left")
        if direction not in _VALID_DIRECTIONS:
            direction = "right-to-left"

        return InscriptionReading(
            glyphs=glyphs,
            gardiner_sequence=str(data.get("gardiner_sequence", "")),
            transliteration=str(data.get("transliteration", "")),
            translation_en=str(data.get("translation_en", "")),
            translation_ar=str(data.get("translation_ar", "")),
            direction=direction,
            notes=str(data.get("notes", "")),
            provider=provider,
            elapsed_ms=elapsed_ms,
        )

    def _parse_glyphs(self, raw_glyphs: list) -> list[dict]:
        """Validate and normalize glyph entries from AI response."""
        glyphs = []
        for g in raw_glyphs:
            if not isinstance(g, dict):
                continue
            code = g.get("gardiner_code", "")
            if not code or not isinstance(code, str):
                continue

            # Normalize Gardiner code: uppercase, strip whitespace
            code = code.upper().strip()

            # Validate bbox_pct
            bbox = g.get("bbox_pct", [0, 0, 100, 100])
            if not isinstance(bbox, list) or len(bbox) != 4:
                bbox = [0, 0, 100, 100]
            try:
                bbox = [max(0.0, min(100.0, float(b))) for b in bbox]
            except (TypeError, ValueError):
                bbox = [0.0, 0.0, 100.0, 100.0]

            # Validate confidence
            try:
                conf = min(1.0, max(0.0, float(g.get("confidence", 0.8))))
            except (TypeError, ValueError):
                conf = 0.8

            glyphs.append({
                "gardiner_code": code,
                "bbox_pct": bbox,
                "confidence": conf,
                "type": str(g.get("type", "unknown")),
                "phonetic": str(g.get("phonetic", "")),
                "description": str(g.get("description", "")),
            })
        return glyphs
