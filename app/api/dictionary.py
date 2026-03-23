"""Dictionary API — Gardiner sign lookup, search, and categories.

GET /api/dictionary           — All signs (with optional ?category=, ?search=, ?type= filters)
GET /api/dictionary/{code}    — Single sign by Gardiner code
GET /api/dictionary/categories — Category list with counts
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.gardiner import (
    GARDINER_TRANSLITERATION,
    GardinerSign,
    SignType,
)

router = APIRouter(prefix="/api/dictionary", tags=["dictionary"])

# Gardiner category names (A-Z, Aa)
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


def _sign_to_dict(sign: GardinerSign) -> dict:
    """Serialize a GardinerSign to a JSON-friendly dict."""
    return {
        "code": sign.code,
        "transliteration": sign.transliteration,
        "type": sign.sign_type.value,
        "description": sign.description,
        "category": sign.category,
        "category_name": CATEGORY_NAMES.get(sign.category, sign.category),
        "phonetic_value": sign.phonetic_value,
        "logographic_value": sign.logographic_value,
        "determinative_class": sign.determinative_class,
        "unicode_char": sign.unicode_char,
    }


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

    return JSONResponse(content={"categories": categories, "total_signs": len(GARDINER_TRANSLITERATION)})


@router.get("/{code}")
async def get_sign(code: str):
    """Get a single sign by Gardiner code."""
    sign = GARDINER_TRANSLITERATION.get(code)
    if not sign:
        raise HTTPException(status_code=404, detail=f"Sign '{code}' not found")
    return JSONResponse(content=_sign_to_dict(sign))


@router.get("")
async def list_signs(
    category: str | None = Query(None, description="Filter by Gardiner category (A-Z, Aa)"),
    search: str | None = Query(None, description="Search in code, transliteration, description"),
    sign_type: str | None = Query(None, alias="type", description="Filter by sign type"),
):
    """List all signs, optionally filtered by category, search query, or type."""
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

    # Sort by category then code
    signs.sort(key=lambda s: (len(s.category), s.category, _natural_sort_key(s.code)))

    return JSONResponse(content={
        "signs": [_sign_to_dict(s) for s in signs],
        "count": len(signs),
        "total": len(GARDINER_TRANSLITERATION),
    })


def _natural_sort_key(code: str) -> tuple:
    """Sort Gardiner codes naturally: A1, A2, ..., A10 (not A1, A10, A2)."""
    import re
    parts = re.match(r"([A-Za-z]+)(\d+)", code)
    if parts:
        return (parts.group(1), int(parts.group(2)))
    return (code, 0)
