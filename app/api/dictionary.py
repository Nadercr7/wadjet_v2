"""Dictionary API — Gardiner sign lookup, search, categories, lessons.

GET /api/dictionary              — All signs (with ?category=, ?search=, ?type=, ?page=, ?per_page=)
GET /api/dictionary/categories   — Category list with counts
GET /api/dictionary/alphabet     — 25 uniliteral signs in teaching order
GET /api/dictionary/lesson/{n}   — Progressive lesson (1=alphabet … 5=determinatives)
GET /api/dictionary/{code}       — Single sign by Gardiner code
"""

from __future__ import annotations

import io
import re
import struct
from collections import OrderedDict
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from app.core.gardiner import (
    GARDINER_TRANSLITERATION,
    GardinerSign,
    SignType,
)
from app.rate_limit import limiter

router = APIRouter(prefix="/api/dictionary", tags=["dictionary"])

# ═══════════════════════════════════════════════════════════════
# Reference data
# ═══════════════════════════════════════════════════════════════

CATEGORY_NAMES: dict[str, str] = {
    "A": "Man and his Activities",
    "B": "Woman and her Activities",
    "C": "Anthropomorphic Deities",
    "D": "Parts of the Human Body",
    "E": "Mammals",
    "F": "Parts of Mammals",
    "G": "Birds",
    "H": "Parts of Birds",
    "I": "Amphibians & Reptiles",
    "K": "Fish & Parts of Fish",
    "L": "Invertebrates & Lesser Animals",
    "M": "Trees & Plants",
    "N": "Sky, Earth, Water",
    "O": "Buildings & Parts of Buildings",
    "P": "Ships & Parts of Ships",
    "Q": "Domestic & Funerary Furniture",
    "R": "Temple Furniture & Sacred Emblems",
    "S": "Crowns, Dress, Staves",
    "T": "Warfare, Hunting, Butchery",
    "U": "Agriculture, Crafts, Professions",
    "V": "Rope, Fibre, Baskets, Bags",
    "W": "Vessels (Stone & Earthenware)",
    "X": "Loaves & Cakes",
    "Y": "Writings, Games, Music",
    "Z": "Strokes & Geometric Figures",
    "Aa": "Unclassified",
}

CATEGORY_NAMES_AR: dict[str, str] = {
    "A": "الإنسان وأنشطته",
    "B": "المرأة وأنشطتها",
    "C": "الآلهة المجسّمة",
    "D": "أجزاء جسم الإنسان",
    "E": "الثدييات",
    "F": "أجزاء الثدييات",
    "G": "الطيور",
    "H": "أجزاء الطيور",
    "I": "البرمائيات والزواحف",
    "K": "الأسماك وأجزاؤها",
    "L": "اللافقاريات والحيوانات الصغيرة",
    "M": "الأشجار والنباتات",
    "N": "السماء والأرض والماء",
    "O": "المباني وأجزاؤها",
    "P": "السفن وأجزاؤها",
    "Q": "الأثاث المنزلي والجنائزي",
    "R": "أثاث المعبد والرموز المقدسة",
    "S": "التيجان والملابس والصولجانات",
    "T": "الحرب والصيد والذبح",
    "U": "الزراعة والحِرَف والمهن",
    "V": "الحبال والألياف والسلال",
    "W": "الأواني (حجرية وفخارية)",
    "X": "الأرغفة والكعك",
    "Y": "الكتابة والألعاب والموسيقى",
    "Z": "الخطوط والأشكال الهندسية",
    "Aa": "غير مصنّف",
}

TYPE_NAMES_AR: dict[str, str] = {
    "uniliteral": "أحادي",
    "biliteral": "ثنائي",
    "triliteral": "ثلاثي",
    "logogram": "لوغوغرام",
    "determinative": "مخصّص",
    "number": "رقم",
    "abbreviation": "اختصار",
}


def _get_category_name(code: str, lang: str = "en") -> str:
    """Get localized category name."""
    if lang == "ar":
        return CATEGORY_NAMES_AR.get(code, code)
    return CATEGORY_NAMES.get(code, code)


def _get_type_name(type_val: str, lang: str = "en") -> str:
    """Get localized type name."""
    if lang == "ar":
        return TYPE_NAMES_AR.get(type_val, type_val)
    return type_val

# Pronunciation guide for the 25 uniliteral sounds
_PRONUNCIATION_GUIDE: dict[str, tuple[str, str]] = {
    "A": ("glottal stop", "like the pause in 'uh-oh'"),
    "i": ("ee", "like 'ee' in 'see'"),
    "y": ("y", "like 'y' in 'yes'"),
    "a": ("ah", "like 'a' in 'father'"),
    "w": ("w / oo", "like 'w' in 'wet' or 'oo' in 'cool'"),
    "b": ("b", "like 'b' in 'boy'"),
    "p": ("p", "like 'p' in 'pet'"),
    "f": ("f", "like 'f' in 'fun'"),
    "m": ("m", "like 'm' in 'mom'"),
    "n": ("n", "like 'n' in 'net'"),
    "r": ("r", "like 'r' in 'run'"),
    "h": ("h", "like 'h' in 'hat'"),
    "H": ("emphatic h", "a forceful 'h' from the throat"),
    "x": ("kh", "like 'ch' in Scottish 'loch'"),
    "X": ("kh (soft)", "like German 'ich'"),
    "z": ("z", "like 'z' in 'zoo'"),
    "s": ("s", "like 's' in 'sun'"),
    "S": ("sh", "like 'sh' in 'ship'"),
    "q": ("q", "like 'k' but deeper in the throat"),
    "k": ("k", "like 'k' in 'king'"),
    "g": ("g", "like 'g' in 'go'"),
    "t": ("t", "like 't' in 'top'"),
    "T": ("ch", "like 'ch' in 'church'"),
    "d": ("d", "like 'd' in 'dog'"),
    "D": ("j", "like 'j' in 'jump'"),
}

_PRONUNCIATION_GUIDE_AR: dict[str, tuple[str, str]] = {
    "A": ("همزة", "مثل الهمزة في 'أحمد'"),
    "i": ("ي", "مثل الياء في 'يمين'"),
    "y": ("ي", "مثل الياء في 'يد'"),
    "a": ("ع", "مثل العين في 'عين'"),
    "w": ("و", "مثل الواو في 'ولد'"),
    "b": ("ب", "مثل الباء في 'باب'"),
    "p": ("پ", "صوت 'ب' بدون تفخيم — لا يوجد في العربية"),
    "f": ("ف", "مثل الفاء في 'فيل'"),
    "m": ("م", "مثل الميم في 'ماء'"),
    "n": ("ن", "مثل النون في 'نور'"),
    "r": ("ر", "مثل الراء في 'رمل'"),
    "h": ("هـ", "مثل الهاء في 'هرم'"),
    "H": ("ح", "مثل الحاء في 'حياة'"),
    "x": ("خ", "مثل الخاء في 'خير'"),
    "X": ("خ (خفيفة)", "مثل الخاء الخفيفة"),
    "z": ("ز", "مثل الزاي في 'زهرة'"),
    "s": ("س", "مثل السين في 'سماء'"),
    "S": ("ش", "مثل الشين في 'شمس'"),
    "q": ("ق", "مثل القاف في 'قمر'"),
    "k": ("ك", "مثل الكاف في 'كتاب'"),
    "g": ("ج", "مثل الجيم المصرية في 'جمل'"),
    "t": ("ت", "مثل التاء في 'تمر'"),
    "T": ("تش", "مثل 'تش' في 'تشاد'"),
    "d": ("د", "مثل الدال في 'دار'"),
    "D": ("ج", "مثل الجيم في 'جبل'"),
}

# Fun facts for important signs
_FUN_FACTS: dict[str, str] = {
    "G1": "The Egyptian vulture was so common in inscriptions that it became the default 'A' sound — appearing in royal names, religious texts, and everyday records alike.",
    "M17": "The single reed was one of the first signs ancient children learned. Two reeds together (M18) give the sound 'y'.",
    "D36": "The forearm was used in offering scenes — Egyptians extended the arm to present gifts to the gods. As a sign, it represents 'a' (ayin).",
    "D21": "The mouth sign is one of the most frequent hieroglyphs. As a logogram it means 'mouth' (rꜣ); as a phonogram it gives 'r'.",
    "S29": "The folded cloth represents the 's' sound. Laundry was a major activity in ancient Egypt — professional washermen were an actual occupation!",
    "N35": "Water ripples appear everywhere in Egyptian writing. The Nile was the source of all life, so it's fitting that its symbol became one of the most common sounds.",
    "G17": "The owl represents 'm' and is instantly recognizable. Owls were associated with darkness and the unseen in Egyptian culture.",
    "X1": "This humble bread loaf is the most frequently written hieroglyph of all — the 't' sound appears in almost every Egyptian word and grammatical ending.",
    "S34": "The ankh is the most universally recognized Egyptian symbol. Its origins are debated — theories range from a sandal strap to a mirror to a ceremonial knot.",
    "D10": "The Eye of Horus (wedjat) was believed to have healing powers. Each part of the eye represented a fraction used in measuring grain.",
    "L1": "The scarab beetle (Khepri) was sacred — Egyptians observed dung beetles rolling balls and connected it to the sun god rolling the sun across the sky.",
    "N5": "The sun disk was central to Egyptian religion — it represents Ra, the sun god, and appears in words meaning 'sun', 'day', and 'time'.",
    "N14": "Stars represented the concept of time and the afterlife. The ceiling of many tombs was painted as a starry sky.",
    "H6": "The ostrich feather represents Maat — truth, justice, and cosmic order. In the afterlife, your heart was weighed against this feather.",
    "G5": "The falcon was the embodiment of Horus, the sky god and protector of the pharaoh. Every king was considered a 'living Horus'.",
    "Q3": "This simple stool gives the 'p' sound. Furniture was a luxury in ancient Egypt — even basic stools indicated status.",
    "I9": "The horned viper was feared and respected. Despite being dangerous, its image became one of the alphabet's essential sounds: 'f'.",
    "D58": "The foot/leg sign gives 'b'. Walking was the primary means of travel for most Egyptians — only royals and officials rode in chariots.",
    "O1": "The house plan gives the sound 'pr'. Egyptian houses were built of mudbrick, and this bird's-eye view floor plan was the standard representation.",
    "V28": "The wick of twisted flax gives the sound 'H' (emphatic h). Flax was Egypt's most important plant fiber, used for linen clothing and lamp wicks.",
    "F34": "The heart was considered the seat of intelligence and emotion in ancient Egypt — not the brain, which was discarded during mummification.",
    "D54": "Walking legs appear at the end of words related to movement. This is a determinative — a silent 'category tag' that helps readers understand meaning.",
    "A1": "The seated man is the most common determinative in Egyptian writing. It appears after male names and words relating to men and people.",
    "G7": "A falcon on a standard marks words related to gods and divine things. When you see this at end of a word, you know it's about something sacred.",
    "N25": "Three hills on the horizon meant 'foreign land'. The Egyptians saw themselves at the center, with strange lands rising at the edges of the world.",
    "D4": "The eye sign gives the biliteral 'ir' and as a logogram means 'eye' or 'to do, make'. Cosmetic eye paint (kohl) was worn by all Egyptians for both beauty and protection from the sun.",
    "M23": "The sedge plant was the heraldic symbol of Upper Egypt. Combined with the bee (Lower Egypt), it formed the title 'King of Upper and Lower Egypt'.",
    "F35": "The heart-and-windpipe gives 'nfr' meaning 'beautiful, good, perfect'. The word 'Nefertiti' comes from this — 'the beautiful one has come'.",
    "D46": "The hand gives 'd'. Egyptian artists always drew the hand with visible fingers, making this one of the most recognizable body-part signs.",
    "V31": "The basket with handle gives 'k'. Baskets were essential tools in ancient Egypt — used for carrying everything from food to building materials.",
    "G43": "The quail chick gives 'w'. These small birds were abundant along the Nile and made a distinctive call that may have inspired the sound association.",
    "I10": "The cobra in repose gives the sound 'D' (like 'j' in 'jump'). The uraeus cobra on the pharaoh's crown was a symbol of royal authority.",
    "N37": "A pool of water gives the sound 'S' (like 'sh'). Ornamental pools were features of wealthy Egyptian gardens.",
    "W11": "The jar stand gives the sound 'g'. Pottery jars needed stable bases — this practical object became an everyday hieroglyph.",
    "O34": "The door bolt gives 'z' (also 's'). Egyptian doors used wooden bolts, and this mechanism was so familiar it became a common sign.",
    "V13": "The hobble rope gives 'T' (like 'ch'). Used to tether animals, this simple rope became associated with control and binding.",
    "Aa1": "This mysterious sign's original meaning is unknown — it may represent a placenta. Despite being 'unclassified', it's one of the 25 essential alphabet signs.",
    "F32": "Animal belly gives the sound 'X' (soft 'kh'). Butchery was depicted in almost every tomb — meat offerings were essential for the afterlife.",
    "N29": "The hillside slope gives the sound 'q'. Egypt's landscape alternated between flat floodplains and the desert hills that bordered the Nile valley.",
    "Z1": "A single stroke under a sign marks it as a logogram (the sign means the word it depicts). This is one of the most important reading aids in the script.",
    "Y1": "The papyrus roll was the Egyptian 'book'. Scribes trained for years to master hieroglyphs — literacy was a path to power and status.",
    "R4": "The offering loaf on a reed mat represents 'htp' (hotep) meaning 'peace, offering, satisfaction'. Names like 'Amenhotep' contain this word.",
    "S42": "The was-scepter represents 'wAs' (dominion, power). Gods and pharaohs were depicted holding this sign to show their authority.",
    "D28": "Two raised arms represent the 'ka' — one's spiritual double or life force. The ka was fed through offerings placed in tombs.",
    "G26": "The sacred ibis represents the ba-soul, the personality aspect of the spirit that could fly between the living world and the afterlife.",
    "O49": "The crossed streets inside a circle means 'city, town'. Egyptian cities grew up around temple complexes, which were the center of economic and religious life.",
    "M4": "The palm rib gives the triliteral 'rnp' and means 'year'. Egyptians notched palm ribs to count years — a living tally stick.",
    "Q7": "The brazier with flame gives 'snTr' (incense). Incense was burned in every temple ritual, believed to carry prayers to the gods.",
    "G14": "The vulture was a symbol of motherhood. The goddess Mut ('mother') was often depicted as a vulture, and the word for 'mother' (mwt) uses this sign.",
}

# ═══════════════════════════════════════════════════════════════
# Speech mapping — transliteration → approximate English phonemes
# ═══════════════════════════════════════════════════════════════

# Character-level mapping for auto-generating speech from any transliteration
# Each Egyptian consonant must have a DISTINCT sound for TTS differentiation
_PHONEME_MAP: dict[str, str] = {
    "A": "ah", "i": "ee", "y": "yah", "a": "aah", "w": "woo",
    "b": "bah", "p": "pah", "f": "fah", "m": "mah", "n": "nah",
    "r": "rah", "h": "hah", "H": "hhah", "x": "khah", "X": "kheh",
    "z": "zah", "s": "sah", "S": "shah", "q": "qah", "k": "kah",
    "g": "gah", "t": "tah", "T": "chah", "d": "dah", "D": "jah",
}

# Hand-curated overrides for common multi-consonant signs (better quality)
# Differentiate: H=emphatic h, x=velar kh, X=palatal kh, q=deep k, a=ayin, A=aleph
# NOTE: Values must be TTS-friendly — NO hyphens. Use spaces for syllable breaks.
_SPEECH_MAP: dict[str, str] = {
    "ir": "eer", "mn": "men", "pr": "per", "wr": "wer",
    "Htp": "hotep", "nfr": "nefer", "anx": "ankh",
    "wAs": "waas", "nTr": "netcher", "xpr": "kheper",
    "mAat": "maat", "rnp": "renep", "snTr": "sentcher",
    "wAst": "waast", "DHwty": "jehuti", "aA": "ah ah",
    "nb": "neb", "Dd": "djed", "mr": "mer", "kA": "kah",
    "bA": "baa", "ms": "mes", "sA": "saa", "wDAt": "wedjat",
    "stp": "setep", "Hr": "her", "sw": "soo",
    "km": "kem", "tp": "tep", "wn": "wen", "Sd": "shed",
    "sk": "sek", "xn": "khen", "xnt": "khent", "Ab": "ahb",
    "ix": "eekh", "im": "eem", "in": "een", "iw": "eeyoo",
    "ib": "eeb", "ip": "eep", "it": "eet", "is": "ees",
    "aH": "ah hha", "ai": "ah ee", "wa": "wah", "wi": "wee",
    "wp": "wep", "wD": "wedj",
    "bH": "beh hha", "pA": "pah", "pH": "peh hha", "pD": "pedj",
    "mH": "meh hha", "mi": "mee", "mw": "moo", "nw": "noo",
    "nn": "nen", "ni": "nee", "rw": "roo", "rd": "red",
    "hA": "hah", "Hm": "hhem", "HH": "hheh", "Hw": "hhoo",
    "xA": "khah", "Xn": "khen", "zA": "zah", "zS": "zesh",
    "sn": "sen", "st": "set", "Sw": "shoo", "Sm": "shem",
    "qd": "qed", "gs": "ges", "gm": "gem", "gb": "geb",
    "tA": "tah", "ti": "tee", "tm": "tem", "Tn": "chen",
    "di": "dee", "dw": "doo", "DA": "jaa", "Db": "jeb",
    # ── Lesson example & practice words ──
    # L1: alphabet words
    "r": "rah", "prt": "peret", "iwf": "eewef", "stt": "setet",
    "mnw": "menoo",
    # L2: biliteral words
    "irt": "eeret", "mntw": "montoo", "pri": "peree",
    "mniw": "meneeoo",
    # L3: triliteral words
    "xpri": "khepree", "nfrt": "neferet", "anxw": "ankhoo",
    # L4: logogram words
    "raanx": "rah ankh", "prnfr": "per nefer",
    # L5: determinative words
    "sx": "sekh", "nb tAwy": "neb tawy", "nTr ra": "netcher rah",
    # Common logograms
    "ra": "rah", "niwt": "neeyoot", "rxyt": "rekheet",
}


def _transliteration_to_speech(translit: str) -> str | None:
    """Convert any transliteration to approximate English phonemes.

    1. Try exact match in _SPEECH_MAP (hand-curated, best quality).
    2. Fall back to character-by-character mapping from _PHONEME_MAP.
    Output is always TTS-friendly (no hyphens — uses spaces).
    """
    if not translit:
        return None
    # Exact curated match
    exact = _SPEECH_MAP.get(translit)
    if exact:
        return exact
    # Also check uniliteral in curated map
    if translit in _PHONEME_MAP:
        return _PHONEME_MAP[translit]
    # Auto-generate: map each character, join with spaces (TTS-friendly)
    parts = []
    for ch in translit:
        phoneme = _PHONEME_MAP.get(ch)
        if phoneme:
            parts.append(phoneme)
    return " ".join(parts) if parts else None


def _word_to_speech(translit: str) -> str | None:
    """Convert a word transliteration (possibly hyphenated/spaced) to speech text.

    Handles lesson-style transliterations like "m-n-w", "mn-t-w", "ra-anx",
    "nTr ra" by:
      1. Try the full string (stripped of hyphens) in _SPEECH_MAP.
      2. Split on hyphens/spaces and resolve each segment.
      3. Fall back to _transliteration_to_speech() per segment.
    Output never contains hyphens (TTS-hostile).
    """
    if not translit:
        return None
    # 1. Strip hyphens → try exact match (covers "m-n-w" → "mnw" → "menoo")
    stripped = translit.replace("-", "")
    exact = _SPEECH_MAP.get(stripped)
    if exact:
        return exact
    # Also try the raw string (handles "nb tAwy" etc.)
    exact = _SPEECH_MAP.get(translit)
    if exact:
        return exact
    # 2. Split on spaces first, then resolve each space-segment
    space_parts = translit.split()
    if len(space_parts) > 1:
        resolved = []
        for sp in space_parts:
            r = _word_to_speech(sp)
            if r:
                resolved.append(r)
        return " ".join(resolved) if resolved else _transliteration_to_speech(stripped)
    # 3. Split on hyphens, resolve each segment
    segments = translit.split("-")
    if len(segments) > 1:
        resolved = []
        for seg in segments:
            r = _SPEECH_MAP.get(seg) or _transliteration_to_speech(seg)
            if r:
                resolved.append(r)
        return " ".join(resolved) if resolved else _transliteration_to_speech(stripped)
    # 4. Single segment fallback
    return _transliteration_to_speech(translit)

# ═══════════════════════════════════════════════════════════════
# Example words — 5 per lesson, with sign sequences and highlights
# ═══════════════════════════════════════════════════════════════

_EXAMPLE_WORDS: dict[int, list[dict]] = {
    1: [
        {
            "hieroglyphs": "𓂋𓏤",
            "codes": ["D21", "Z1"],
            "transliteration": "r",
            "translation": {"en": "mouth", "ar": "فم"},
            "highlight_codes": ["D21"],
        },
        {
            "hieroglyphs": "𓊪𓂋𓏏𓉐",
            "codes": ["Q3", "D21", "X1", "O1"],
            "transliteration": "p-r-t",
            "translation": {"en": "to go out", "ar": "يخرج"},
            "highlight_codes": ["Q3", "D21", "X1"],
        },
        {
            "hieroglyphs": "𓅓𓈖",
            "codes": ["G17", "N35"],
            "transliteration": "m-n",
            "translation": {"en": "to remain, endure", "ar": "يبقى، يدوم"},
            "highlight_codes": ["G17", "N35"],
        },
        {
            "hieroglyphs": "𓊃𓈖",
            "codes": ["S29", "N35"],
            "transliteration": "s-n",
            "translation": {"en": "brother", "ar": "أخ"},
            "highlight_codes": ["S29", "N35"],
        },
        {
            "hieroglyphs": "𓇋𓅱𓆑",
            "codes": ["M17", "G43", "I9"],
            "transliteration": "i-w-f",
            "translation": {"en": "flesh, meat", "ar": "لحم"},
            "highlight_codes": ["M17", "G43", "I9"],
        },
    ],
    2: [
        {
            "hieroglyphs": "𓇋𓂋𓏏",
            "codes": ["M17", "D21", "X1"],
            "transliteration": "ir-t",
            "translation": {"en": "eye", "ar": "عين"},
            "highlight_codes": ["D4"],
        },
        {
            "hieroglyphs": "𓅓𓈖𓏏𓅱",
            "codes": ["G17", "N35", "X1", "G43"],
            "transliteration": "mn-t-w",
            "translation": {"en": "Montu (war god)", "ar": "مونتو (إله الحرب)"},
            "highlight_codes": ["G17", "N35"],
        },
        {
            "hieroglyphs": "𓊪𓂋𓏤",
            "codes": ["Q3", "D21", "Z1"],
            "transliteration": "pr",
            "translation": {"en": "house", "ar": "بيت"},
            "highlight_codes": ["O1"],
        },
        {
            "hieroglyphs": "𓅱𓂋",
            "codes": ["G43", "D21"],
            "transliteration": "wr",
            "translation": {"en": "great, chief", "ar": "عظيم، رئيس"},
            "highlight_codes": ["G43", "D21"],
        },
        {
            "hieroglyphs": "𓎡𓏤",
            "codes": ["V31", "Z1"],
            "transliteration": "kA",
            "translation": {"en": "ka (spirit double)", "ar": "كا (الروح المزدوجة)"},
            "highlight_codes": ["D28"],
        },
    ],
    3: [
        {
            "hieroglyphs": "𓋹𓈖𓐍",
            "codes": ["S34", "N35", "Aa1"],
            "transliteration": "anx",
            "translation": {"en": "life, to live", "ar": "حياة، يعيش"},
            "highlight_codes": ["S34"],
        },
        {
            "hieroglyphs": "𓄤𓆑𓂋",
            "codes": ["F35", "I9", "D21"],
            "transliteration": "nfr",
            "translation": {"en": "beautiful, good, perfect", "ar": "جميل، طيب، كامل"},
            "highlight_codes": ["F35"],
        },
        {
            "hieroglyphs": "𓆣𓂋𓇋",
            "codes": ["L1", "D21", "M17"],
            "transliteration": "xpr-i",
            "translation": {"en": "to come into being", "ar": "يأتي إلى الوجود"},
            "highlight_codes": ["L1"],
        },
        {
            "hieroglyphs": "𓊵𓏏𓊪",
            "codes": ["R4", "X1", "Q3"],
            "transliteration": "Htp",
            "translation": {"en": "peace, offering, to be content", "ar": "سلام، قربان، رضا"},
            "highlight_codes": ["R4"],
        },
        {
            "hieroglyphs": "𓌳𓁹𓏏",
            "codes": ["U1", "D4", "X1"],
            "transliteration": "mAat",
            "translation": {"en": "truth, justice, cosmic order", "ar": "حقيقة، عدالة، نظام كوني"},
            "highlight_codes": ["H6"],
        },
    ],
    4: [
        {
            "hieroglyphs": "𓇳𓏤",
            "codes": ["N5", "Z1"],
            "transliteration": "ra",
            "translation": {"en": "sun, Ra (the sun god)", "ar": "شمس، رع (إله الشمس)"},
            "highlight_codes": ["N5"],
        },
        {
            "hieroglyphs": "𓉐𓏤",
            "codes": ["O1", "Z1"],
            "transliteration": "pr",
            "translation": {"en": "house", "ar": "بيت"},
            "highlight_codes": ["O1"],
        },
        {
            "hieroglyphs": "𓋹𓏤",
            "codes": ["S34", "Z1"],
            "transliteration": "anx",
            "translation": {"en": "life", "ar": "حياة"},
            "highlight_codes": ["S34"],
        },
        {
            "hieroglyphs": "𓌻𓏤",
            "codes": ["U35", "Z1"],
            "transliteration": "wAs",
            "translation": {"en": "dominion, power", "ar": "سيادة، قوة"},
            "highlight_codes": ["S42"],
        },
        {
            "hieroglyphs": "𓊹𓏤",
            "codes": ["R8", "Z1"],
            "transliteration": "nTr",
            "translation": {"en": "god, divine", "ar": "إله، إلهي"},
            "highlight_codes": ["R8"],
        },
    ],
    5: [
        {
            "hieroglyphs": "𓋴𓈖𓀀",
            "codes": ["S29", "N35", "A1"],
            "transliteration": "sn",
            "translation": {"en": "brother (male person)", "ar": "أخ (شخص ذكر)"},
            "highlight_codes": ["A1"],
        },
        {
            "hieroglyphs": "𓊪𓂋𓏏𓂻",
            "codes": ["Q3", "D21", "X1", "D54"],
            "transliteration": "prt",
            "translation": {"en": "to go out (with motion)", "ar": "يخرج (مع حركة)"},
            "highlight_codes": ["D54"],
        },
        {
            "hieroglyphs": "𓊃𓐍𓏛",
            "codes": ["S29", "Aa1", "Y1"],
            "transliteration": "sx",
            "translation": {"en": "writing, document (abstract)", "ar": "كتابة، وثيقة (مجرد)"},
            "highlight_codes": ["Y1"],
        },
        {
            "hieroglyphs": "𓇋𓅱𓀁",
            "codes": ["M17", "G43", "A2"],
            "transliteration": "iw",
            "translation": {"en": "to say (speech act)", "ar": "يقول (فعل كلام)"},
            "highlight_codes": ["A2"],
        },
        {
            "hieroglyphs": "𓎟𓇿𓇿",
            "codes": ["V30", "N16", "N16"],
            "transliteration": "nb tAwy",
            "translation": {"en": "lord of the Two Lands", "ar": "سيد الأرضين"},
            "highlight_codes": ["O49"],
        },
    ],
}

_PRACTICE_WORDS: dict[int, list[dict]] = {
    1: [
        {
            "hieroglyphs": "𓅓𓈖𓅱",
            "transliteration": "m-n-w",
            "translation": {"en": "Minu (the god Min)", "ar": "مينو (الإله مين)"},
            "hint": {"en": "Sound out each sign: m + n + w", "ar": "انطق كل علامة: م + ن + و"},
        },
        {
            "hieroglyphs": "𓊃𓏏𓏏",
            "transliteration": "s-t-t",
            "translation": {"en": "to shoot (an arrow)", "ar": "يطلق (سهمًا)"},
            "hint": {"en": "Three consonants: s + t + t", "ar": "ثلاثة حروف ساكنة: س + ت + ت"},
        },
    ],
    2: [
        {
            "hieroglyphs": "𓅓𓈖𓇋𓅱",
            "transliteration": "mn-i-w",
            "translation": {"en": "herdsman", "ar": "راعي الماشية"},
            "hint": {"en": "mn is a biliteral + alphabet signs", "ar": "من هي ثنائية + علامات أبجدية"},
        },
        {
            "hieroglyphs": "𓊪𓂋𓇋",
            "transliteration": "pr-i",
            "translation": {"en": "to go forth", "ar": "يمضي قُدمًا"},
            "hint": {"en": "pr is a biliteral + complement", "ar": "بر هي ثنائية + مكمّل"},
        },
    ],
    3: [
        {
            "hieroglyphs": "𓄤𓆑𓂋𓏏",
            "transliteration": "nfr-t",
            "translation": {"en": "beautiful woman (Nefret)", "ar": "المرأة الجميلة (نفرت)"},
            "hint": {"en": "nfr is a triliteral + feminine ending t", "ar": "نفر هي ثلاثية + نهاية مؤنثة ت"},
        },
        {
            "hieroglyphs": "𓋹𓈖𓐍𓅱",
            "transliteration": "anx-w",
            "translation": {"en": "may he live!", "ar": "عاش! (ليحيا)"},
            "hint": {"en": "anx is a triliteral + w ending", "ar": "عنخ هي ثلاثية + نهاية و"},
        },
    ],
    4: [
        {
            "hieroglyphs": "𓇳𓏤𓋹𓏤",
            "transliteration": "ra-anx",
            "translation": {"en": "Ra lives", "ar": "رع يعيش"},
            "hint": {"en": "Two logograms — each has the stroke marker 𓏤", "ar": "لوغوغرامان — كل واحد له علامة الخط 𓏤"},
        },
        {
            "hieroglyphs": "𓉐𓄤",
            "transliteration": "pr-nfr",
            "translation": {"en": "beautiful house", "ar": "البيت الجميل"},
            "hint": {"en": "Logogram + triliteral", "ar": "لوغوغرام + ثلاثية"},
        },
    ],
    5: [
        {
            "hieroglyphs": "𓋴𓏏𓀁",
            "transliteration": "st",
            "translation": {"en": "she (with female + speech determinative)", "ar": "هي (مع مخصّص المؤنث + الكلام)"},
            "hint": {"en": "s + t are phonetic — A2 at the end is SILENT", "ar": "س + ت صوتية — A2 في النهاية صامتة"},
        },
        {
            "hieroglyphs": "𓊹𓇳𓀭",
            "transliteration": "nTr ra",
            "translation": {"en": "the sun god (with deity determinative)", "ar": "إله الشمس (مع مخصّص الإله)"},
            "hint": {"en": "Look for the seated god at the end — it adds no sound", "ar": "ابحث عن الإله الجالس في النهاية — لا يضيف صوتًا"},
        },
    ],
}

# Teaching-order alphabet (traditional Egyptological sequence)
_ALPHABET_CODES = [
    "G1", "M17", "M18", "D36", "G43", "D58", "Q3", "I9",
    "G17", "N35", "D21", "O4", "V28", "Aa1", "F32", "S29",
    "O34", "N37", "N29", "V31", "W11", "X1", "V13", "D46", "I10",
]

_COMMON_BILITERALS = [
    "D4", "D28", "D33", "D34", "D37", "D39", "D52", "D56",
    "E34", "F4", "F13", "F16", "F18", "F22", "F26", "F30",
    "F31", "F34", "F40", "G10", "G21", "G25", "G26", "G29",
    "G35", "G36", "G39", "G40", "M1", "M3", "M8", "M12",
    "M16", "M20", "M23", "M40", "M42", "M44", "N1", "N18",
    "N26", "N29", "N36", "N41", "O1", "O11", "O29", "Q1",
    "T21", "T22", "T30", "U1", "U7", "U15", "U28", "U33",
    "V4", "V6", "V16", "V22", "V24", "V30", "W14", "W19",
    "W22", "W24", "X8", "Y3", "Y5",
]

_COMMON_TRILITERALS = [
    "D10", "D19", "D60", "E9", "E17", "E23", "F9", "F12",
    "F21", "F23", "F29", "F35", "G4", "G14", "G37", "G50",
    "H6", "I5", "L1", "M4", "M26", "M29", "M41", "N14",
    "N24", "N25", "N30", "N31", "O28", "O31", "O50", "P6",
    "P8", "Q7", "R4", "R8", "S24", "S28", "S34", "S42",
    "T14", "T20", "T28", "U35", "V7", "V25", "W15", "W18",
    "W25", "X6", "Y1", "Y2", "Z11",
]

# Curated common logograms (signs that represent whole words)
_COMMON_LOGOGRAMS = [
    "N5", "N14", "N16", "N25", "N26", "N29", "N31",  # sun, star, land, foreign, mountain, water, road
    "O1", "O49",  # house, city
    "D1", "D2", "D4",  # head, face, eye
    "D28",  # ka (spirit)
    "E1",  # bull
    "F34",  # heart
    "G5", "G14",  # Horus, vulture (mother)
    "H6",  # feather (Maat)
    "L1",  # scarab (Khepri)
    "M1", "M4", "M23",  # tree, palm-rib (year), plant (King)
    "O11",  # palace
    "Q1",  # throne
    "R4", "R8",  # altar (offering), flag (god)
    "S34", "S42",  # ankh (life), was-scepter
    "V30",  # basket (lord)
    "X6", "X8",  # cake, loaf (to give)
    "Y3", "Y5",  # scribe palette, senet board
    "Z1",  # stroke (ideogram marker)
    "D10",  # Eye of Horus
    "F35",  # heart+windpipe (beautiful)
    "N24",  # nome/district
    "Q7",  # brazier (incense)
]

# Curated common determinatives (silent classifiers) — the 30 most important
_COMMON_DETERMINATIVES = [
    "A1",   # seated man → male person
    "A2",   # man with hand to mouth → eat, drink, speak
    "A7",   # fatigued man → weary, weak
    "A14",  # falling man → enemy, death
    "A24",  # man striking → force, effort
    "A28",  # man with raised arms → joy, mourning
    "A40",  # seated god → god, king
    "A55",  # mummy → death, burial
    "B1",   # seated woman → female person
    "D54",  # walking legs → motion, travel
    "D55",  # legs walking backward → retreat, return
    "E1",   # bull → cattle
    "F51",  # piece of flesh → body parts, meat
    "G7",   # falcon on standard → god, divine
    "G37",  # sparrow → small, bad, weak
    "M2",   # plant/herb → plants, vegetation
    "N1",   # sky → sky, above
    "N2",   # sky with rain → storm, weather
    "N5",   # sun disk → sun, time, day
    "N23",  # irrigation canal → canal, garden
    "N33",  # grain → grain, mineral
    "O1",   # house plan → building, place
    "O49",  # town → city, inhabited place
    "T14",  # throwstick → foreign, enemy
    "V1",   # coil of rope → rope, actions
    "W24",  # bowl → vessel, drink
    "Y1",   # papyrus roll → writing, abstract idea
    "Z2",   # three strokes → plural marker
    "Z3",   # three vertical strokes → plural
    "Z4",   # two diagonal strokes → dual marker
]

# Lesson content — intro paragraphs, tips, subtitles (bilingual)
_LESSON_CONTENT: dict[int, dict] = {
    1: {
        "title": {"en": "The Egyptian Alphabet", "ar": "الأبجدية المصرية"},
        "subtitle": {"en": "25 single-consonant signs", "ar": "٢٥ علامة أحادية الصوت"},
        "desc": {"en": "25 uniliteral signs — each represents one consonant sound.", "ar": "٢٥ علامة أحادية — كل واحدة تمثّل صوتًا ساكنًا واحدًا."},
        "intro": {
            "en": [
                "Ancient Egyptian hieroglyphs only wrote consonants — no vowels at all! These 25 signs are the building blocks of the entire writing system. Each one represents a single consonant sound.",
                "Modern Egyptologists add an 'e' between consonants to make words pronounceable. So the word 'nfr' (beautiful) is spoken as 'nefer', and 'Htp' (peace) becomes 'hotep'.",
                "Master these 25 signs and you can sound out any Egyptian word, letter by letter. They work just like an alphabet — which is fitting, since the Phoenician alphabet (ancestor of our own) was inspired by Egyptian hieroglyphs!",
            ],
            "ar": [
                "الهيروغليفية المصرية القديمة كانت تكتب الحروف الساكنة فقط — بدون حركات نهائيًا! هذه الـ ٢٥ علامة هي اللبنات الأساسية لنظام الكتابة بأكمله. كل علامة تمثّل صوتًا ساكنًا واحدًا.",
                "علماء المصريات الحديثون يضيفون حرف 'e' بين الحروف الساكنة لتسهيل النطق. فكلمة 'nfr' (جميل) تُنطق 'نِفِر'، و'Htp' (سلام) تصبح 'حوتب'.",
                "أتقن هذه الـ ٢٥ علامة وستتمكن من قراءة أي كلمة مصرية، حرفًا بحرف. إنها تعمل تمامًا كالأبجدية — وهذا منطقي، فالأبجدية الفينيقية (جدّة أبجديتنا) كانت مستوحاة من الهيروغليفية المصرية!",
            ],
        },
        "tip": {
            "en": "Try pronouncing 'nfr' (beautiful) as \"nefer\" — just add an 'e' between each consonant. That's how Egyptologists read hieroglyphs aloud!",
            "ar": "جرّب نطق 'nfr' (جميل) كـ \"نِفِر\" — فقط أضف حرف 'e' بين كل ساكنين. هكذا يقرأ علماء المصريات الهيروغليفية بصوت عالٍ!",
        },
    },
    2: {
        "title": {"en": "Common Biliterals", "ar": "الثنائيات الشائعة"},
        "subtitle": {"en": "Two-consonant signs", "ar": "علامات ذات صوتين ساكنين"},
        "desc": {"en": "Two-consonant signs used frequently in hieroglyphic writing.", "ar": "علامات ذات صوتين ساكنين تُستخدم بكثرة في الكتابة الهيروغليفية."},
        "intro": {
            "en": [
                "Biliterals pack two consonant sounds into a single sign. Instead of writing 'm' + 'n' as two separate signs, scribes could write one biliteral sign 'mn' — faster and more elegant.",
                "Ancient scribes often added a 'phonetic complement' after a biliteral — one of the alphabet signs repeating the last consonant. For example: 𓅓𓈖 = mn + n. The extra 'n' isn't pronounced again; it just confirms the reading.",
                "Think of biliterals as the common two-letter combinations of Egyptian. Once you recognize them, you'll read inscriptions much faster.",
            ],
            "ar": [
                "الثنائيات تجمع صوتين ساكنين في علامة واحدة. بدلًا من كتابة 'م' + 'ن' كعلامتين منفصلتين، كان الكتبة يكتبون علامة ثنائية واحدة 'من' — أسرع وأكثر أناقة.",
                "كان الكتبة القدماء يضيفون 'مكمّل صوتي' بعد الثنائية — واحدة من علامات الأبجدية تكرر الحرف الساكن الأخير. مثلًا: 𓅓𓈖 = من + ن. الـ 'ن' الإضافية لا تُنطق مرة أخرى؛ إنها فقط تؤكد القراءة.",
                "فكّر في الثنائيات كالمقاطع الشائعة ذات الحرفين في المصرية. بمجرد أن تتعرف عليها، ستقرأ النقوش بسرعة أكبر بكثير.",
            ],
        },
        "tip": {
            "en": "When you see a biliteral followed by one of its consonants repeated as an alphabet sign — that's a phonetic complement. It confirms the reading, not a new sound!",
            "ar": "عندما ترى ثنائية يتبعها أحد حروفها مكررًا كعلامة أبجدية — هذا مكمّل صوتي. إنه يؤكد القراءة، وليس صوتًا جديدًا!",
        },
    },
    3: {
        "title": {"en": "Common Triliterals", "ar": "الثلاثيات الشائعة"},
        "subtitle": {"en": "Three-consonant signs", "ar": "علامات ذات ثلاثة أصوات ساكنة"},
        "desc": {"en": "Three-consonant signs — each one packs an entire syllable.", "ar": "علامات ذات ثلاثة أصوات ساكنة — كل واحدة تتضمن مقطعًا كاملًا."},
        "intro": {
            "en": [
                "Triliterals are the powerhouses of Egyptian writing — one sign represents three consonants at once. Many of these signs depict the very thing they spell.",
                "The famous ankh (𓋹) is a triliteral for 'anx' — and it means 'life'. The nefer sign (𓄤) represents 'nfr' — 'beautiful, good, perfect'. The name Nefertiti literally means 'the beautiful one has come'.",
                "Like biliterals, triliterals are often followed by one or two phonetic complements. When you see 𓋹𓈖𓐍, that's ankh + n + kh — the last two signs just confirm the reading of the triliteral.",
            ],
            "ar": [
                "الثلاثيات هي القوة المحركة للكتابة المصرية — علامة واحدة تمثل ثلاثة أصوات ساكنة دفعة واحدة. كثير من هذه العلامات تصوّر الشيء الذي تكتبه بالضبط.",
                "العنخ الشهير (𓋹) هو ثلاثي لـ 'anx' — ومعناه 'حياة'. وعلامة النفر (𓄤) تمثل 'nfr' — 'جميل، طيب، كامل'. واسم نفرتيتي يعني حرفيًا 'الجميلة قد أتت'.",
                "مثل الثنائيات، غالبًا ما تُتبع الثلاثيات بمكمّل صوتي واحد أو اثنين. عندما ترى 𓋹𓈖𓐍، هذا عنخ + ن + خ — العلامتان الأخيرتان تؤكدان فقط قراءة الثلاثي.",
            ],
        },
        "tip": {
            "en": "Many triliterals depict the very word they spell — the ankh sign means 'life', the nefer sign means 'beautiful'. Look for the connection between the picture and the word!",
            "ar": "كثير من الثلاثيات تصوّر الكلمة التي تكتبها — علامة العنخ تعني 'حياة'، وعلامة النفر تعني 'جميل'. ابحث عن العلاقة بين الصورة والكلمة!",
        },
    },
    4: {
        "title": {"en": "Common Logograms", "ar": "اللوغوغرامات الشائعة"},
        "subtitle": {"en": "Signs that ARE the word", "ar": "علامات هي الكلمة نفسها"},
        "desc": {"en": "Logograms represent entire words — the sign IS the meaning.", "ar": "اللوغوغرامات تمثل كلمات كاملة — العلامة هي المعنى نفسه."},
        "intro": {
            "en": [
                "Some hieroglyphs skip phonetics entirely — the picture IS the word. A house plan (𓉐) means 'house' (pr). A sun disk (𓇳) means 'sun, day, Ra'. These are logograms (also called ideograms).",
                "How do you know when a sign is being used as a logogram rather than a phonogram? Ancient scribes added a single vertical stroke (𓏤) underneath to say 'read this sign as the word it depicts'.",
                "Most logograms pull double duty — they can also be used for their sound value in other words. Context tells you which reading to use. This flexibility is part of what makes hieroglyphs so rich.",
            ],
            "ar": [
                "بعض الهيروغليفية تتخطى الأصوات تمامًا — الصورة هي الكلمة. مخطط المنزل (𓉐) يعني 'بيت' (pr). قرص الشمس (𓇳) يعني 'شمس، يوم، رع'. هذه هي اللوغوغرامات (تُسمى أيضًا الأيديوغرامات).",
                "كيف تعرف أن العلامة تُستخدم كلوغوغرام وليس كصوت؟ الكتبة القدماء كانوا يضيفون خطًا عموديًا واحدًا (𓏤) تحتها ليقولوا 'اقرأ هذه العلامة ككلمة تصوّرها'.",
                "معظم اللوغوغرامات تعمل بشكل مزدوج — يمكن استخدامها أيضًا لقيمتها الصوتية في كلمات أخرى. السياق يخبرك أي قراءة تستخدم. هذه المرونة هي جزء مما يجعل الهيروغليفية غنية جدًا.",
            ],
        },
        "tip": {
            "en": "Look for the single stroke (𓏤) under a sign — it's the scribe's way of saying 'this sign means exactly what it shows!'",
            "ar": "ابحث عن الخط الواحد (𓏤) تحت العلامة — إنها طريقة الكاتب ليقول 'هذه العلامة تعني بالضبط ما تُظهره!'",
        },
    },
    5: {
        "title": {"en": "Determinatives", "ar": "المخصّصات"},
        "subtitle": {"en": "Silent classifiers at word endings", "ar": "مصنّفات صامتة في نهاية الكلمات"},
        "desc": {"en": "Determinatives are SILENT — they classify a word's meaning, not its sound.", "ar": "المخصّصات صامتة تمامًا — تصنّف معنى الكلمة، وليس صوتها."},
        "intro": {
            "en": [
                "Here's the key insight that explains why so many signs have no pronunciation: determinatives are completely SILENT. They appear at the end of a word to classify its meaning — like a visual category tag.",
                "Walking legs (𓂻) after a verb means it involves motion. A seated man (𓀀) after a name means it's a male person. A papyrus roll (𓏛) means the word is abstract or related to writing. A sun disk (𓇳) tells you the word relates to time or the sun god.",
                "Without determinatives, Egyptian would be deeply ambiguous — many words share the same consonants. The word 'pr' could mean 'house', 'go out', 'winter', or more. Only the determinative tells you which meaning is intended!",
            ],
            "ar": [
                "هذه هي النقطة الجوهرية التي تفسّر لماذا كثير من العلامات ليس لها نطق: المخصّصات صامتة تمامًا. تظهر في نهاية الكلمة لتصنّف معناها — مثل وسم تصنيف مرئي.",
                "أرجل تمشي (𓂻) بعد الفعل تعني أنه يتضمن حركة. رجل جالس (𓀀) بعد الاسم يعني أنه شخص ذكر. لفافة بردي (𓏛) تعني أن الكلمة مجردة أو متعلقة بالكتابة. قرص الشمس (𓇳) يخبرك أن الكلمة تتعلق بالوقت أو إله الشمس.",
                "بدون المخصّصات، ستكون المصرية غامضة جدًا — كثير من الكلمات تشترك في نفس الحروف الساكنة. كلمة 'pr' يمكن أن تعني 'بيت' أو 'يخرج' أو 'شتاء' أو غيرها. فقط المخصّص يخبرك أي معنى مقصود!",
            ],
        },
        "tip": {
            "en": "Think of determinatives as hashtags — they don't change the pronunciation, but they tell you what category the word belongs to. That's why ~80% of all Gardiner signs have no sound value!",
            "ar": "فكّر في المخصّصات كالهاشتاغات — لا تغيّر النطق، لكنها تخبرك بالفئة التي تنتمي إليها الكلمة. لهذا السبب ~٨٠٪ من علامات جاردنر ليس لها قيمة صوتية!",
        },
    },
}


# ═══════════════════════════════════════════════════════════════
# Serialization — type-aware, no duplicate fields
# ═══════════════════════════════════════════════════════════════

def _make_reading(sign: GardinerSign) -> str:
    """Human-friendly reading label that varies by sign type."""
    t = sign.sign_type
    if t in (SignType.UNILITERAL, SignType.BILITERAL, SignType.TRILITERAL):
        tr = sign.transliteration
        if not tr:
            return ""
        if t == SignType.UNILITERAL:
            pron = _PRONUNCIATION_GUIDE.get(tr)
            if pron:
                return f"Sounds like '{pron[0]}' — {pron[1]}"
            return f"Sounds like '{tr}'"
        # Bi/triliterals that also have a logographic meaning
        if sign.logographic_value:
            return f"Sounds like '{tr}' · Means: {sign.logographic_value}"
        return f"Sounds like '{tr}'"
    if t == SignType.LOGOGRAM:
        if sign.logographic_value:
            return f"Means: {sign.logographic_value}"
        return sign.description
    if t == SignType.DETERMINATIVE:
        if sign.determinative_class:
            return f"Classifier for: {sign.determinative_class}"
        return f"Classifier — {sign.description}"
    if t == SignType.NUMBER:
        return "Number sign"
    if t == SignType.ABBREVIATION:
        return "Abbreviation"
    return ""


def _sign_to_dict(sign: GardinerSign, lang: str = "en") -> dict:
    """Serialize a GardinerSign — type-aware, no duplicate fields."""
    t = sign.sign_type
    is_phonetic = t in (
        SignType.UNILITERAL, SignType.BILITERAL, SignType.TRILITERAL,
    )
    # Pronunciation guide for uniliterals
    pronunciation = None
    if t == SignType.UNILITERAL and sign.transliteration:
        guide = _PRONUNCIATION_GUIDE_AR if lang == "ar" else _PRONUNCIATION_GUIDE
        pron = guide.get(sign.transliteration)
        if pron:
            pronunciation = {"sound": pron[0], "example": pron[1]}

    # Speech text for SpeechSynthesis — any sign with a transliteration gets audio
    speech_text = _transliteration_to_speech(sign.transliteration) if sign.transliteration else None

    return {
        "code": sign.code,
        "transliteration": sign.transliteration,
        "type": t.value,
        "type_name": _get_type_name(t.value, lang),
        "description": sign.description,
        "category": sign.category,
        "category_name": _get_category_name(sign.category, lang),
        "reading": _make_reading(sign),
        "logographic_value": sign.logographic_value,
        "determinative_class": sign.determinative_class,
        "unicode_char": sign.unicode_char,
        "is_phonetic": is_phonetic,
        "pronunciation": pronunciation,
        "fun_fact": _FUN_FACTS.get(sign.code),
        "speech_text": speech_text,
    }


def _natural_sort_key(code: str) -> tuple:
    """Sort Gardiner codes naturally: A1, A2, ..., A10 (not A1, A10, A2)."""
    parts = re.match(r"([A-Za-z]+)(\d+)(.*)", code)
    if parts:
        return (parts.group(1), int(parts.group(2)), parts.group(3))
    return (code, 0, "")


# ═══════════════════════════════════════════════════════════════
# TTS — WAV helper + cached speak endpoint
# ═══════════════════════════════════════════════════════════════

def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Wrap raw PCM (L16) bytes in a WAV container."""
    buf = io.BytesIO()
    data_size = len(pcm_data)
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    # fmt sub-chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size
    buf.write(struct.pack("<H", 1))   # PCM format
    buf.write(struct.pack("<H", channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * channels * sample_width))  # byte rate
    buf.write(struct.pack("<H", channels * sample_width))  # block align
    buf.write(struct.pack("<H", sample_width * 8))  # bits per sample
    # data sub-chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm_data)
    return buf.getvalue()


@lru_cache(maxsize=256)
def _cached_speech_text(text: str) -> str:
    """Normalize text for cache key purposes."""
    return text.strip().lower()


# In-memory bounded LRU cache for generated audio (text -> WAV bytes)
_TTS_CACHE_MAXSIZE = 500
_tts_cache: OrderedDict[str, bytes] = OrderedDict()


@router.get("/speak")
@limiter.limit("30/minute")
async def speak(request: Request, text: str = Query(..., min_length=1, max_length=100)):
    """Generate natural TTS audio for a pronunciation string.

    Returns audio/wav. Uses Gemini TTS with in-memory caching.
    Falls back to 404 if AI service is unavailable.
    """
    cache_key = _cached_speech_text(text)

    # Return cached audio immediately
    if cache_key in _tts_cache:
        _tts_cache.move_to_end(cache_key)
        return Response(
            content=_tts_cache[cache_key],
            media_type="audio/wav",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # Try Gemini TTS
    gemini = getattr(request.app.state, "gemini", None)
    if gemini is None or not gemini.available:
        raise HTTPException(status_code=404, detail="TTS not available")

    pcm_data = await gemini.generate_tts(text)
    if not pcm_data:
        raise HTTPException(status_code=404, detail="TTS generation failed")

    wav_data = _pcm_to_wav(pcm_data)
    _tts_cache[cache_key] = wav_data
    _tts_cache.move_to_end(cache_key)
    while len(_tts_cache) > _TTS_CACHE_MAXSIZE:
        _tts_cache.popitem(last=False)

    return Response(
        content=wav_data,
        media_type="audio/wav",
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ═══════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/categories")
async def list_categories(lang: str = Query("en", description="Language code (en/ar)")):
    """List all Gardiner categories with sign counts."""
    counts: dict[str, int] = {}
    for sign in GARDINER_TRANSLITERATION.values():
        counts[sign.category] = counts.get(sign.category, 0) + 1

    categories = []
    for code in sorted(counts.keys(), key=lambda c: (len(c), c)):
        categories.append({
            "code": code,
            "name": _get_category_name(code, lang),
            "count": counts[code],
        })

    return JSONResponse(content={
        "categories": categories,
        "total_signs": len(GARDINER_TRANSLITERATION),
    })


@router.get("/alphabet")
async def get_alphabet(lang: str = Query("en", description="Language code (en/ar)")):
    """Return the 25 primary uniliteral signs in traditional teaching order."""
    signs = []
    for code in _ALPHABET_CODES:
        sign = GARDINER_TRANSLITERATION.get(code)
        if sign:
            signs.append(_sign_to_dict(sign, lang))
    return JSONResponse(content={"signs": signs, "count": len(signs)})


def _loc(val, lang: str = "en"):
    """Extract localized text from a bilingual dict or return string as-is."""
    if isinstance(val, dict):
        return val.get(lang, val.get("en", ""))
    return val


@router.get("/lesson/{level}")
async def get_lesson(level: int, lang: str = Query("en", description="Language code (en/ar)")):
    """Progressive lessons with teaching content."""
    content = _LESSON_CONTENT.get(level)
    if not content:
        raise HTTPException(status_code=404, detail="Lesson levels: 1-5")

    if level == 1:
        codes = _ALPHABET_CODES
    elif level == 2:
        codes = _COMMON_BILITERALS
    elif level == 3:
        codes = _COMMON_TRILITERALS
    elif level == 4:
        codes = _COMMON_LOGOGRAMS
    else:
        codes = _COMMON_DETERMINATIVES

    signs = []
    for code in codes:
        sign = GARDINER_TRANSLITERATION.get(code)
        if sign:
            signs.append(_sign_to_dict(sign, lang))

    # Next/prev lesson info
    prev_lesson = None
    next_lesson = None
    if level > 1:
        pc = _LESSON_CONTENT[level - 1]
        prev_lesson = {"level": level - 1, "title": _loc(pc["title"], lang)}
    if level < 5:
        nc = _LESSON_CONTENT[level + 1]
        next_lesson = {"level": level + 1, "title": _loc(nc["title"], lang)}

    # Localize example & practice words
    def _loc_words(words: list[dict]) -> list[dict]:
        out = []
        for w in words:
            lw = {**w}
            for k in ("translation", "hint"):
                if k in lw:
                    lw[k] = _loc(lw[k], lang)
            # Generate speech_text from transliteration (resolves hyphens)
            if "transliteration" in lw:
                lw["speech_text"] = _word_to_speech(lw["transliteration"])
            out.append(lw)
        return out

    return JSONResponse(content={
        "level": level,
        "title": _loc(content["title"], lang),
        "subtitle": _loc(content["subtitle"], lang),
        "description": _loc(content["desc"], lang),
        "intro_paragraphs": _loc(content["intro"], lang),
        "tip": _loc(content["tip"], lang),
        "prev_lesson": prev_lesson,
        "next_lesson": next_lesson,
        "total_lessons": 5,
        "signs": signs,
        "count": len(signs),
        "example_words": _loc_words(_EXAMPLE_WORDS.get(level, [])),
        "practice_words": _loc_words(_PRACTICE_WORDS.get(level, [])),
    })


# ── Enrichment helpers (Used-in / See-also) for single-sign detail ──

def _build_usage_index() -> dict[str, list[dict]]:
    """Build code → [{hieroglyphs, transliteration, translation}] from _EXAMPLE_WORDS."""
    idx: dict[str, list[dict]] = {}
    for words in _EXAMPLE_WORDS.values():
        for w in words:
            entry = {
                "hieroglyphs": w["hieroglyphs"],
                "transliteration": w["transliteration"],
                "translation": w["translation"],
            }
            for code in w["codes"]:
                idx.setdefault(code, []).append(entry)
    return idx


_USAGE_INDEX: dict[str, list[dict]] = _build_usage_index()


def _find_related_signs(sign: GardinerSign, limit: int = 4) -> list[dict]:
    """Find related signs: same category, different code, prioritising same type."""
    candidates = [
        s for s in GARDINER_TRANSLITERATION.values()
        if s.category == sign.category and s.code != sign.code
    ]
    # Prioritise same sign type, then by natural sort proximity
    same_type = [s for s in candidates if s.sign_type == sign.sign_type]
    other_type = [s for s in candidates if s.sign_type != sign.sign_type]
    pool = same_type[:limit] if len(same_type) >= limit else same_type + other_type
    pool = pool[:limit]
    return [
        {
            "code": s.code,
            "unicode_char": s.unicode_char,
            "transliteration": s.transliteration,
            "reading": _make_reading(s),
            "type": s.sign_type.value,
        }
        for s in pool
    ]


@router.get("/{code}")
async def get_sign(code: str, lang: str = Query("en", description="Language code (en/ar)")):
    """Get a single sign by Gardiner code — enriched with usages & related signs."""
    sign = GARDINER_TRANSLITERATION.get(code)
    if not sign:
        raise HTTPException(status_code=404, detail=f"Sign '{code}' not found")
    data = _sign_to_dict(sign, lang)
    # Deduplicate usages (same word may appear from multiple codes)
    seen = set()
    usages = []
    for u in _USAGE_INDEX.get(code, []):
        key = u["transliteration"]
        if key not in seen:
            seen.add(key)
            usages.append(u)
    data["example_usages"] = usages[:5]
    data["related_signs"] = _find_related_signs(sign)
    return JSONResponse(content=data)


@router.get("")
async def list_signs(
    category: str | None = Query(None, description="Filter by Gardiner category (A-Z, Aa)"),
    search: str | None = Query(None, description="Search in code, transliteration, description"),
    sign_type: str | None = Query(None, alias="type", description="Filter by sign type"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(50, ge=1, le=200, description="Signs per page"),
    lang: str = Query("en", description="Language code (en/ar)"),
):
    """List all signs with filtering and pagination."""
    signs = list(GARDINER_TRANSLITERATION.values())

    if category:
        signs = [s for s in signs if s.category == category]

    if sign_type:
        try:
            st = SignType(sign_type)
            signs = [s for s in signs if s.sign_type == st]
        except ValueError:
            valid = [t.value for t in SignType]
            raise HTTPException(status_code=400, detail=f"Invalid type. Valid: {valid}") from None

    if search:
        q = search.lower()
        signs = [
            s for s in signs
            if q in s.code.lower()
            or q in s.transliteration.lower()
            or q in s.description.lower()
            or q in s.phonetic_value.lower()
            or q in (s.logographic_value or "").lower()
        ]

    signs.sort(key=lambda s: (len(s.category), s.category, _natural_sort_key(s.code)))

    total_filtered = len(signs)
    total_pages = max(1, (total_filtered + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    page_signs = signs[start:end]

    return JSONResponse(content={
        "signs": [_sign_to_dict(s, lang) for s in page_signs],
        "count": len(page_signs),
        "total": total_filtered,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    })
