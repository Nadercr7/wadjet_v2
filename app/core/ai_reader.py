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
    "You are a world-class Egyptologist with complete mastery of the Gardiner "
    "Sign List (700+ hieroglyphs). You can read ancient Egyptian hieroglyphic "
    "inscriptions from photographs with near-perfect accuracy, including "
    "weathered stone carvings, painted reliefs, and papyrus.\n\n"
    "IMPORTANT RULES:\n"
    "- Use STANDARD Gardiner codes only (e.g., A1, D21, G1, M17, N35)\n"
    "- The category letter is uppercase, followed by a number\n"
    "- Common uniliterals: M17=reed (i), D21=mouth (r), N35=water (n), "
    "G43=quail chick (w), X1=bread (t), D4=eye (ir), O1=house (pr), "
    "V4=lasso (wA), S29=folded cloth (s), Q3=stool (p), V31=basket (k), "
    "D46=hand (d), I9=horned viper (f), G17=owl (m), N29=hillslope (q)\n"
    "- Common logograms: N5=sun disk (Ra), M23=sedge plant (nsw/sw), "
    "L2=bee (bity), S34=ankh (life), R4=Hotep altar, Aa1=placenta (x), "
    "U1=sickle (mA), Y5=game board (mn)\n"
    "- CARTOUCHES: oval frames containing royal names. Read signs inside "
    "the cartouche as a group. Look for common pharaoh name patterns:\n"
    "  * Ra + mn + kheper = Menkheperra (Thutmose III)\n"
    "  * Imn + Ra + ms + s = Ramesses\n"
    "  * Wsr + mAat + Ra = Usermaatre (Ramesses II)\n"
    "  * twt + anx + Imn = Tutankhamun\n"
    "- For MdC: use hyphens between signs, colons for vertical stacking, "
    "asterisks for horizontal juxtaposition\n"
    "- Respond ONLY with valid JSON. No markdown, no explanation outside JSON."
)

_USER_PROMPT = """\
Read the hieroglyphs in this photograph of an ancient Egyptian inscription.

STEP 1 — Survey the image:
- Identify all inscription areas (cartouches, columns, registers)
- Determine the reading direction (signs face INTO the reading direction)
- Note the surface type (stone relief, painted, papyrus)

STEP 2 — For EACH hieroglyph visible:
1. Identify its Gardiner code precisely (e.g., G1, D21, M17)
2. Estimate its bounding box as percentages [x1%, y1%, x2%, y2%]
3. State if it's a phonogram, logogram, or determinative
4. Provide its transliteration value

STEP 3 — Read and translate:
5. Read the full inscription in the correct order
6. Provide MdC (Manuel de Codage) transliteration
7. Provide literal English translation
8. Provide Arabic translation (فصحى)
9. Add brief scholarly notes (period, formula type, significance)

IMPORTANT: If you see cartouches, identify the royal name(s) they contain.

Return ONLY valid JSON in this exact format:
{
  "glyphs": [
    {
      "gardiner_code": "G1",
      "bbox_pct": [10.0, 20.0, 25.0, 45.0],
      "confidence": 0.95,
      "type": "uniliteral",
      "phonetic": "A",
      "description": "Egyptian vulture"
    }
  ],
  "direction": "right-to-left",
  "gardiner_sequence": "G1-D21-M17-N35",
  "transliteration": "A-r-i-n",
  "translation_en": "the son of Ra",
  "translation_ar": "ابن رع",
  "notes": "Royal titulary formula from the New Kingdom period"
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
