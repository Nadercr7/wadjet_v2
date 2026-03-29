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
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from app.core.gardiner import (
    GARDINER_TRANSLITERATION,
    GardinerSign,
    SignType,
)

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
_SPEECH_MAP: dict[str, str] = {
    "ir": "eer", "mn": "men", "pr": "per", "wr": "wer",
    "Htp": "hotep", "nfr": "nefer", "anx": "ankh",
    "wAs": "waas", "nTr": "netcher", "xpr": "kheper",
    "mAat": "mah-aht", "rnp": "renep", "snTr": "sentcher",
    "wAst": "waast", "DHwty": "jehuti", "aA": "aah-ah",
    "nb": "neb", "Dd": "djed", "mr": "mer", "kA": "kah",
    "bA": "baa", "ms": "mes", "sA": "saa", "wDAt": "wedjat",
    "stp": "setep", "Hr": "her", "sw": "soo",
    "km": "kem", "tp": "tep", "wn": "wen", "Sd": "shed",
    "sk": "sek", "xn": "khen", "xnt": "khent", "Ab": "ahb",
    "ix": "eekh", "im": "eem", "in": "een", "iw": "ee-oo",
    "ib": "eeb", "ip": "eep", "it": "eet", "is": "ees",
    "aH": "aah-hha", "ai": "aah-ee", "wa": "wah", "wi": "wee",
    "wp": "wep", "wD": "wedj",
    "bH": "beh-hha", "pA": "pah", "pH": "peh-hha", "pD": "pedj",
    "mH": "meh-hha", "mi": "mee", "mw": "moo", "nw": "noo",
    "nn": "nen", "ni": "nee", "rw": "roo", "rd": "red",
    "hA": "hah", "Hm": "hhem", "HH": "hheh", "Hw": "hhoo",
    "xA": "khah", "Xn": "kheh-n", "zA": "zah", "zS": "zesh",
    "sn": "sen", "st": "set", "Sw": "shoo", "Sm": "shem",
    "qd": "qed", "gs": "ges", "gm": "gem", "gb": "geb",
    "tA": "tah", "ti": "tee", "tm": "tem", "Tn": "chen",
    "di": "dee", "dw": "doo", "DA": "jaa", "Db": "jeb",
    # Lesson words (multi-consonant words students encounter)
    "prt": "peret", "iwf": "ee-oo-ef", "stt": "setet",
    "mnw": "menoo", "mntw": "montoo", "pri": "peree",
    "sx": "sekh", "nfrt": "neferet", "anxw": "ankh-oo",
    "nb tAwy": "neb tawy", "xpri": "khepree",
    # Common logograms
    "ra": "rah", "niwt": "nee-oot", "rxyt": "rekh-eet",
}


def _transliteration_to_speech(translit: str) -> str | None:
    """Convert any transliteration to approximate English phonemes.

    1. Try exact match in _SPEECH_MAP (hand-curated, best quality).
    2. Fall back to character-by-character mapping from _PHONEME_MAP.
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
    # Auto-generate: map each character, join with hyphens
    parts = []
    for ch in translit:
        phoneme = _PHONEME_MAP.get(ch)
        if phoneme:
            parts.append(phoneme)
    return "-".join(parts) if parts else None

# ═══════════════════════════════════════════════════════════════
# Example words — 5 per lesson, with sign sequences and highlights
# ═══════════════════════════════════════════════════════════════

_EXAMPLE_WORDS: dict[int, list[dict]] = {
    1: [
        {
            "hieroglyphs": "𓂋𓏤",
            "codes": ["D21", "Z1"],
            "transliteration": "r",
            "translation": "mouth",
            "highlight_codes": ["D21"],
        },
        {
            "hieroglyphs": "𓊪𓂋𓏏𓉐",
            "codes": ["Q3", "D21", "X1", "O1"],
            "transliteration": "p-r-t",
            "translation": "to go out",
            "highlight_codes": ["Q3", "D21", "X1"],
        },
        {
            "hieroglyphs": "𓅓𓈖",
            "codes": ["G17", "N35"],
            "transliteration": "m-n",
            "translation": "to remain, endure",
            "highlight_codes": ["G17", "N35"],
        },
        {
            "hieroglyphs": "𓊃𓈖",
            "codes": ["S29", "N35"],
            "transliteration": "s-n",
            "translation": "brother",
            "highlight_codes": ["S29", "N35"],
        },
        {
            "hieroglyphs": "𓇋𓅱𓆑",
            "codes": ["M17", "G43", "I9"],
            "transliteration": "i-w-f",
            "translation": "flesh, meat",
            "highlight_codes": ["M17", "G43", "I9"],
        },
    ],
    2: [
        {
            "hieroglyphs": "𓇋𓂋𓏏",
            "codes": ["M17", "D21", "X1"],
            "transliteration": "ir-t",
            "translation": "eye",
            "highlight_codes": ["D4"],
        },
        {
            "hieroglyphs": "𓅓𓈖𓏏𓅱",
            "codes": ["G17", "N35", "X1", "G43"],
            "transliteration": "mn-t-w",
            "translation": "Montu (war god)",
            "highlight_codes": ["G17", "N35"],
        },
        {
            "hieroglyphs": "𓊪𓂋𓏤",
            "codes": ["Q3", "D21", "Z1"],
            "transliteration": "pr",
            "translation": "house",
            "highlight_codes": ["O1"],
        },
        {
            "hieroglyphs": "𓅱𓂋",
            "codes": ["G43", "D21"],
            "transliteration": "wr",
            "translation": "great, chief",
            "highlight_codes": ["G43", "D21"],
        },
        {
            "hieroglyphs": "𓎡𓏤",
            "codes": ["V31", "Z1"],
            "transliteration": "kA",
            "translation": "ka (spirit double)",
            "highlight_codes": ["D28"],
        },
    ],
    3: [
        {
            "hieroglyphs": "𓋹𓈖𓐍",
            "codes": ["S34", "N35", "Aa1"],
            "transliteration": "anx",
            "translation": "life, to live",
            "highlight_codes": ["S34"],
        },
        {
            "hieroglyphs": "𓄤𓆑𓂋",
            "codes": ["F35", "I9", "D21"],
            "transliteration": "nfr",
            "translation": "beautiful, good, perfect",
            "highlight_codes": ["F35"],
        },
        {
            "hieroglyphs": "𓆣𓂋𓇋",
            "codes": ["L1", "D21", "M17"],
            "transliteration": "xpr-i",
            "translation": "to come into being",
            "highlight_codes": ["L1"],
        },
        {
            "hieroglyphs": "𓊵𓏏𓊪",
            "codes": ["R4", "X1", "Q3"],
            "transliteration": "Htp",
            "translation": "peace, offering, to be content",
            "highlight_codes": ["R4"],
        },
        {
            "hieroglyphs": "𓌳𓁹𓏏",
            "codes": ["U1", "D4", "X1"],
            "transliteration": "mAat",
            "translation": "truth, justice, cosmic order",
            "highlight_codes": ["H6"],
        },
    ],
    4: [
        {
            "hieroglyphs": "𓇳𓏤",
            "codes": ["N5", "Z1"],
            "transliteration": "ra",
            "translation": "sun, Ra (the sun god)",
            "highlight_codes": ["N5"],
        },
        {
            "hieroglyphs": "𓉐𓏤",
            "codes": ["O1", "Z1"],
            "transliteration": "pr",
            "translation": "house",
            "highlight_codes": ["O1"],
        },
        {
            "hieroglyphs": "𓋹𓏤",
            "codes": ["S34", "Z1"],
            "transliteration": "anx",
            "translation": "life",
            "highlight_codes": ["S34"],
        },
        {
            "hieroglyphs": "𓌻𓏤",
            "codes": ["U35", "Z1"],
            "transliteration": "wAs",
            "translation": "dominion, power",
            "highlight_codes": ["S42"],
        },
        {
            "hieroglyphs": "𓊹𓏤",
            "codes": ["R8", "Z1"],
            "transliteration": "nTr",
            "translation": "god, divine",
            "highlight_codes": ["R8"],
        },
    ],
    5: [
        {
            "hieroglyphs": "𓋴𓈖𓀀",
            "codes": ["S29", "N35", "A1"],
            "transliteration": "sn",
            "translation": "brother (male person)",
            "highlight_codes": ["A1"],
        },
        {
            "hieroglyphs": "𓊪𓂋𓏏𓂻",
            "codes": ["Q3", "D21", "X1", "D54"],
            "transliteration": "prt",
            "translation": "to go out (with motion)",
            "highlight_codes": ["D54"],
        },
        {
            "hieroglyphs": "𓊃𓐍𓏛",
            "codes": ["S29", "Aa1", "Y1"],
            "transliteration": "sx",
            "translation": "writing, document (abstract)",
            "highlight_codes": ["Y1"],
        },
        {
            "hieroglyphs": "𓇋𓅱𓀁",
            "codes": ["M17", "G43", "A2"],
            "transliteration": "iw",
            "translation": "to say (speech act)",
            "highlight_codes": ["A2"],
        },
        {
            "hieroglyphs": "𓎟𓇿𓇿",
            "codes": ["V30", "N16", "N16"],
            "transliteration": "nb tAwy",
            "translation": "lord of the Two Lands",
            "highlight_codes": ["O49"],
        },
    ],
}

_PRACTICE_WORDS: dict[int, list[dict]] = {
    1: [
        {
            "hieroglyphs": "𓅓𓈖𓅱",
            "transliteration": "m-n-w",
            "translation": "Minu (the god Min)",
            "hint": "Sound out each sign: m + n + w",
        },
        {
            "hieroglyphs": "𓊃𓏏𓏏",
            "transliteration": "s-t-t",
            "translation": "to shoot (an arrow)",
            "hint": "Three consonants: s + t + t",
        },
    ],
    2: [
        {
            "hieroglyphs": "𓅓𓈖𓇋𓅱",
            "transliteration": "mn-i-w",
            "translation": "herdsman",
            "hint": "mn is a biliteral + alphabet signs",
        },
        {
            "hieroglyphs": "𓊪𓂋𓇋",
            "transliteration": "pr-i",
            "translation": "to go forth",
            "hint": "pr is a biliteral + complement",
        },
    ],
    3: [
        {
            "hieroglyphs": "𓄤𓆑𓂋𓏏",
            "transliteration": "nfr-t",
            "translation": "beautiful woman (Nefret)",
            "hint": "nfr is a triliteral + feminine ending t",
        },
        {
            "hieroglyphs": "𓋹𓈖𓐍𓅱",
            "transliteration": "anx-w",
            "translation": "may he live!",
            "hint": "anx is a triliteral + w ending",
        },
    ],
    4: [
        {
            "hieroglyphs": "𓇳𓏤𓋹𓏤",
            "transliteration": "ra-anx",
            "translation": "Ra lives",
            "hint": "Two logograms — each has the stroke marker 𓏤",
        },
        {
            "hieroglyphs": "𓉐𓄤",
            "transliteration": "pr-nfr",
            "translation": "beautiful house",
            "hint": "Logogram + triliteral",
        },
    ],
    5: [
        {
            "hieroglyphs": "𓋴𓏏𓀁",
            "transliteration": "st",
            "translation": "she (with female + speech determinative)",
            "hint": "s + t are phonetic — A2 at the end is SILENT",
        },
        {
            "hieroglyphs": "𓊹𓇳𓀭",
            "transliteration": "nTr ra",
            "translation": "the sun god (with deity determinative)",
            "hint": "Look for the seated god at the end — it adds no sound",
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

# Lesson content — intro paragraphs, tips, subtitles
_LESSON_CONTENT: dict[int, dict] = {
    1: {
        "title": "The Egyptian Alphabet",
        "subtitle": "25 single-consonant signs",
        "desc": "25 uniliteral signs — each represents one consonant sound.",
        "intro": [
            "Ancient Egyptian hieroglyphs only wrote consonants — no vowels at all! These 25 signs are the building blocks of the entire writing system. Each one represents a single consonant sound.",
            "Modern Egyptologists add an 'e' between consonants to make words pronounceable. So the word 'nfr' (beautiful) is spoken as 'nefer', and 'Htp' (peace) becomes 'hotep'.",
            "Master these 25 signs and you can sound out any Egyptian word, letter by letter. They work just like an alphabet — which is fitting, since the Phoenician alphabet (ancestor of our own) was inspired by Egyptian hieroglyphs!",
        ],
        "tip": "Try pronouncing 'nfr' (beautiful) as \"nefer\" — just add an 'e' between each consonant. That's how Egyptologists read hieroglyphs aloud!",
    },
    2: {
        "title": "Common Biliterals",
        "subtitle": "Two-consonant signs",
        "desc": "Two-consonant signs used frequently in hieroglyphic writing.",
        "intro": [
            "Biliterals pack two consonant sounds into a single sign. Instead of writing 'm' + 'n' as two separate signs, scribes could write one biliteral sign 'mn' — faster and more elegant.",
            "Ancient scribes often added a 'phonetic complement' after a biliteral — one of the alphabet signs repeating the last consonant. For example: 𓅓𓈖 = mn + n. The extra 'n' isn't pronounced again; it just confirms the reading.",
            "Think of biliterals as the common two-letter combinations of Egyptian. Once you recognize them, you'll read inscriptions much faster.",
        ],
        "tip": "When you see a biliteral followed by one of its consonants repeated as an alphabet sign — that's a phonetic complement. It confirms the reading, not a new sound!",
    },
    3: {
        "title": "Common Triliterals",
        "subtitle": "Three-consonant signs",
        "desc": "Three-consonant signs — each one packs an entire syllable.",
        "intro": [
            "Triliterals are the powerhouses of Egyptian writing — one sign represents three consonants at once. Many of these signs depict the very thing they spell.",
            "The famous ankh (𓋹) is a triliteral for 'anx' — and it means 'life'. The nefer sign (𓄤) represents 'nfr' — 'beautiful, good, perfect'. The name Nefertiti literally means 'the beautiful one has come'.",
            "Like biliterals, triliterals are often followed by one or two phonetic complements. When you see 𓋹𓈖𓐍, that's ankh + n + kh — the last two signs just confirm the reading of the triliteral.",
        ],
        "tip": "Many triliterals depict the very word they spell — the ankh sign means 'life', the nefer sign means 'beautiful'. Look for the connection between the picture and the word!",
    },
    4: {
        "title": "Common Logograms",
        "subtitle": "Signs that ARE the word",
        "desc": "Logograms represent entire words — the sign IS the meaning.",
        "intro": [
            "Some hieroglyphs skip phonetics entirely — the picture IS the word. A house plan (𓉐) means 'house' (pr). A sun disk (𓇳) means 'sun, day, Ra'. These are logograms (also called ideograms).",
            "How do you know when a sign is being used as a logogram rather than a phonogram? Ancient scribes added a single vertical stroke (𓏤) underneath to say 'read this sign as the word it depicts'.",
            "Most logograms pull double duty — they can also be used for their sound value in other words. Context tells you which reading to use. This flexibility is part of what makes hieroglyphs so rich.",
        ],
        "tip": "Look for the single stroke (𓏤) under a sign — it's the scribe's way of saying 'this sign means exactly what it shows!'",
    },
    5: {
        "title": "Determinatives",
        "subtitle": "Silent classifiers at word endings",
        "desc": "Determinatives are SILENT — they classify a word's meaning, not its sound.",
        "intro": [
            "Here's the key insight that explains why so many signs have no pronunciation: determinatives are completely SILENT. They appear at the end of a word to classify its meaning — like a visual category tag.",
            "Walking legs (𓂻) after a verb means it involves motion. A seated man (𓀀) after a name means it's a male person. A papyrus roll (𓏛) means the word is abstract or related to writing. A sun disk (𓇳) tells you the word relates to time or the sun god.",
            "Without determinatives, Egyptian would be deeply ambiguous — many words share the same consonants. The word 'pr' could mean 'house', 'go out', 'winter', or more. Only the determinative tells you which meaning is intended!",
        ],
        "tip": "Think of determinatives as hashtags — they don't change the pronunciation, but they tell you what category the word belongs to. That's why ~80% of all Gardiner signs have no sound value!",
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


def _sign_to_dict(sign: GardinerSign) -> dict:
    """Serialize a GardinerSign — type-aware, no duplicate fields."""
    t = sign.sign_type
    is_phonetic = t in (
        SignType.UNILITERAL, SignType.BILITERAL, SignType.TRILITERAL,
    )
    # Pronunciation guide for uniliterals
    pronunciation = None
    if t == SignType.UNILITERAL and sign.transliteration:
        pron = _PRONUNCIATION_GUIDE.get(sign.transliteration)
        if pron:
            pronunciation = {"sound": pron[0], "example": pron[1]}

    # Speech text for SpeechSynthesis — any sign with a transliteration gets audio
    speech_text = _transliteration_to_speech(sign.transliteration) if sign.transliteration else None

    return {
        "code": sign.code,
        "transliteration": sign.transliteration,
        "type": t.value,
        "description": sign.description,
        "category": sign.category,
        "category_name": CATEGORY_NAMES.get(sign.category, sign.category),
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


# In-memory cache for generated audio (text -> WAV bytes)
_tts_cache: dict[str, bytes] = {}


@router.get("/speak")
async def speak(request: Request, text: str = Query(..., min_length=1, max_length=100)):
    """Generate natural TTS audio for a pronunciation string.

    Returns audio/wav. Uses Gemini TTS with in-memory caching.
    Falls back to 404 if AI service is unavailable.
    """
    cache_key = _cached_speech_text(text)

    # Return cached audio immediately
    if cache_key in _tts_cache:
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

    return Response(
        content=wav_data,
        media_type="audio/wav",
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ═══════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/categories")
async def list_categories():
    """List all Gardiner categories with sign counts."""
    counts: dict[str, int] = {}
    for sign in GARDINER_TRANSLITERATION.values():
        counts[sign.category] = counts.get(sign.category, 0) + 1

    categories = []
    for code in sorted(counts.keys(), key=lambda c: (len(c), c)):
        categories.append({
            "code": code,
            "name": CATEGORY_NAMES.get(code, code),
            "count": counts[code],
        })

    return JSONResponse(content={
        "categories": categories,
        "total_signs": len(GARDINER_TRANSLITERATION),
    })


@router.get("/alphabet")
async def get_alphabet():
    """Return the 25 primary uniliteral signs in traditional teaching order."""
    signs = []
    for code in _ALPHABET_CODES:
        sign = GARDINER_TRANSLITERATION.get(code)
        if sign:
            signs.append(_sign_to_dict(sign))
    return JSONResponse(content={"signs": signs, "count": len(signs)})


@router.get("/lesson/{level}")
async def get_lesson(level: int):
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
            signs.append(_sign_to_dict(sign))

    # Next/prev lesson info
    prev_lesson = None
    next_lesson = None
    if level > 1:
        pc = _LESSON_CONTENT[level - 1]
        prev_lesson = {"level": level - 1, "title": pc["title"]}
    if level < 5:
        nc = _LESSON_CONTENT[level + 1]
        next_lesson = {"level": level + 1, "title": nc["title"]}

    return JSONResponse(content={
        "level": level,
        "title": content["title"],
        "subtitle": content["subtitle"],
        "description": content["desc"],
        "intro_paragraphs": content["intro"],
        "tip": content["tip"],
        "prev_lesson": prev_lesson,
        "next_lesson": next_lesson,
        "total_lessons": 5,
        "signs": signs,
        "count": len(signs),
        "example_words": _EXAMPLE_WORDS.get(level, []),
        "practice_words": _PRACTICE_WORDS.get(level, []),
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
async def get_sign(code: str):
    """Get a single sign by Gardiner code — enriched with usages & related signs."""
    sign = GARDINER_TRANSLITERATION.get(code)
    if not sign:
        raise HTTPException(status_code=404, detail=f"Sign '{code}' not found")
    data = _sign_to_dict(sign)
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
            raise HTTPException(status_code=400, detail=f"Invalid type. Valid: {valid}")

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
        "signs": [_sign_to_dict(s) for s in page_signs],
        "count": len(page_signs),
        "total": total_filtered,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    })
