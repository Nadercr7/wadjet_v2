"""Write API — convert text to hieroglyphs + palette data.

POST /api/write          — Convert transliteration text to hieroglyphic sequence
GET  /api/write/palette  — Get clickable palette signs grouped by type
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.rate_limit import limiter

from app.core.gardiner import (
    GARDINER_TRANSLITERATION,
    GardinerSign,
    SignType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/write", tags=["write"])

# ── Write corpus for few-shot examples ──
_WRITE_CORPUS: list[dict] = []
_CORPUS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "translation" / "write_corpus.jsonl"


def _load_write_corpus():
    """Load EN→MdC corpus for few-shot prompting."""
    if _WRITE_CORPUS:
        return
    if not _CORPUS_PATH.exists():
        logger.warning("write_corpus.jsonl not found at %s", _CORPUS_PATH)
        return
    for line in _CORPUS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            _WRITE_CORPUS.append(json.loads(line))


# ── Known phrase shortcuts — bypass AI entirely ──
_SHORTCUTS: dict[str, str] = {
    # Offering formula
    "an offering which the king gives": "Htp di nsw",
    "a royal offering": "Htp di nsw",
    "offering formula": "Htp di nsw",
    # Key phrases
    "life prosperity health": "anx wDA snb",
    "life, prosperity, health": "anx wDA snb",
    "given life forever": "Dj anx Dt",
    "words to be spoken": "Dd mdw",
    "recitation": "Dd mdw",
    "true of voice": "mAa xrw",
    "justified": "mAa xrw",
    "beloved of amun": "mry jmn",
    "lord of the two lands": "nb tAwj",
    "king of upper and lower egypt": "nsw bjt",
    "son of ra": "sA ra",
    "son of re": "sA ra",
    "good god": "nTr nfr",
    "great god": "nTr aA",
    "lord of heaven": "nb pt",
    "lord of eternity": "nb Dt",
    "may he live forever": "anx Dt",
    "in peace": "m Htp",
    "welcome": "jj m Htp",
    "welcome in peace": "jj m Htp",
    "go in peace": "Sm m Htp",
    "praising the god": "dwA nTr",
    "the book of the dead": "rw nw prt m hrw",
    "book of coming forth by day": "rw nw prt m hrw",
    "the opening of the mouth": "wpt r",
    "the beautiful west": "jmnt nfrt",
    # Common words
    "life": "anx",
    "live": "anx",
    "health": "snb",
    "peace": "Htp",
    "truth": "mAat",
    "beautiful": "nfr",
    "good": "nfr",
    "great": "aA",
    "love": "mr",
    "eternity": "Dt",
    "forever": "Dt",
    "god": "nTr",
    "king": "nsw",
    "pharaoh": "pr aA",
    "lord": "nb",
    "water": "mw",
    "bread": "t",
    "gold": "nbw",
    "heart": "jb",
    "soul": "bA",
    "spirit": "kA",
    # Deity names
    "amun": "jmn",
    "ra": "ra",
    "osiris": "wsjr",
    "horus": "Hr",
    "isis": "Ast",
    "anubis": "jnpw",
    "thoth": "DHwtj",
    "hathor": "Hwt Hr",
    "maat": "mAat",
    "ptah": "ptH",
    # Pharaoh names
    "tutankhamun": "twt anx jmn",
    "ramesses": "ra ms sw",
    "ramses": "ra ms sw",
    "nefertiti": "nfrt jjtj",
    "hatshepsut": "HAt Spswt",
    "akhenaten": "Ax n jtn",
    "khufu": "xwfw",
}

# ── Valid Gardiner code pattern ──
_GARDINER_RE = re.compile(r'^(?:Aa|NL|NU|[A-Z])\d{1,4}[A-Za-z]?$')


def _is_mdc_input(text: str) -> bool:
    """Detect if input looks like MdC transliteration (not English)."""
    mdc_chars = set("AaDdHhSsTtjnrwbpfmxqkgszt.=-")
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return False
    mdc_ratio = sum(1 for c in alpha if c in mdc_chars) / len(alpha)
    has_uppercase_mdc = any(c in text for c in "ADHSTDd")
    return mdc_ratio > 0.8 and has_uppercase_mdc


def _find_few_shot_examples(text: str, n: int = 5) -> list[dict]:
    """Find the most relevant corpus examples via keyword overlap."""
    _load_write_corpus()
    if not _WRITE_CORPUS:
        return []

    words = set(text.lower().split())
    scored = []
    for entry in _WRITE_CORPUS:
        en = entry.get("english", "")
        en_words = set(en.split())
        overlap = len(words & en_words)
        if overlap > 0:
            # Prefer curated, shorter entries, and higher overlap
            bonus = 2 if entry.get("source") == "curated" else 0
            scored.append((overlap + bonus, entry))

    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:n]]


# ── Reverse mapping: transliteration → Gardiner sign ──
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

    # Pass 3: MdC aliases — j↔i and z→s
    # In MdC, 'j' and 'i' represent the same consonant (reed, M17).
    # Many texts use 'j' form; add aliases so both resolve.
    aliases: list[tuple[str, str]] = []
    for key in list(seen):
        if key.startswith("i"):
            j_key = "j" + key[1:]
            if j_key not in seen:
                aliases.append((j_key, key))
        elif key.startswith("j"):
            i_key = "i" + key[1:]
            if i_key not in seen:
                aliases.append((i_key, key))
    # 'z' and 's' merged in Middle Egyptian — add z→s aliases
    for key in list(seen):
        if key.startswith("s") and not key.startswith("sA"):
            z_key = "z" + key[1:]
            if z_key not in seen:
                aliases.append((z_key, key))
    for alias_key, orig_key in aliases:
        orig_sign = next((s for t, s in _TRANSLIT_TO_SIGN if t == orig_key), None)
        if orig_sign and alias_key not in seen:
            _TRANSLIT_TO_SIGN.append((alias_key, orig_sign))
            seen.add(alias_key)

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


def _build_smart_prompt(text: str) -> tuple[str, str]:
    """Build system instruction and prompt for smart mode AI call."""
    examples = _find_few_shot_examples(text)
    examples_block = ""
    if examples:
        lines = []
        for ex in examples:
            lines.append(f'  "{ex["english"]}" → "{ex["mdc"]}"')
        examples_block = "Reference examples:\n" + "\n".join(lines) + "\n\n"

    sign_hint = (
        "Common signs available: "
        "anx (S34, life), Htp (R4, offering), nTr (R8, god), nfr (F35, good/beautiful), "
        "ra (N5, sun), nb (V30, lord/all), mr (U6, love), sA (G39, son), wAs (S42, dominion), "
        "xpr (L1, become/Khepri), mn (Y5, endure), sw (M23, sedge), "
        "Dd (I10+D46, say/speak), di (X8, give), pt (N1, sky), "
        "jmn (M17+Y5+N35, Amun), wsjr (Q1+D4, Osiris), Hr (D2, Horus/face)\n"
    )

    system = (
        "You are a professional Egyptologist specializing in Middle Egyptian hieroglyphic writing. "
        "Your task is to translate English text into Manuel de Codage (MdC) transliteration, "
        "which represents Egyptian hieroglyphs.\n\n"
        "RULES:\n"
        "1. Use standard MdC transliteration conventions (A, D, H, S, T, x, X, etc.)\n"
        "2. Separate words with spaces\n"
        "3. Use suffix pronouns with dots: .f (his), .s (her), .sn (their), .k (your), .j (my)\n"
        "4. Prefer well-known sign groups for common words\n"
        "5. For proper nouns, transliterate phonetically into Egyptian\n"
        "6. Keep it scholarly — use forms attested in Middle Egyptian texts\n"
        "7. If unsure, prefer the simpler/more common form\n\n"
        + sign_hint + "\n"
        "Respond ONLY with valid JSON."
    )

    prompt = (
        f'{examples_block}'
        f'Translate this English text into Egyptian hieroglyphs (MdC transliteration): "{text}"\n\n'
        f'For each word/sign group in the translation, provide the MdC transliteration.\n'
        f'Return JSON:\n'
        f'{{\n'
        f'  "mdc": "the full MdC transliteration string",\n'
        f'  "glyphs": [\n'
        f'    {{"mdc": "Htp", "meaning": "offering/peace"}},\n'
        f'    {{"mdc": "di", "meaning": "give"}},\n'
        f'    ...\n'
        f'  ],\n'
        f'  "explanation": "brief note on translation choices"\n'
        f'}}'
    )
    return system, prompt


def _mdc_to_glyphs(mdc_text: str) -> list[dict]:
    """Convert MdC transliteration string to glyph list using greedy matching."""
    _build_reverse_map()

    # Strip MdC formatting characters: cartouches <>, damaged [], groups {}, etc.
    cleaned = re.sub(r'[<>\[\]{}()^"\'\\]', '', mdc_text)
    # Treat / and digits as separators (register marks, numbering)
    cleaned = re.sub(r'[/0-9]+', ' ', cleaned)

    result: list[dict] = []
    for part in cleaned.replace("-", " ").replace("=", " ").split():
        remaining = part
        while remaining:
            matched = False
            # Skip leading dots (suffix pronoun markers: .f, .s, .sn, .k, .j)
            if remaining.startswith("."):
                remaining = remaining[1:]
                continue
            for translit, sign in _TRANSLIT_TO_SIGN:
                if remaining.startswith(translit):
                    result.append({
                        "type": "glyph",
                        "code": sign.code,
                        "transliteration": sign.transliteration,
                        "unicode_char": sign.unicode_char,
                        "description": sign.description,
                        "verified": True,
                    })
                    remaining = remaining[len(translit):]
                    matched = True
                    break
            if not matched:
                for translit, sign in _TRANSLIT_TO_SIGN:
                    if remaining.lower().startswith(translit):
                        result.append({
                            "type": "glyph",
                            "code": sign.code,
                            "transliteration": sign.transliteration,
                            "unicode_char": sign.unicode_char,
                            "description": sign.description,
                            "verified": True,
                        })
                        remaining = remaining[len(translit):]
                        matched = True
                        break
            if not matched:
                result.append({"type": "unknown", "display": remaining[0]})
                remaining = remaining[1:]
        result.append({"type": "separator", "display": " "})

    if result and result[-1].get("type") == "separator":
        result.pop()
    return result


def _validate_ai_glyphs(glyphs: list[dict]) -> list[dict]:
    """Validate AI-returned Gardiner codes against our known sign list."""
    validated = []
    for g in glyphs:
        code = g.get("code", "")
        sign = GARDINER_TRANSLITERATION.get(code)
        if sign:
            validated.append({
                "type": "glyph",
                "code": sign.code,
                "transliteration": sign.transliteration,
                "unicode_char": sign.unicode_char,
                "description": sign.description,
                "verified": True,
            })
        elif code and _GARDINER_RE.match(code):
            validated.append({
                "type": "glyph",
                "code": code,
                "transliteration": g.get("transliteration", ""),
                "unicode_char": "",
                "description": g.get("description", ""),
                "verified": False,
            })
    return validated


async def _ai_translate_to_hieroglyphs(request: Request, text: str) -> tuple[list[dict], str]:
    """Use AI (Gemini→Groq→Grok fallback) to translate text into hieroglyphs.

    Returns (glyph_list, provider_name). AI returns MdC which we parse into signs.
    """
    ai_service = getattr(request.app.state, "ai_service", None)
    if not ai_service:
        return [], "none"

    system, prompt = _build_smart_prompt(text)

    try:
        data, provider = await ai_service.text_json(
            system=system, prompt=prompt, max_tokens=1024,
        )
        if not data:
            return [], "none"

        mdc_str = data.get("mdc", "")
        if mdc_str:
            glyphs = _mdc_to_glyphs(mdc_str)
            if glyphs:
                return glyphs, provider

        ai_glyphs = data.get("glyphs", [])
        if ai_glyphs:
            validated = _validate_ai_glyphs(ai_glyphs)
            if validated:
                return validated, provider

        return [], provider
    except Exception:
        logger.warning("AI hieroglyph translation failed", exc_info=True)
        return [], "none"


@router.post("")
@limiter.limit("30/minute")
async def convert_text(req: WriteRequest, request: Request):
    """Convert text to hieroglyphic sequence.

    Modes:
    - alpha: Map each English letter to its closest uniliteral sign
    - mdc: Parse Manuel de Codage transliteration and find matching signs
    - smart: AI-powered translation (shortcuts → MdC detect → AI → fallback)
    """
    _build_reverse_map()
    _build_alpha_map()

    text = req.text.strip()
    result_glyphs: list[dict] = []
    provider = "local"

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
        result_glyphs = _mdc_to_glyphs(text)

    elif req.mode == "smart":
        # Step 1: Check known phrase shortcuts (instant, guaranteed correct)
        shortcut_mdc = _SHORTCUTS.get(text.lower().strip())
        if shortcut_mdc:
            result_glyphs = _mdc_to_glyphs(shortcut_mdc)
            provider = "shortcut"

        # Step 2: If input looks like MdC, parse directly
        elif _is_mdc_input(text):
            result_glyphs = _mdc_to_glyphs(text)
            provider = "mdc_detect"

        # Step 3: Call AI with fallback chain
        else:
            ai_glyphs, provider = await _ai_translate_to_hieroglyphs(request, text)
            if ai_glyphs:
                result_glyphs = ai_glyphs
            else:
                # Final fallback: alpha mode (letter-by-letter)
                provider = "alpha_fallback"
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
        "provider": provider,
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
