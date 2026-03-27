"""Write API — convert text to hieroglyphs + palette data.

POST /api/write          — Convert transliteration text to hieroglyphic sequence
GET  /api/write/palette  — Get clickable palette signs grouped by type
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.gardiner import (
    GARDINER_TRANSLITERATION,
    GardinerSign,
    SignType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/write", tags=["write"])


# ── Reverse mapping: transliteration → Gardiner sign ──
# Build from longest transliteration to shortest for greedy matching
_TRANSLIT_TO_SIGN: list[tuple[str, GardinerSign]] = []


def _build_reverse_map():
    """Build transliteration → sign lookup, sorted by length (longest first)."""
    if _TRANSLIT_TO_SIGN:
        return

    seen: set[str] = set()
    # Pass 1: exact-case entries (these always win)
    for sign in GARDINER_TRANSLITERATION.values():
        if sign.sign_type == SignType.DETERMINATIVE:
            continue
        pv = sign.phonetic_value
        if pv and pv not in seen:
            _TRANSLIT_TO_SIGN.append((pv, sign))
            seen.add(pv)
        tl = sign.transliteration
        if tl and tl not in seen:
            _TRANSLIT_TO_SIGN.append((tl, sign))
            seen.add(tl)
    # Pass 2: lowercase fallbacks only for unclaimed keys
    for sign in GARDINER_TRANSLITERATION.values():
        if sign.sign_type == SignType.DETERMINATIVE:
            continue
        for val in (sign.phonetic_value, sign.transliteration):
            if not val:
                continue
            lc = val.lower()
            if lc != val and lc not in seen:
                _TRANSLIT_TO_SIGN.append((lc, sign))
                seen.add(lc)

    # Sort longest first for greedy matching
    _TRANSLIT_TO_SIGN.sort(key=lambda x: -len(x[0]))


# ── Simple letter → uniliteral mapping for alphabetic input ──
_ALPHA_TO_SIGN: dict[str, GardinerSign] = {}


def _build_alpha_map():
    """Map English alphabet letters to closest uniliteral signs."""
    if _ALPHA_TO_SIGN:
        return

    # Direct transliteration matches (case-insensitive)
    for sign in GARDINER_TRANSLITERATION.values():
        if sign.sign_type == SignType.UNILITERAL:
            key = sign.transliteration.lower()
            if len(key) == 1 and key not in _ALPHA_TO_SIGN:
                _ALPHA_TO_SIGN[key] = sign

    # Common English letter approximations for letters without direct match
    approx = {
        'c': 'V31',   # k (basket) — C often = K
        'e': 'M17',   # i (reed) — E approximated as i
        'j': 'I10',   # D (cobra) — J approximated as D
        'l': 'D21',   # r (mouth) — L mapped to r (no L in Egyptian)
        'o': 'G43',   # w (quail chick) — O approximated as w
        'u': 'G43',   # w (quail chick) — U approximated as w
        'v': 'I9',    # f (viper) — V mapped to f
        'x': 'Aa1',   # x (placenta)
        'y': 'M17',   # i (reed) — Y approximated as i
        'z': 'S29',   # s (cloth) — Z mapped to s
    }
    for letter, code in approx.items():
        if letter not in _ALPHA_TO_SIGN:
            sign = GARDINER_TRANSLITERATION.get(code)
            if sign:
                _ALPHA_TO_SIGN[letter] = sign


class WriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="Text to convert")
    mode: str = Field("alpha", pattern="^(alpha|mdc|smart)$", description="'alpha' for English letters, 'mdc' for transliteration, 'smart' for AI translation")


async def _ai_translate_to_hieroglyphs(request: Request, text: str) -> list[dict] | None:
    """Use Gemini to intelligently translate text into hieroglyphs."""
    gemini = getattr(request.app.state, "gemini", None)
    if not gemini or not gemini.available:
        return None

    system = (
        "You are an expert Egyptologist. Translate the given text into Egyptian hieroglyphs "
        "using the Gardiner Sign List. Return only the hieroglyphic signs needed.\n"
        "Always prefer common, well-known signs. Use proper Egyptian grammar where possible.\n"
        "Respond ONLY with valid JSON."
    )

    prompt = (
        f'Translate this text into Egyptian hieroglyphs: "{text}"\n\n'
        f"For each hieroglyph in the translation, provide:\n"
        f"- code: Gardiner code (e.g. G1, D21, N35)\n"
        f"- transliteration: the transliteration value\n"
        f"- description: brief sign description\n\n"
        f"Return JSON:\n"
        f'{{\n'
        f'  "glyphs": [\n'
        f'    {{"code": "G1", "transliteration": "A", "description": "Egyptian vulture"}},\n'
        f'    ...\n'
        f'  ],\n'
        f'  "explanation": "brief note on the translation approach"\n'
        f'}}'
    )

    try:
        result_text = await gemini.generate_json(
            prompt, system_instruction=system,
            temperature=0.2, max_output_tokens=1024,
        )
        data = json.loads(result_text)
        return data.get("glyphs", [])
    except Exception:
        logger.warning("AI hieroglyph translation failed", exc_info=True)
        return None


@router.post("")
async def convert_text(req: WriteRequest, request: Request):
    """Convert text to hieroglyphic sequence.

    Modes:
    - alpha: Map each English letter to its closest uniliteral sign
    - mdc: Parse Manuel de Codage transliteration and find matching signs
    - smart: AI-powered translation via Gemini (handles full phrases)
    """
    _build_reverse_map()
    _build_alpha_map()

    text = req.text.strip()
    result_glyphs: list[dict] = []

    if req.mode == "alpha":
        for char in text.lower():
            if char == ' ':
                result_glyphs.append({"type": "separator", "display": " "})
                continue
            sign = _ALPHA_TO_SIGN.get(char)
            if sign:
                result_glyphs.append({
                    "type": "glyph",
                    "code": sign.code,
                    "transliteration": sign.transliteration,
                    "unicode_char": sign.unicode_char,
                    "description": sign.description,
                })
            else:
                result_glyphs.append({"type": "unknown", "display": char})

    elif req.mode == "mdc":
        # MdC transliteration parsing: split by - or space, match each token
        tokens = []
        for part in text.replace("-", " ").split():
            tokens.append(part)

        for token in tokens:
            remaining = token
            token_glyphs = []
            while remaining:
                matched = False
                for translit, sign in _TRANSLIT_TO_SIGN:
                    if remaining.startswith(translit):
                        token_glyphs.append({
                            "type": "glyph",
                            "code": sign.code,
                            "transliteration": sign.transliteration,
                            "unicode_char": sign.unicode_char,
                            "description": sign.description,
                        })
                        remaining = remaining[len(translit):]
                        matched = True
                        break
                # Fallback: try lowercase match
                if not matched:
                    for translit, sign in _TRANSLIT_TO_SIGN:
                        if remaining.lower().startswith(translit):
                            token_glyphs.append({
                                "type": "glyph",
                                "code": sign.code,
                                "transliteration": sign.transliteration,
                                "unicode_char": sign.unicode_char,
                                "description": sign.description,
                            })
                            remaining = remaining[len(translit):]
                            matched = True
                            break
                if not matched:
                    token_glyphs.append({"type": "unknown", "display": remaining[0]})
                    remaining = remaining[1:]
            result_glyphs.extend(token_glyphs)
            result_glyphs.append({"type": "separator", "display": "-"})

        # Remove trailing separator
        if result_glyphs and result_glyphs[-1].get("type") == "separator":
            result_glyphs.pop()

    elif req.mode == "smart":
        ai_glyphs = await _ai_translate_to_hieroglyphs(request, text)
        if ai_glyphs:
            for g in ai_glyphs:
                code = g.get("code", "")
                sign = GARDINER_TRANSLITERATION.get(code)
                result_glyphs.append({
                    "type": "glyph",
                    "code": code,
                    "transliteration": g.get("transliteration", sign.transliteration if sign else ""),
                    "unicode_char": sign.unicode_char if sign else "",
                    "description": g.get("description", sign.description if sign else ""),
                })
        else:
            # Fallback to alpha mode if AI unavailable
            _build_alpha_map()
            for char in text.lower():
                if char == ' ':
                    result_glyphs.append({"type": "separator", "display": " "})
                    continue
                sign = _ALPHA_TO_SIGN.get(char)
                if sign:
                    result_glyphs.append({
                        "type": "glyph",
                        "code": sign.code,
                        "transliteration": sign.transliteration,
                        "unicode_char": sign.unicode_char,
                        "description": sign.description,
                    })
                else:
                    result_glyphs.append({"type": "unknown", "display": char})

    # Build the display string
    hieroglyphs_str = ""
    for g in result_glyphs:
        if g["type"] == "glyph":
            hieroglyphs_str += g.get("unicode_char") or f"[{g['code']}]"
        elif g["type"] == "separator":
            hieroglyphs_str += " "
        else:
            hieroglyphs_str += "?"

    return JSONResponse(content={
        "glyphs": result_glyphs,
        "hieroglyphs": hieroglyphs_str,
        "input": text,
        "mode": req.mode,
    })


@router.get("/palette")
async def get_palette():
    """Get palette signs grouped by type for the sign picker."""
    groups: dict[str, list[dict]] = {
        "uniliteral": [],
        "biliteral": [],
        "triliteral": [],
        "logogram": [],
    }

    for sign in GARDINER_TRANSLITERATION.values():
        key = sign.sign_type.value
        if key in groups:
            groups[key].append({
                "code": sign.code,
                "transliteration": sign.transliteration,
                "unicode_char": sign.unicode_char,
                "description": sign.description,
                "phonetic_value": sign.phonetic_value,
            })

    # Sort each group naturally
    for key in groups:
        groups[key].sort(key=lambda s: s["transliteration"])

    return JSONResponse(content={"groups": groups})
