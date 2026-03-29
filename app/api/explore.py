"""Explore API — Egyptian landmarks browsing, detail, and identification.

GET /api/landmarks             — List all landmarks (with optional ?category=, ?city=, ?search= filters)
GET /api/landmarks/categories  — Category + city lists with counts
GET /api/landmarks/{slug}      — Single landmark detail (includes children + sections)
GET /api/landmarks/{slug}/children — List child sub-sites for a parent site
POST /api/explore/identify     — Hybrid ONNX + Gemini landmark identification
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from app.rate_limit import limiter

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
EXPANDED_SITES_FILE = DATA_DIR / "expanded_sites.json"
TEXT_DIR = DATA_DIR / "text"
METADATA_DIR = DATA_DIR / "metadata"
MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "landmark"
MODEL_META = MODEL_DIR / "model_metadata.json"
LABEL_MAPPING = MODEL_DIR / "landmark_label_mapping.json"

# ── AI-generated detail enrichment cache (LRU) ──
_ENRICHMENT_CACHE_FILE = DATA_DIR / "landmark_enrichment_cache.json"
_MAX_ENRICHMENT_CACHE = 300


class _EnrichmentCache:
    """LRU cache for AI-generated landmark detail fields.

    Persists to disk so regeneration only happens once per site.
    """

    def __init__(self) -> None:
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if _ENRICHMENT_CACHE_FILE.exists():
            try:
                data = json.loads(_ENRICHMENT_CACHE_FILE.read_text(encoding="utf-8"))
                for slug, fields in data.items():
                    self._cache[slug] = fields
            except Exception:
                logger.warning("Failed to load enrichment cache")

    def get(self, slug: str) -> dict | None:
        self._load()
        if slug in self._cache:
            self._cache.move_to_end(slug)
            return self._cache[slug]
        return None

    def put(self, slug: str, fields: dict) -> None:
        self._load()
        self._cache[slug] = fields
        self._cache.move_to_end(slug)
        if len(self._cache) > _MAX_ENRICHMENT_CACHE:
            self._cache.popitem(last=False)

    async def put_async(self, slug: str, fields: dict) -> None:
        self.put(slug, fields)
        await self.save_async()

    def _save(self) -> None:
        try:
            data = json.dumps(dict(self._cache), ensure_ascii=False, indent=2)
            tmp = _ENRICHMENT_CACHE_FILE.with_suffix('.tmp')
            tmp.write_text(data, encoding="utf-8")
            tmp.replace(_ENRICHMENT_CACHE_FILE)
        except Exception:
            logger.warning("Failed to save enrichment cache")

    async def save_async(self) -> None:
        await asyncio.to_thread(self._save)


_enrichment_cache = _EnrichmentCache()


async def _enrich_landmark_detail(request, result: dict) -> None:
    """Fill empty highlights/visiting_tips/historical_significance via AI.

    Only runs for non-curated sites. Results are cached to disk.
    """
    # Skip if already has content (curated sites)
    if result.get("highlights") or result.get("visiting_tips"):
        return

    slug = result.get("slug", "").replace("-", "_")
    cached = _enrichment_cache.get(slug)
    if cached:
        result["highlights"] = cached.get("highlights", "")
        result["visiting_tips"] = cached.get("visiting_tips", "")
        result["historical_significance"] = cached.get("historical_significance", "")
        return

    # Try AI generation
    ai_service = getattr(request.app.state, "ai_service", None)
    if not ai_service or not ai_service.available:
        return

    name = result.get("name", slug.replace("_", " ").title())
    city = result.get("city", "Egypt")
    category = result.get("type", "")
    period = result.get("period", "")
    description = result.get("description", "")

    system = "You are an expert Egyptian history and travel guide."
    prompt = (
        f'For the Egyptian landmark "{name}" in {city}'
        f'{f" ({category}, {period})" if category else ""}:\n'
        f'Description: {description[:300]}\n\n'
        f'Generate JSON with these fields:\n'
        f'{{\n'
        f'  "highlights": "3-5 key features as bullet points separated by |",\n'
        f'  "visiting_tips": "2-3 practical tips separated by |",\n'
        f'  "historical_significance": "1-2 sentences on why this site matters"\n'
        f'}}\n'
        f'Be concise, accurate, and informative. Use known historical facts.'
    )

    try:
        data, _ = await ai_service.text_json(system=system, prompt=prompt, max_tokens=512)
        if data:
            fields = {
                "highlights": data.get("highlights", ""),
                "visiting_tips": data.get("visiting_tips", ""),
                "historical_significance": data.get("historical_significance", ""),
            }
            await _enrichment_cache.put_async(slug, fields)
            result["highlights"] = fields["highlights"]
            result["visiting_tips"] = fields["visiting_tips"]
            result["historical_significance"] = fields["historical_significance"]
    except Exception:
        logger.warning("AI enrichment failed for %s", slug)

# Slug aliases: old duplicate/alternate slugs → canonical
_SLUG_ALIASES: dict[str, str] = {
    "aswan_dam": "aswan_high_dam",
    "pompey_pillar": "pompeys_pillar",
    "catacombs_of_kom_el_shoqafa": "catacombs_of_kom_el_shoqafa",
    "catacombs_kom_el_shoqafa": "catacombs_of_kom_el_shoqafa",
    "egyptian_museum_cairo": "egyptian_museum",
    "great_pyramid_of_giza": "great_pyramids_of_giza",
    "step_pyramid_of_djoser": "pyramid_of_djoser",
    "saladin_citadel": "cairo_citadel",
    "qaitbay_citadel": "citadel_of_qaitbay",
    "temple_of_isis_philae": "philae_temple",
    "temple_of_seti_i_abydos": "abydos_temple",
    "temple_of_mandulis": "kalabsha_temple",
    "temple_of_derr": "temple_of_amada",
    "wadi_rayan": "wadi_el_rayan",
    # Curated slug mismatches
    "the_unfinished_obelisk": "unfinished_obelisk",
    "montazah_palace_gardens": "montaza_palace",
}

# Reverse map: expanded underscore slug → curated hyphen slug (for curated lookup)
_CURATED_SLUG_MAP: dict[str, str] = {
    "unfinished_obelisk": "the-unfinished-obelisk",
    "montaza_palace": "montazah-palace-gardens",
}


# ── Data loaders ──

@lru_cache(maxsize=1)
def _load_expanded_sites() -> dict[str, dict]:
    """Load expanded_sites.json as primary site database."""
    if not EXPANDED_SITES_FILE.exists():
        return {}
    try:
        sites = json.loads(EXPANDED_SITES_FILE.read_text(encoding="utf-8"))
        return {s["slug"]: s for s in sites}
    except Exception:
        logger.warning("Failed to load expanded_sites.json")
        return {}


def _resolve_slug(raw: str) -> str:
    """Resolve slug aliases to canonical slug."""
    normalized = raw.lower().strip().replace("-", "_")
    return _SLUG_ALIASES.get(normalized, normalized)


@lru_cache(maxsize=1)
def _load_wiki_data() -> dict[str, dict]:
    """Load Wikipedia text data for all landmarks."""
    wiki: dict[str, dict] = {}
    if not TEXT_DIR.exists():
        return wiki
    for f in TEXT_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            slug = f.stem
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
    # Try class_names from model_metadata.json
    if MODEL_META.exists():
        try:
            data = json.loads(MODEL_META.read_text(encoding="utf-8"))
            names = data.get("class_names", [])
            if names:
                return names
        except Exception:
            pass
    # Fallback: get slugs from label_mapping.json
    if LABEL_MAPPING.exists():
        try:
            mapping = json.loads(LABEL_MAPPING.read_text(encoding="utf-8"))
            return sorted(set(mapping.values()))
        except Exception:
            pass
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

    # Use category/region from expanded data if available, else guess
    city = wiki.get("region") or _guess_city(slug)
    site_type = wiki.get("category") or _guess_type(slug)

    return {
        "slug": slug.replace("_", "-"),
        "name": wiki.get("title", slug.replace("_", " ").title()),
        "city": city,
        "type": site_type,
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
    """Build unified list from expanded_sites.json + curated ATTRACTIONS + wiki text."""
    landmarks = []
    seen_slugs: set[str] = set()
    expanded = _load_expanded_sites()
    wiki_data = _load_wiki_data()
    img_counts = _load_image_counts()

    # 1. All expanded sites (primary source)
    for slug, site in expanded.items():
        wiki = wiki_data.get(slug, {})
        # Check if also curated — try direct match + mapped aliases
        hyphen_slug = slug.replace("_", "-")
        curated = get_by_slug(hyphen_slug) or get_by_slug(_CURATED_SLUG_MAP.get(slug, ""))
        coords = site.get("coordinates")
        lm = {
            "slug": slug.replace("_", "-"),
            "name": site.get("name", slug.replace("_", " ").title()),
            "name_ar": site.get("name_ar", ""),
            "city": site.get("region", ""),
            "type": site.get("category", ""),
            "subcategory": site.get("subcategory", ""),
            "era": curated.era if curated else site.get("period", ""),
            "period": site.get("period", ""),
            "popularity": curated.popularity if curated else 5,
            "description": curated.description if curated else site.get("description", ""),
            "coordinates": [coords["lat"], coords["lng"]] if coords else None,
            "maps_url": curated.maps_url if curated else f"https://www.google.com/maps/search/?api=1&query={site.get('name', '').replace(' ', '+')}",
            "thumbnail": wiki.get("thumbnail", "") or wiki.get("original_image", ""),
            "image_count": img_counts.get(slug, 0),
            "tags": site.get("tags", []),
            "related_sites": site.get("related_sites", []),
            "parent_slug": (site.get("parent_slug") or "").replace("_", "-") or None,
            "children_slugs": [c.replace("_", "-") for c in site.get("children_slugs", [])],
            "featured": site.get("featured", False),
            "images": site.get("images", []),
            "sections": site.get("sections", []),
            "source": "curated" if curated else "expanded",
        }
        landmarks.append(lm)
        seen_slugs.add(slug)

    # 2. Any curated ATTRACTIONS not in expanded (safety net)
    for a in ATTRACTIONS:
        a_slug = _resolve_slug(get_slug(a).replace("-", "_"))
        if a_slug not in seen_slugs:
            d = _attraction_to_dict(a)
            d.setdefault("name_ar", "")
            d.setdefault("subcategory", "")
            d.setdefault("tags", [])
            d.setdefault("related_sites", [])
            d.setdefault("period", a.period)
            d.setdefault("parent_slug", None)
            d.setdefault("children_slugs", [])
            d.setdefault("featured", False)
            d.setdefault("images", [])
            d.setdefault("sections", [])
            landmarks.append(d)
            seen_slugs.add(a_slug)

    return landmarks


# ── Endpoints ──

@router.get("/categories")
@limiter.limit("60/minute")
async def list_categories(request: Request):
    """List available types, cities, and subcategories with counts."""
    all_lm = _get_all_landmarks()
    # Only count top-level sites for category/city counts
    top_level = [lm for lm in all_lm if not lm.get("parent_slug")]

    types: dict[str, int] = {}
    cities: dict[str, int] = {}
    subcats: dict[str, dict[str, int]] = {}  # type -> {subcat: count}
    for lm in top_level:
        t = lm["type"]
        c = lm["city"]
        sc = lm.get("subcategory", "")
        types[t] = types.get(t, 0) + 1
        cities[c] = cities.get(c, 0) + 1
        if t and sc:
            subcats.setdefault(t, {})
            subcats[t][sc] = subcats[t].get(sc, 0) + 1

    # Build category tree with subcategories
    category_tree = []
    for cat_name in sorted(types.keys()):
        cat_subcats = subcats.get(cat_name, {})
        category_tree.append({
            "name": cat_name,
            "count": types[cat_name],
            "subcategories": [
                {"name": sc, "count": cnt}
                for sc, cnt in sorted(cat_subcats.items())
            ],
        })

    return JSONResponse(content={
        "types": [{"name": k, "count": v} for k, v in sorted(types.items())],
        "cities": [{"name": k, "count": v} for k, v in sorted(cities.items())],
        "category_tree": category_tree,
        "total": len(top_level),
    })


@router.get("/{slug}/children")
@limiter.limit("60/minute")
async def get_landmark_children(slug: str, request: Request):
    """Get child sub-sites for a parent landmark."""
    normalized = _normalize_slug(slug.lower().strip())
    resolved = _resolve_slug(normalized)
    hyphen_slug = resolved.replace("_", "-")

    all_lm = _get_all_landmarks()
    children = [
        lm for lm in all_lm
        if (lm.get("parent_slug") or "").replace("_", "-") == hyphen_slug
    ]

    if not children:
        raise HTTPException(status_code=404, detail=f"No children found for '{slug}'")

    children.sort(key=lambda c: (not c.get("featured", False), c["name"]))
    return JSONResponse(content={"parent_slug": hyphen_slug, "children": children, "count": len(children)})


@router.get("/{slug}")
@limiter.limit("60/minute")
async def get_landmark(slug: str, request: Request):
    """Get full detail for a single landmark by slug."""
    # Normalize slug — try both hyphen and underscore variants
    normalized = _normalize_slug(slug.lower().strip())
    resolved = _resolve_slug(normalized)
    hyphen_slug = resolved.replace("_", "-")
    underscore_slug = resolved.replace("-", "_")

    # Load expanded site data (primary source)
    expanded = _load_expanded_sites()
    site = expanded.get(underscore_slug, {})

    # Try curated first (rich data) — curated uses hyphens
    attraction = (
        get_by_slug(hyphen_slug)
        or get_by_slug(underscore_slug)
        or get_by_slug(resolved)
        or get_by_slug(_CURATED_SLUG_MAP.get(underscore_slug, ""))
    )
    wiki = _load_wiki_data().get(underscore_slug, {})

    # Build base response from expanded sites + wiki + curated enrichment
    if attraction:
        img_counts = _load_image_counts()

        # Recommendations
        from app.core.recommendation_engine import recommend
        recs = recommend(attraction.name, limit=5)
        rec_list = [
            {"slug": get_slug(r.attraction), "name": r.attraction.name,
             "score": r.score, "reasons": r.reasons}
            for r in recs
        ]

        result = {
            **_attraction_to_dict(attraction),
            "highlights": attraction.highlights,
            "visiting_tips": attraction.visiting_tips,
            "historical_significance": attraction.historical_significance,
            "period": site.get("period") or attraction.period,
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
        }
    elif underscore_slug in wiki or site:
        site_coords = site.get("coordinates") if site else None
        coords_list = [site_coords["lat"], site_coords["lng"]] if site_coords else None
        result = {
            **(_wiki_to_dict(underscore_slug, wiki) if wiki else {
                "slug": underscore_slug,
                "name": site.get("name", underscore_slug.replace("_", " ").title()),
                "city": site.get("region", ""),
                "type": site.get("category", ""),
                "era": site.get("period", ""),
                "popularity": 5,
                "description": site.get("description", ""),
                "coordinates": coords_list,
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={site.get('name', '').replace(' ', '+')}",
                "thumbnail": wiki.get("thumbnail", "") if wiki else "",
                "image_count": 0,
                "source": "expanded",
            }),
            "highlights": "",
            "visiting_tips": "",
            "historical_significance": "",
            "period": site.get("period"),
            "dynasty": None,
            "notable_pharaohs": None,
            "notable_tombs": None,
            "notable_features": None,
            "key_artifacts": None,
            "architectural_features": None,
            "wikipedia_extract": wiki.get("extract", ""),
            "wikipedia_url": wiki.get("wikipedia_url", ""),
            "original_image": wiki.get("original_image", ""),
        }
    else:
        # Fallback: model-only landmark
        display_names = _load_display_names()
        if underscore_slug in display_names:
            name = display_names[underscore_slug]
            result = {
                "slug": resolved,
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
            }
        else:
            raise HTTPException(status_code=404, detail=f"Landmark '{slug}' not found")

    # Enrich with expanded_sites.json fields
    if site:
        result["name_ar"] = site.get("name_ar", "")
        result["subcategory"] = site.get("subcategory", "")
        result["tags"] = site.get("tags", [])
        result["related_sites"] = site.get("related_sites", [])
        result["sections"] = site.get("sections", [])
        result["images"] = site.get("images", [])
        result["featured"] = site.get("featured", False)
        result["parent_slug"] = (site.get("parent_slug") or "").replace("_", "-") or None
        result["children_slugs"] = [c.replace("_", "-") for c in site.get("children_slugs", [])]
        if not result.get("period"):
            result["period"] = site.get("period")
        if not result.get("coordinates") and site.get("coordinates"):
            sc = site["coordinates"]
            result["coordinates"] = [sc["lat"], sc["lng"]]
        if not result.get("type") and site.get("category"):
            result["type"] = site["category"]
        if not result.get("city") and site.get("region"):
            result["city"] = site["region"]
    else:
        result.setdefault("name_ar", "")
        result.setdefault("subcategory", "")
        result.setdefault("tags", [])
        result.setdefault("related_sites", [])
        result.setdefault("sections", [])
        result.setdefault("images", [])
        result.setdefault("featured", False)
        result.setdefault("parent_slug", None)
        result.setdefault("children_slugs", [])

    # Attach child summaries if this site has children
    children_slugs = result.get("children_slugs", [])
    if children_slugs:
        all_lm = _get_all_landmarks()
        lm_map = {lm["slug"]: lm for lm in all_lm}
        children_data = []
        for cs in children_slugs:
            child = lm_map.get(cs)
            if child:
                children_data.append({
                    "slug": child["slug"],
                    "name": child["name"],
                    "name_ar": child.get("name_ar", ""),
                    "description": child.get("description", ""),
                    "thumbnail": child.get("thumbnail", ""),
                    "featured": child.get("featured", False),
                    "tags": child.get("tags", []),
                    "subcategory": child.get("subcategory", ""),
                })
        # Sort children: featured first
        children_data.sort(key=lambda c: (not c.get("featured", False), c["name"]))
        result["children"] = children_data

    # Attach parent info if this is a child site
    if result.get("parent_slug"):
        all_lm = _get_all_landmarks()
        lm_map = {lm["slug"]: lm for lm in all_lm}
        parent = lm_map.get(result["parent_slug"])
        if parent:
            result["parent"] = {
                "slug": parent["slug"],
                "name": parent["name"],
                "name_ar": parent.get("name_ar", ""),
            }

    # AI-enrich empty detail fields for non-curated sites
    await _enrich_landmark_detail(request, result)

    return JSONResponse(content=result)


def _normalize_slug(raw_slug: str) -> str:
    """Map an arbitrary slug (e.g. from Gemini) to the closest known model class.

    Tries exact match first, then checks if any known class is a prefix/substring
    of the raw slug, or vice-versa. Returns the raw slug unchanged if no match.
    """
    normalized = raw_slug.lower().strip().replace("-", "_")
    classes = _load_model_classes()
    if not classes:
        return normalized
    class_set = set(classes)

    # Exact match
    if normalized in class_set:
        return normalized

    # Check known class as prefix of raw slug (e.g. "bibliotheca_alexandrina" in "bibliotheca_alexandrina_planetarium")
    best_match = ""
    for cls in classes:
        if normalized.startswith(cls) and len(cls) > len(best_match):
            best_match = cls
        elif cls.startswith(normalized) and len(cls) > len(best_match):
            best_match = cls

    if best_match and best_match in class_set:
        return best_match

    # Also check wiki data slugs
    wiki = _load_wiki_data()
    if normalized in wiki:
        return normalized
    for slug in wiki:
        if normalized.startswith(slug) and len(slug) > len(best_match):
            best_match = slug
    if best_match:
        return best_match

    return normalized


@router.get("")
@limiter.limit("60/minute")
async def list_landmarks(
    request: Request,
    category: str | None = Query(None, description="Filter by type (Pharaonic, Islamic, etc.)"),
    subcategory: str | None = Query(None, description="Filter by subcategory"),
    city: str | None = Query(None, description="Filter by region/city"),
    search: str | None = Query(None, description="Search in name/description"),
    parent: str | None = Query(None, description="Show children of this parent slug"),
    include_children: bool = Query(False, description="Include child sub-sites in the list"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(24, ge=1, le=100, description="Items per page"),
):
    """List landmarks with optional filters. By default hides child sub-sites."""
    landmarks = list(_get_all_landmarks())

    # Filter children unless explicitly requested or browsing inside a parent
    if parent:
        parent_norm = parent.lower().strip().replace("-", "_").replace("_", "-")
        landmarks = [lm for lm in landmarks if (lm.get("parent_slug") or "").replace("_", "-") == parent_norm]
    elif not include_children:
        landmarks = [lm for lm in landmarks if not lm.get("parent_slug")]

    if category:
        cat_lower = category.lower()
        landmarks = [lm for lm in landmarks if lm["type"].lower() == cat_lower]

    if subcategory:
        sc_lower = subcategory.lower()
        landmarks = [lm for lm in landmarks if lm.get("subcategory", "").lower() == sc_lower]

    if city:
        city_lower = city.lower()
        landmarks = [lm for lm in landmarks if lm["city"].lower() == city_lower]

    if search:
        q = search.lower()
        landmarks = [
            lm for lm in landmarks
            if q in lm["name"].lower() or q in lm.get("description", "").lower()
               or q in lm.get("name_ar", "")
        ]

    # Sort: featured first, then by popularity desc, then name
    landmarks.sort(key=lambda lm: (not lm.get("featured", False), -lm.get("popularity", 5), lm["name"]))

    # Paginate
    total = len(landmarks)
    start = (page - 1) * per_page
    end = start + per_page
    page_landmarks = landmarks[start:end]
    has_more = end < total

    return JSONResponse(content={
        "landmarks": page_landmarks,
        "count": len(page_landmarks),
        "total": total,
        "page": page,
        "has_more": has_more,
    })


# ══════════════════════════════════════════════════════════════
# Parallel Ensemble: ONNX + Gemini + Grok (tiebreaker)
# ══════════════════════════════════════════════════════════════

identify_router = APIRouter(prefix="/api/explore", tags=["explore"])

MAX_FILE_SIZE = 10 * 1024 * 1024

# Magic byte signatures for image validation
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG': 'image/png',
    b'RIFF': 'image/webp',
}

_landmark_pipeline = None
_pipeline_lock = threading.Lock()


def _get_landmark_pipeline():
    """Lazy-load singleton LandmarkPipeline."""
    global _landmark_pipeline
    if _landmark_pipeline is None:
        with _pipeline_lock:
            if _landmark_pipeline is None:
                from app.core.landmark_pipeline import LandmarkPipeline
                _landmark_pipeline = LandmarkPipeline()
    return _landmark_pipeline


def _get_gemini(request: Request):
    """Retrieve GeminiService from app state."""
    return getattr(request.app.state, "gemini", None)


def _get_grok(request: Request):
    """Retrieve GrokService from app state."""
    return getattr(request.app.state, "grok", None)


def _get_groq(request: Request):
    """Retrieve GroqService from app state."""
    return getattr(request.app.state, "groq", None)


def _get_cloudflare(request: Request):
    """Retrieve CloudflareService from app state."""
    return getattr(request.app.state, "cloudflare", None)


async def _run_onnx(image) -> dict | None:
    """Run ONNX landmark model in thread pool."""
    try:
        pipeline = _get_landmark_pipeline()
        if not pipeline.available:
            return None
        import asyncio
        from functools import partial
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, partial(pipeline.predict, image, top_k=3)
        )
    except Exception:
        logger.exception("ONNX landmark inference failed")
        return None


async def _run_gemini_vision(gemini, data: bytes, mime: str) -> dict:
    """Run Gemini Vision landmark identification."""
    try:
        if gemini and gemini.available:
            return await gemini.identify_landmark(data, mime)
    except Exception:
        logger.warning("Gemini identify_landmark failed")
    return {}


async def _run_grok_vision(grok, data: bytes, mime: str) -> dict:
    """Run Grok Vision landmark identification (tiebreaker)."""
    try:
        if grok and grok.available:
            return await grok.identify_landmark(data, mime)
    except Exception:
        logger.warning("Grok identify_landmark failed")
    return {}


_IDENTIFY_SYSTEM = (
    "You are an expert on Egyptian landmarks and archaeological sites.\n"
    "Identify the Egyptian landmark in the photo. Respond ONLY with valid JSON."
)
_IDENTIFY_PROMPT = (
    'Identify the Egyptian landmark in this image.\n'
    'Return JSON with these exact keys:\n'
    '{"name": "display name", "slug": "snake_case_id",\n'
    ' "confidence": 0.0-1.0, "description": "1-2 sentence description"}\n'
    'If this is not an Egyptian landmark, return\n'
    '{"name": "", "slug": "", "confidence": 0.0,\n'
    ' "description": "Not an Egyptian landmark"}'
)


async def _run_groq_vision(groq, data: bytes, mime: str) -> dict:
    """Run Groq Vision (Llama 4 Scout) landmark identification."""
    try:
        if groq and groq.available:
            result = await groq.vision_json(
                data, mime,
                system=_IDENTIFY_SYSTEM,
                prompt=_IDENTIFY_PROMPT,
                max_tokens=512,
            )
            return result or {}
    except Exception:
        logger.warning("Groq identify_landmark failed")
    return {}


async def _run_cloudflare_vision(cloudflare, data: bytes, mime: str) -> dict:
    """Run Cloudflare Workers AI vision landmark identification."""
    try:
        if cloudflare and cloudflare.available:
            return await cloudflare.identify_landmark(data, mime)
    except Exception:
        logger.warning("Cloudflare identify_landmark failed")
    return {}


@identify_router.post("/identify")
@limiter.limit("20/minute")
async def identify_landmark(request: Request, file: UploadFile = File(...)):
    """Parallel ensemble landmark identification.

    1. Run ONNX + Gemini Vision in parallel
    2. Merge results with ensemble logic:
       - Both agree → boosted confidence
       - Gemini matches ONNX top2/3 → use Gemini's pick
       - Disagreement → Grok Vision tiebreaker
    3. Normalize slug + generate description
    """
    import asyncio
    from app.core.ensemble import Candidate, merge_landmark

    # Validate file
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Validate magic bytes (not just content-type header)
    detected_mime = ""
    for magic, _mime in MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            if magic == b'RIFF' and data[8:12] != b'WEBP':
                continue
            detected_mime = _mime
            break
    if not detected_mime:
        raise HTTPException(status_code=422, detail="Unsupported file type. Use JPEG, PNG, or WebP.")

    arr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="Could not decode image")

    gemini = _get_gemini(request)
    grok = _get_grok(request)
    groq = _get_groq(request)
    cloudflare = _get_cloudflare(request)
    mime = detected_mime

    # ── Step 1: ONNX + Gemini in parallel ──
    onnx_task = asyncio.create_task(_run_onnx(image))
    gemini_task = asyncio.create_task(_run_gemini_vision(gemini, data, mime))
    onnx_result, gemini_result = await asyncio.gather(onnx_task, gemini_task)

    # Build candidates
    onnx_candidate = None
    onnx_top3 = []
    if onnx_result and onnx_result.get("slug"):
        onnx_candidate = Candidate(
            slug=_normalize_slug(onnx_result["slug"]),
            name=onnx_result.get("name", ""),
            confidence=onnx_result.get("confidence", 0),
            source="onnx",
        )
        onnx_top3 = [
            {**m, "slug": _normalize_slug(m.get("slug", ""))}
            for m in onnx_result.get("top3", [])
        ]

    gemini_candidate = None
    if gemini_result and gemini_result.get("slug"):
        gemini_candidate = Candidate(
            slug=_normalize_slug(gemini_result["slug"]),
            name=gemini_result.get("name", ""),
            confidence=gemini_result.get("confidence", 0),
            source="gemini",
            description=gemini_result.get("description", ""),
        )

    # ── Step 1b: If Gemini failed, try Groq as vision fallback ──
    groq_fallback = None
    if not gemini_candidate and groq and groq.available:
        logger.info("Gemini failed — trying Groq vision fallback")
        groq_result = await _run_groq_vision(groq, data, mime)
        if groq_result and groq_result.get("slug"):
            groq_fallback = Candidate(
                slug=_normalize_slug(groq_result["slug"]),
                name=groq_result.get("name", ""),
                confidence=groq_result.get("confidence", 0),
                source="groq",
                description=groq_result.get("description", ""),
            )
            # Treat Groq as if it were Gemini for the merge logic
            gemini_candidate = groq_fallback

    # ── Step 1c: If Gemini + Groq both failed, try Cloudflare ──
    if not gemini_candidate and cloudflare and cloudflare.available:
        logger.info("Gemini + Groq failed — trying Cloudflare vision fallback")
        cf_result = await _run_cloudflare_vision(cloudflare, data, mime)
        if cf_result and cf_result.get("slug"):
            gemini_candidate = Candidate(
                slug=_normalize_slug(cf_result["slug"]),
                name=cf_result.get("name", ""),
                confidence=cf_result.get("confidence", 0),
                source="cloudflare",
                description=cf_result.get("description", ""),
            )

    # ── Step 2: Check if tiebreaker needed ──
    grok_candidate = None
    need_tiebreak = (
        onnx_candidate and gemini_candidate
        and onnx_candidate.slug != gemini_candidate.slug
        and (not onnx_top3 or gemini_candidate.slug not in [
            m.get("slug", "") for m in onnx_top3
        ])
    )

    if need_tiebreak and grok and grok.available:
        logger.info(
            "Tiebreak: ONNX=%s vs Gemini=%s — calling Grok",
            onnx_candidate.slug, gemini_candidate.slug,
        )
        grok_result = await _run_grok_vision(grok, data, mime)
        if grok_result and grok_result.get("slug"):
            grok_candidate = Candidate(
                slug=_normalize_slug(grok_result["slug"]),
                name=grok_result.get("name", ""),
                confidence=grok_result.get("confidence", 0),
                source="grok",
                description=grok_result.get("description", ""),
            )

    # ── Step 3: Merge ──
    merged = merge_landmark(
        onnx=onnx_candidate,
        gemini=gemini_candidate,
        grok=grok_candidate,
        onnx_top3=onnx_top3,
    )

    if not merged.slug:
        # No model could identify anything — check if vision AI said "not Egyptian"
        vision_said_not_egyptian = (
            (gemini_result and not gemini_result.get("slug"))
            or (groq_fallback is None and not gemini_candidate)
        )
        if vision_said_not_egyptian:
            not_egyptian = {
                "name": "",
                "confidence": 0.0,
                "slug": "",
                "source": "none",
                "agreement": "none",
                "description": "This does not appear to be an Egyptian landmark.",
                "is_known_landmark": False,
                "is_egyptian": False,
                "top3": [],
            }
            if request.headers.get("HX-Request"):
                templates = request.app.state.templates
                return templates.TemplateResponse(
                    request, "partials/identify_result.html", context=not_egyptian,
                )
            return JSONResponse(content=not_egyptian)

        raise HTTPException(
            status_code=503,
            detail="Landmark identification temporarily unavailable",
        )

    # ── Step 4: Check if result is a known landmark ──
    model_classes = set(_load_model_classes())
    wiki_data = _load_wiki_data()
    known_slugs = model_classes | set(wiki_data.keys())
    normalized_slug = _normalize_slug(merged.slug)
    is_known = normalized_slug in known_slugs

    # ── Step 5: Get description if missing ──
    description = merged.description
    if not description and gemini and gemini.available:
        try:
            description = await gemini.describe_landmark(merged.slug, merged.name)
        except Exception:
            pass

    result = {
        "name": merged.name or _load_display_names().get(merged.slug, merged.slug.replace("_", " ").title()),
        "confidence": merged.confidence,
        "slug": merged.slug,
        "source": merged.source,
        "agreement": merged.agreement,
        "description": description,
        "is_known_landmark": is_known,
        "is_egyptian": True,
        "top3": onnx_top3 or (
            [{"slug": merged.slug, "name": merged.name, "confidence": merged.confidence}]
        ),
    }

    if request.headers.get("HX-Request"):
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "partials/identify_result.html",
            context=result,
        )

    return JSONResponse(content=result)
