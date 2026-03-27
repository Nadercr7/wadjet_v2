"""
Wadjet AI — Hieroglyphs learning data.

Migrated from the legacy ``learn_hieroglyphs.html`` template and extended
with additional categories (numbers, common symbols) to provide a richer
learning experience.

Each entry carries:

* **symbol** - the Unicode Egyptian Hieroglyph character
* **transliteration** - romanised phonetic value (e.g. ``"A"``)
* **meaning** - the pictorial origin of the sign
* **pronunciation** - IPA-style pronunciation guide
* **gardiner_code** - `Gardiner's Sign List`_ identifier (when known)
* **category** - ``alphabet`` | ``numbers`` | ``common_symbols``
* **image_url** - optional Wikimedia/CDN URL (``None`` until Phase 5)

Public helpers
--------------
``get_all()``
    Return every hieroglyph entry.
``get_by_category(cat)``
    Filter by category string; returns empty list for unknown categories.
``get_categories()``
    Return the sorted list of distinct category names.
``get_by_id(hid)``
    O(1) lookup by hieroglyph ID.
``search(query)``
    Case-insensitive substring match across transliteration, meaning,
    and pronunciation fields.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Hieroglyph:
    """A single hieroglyph learning entry."""

    id: str
    symbol: str
    transliteration: str
    meaning: str
    pronunciation: str
    category: str
    gardiner_code: str | None = None
    image_url: str | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# ── Alphabet (unilateral / single-consonant signs) ────────────────────────
# Migrated from legacy learn_hieroglyphs.html hieroglyphMap
# ---------------------------------------------------------------------------

_ALPHABET: list[Hieroglyph] = [
    Hieroglyph(
        id="alpha-a",
        symbol="\U00013177",  # 𓄿 Egyptian Vulture
        transliteration="A",
        meaning="Vulture (Aleph)",
        pronunciation="ah (glottal stop)",
        category="alphabet",
        gardiner_code="G1",
    ),
    Hieroglyph(
        id="alpha-b",
        symbol="\U000130c0",  # 𓃀 Foot
        transliteration="B",
        meaning="Foot",
        pronunciation="b",
        category="alphabet",
        gardiner_code="D58",
    ),
    Hieroglyph(
        id="alpha-c",
        symbol="\U0001337f",  # 𓍿 Basket
        transliteration="C",
        meaning="Basket (used for K/S sounds)",
        pronunciation="k or s",
        category="alphabet",
        gardiner_code="V31",
        notes="Not a native Egyptian sound; used as substitute for K or S.",
    ),
    Hieroglyph(
        id="alpha-d",
        symbol="\U000130a7",  # 𓂧 Hand
        transliteration="D",
        meaning="Hand",
        pronunciation="d",
        category="alphabet",
        gardiner_code="D46",
    ),
    Hieroglyph(
        id="alpha-e",
        symbol="\U000131cb",  # 𓇋 Reed Leaf
        transliteration="E / I",
        meaning="Reed Leaf",
        pronunciation="ee",
        category="alphabet",
        gardiner_code="M17",
        notes="Same sign used for both E and I sounds.",
    ),
    Hieroglyph(
        id="alpha-f",
        symbol="\U00013191",  # 𓆑 Horned Viper
        transliteration="F",
        meaning="Horned Viper",
        pronunciation="f",
        category="alphabet",
        gardiner_code="I9",
    ),
    Hieroglyph(
        id="alpha-g",
        symbol="\U000133bc",  # 𓎼 Jar Stand
        transliteration="G",
        meaning="Jar Stand",
        pronunciation="g (hard g)",
        category="alphabet",
        gardiner_code="W11",
    ),
    Hieroglyph(
        id="alpha-h",
        symbol="\U000133db",  # 𓎛 Twisted Flax (Placenta)
        transliteration="H",
        meaning="Twisted Flax",
        pronunciation="h",
        category="alphabet",
        gardiner_code="V28",
    ),
    Hieroglyph(
        id="alpha-j",
        symbol="\U00013193",  # 𓆓 Cobra
        transliteration="J",
        meaning="Cobra",
        pronunciation="dj",
        category="alphabet",
        gardiner_code="I10",
    ),
    Hieroglyph(
        id="alpha-k",
        symbol="\U000133a1",  # 𓎡 Hill Slope
        transliteration="K",
        meaning="Hill Slope",
        pronunciation="k",
        category="alphabet",
        gardiner_code="N29",
    ),
    Hieroglyph(
        id="alpha-l",
        symbol="\U000130ed",  # 𓃭 Lion
        transliteration="L",
        meaning="Lion",
        pronunciation="l",
        category="alphabet",
        gardiner_code="E23",
    ),
    Hieroglyph(
        id="alpha-m",
        symbol="\U00013153",  # 𓅓 Owl
        transliteration="M",
        meaning="Owl",
        pronunciation="m",
        category="alphabet",
        gardiner_code="G17",
    ),
    Hieroglyph(
        id="alpha-n",
        symbol="\U00013216",  # 𓈖 Water Ripple
        transliteration="N",
        meaning="Water Ripple",
        pronunciation="n",
        category="alphabet",
        gardiner_code="N35",
    ),
    Hieroglyph(
        id="alpha-o",
        symbol="\U00013171",  # 𓅱 Quail Chick
        transliteration="O / U / V",
        meaning="Quail Chick",
        pronunciation="oo / w",
        category="alphabet",
        gardiner_code="G43",
        notes="Same sign used for O, U, and V sounds.",
    ),
    Hieroglyph(
        id="alpha-p",
        symbol="\U000132aa",  # 𓊪 Stool
        transliteration="P",
        meaning="Stool",
        pronunciation="p",
        category="alphabet",
        gardiner_code="Q3",
    ),
    Hieroglyph(
        id="alpha-q",
        symbol="\U00013398",  # 𓏘 Hill / Sand Hill
        transliteration="Q",
        meaning="Hill",
        pronunciation="q (deep k)",
        category="alphabet",
        gardiner_code="N29A",
    ),
    Hieroglyph(
        id="alpha-r",
        symbol="\U0001308b",  # 𓂋 Mouth
        transliteration="R",
        meaning="Mouth",
        pronunciation="r",
        category="alphabet",
        gardiner_code="D21",
    ),
    Hieroglyph(
        id="alpha-s",
        symbol="\U000132f4",  # 𓋴 Folded Cloth
        transliteration="S",
        meaning="Folded Cloth",
        pronunciation="s",
        category="alphabet",
        gardiner_code="S29",
    ),
    Hieroglyph(
        id="alpha-t",
        symbol="\U000133cf",  # 𓏏 Bread Loaf
        transliteration="T",
        meaning="Bread Loaf",
        pronunciation="t",
        category="alphabet",
        gardiner_code="X1",
    ),
    Hieroglyph(
        id="alpha-w",
        symbol="\U00013168",  # 𓅨 Quail Chick (alt.)
        transliteration="W",
        meaning="Quail Chick (alternative)",
        pronunciation="w",
        category="alphabet",
        gardiner_code="G43A",
        notes="Alternative form of the quail chick, specifically for W.",
    ),
    Hieroglyph(
        id="alpha-x",
        symbol="\U0001337f",  # 𓍿 Basket (same as C)
        transliteration="X",
        meaning="Basket (used for K/S sounds)",
        pronunciation="kh",
        category="alphabet",
        gardiner_code="V31",
        notes="Same sign as C; represents a guttural sound.",
    ),
    Hieroglyph(
        id="alpha-y",
        symbol="\U000133ed",  # 𓏭 Double Reed Leaf
        transliteration="Y",
        meaning="Double Reed Leaf",
        pronunciation="y / ee",
        category="alphabet",
        gardiner_code="M17A",
    ),
    Hieroglyph(
        id="alpha-z",
        symbol="\U000131cc",  # 𓇌 Door Bolt
        transliteration="Z",
        meaning="Door Bolt",
        pronunciation="z",
        category="alphabet",
        gardiner_code="O34",
    ),
]


# ---------------------------------------------------------------------------
# ── Numbers ───────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

_NUMBERS: list[Hieroglyph] = [
    Hieroglyph(
        id="num-1",
        symbol="\U000133fa",  # 𓏺 single stroke
        transliteration="1",
        meaning="Single stroke",
        pronunciation="wa (one)",
        category="numbers",
        gardiner_code="Z1",
    ),
    Hieroglyph(
        id="num-10",
        symbol="\U00013386",  # 𓎆 Cattle hobble
        transliteration="10",
        meaning="Cattle hobble / arch",
        pronunciation="medju (ten)",
        category="numbers",
        gardiner_code="V20",
    ),
    Hieroglyph(
        id="num-100",
        symbol="\U00013362",  # 𓍢 Coiled rope
        transliteration="100",
        meaning="Coiled rope",
        pronunciation="shet (hundred)",
        category="numbers",
        gardiner_code="V1",
    ),
    Hieroglyph(
        id="num-1000",
        symbol="\U000131f0",  # 𓇰 Lotus flower
        transliteration="1,000",
        meaning="Lotus flower",
        pronunciation="kha (thousand)",
        category="numbers",
        gardiner_code="M12",
    ),
    Hieroglyph(
        id="num-10000",
        symbol="\U0001309e",  # 𓂞 Bent finger
        transliteration="10,000",
        meaning="Bent finger",
        pronunciation="djeba (ten-thousand)",
        category="numbers",
        gardiner_code="D50",
    ),
    Hieroglyph(
        id="num-100000",
        symbol="\U000131e6",  # 𓇦 Tadpole
        transliteration="100,000",
        meaning="Tadpole",
        pronunciation="hefen (hundred-thousand)",
        category="numbers",
        gardiner_code="I8",
    ),
    Hieroglyph(
        id="num-1000000",
        symbol="\U00013067",  # 𓁧 God Heh
        transliteration="1,000,000",
        meaning="God Heh (eternity)",
        pronunciation="heh (million / infinity)",
        category="numbers",
        gardiner_code="C11",
    ),
]


# ---------------------------------------------------------------------------
# ── Common symbols / determinatives ──────────────────────────────────────
# ---------------------------------------------------------------------------

_COMMON_SYMBOLS: list[Hieroglyph] = [
    Hieroglyph(
        id="sym-ankh",
        symbol="\U0001332b",  # 𓌫 (closest to Ankh)
        transliteration="ankh",
        meaning="Key of Life / Eternal life",
        pronunciation="ankh",
        category="common_symbols",
        gardiner_code="S34",
        notes="One of the most iconic Egyptian symbols, representing life.",
    ),
    Hieroglyph(
        id="sym-eye-of-horus",
        symbol="\U00013080",  # 𓂀 Eye of Horus
        transliteration="wedjat",
        meaning="Eye of Horus / Protection",
        pronunciation="wedjat",
        category="common_symbols",
        gardiner_code="D10",
        notes="Symbol of protection, royal power, and good health.",
    ),
    Hieroglyph(
        id="sym-scarab",
        symbol="\U000131a8",  # 𓆨 Scarab beetle
        transliteration="kheper",
        meaning="Scarab beetle / Becoming",
        pronunciation="kheper",
        category="common_symbols",
        gardiner_code="L1",
        notes="Represents transformation and the rising sun god Khepri.",
    ),
    Hieroglyph(
        id="sym-sun",
        symbol="\U00013283",  # 𓊃 (Sun disk placeholder — closest match)
        transliteration="ra",
        meaning="Sun / Sun god Ra",
        pronunciation="ra",
        category="common_symbols",
        gardiner_code="N5",
        notes="Represents the sun and the god Ra.",
    ),
    Hieroglyph(
        id="sym-water",
        symbol="\U00013214",  # 𓈔 Water
        transliteration="mu",
        meaning="Water",
        pronunciation="moo",
        category="common_symbols",
        gardiner_code="N35A",
    ),
    Hieroglyph(
        id="sym-house",
        symbol="\U00013250",  # 𓉐 House
        transliteration="per",
        meaning="House / Estate",
        pronunciation="per",
        category="common_symbols",
        gardiner_code="O1",
    ),
    Hieroglyph(
        id="sym-feather",
        symbol="\U000131fa",  # 𓇺 Feather
        transliteration="maat",
        meaning="Feather of Ma'at / Truth",
        pronunciation="maat",
        category="common_symbols",
        gardiner_code="H6",
        notes="Feather of the goddess Ma'at, symbol of truth and justice.",
    ),
    Hieroglyph(
        id="sym-djed",
        symbol="\U00013319",  # 𓌙 Djed pillar
        transliteration="djed",
        meaning="Djed pillar / Stability",
        pronunciation="djed",
        category="common_symbols",
        gardiner_code="R11",
        notes="Represents stability and the backbone of Osiris.",
    ),
    Hieroglyph(
        id="sym-was",
        symbol="\U00013340",  # 𓍀 Was sceptre
        transliteration="was",
        meaning="Was sceptre / Power",
        pronunciation="was",
        category="common_symbols",
        gardiner_code="S40",
        notes="Symbol of power and dominion, often held by gods.",
    ),
    Hieroglyph(
        id="sym-falcon",
        symbol="\U00013143",  # 𓅃 Falcon / Horus
        transliteration="hor",
        meaning="Falcon / Horus",
        pronunciation="hor",
        category="common_symbols",
        gardiner_code="G5",
        notes="Represents the god Horus and kingship.",
    ),
]


# ---------------------------------------------------------------------------
# Combined data & indexes
# ---------------------------------------------------------------------------

_ALL_HIEROGLYPHS: list[Hieroglyph] = _ALPHABET + _NUMBERS + _COMMON_SYMBOLS

_ID_INDEX: dict[str, Hieroglyph] = {h.id: h for h in _ALL_HIEROGLYPHS}

_CATEGORY_INDEX: dict[str, list[Hieroglyph]] = {}
for _h in _ALL_HIEROGLYPHS:
    _CATEGORY_INDEX.setdefault(_h.category, []).append(_h)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_all() -> list[Hieroglyph]:
    """Return every hieroglyph entry."""
    return list(_ALL_HIEROGLYPHS)


def get_by_category(category: str) -> list[Hieroglyph]:
    """Return hieroglyphs matching *category* (case-insensitive).

    Returns an empty list for unknown categories.
    """
    return list(_CATEGORY_INDEX.get(category.lower(), []))


def get_categories() -> list[str]:
    """Return the sorted list of distinct category names."""
    return sorted(_CATEGORY_INDEX.keys())


def get_by_id(hieroglyph_id: str) -> Hieroglyph | None:
    """O(1) lookup by hieroglyph ID.  Returns ``None`` if not found."""
    return _ID_INDEX.get(hieroglyph_id)


def search(query: str) -> list[Hieroglyph]:
    """Case-insensitive substring search across transliteration, meaning,
    and pronunciation fields.

    Returns an empty list when *query* is blank or has no matches.
    """
    q = query.strip().lower()
    if not q:
        return []
    return [
        h
        for h in _ALL_HIEROGLYPHS
        if q in h.transliteration.lower()
        or q in h.meaning.lower()
        or q in h.pronunciation.lower()
        or (h.notes and q in h.notes.lower())
    ]


def translate_to_hieroglyphs(text: str) -> str:
    """Convert a Latin-alphabet string to hieroglyph Unicode characters.

    Mirrors the legacy ``hieroglyphMap`` JavaScript function.
    Unknown characters are silently dropped; spaces become triple-spaces.
    """
    letter_map: dict[str, str] = {
        "A": "\U00013177",
        "B": "\U000130c0",
        "C": "\U0001337f",
        "D": "\U000130a7",
        "E": "\U000131cb",
        "F": "\U00013191",
        "G": "\U000133bc",
        "H": "\U000133db",
        "I": "\U000131cb",
        "J": "\U00013193",
        "K": "\U000133a1",
        "L": "\U000130ed",
        "M": "\U00013153",
        "N": "\U00013216",
        "O": "\U00013171",
        "P": "\U000132aa",
        "Q": "\U00013398",
        "R": "\U0001308b",
        "S": "\U000132f4",
        "T": "\U000133cf",
        "U": "\U00013171",
        "V": "\U00013171",
        "W": "\U00013168",
        "X": "\U0001337f",
        "Y": "\U000133ed",
        "Z": "\U000131cc",
    }
    parts: list[str] = []
    for ch in text.upper():
        if ch in letter_map:
            parts.append(letter_map[ch])
        elif ch == " ":
            parts.append("   ")
    return "".join(parts)
