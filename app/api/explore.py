"""Explore API — Egyptian landmarks browsing, detail, and identification.

GET /api/landmarks             — List all landmarks (with optional ?category=, ?city=, ?search= filters)
GET /api/landmarks/categories  — Category + city lists with counts
GET /api/landmarks/{slug}      — Single landmark detail
POST /api/explore/identify     — Hybrid ONNX + Gemini landmark identification
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.landmarks import (
    ATTRACTIONS,
    Attraction,
    AttractionType,
    City,
    get_by_slug,
    get_slug,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/landmarks", tags=["landmarks"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"
TEXT_DIR = DATA_DIR / "text"
METADATA_DIR = DATA_DIR / "metadata"
MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "landmark"
MODEL_META = MODEL_DIR / "model_metadata.json"
LABEL_MAPPING = MODEL_DIR / "landmark_label_mapping.json"


# ── Wikipedia data loader ──

@lru_cache(maxsize=1)
def _load_wiki_data() -> dict[str, dict]:
    """Load Wikipedia text data for all landmarks."""
    wiki: dict[str, dict] = {}
    if not TEXT_DIR.exists():
        return wiki
    for f in TEXT_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            slug = f.stem  # e.g. "abu_simbel"
            en = data.get("wikipedia", {}).get("en", {})
            wiki[slug] = {
                "title": en.get("title", slug.replace("_", " ").title()),
                "extract": en.get("extract", ""),
                "description": en.get("description", ""),
                "coordinates": en.get("coordinates"),
                "thumbnail": en.get("thumbnail", ""),
                "original_image": en.get("original_image", ""),
                "wikipedia_url": en.get("wikipedia_url", ""),
            }
        except Exception:
            logger.warning("Failed to load wiki data for %s", f.stem)
    return wiki


@lru_cache(maxsize=1)
def _load_model_classes() -> list[str]:
    """Load model class names for identification mapping."""
    if not MODEL_META.exists():
        return []
    try:
        data = json.loads(MODEL_META.read_text(encoding="utf-8"))
        return data.get("class_names", [])
    except Exception:
        return []


@lru_cache(maxsize=1)
def _load_display_names() -> dict[str, str]:
    """Load display names from model metadata or label mapping."""
    # Try model_metadata.json first
    if MODEL_META.exists():
        try:
            data = json.loads(MODEL_META.read_text(encoding="utf-8"))
            names = data.get("display_names", {})
            if names:
                return names
        except Exception:
            pass
    # Fallback: generate from label_mapping.json
    if LABEL_MAPPING.exists():
        try:
            mapping = json.loads(LABEL_MAPPING.read_text(encoding="utf-8"))
            return {
                slug: slug.replace("_", " ").title()
                for slug in mapping.values()
            }
        except Exception:
            pass
    return {}


@lru_cache(maxsize=1)
def _load_image_counts() -> dict[str, int]:
    """Count available images per landmark from metadata."""
    counts: dict[str, int] = {}
    if not METADATA_DIR.exists():
        return counts
    for f in METADATA_DIR.glob("*.json"):
        if f.stem == "kaggle_download_stats":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            counts[f.stem] = len(data) if isinstance(data, list) else 0
        except Exception:
            counts[f.stem] = 0
    return counts


def _attraction_to_dict(a: Attraction) -> dict:
    """Serialize a curated Attraction to API-friendly dict."""
    slug = get_slug(a)
    wiki = _load_wiki_data().get(slug.replace("-", "_"), {})
    img_counts = _load_image_counts()

    return {
        "slug": slug,
        "name": a.name,
        "city": a.city.value,
        "type": a.type.value,
        "era": a.era,
        "popularity": a.popularity,
        "description": a.description,
        "coordinates": list(a.coordinates) if a.coordinates else None,
        "maps_url": a.maps_url,
        "thumbnail": wiki.get("thumbnail", "") or wiki.get("original_image", ""),
        "image_count": img_counts.get(slug.replace("-", "_"), 0),
        "source": "curated",
    }


def _wiki_to_dict(slug: str, wiki: dict) -> dict:
    """Serialize a Wikipedia-only landmark to API-friendly dict."""
    img_counts = _load_image_counts()
    coords = wiki.get("coordinates")

    return {
        "slug": slug.replace("_", "-"),
        "name": wiki.get("title", slug.replace("_", " ").title()),
        "city": _guess_city(slug),
        "type": _guess_type(slug),
        "era": "",
        "popularity": 5,
        "description": wiki.get("description", ""),
        "coordinates": [coords["lat"], coords["lon"]] if coords else None,
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={wiki.get('title', slug.replace('_', '+'))}",
        "thumbnail": wiki.get("thumbnail", "") or wiki.get("original_image", ""),
        "image_count": img_counts.get(slug, 0),
        "source": "wikipedia",
    }


def _guess_city(slug: str) -> str:
    """Best-effort city classification from slug."""
    cairo_kw = {"cairo", "citadel", "mosque", "khan", "bab", "muizz", "tulun", "sultan", "baron", "synagogue", "church", "museum", "tower"}
    luxor_kw = {"luxor", "karnak", "valley", "medinet", "ramesseum", "hatshepsut", "deir", "colossi", "memnon", "tomb", "nefertari", "thutmose"}
    aswan_kw = {"aswan", "philae", "obelisk", "abu_simbel", "kom_ombo", "edfu"}
    alexandria_kw = {"bibliotheca", "alexandrina", "qaitbay", "pompey", "catacombs"}

    for kw in cairo_kw:
        if kw in slug:
            return "Cairo"
    for kw in luxor_kw:
        if kw in slug:
            return "Luxor"
    for kw in aswan_kw:
        if kw in slug:
            return "Aswan"
    for kw in alexandria_kw:
        if kw in slug:
            return "Alexandria"
    return "Egypt"


def _guess_type(slug: str) -> str:
    """Best-effort type classification from slug."""
    pharaonic_kw = {"pyramid", "sphinx", "temple", "obelisk", "simbel", "karnak", "luxor", "valley", "tomb", "ramess", "hatshepsut", "thutmose", "amenhotep", "akhenaten", "nefertiti", "tutankhamun", "memnon", "medinet", "deir", "abydos", "dendera", "edfu", "philae", "kom_ombo"}
    islamic_kw = {"mosque", "khan", "bab", "muizz", "sultan", "tulun", "citadel"}
    greco_roman_kw = {"bibliotheca", "alexandrina", "qaitbay", "pompey", "catacombs", "synagogue"}

    for kw in pharaonic_kw:
        if kw in slug:
            return "Pharaonic"
    for kw in islamic_kw:
        if kw in slug:
            return "Islamic"
    for kw in greco_roman_kw:
        if kw in slug:
            return "Greco-Roman"
    return "Modern"


# ── Unified landmark list ──

@lru_cache(maxsize=1)
def _get_all_landmarks() -> list[dict]:
    """Build unified list: 20 curated + remaining from Wikipedia data."""
    landmarks = []

    # 1. Curated attractions (rich data)
    curated_slugs = set()
    for a in ATTRACTIONS:
        landmarks.append(_attraction_to_dict(a))
        curated_slugs.add(get_slug(a).replace("-", "_"))

    # 2. Wikipedia-only landmarks (not in curated set)
    wiki_data = _load_wiki_data()
    for slug, wiki in sorted(wiki_data.items()):
        if slug not in curated_slugs:
            landmarks.append(_wiki_to_dict(slug, wiki))

    return landmarks


# ── Endpoints ──

@router.get("/categories")
async def list_categories():
    """List available types and cities with counts."""
    all_lm = _get_all_landmarks()

    types: dict[str, int] = {}
    cities: dict[str, int] = {}
    for lm in all_lm:
        t = lm["type"]
        c = lm["city"]
        types[t] = types.get(t, 0) + 1
        cities[c] = cities.get(c, 0) + 1

    return JSONResponse(content={
        "types": [{"name": k, "count": v} for k, v in sorted(types.items())],
        "cities": [{"name": k, "count": v} for k, v in sorted(cities.items())],
        "total": len(all_lm),
    })


@router.get("/{slug}")
async def get_landmark(slug: str):
    """Get full detail for a single landmark by slug."""
    # Normalize slug — try both hyphen and underscore variants
    normalized = slug.lower().strip()
    hyphen_slug = normalized.replace("_", "-")
    underscore_slug = normalized.replace("-", "_")

    # Try curated first (rich data) — curated uses hyphens
    attraction = get_by_slug(hyphen_slug) or get_by_slug(underscore_slug) or get_by_slug(normalized)
    if attraction:
        wiki = _load_wiki_data().get(underscore_slug, {})
        img_counts = _load_image_counts()

        # Recommendations
        from app.core.recommendation_engine import recommend
        recs = recommend(attraction.name, limit=5)
        rec_list = [
            {"slug": get_slug(r.attraction), "name": r.attraction.name,
             "score": r.score, "reasons": r.reasons}
            for r in recs
        ]

        return JSONResponse(content={
            **_attraction_to_dict(attraction),
            "highlights": attraction.highlights,
            "visiting_tips": attraction.visiting_tips,
            "historical_significance": attraction.historical_significance,
            "period": attraction.period,
            "dynasty": attraction.dynasty,
            "notable_pharaohs": attraction.notable_pharaohs,
            "notable_tombs": attraction.notable_tombs,
            "notable_features": attraction.notable_features,
            "key_artifacts": attraction.key_artifacts,
            "architectural_features": attraction.architectural_features,
            "wikipedia_extract": wiki.get("extract", ""),
            "wikipedia_url": wiki.get("wikipedia_url", ""),
            "original_image": wiki.get("original_image", ""),
            "recommendations": rec_list,
        })

    # Try Wikipedia data
    wiki_data = _load_wiki_data()
    if underscore_slug in wiki_data:
        wiki = wiki_data[underscore_slug]
        return JSONResponse(content={
            **_wiki_to_dict(underscore_slug, wiki),
            "highlights": "",
            "visiting_tips": "",
            "historical_significance": "",
            "period": None,
            "dynasty": None,
            "notable_pharaohs": None,
            "notable_tombs": None,
            "notable_features": None,
            "key_artifacts": None,
            "architectural_features": None,
            "wikipedia_extract": wiki.get("extract", ""),
            "wikipedia_url": wiki.get("wikipedia_url", ""),
            "original_image": wiki.get("original_image", ""),
        })

    # Fallback: model-only landmark (no text data)
    display_names = _load_display_names()
    if underscore_slug in display_names:
        name = display_names[underscore_slug]
        return JSONResponse(content={
            "slug": normalized,
            "name": name,
            "city": _guess_city(underscore_slug),
            "type": _guess_type(underscore_slug),
            "era": "",
            "popularity": 5,
            "description": f"{name} is an Egyptian heritage landmark recognized by the Wadjet AI model.",
            "coordinates": None,
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}",
            "thumbnail": "",
            "image_count": 0,
            "source": "model",
            "highlights": "",
            "visiting_tips": "",
            "historical_significance": "",
            "period": None,
            "dynasty": None,
            "notable_pharaohs": None,
            "notable_tombs": None,
            "notable_features": None,
            "key_artifacts": None,
            "architectural_features": None,
            "wikipedia_extract": "",
            "wikipedia_url": "",
            "original_image": "",
        })

    raise HTTPException(status_code=404, detail=f"Landmark '{slug}' not found")


@router.get("")
async def list_landmarks(
    category: str | None = Query(None, description="Filter by type (Pharaonic, Islamic, etc.)"),
    city: str | None = Query(None, description="Filter by city"),
    search: str | None = Query(None, description="Search in name/description"),
):
    """List all landmarks with optional filters."""
    landmarks = list(_get_all_landmarks())

    if category:
        cat_lower = category.lower()
        landmarks = [lm for lm in landmarks if lm["type"].lower() == cat_lower]

    if city:
        city_lower = city.lower()
        landmarks = [lm for lm in landmarks if lm["city"].lower() == city_lower]

    if search:
        q = search.lower()
        landmarks = [
            lm for lm in landmarks
            if q in lm["name"].lower() or q in lm.get("description", "").lower()
        ]

    return JSONResponse(content={"landmarks": landmarks, "count": len(landmarks)})


# ══════════════════════════════════════════════════════════════
# Hybrid landmark identification: ONNX model + Gemini Vision
# ══════════════════════════════════════════════════════════════

identify_router = APIRouter(prefix="/api/explore", tags=["explore"])

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
HIGH_CONFIDENCE = 0.5

_landmark_pipeline = None


def _get_landmark_pipeline():
    """Lazy-load singleton LandmarkPipeline."""
    global _landmark_pipeline
    if _landmark_pipeline is None:
        from app.core.landmark_pipeline import LandmarkPipeline
        _landmark_pipeline = LandmarkPipeline()
    return _landmark_pipeline


def _get_gemini(request: Request):
    """Retrieve GeminiService from app state."""
    gemini = getattr(request.app.state, "gemini", None)
    return gemini


@identify_router.post("/identify")
async def identify_landmark(request: Request, file: UploadFile = File(...)):
    """Hybrid landmark identification.

    1. Run ONNX model → class + confidence + top3
    2. If confidence >= 0.5 → Gemini describes (text only, no image sent)
    3. If confidence < 0.5 → Gemini also identifies (image sent)
    4. If ONNX fails → Gemini-only fallback
    5. If both fail → 503
    """
    # Validate file
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="File is not a valid image")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    if not data:
        raise HTTPException(status_code=422, detail="Empty file")

    # Decode image
    arr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="Could not decode image")

    gemini = _get_gemini(request)
    onnx_result = None
    source = "unknown"
    description = ""

    # Step 1: Try ONNX model
    try:
        pipeline = _get_landmark_pipeline()
        if pipeline.available:
            import asyncio
            from functools import partial
            loop = asyncio.get_event_loop()
            onnx_result = await loop.run_in_executor(
                None, partial(pipeline.predict, image, top_k=3)
            )
    except Exception:
        logger.exception("ONNX landmark inference failed")

    # Step 2: Decide enrichment vs fallback
    if onnx_result and onnx_result["confidence"] >= HIGH_CONFIDENCE:
        # High confidence: use ONNX result, Gemini describes only
        source = "local_model"
        if gemini and gemini.available:
            try:
                description = await gemini.describe_landmark(
                    onnx_result["slug"], onnx_result["name"]
                )
            except Exception:
                logger.warning("Gemini describe_landmark failed, using ONNX only")

    elif onnx_result and onnx_result["confidence"] > 0:
        # Low confidence: ONNX + Gemini Vision double-check
        source = "hybrid"
        if gemini and gemini.available:
            try:
                mime = file.content_type or "image/jpeg"
                gemini_result = await gemini.identify_landmark(data, mime)
                if gemini_result.get("confidence", 0) > onnx_result["confidence"]:
                    # Gemini is more confident — use its identification
                    onnx_result = {
                        "slug": gemini_result.get("slug", onnx_result["slug"]),
                        "name": gemini_result.get("name", onnx_result["name"]),
                        "confidence": gemini_result.get("confidence", onnx_result["confidence"]),
                        "top3": onnx_result["top3"],
                    }
                description = gemini_result.get("description", "")
            except Exception:
                logger.warning("Gemini identify_landmark failed, using ONNX only")
    else:
        # ONNX failed entirely — Gemini-only fallback
        if gemini and gemini.available:
            try:
                mime = file.content_type or "image/jpeg"
                gemini_result = await gemini.identify_landmark(data, mime)
                if gemini_result.get("slug"):
                    onnx_result = {
                        "slug": gemini_result["slug"],
                        "name": gemini_result.get("name", ""),
                        "confidence": gemini_result.get("confidence", 0),
                        "top3": [{
                            "slug": gemini_result["slug"],
                            "name": gemini_result.get("name", ""),
                            "confidence": gemini_result.get("confidence", 0),
                        }],
                    }
                    description = gemini_result.get("description", "")
                    source = "gemini"
            except Exception:
                logger.exception("Gemini fallback failed")

    if not onnx_result or not onnx_result.get("slug"):
        raise HTTPException(
            status_code=503,
            detail="Landmark identification temporarily unavailable",
        )

    result = {
        "name": onnx_result["name"],
        "confidence": onnx_result["confidence"],
        "slug": onnx_result["slug"],
        "source": source,
        "description": description,
        "top3": onnx_result.get("top3", []),
    }

    # Return HTML partial for HTMX requests, JSON otherwise
    if request.headers.get("HX-Request"):
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "partials/identify_result.html",
            context=result,
        )

    return JSONResponse(content=result)
