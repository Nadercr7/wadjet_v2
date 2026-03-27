#!/usr/bin/env python3
"""Build the comprehensive expanded_sites.json for Wadjet v2.

Reads existing wiki text files from data/text/*.json and merges with
curated site data to produce a clean, deduplicated, fully-categorized
heritage site index.

Run: python scripts/build_heritage_sites.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEXT_DIR = BASE_DIR / "data" / "text"
OUTPUT = BASE_DIR / "data" / "expanded_sites.json"

# ── Dedup map: old slug → canonical slug ──
DEDUP_MAP: dict[str, str] = {
    "aswan_dam": "aswan_high_dam",
    "pompey_pillar": "pompeys_pillar",
    "catacombs_of_kom_el_shoqafa": "catacombs_kom_el_shoqafa",
    "egyptian_museum_cairo": "egyptian_museum",
    "great_pyramid_of_giza": "great_pyramids_of_giza",
    "step_pyramid_of_djoser": "pyramid_of_djoser",
    "temple_of_isis_philae": "philae_temple",
    "wadi_rayan": "wadi_el_rayan",
}

# ── Non-place slugs (pharaohs/artifacts) → redirect to parent site ──
NON_PLACES: dict[str, str] = {
    "akhenaten": "tell_el_amarna",
    "amenhotep_iii": "colossi_of_memnon",
    "king_thutmose_iii": "karnak_temple",
    "ramesses_ii": "abu_simbel",
    "nefertiti_bust": "grand_egyptian_museum",
    "statue_of_tutankhamun": "grand_egyptian_museum",
    "mask_of_tutankhamun": "grand_egyptian_museum",
}


def _load_wiki(slug: str) -> dict:
    """Load wiki data for a slug if the file exists."""
    fp = TEXT_DIR / f"{slug}.json"
    if not fp.exists():
        return {}
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("wikipedia", {})


def _wiki_fields(slug: str) -> dict:
    """Extract useful fields from wiki data."""
    w = _load_wiki(slug)
    en = w.get("en", {})
    ar = w.get("ar", {})
    coords = en.get("coordinates", {})
    return {
        "wiki_title": en.get("title", ""),
        "wiki_desc": en.get("description", ""),
        "wiki_extract": en.get("extract", ""),
        "wiki_url": en.get("wikipedia_url", ""),
        "thumbnail": en.get("thumbnail", ""),
        "original_image": en.get("original_image", ""),
        "coordinates": {"lat": coords["lat"], "lng": coords["lon"]} if coords.get("lat") else None,
        "name_ar": ar.get("title", ""),
        "description_ar": ar.get("extract", ""),
        "wiki_url_ar": ar.get("wikipedia_url", ""),
    }


def _site(
    slug: str,
    name: str,
    name_ar: str = "",
    category: str = "",
    subcategory: str = "",
    region: str = "",
    period: str = "",
    description: str = "",
    description_ar: str = "",
    highlights: list[str] | None = None,
    visiting_tips: list[str] | None = None,
    historical_significance: str = "",
    coordinates: dict | None = None,
    related_sites: list[str] | None = None,
    parent_site: str | None = None,
    child_sites: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Create a site entry, enriching from wiki data if available."""
    wiki = _wiki_fields(slug)

    # Use wiki data as fallback
    if not name_ar and wiki["name_ar"]:
        name_ar = wiki["name_ar"]
    if not description and wiki["wiki_extract"]:
        description = wiki["wiki_extract"]
    if not description_ar and wiki["description_ar"]:
        description_ar = wiki["description_ar"]
    if not coordinates and wiki["coordinates"]:
        coordinates = wiki["coordinates"]

    has_image = bool(wiki["thumbnail"] or wiki["original_image"])
    has_coordinates = coordinates is not None

    return {
        "slug": slug,
        "name": name,
        "name_ar": name_ar,
        "category": category,
        "subcategory": subcategory,
        "region": region,
        "period": period,
        "description": description,
        "description_ar": description_ar,
        "highlights": highlights or [],
        "visiting_tips": visiting_tips or [],
        "historical_significance": historical_significance,
        "coordinates": coordinates,
        "related_sites": related_sites or [],
        "parent_site": parent_site,
        "child_sites": child_sites or [],
        "tags": tags or [],
        "has_image": has_image,
        "has_coordinates": has_coordinates,
        "thumbnail": wiki["thumbnail"],
        "original_image": wiki["original_image"],
        "wikipedia_url": wiki["wiki_url"],
    }


# Import site definitions from separate modules
from scripts._sites_pharaonic import get_pharaonic_sites
from scripts._sites_greco_coptic import get_greco_roman_sites, get_coptic_sites
from scripts._sites_islamic import get_islamic_sites
from scripts._sites_museums import get_museum_sites
from scripts._sites_natural import get_natural_sites
from scripts._sites_modern_resort import get_modern_sites, get_resort_sites


def build_all_sites() -> list[dict]:
    """Build the complete site list from all category modules."""
    all_sites: list[dict] = []

    all_sites.extend(get_pharaonic_sites(_site))
    all_sites.extend(get_greco_roman_sites(_site))
    all_sites.extend(get_coptic_sites(_site))
    all_sites.extend(get_islamic_sites(_site))
    all_sites.extend(get_museum_sites(_site))
    all_sites.extend(get_natural_sites(_site))
    all_sites.extend(get_modern_sites(_site))
    all_sites.extend(get_resort_sites(_site))

    # Deduplicate by slug
    seen: set[str] = set()
    unique: list[dict] = []
    for site in all_sites:
        slug = site["slug"]
        if slug not in seen:
            seen.add(slug)
            unique.append(site)

    # Sort by category then name
    unique.sort(key=lambda s: (s["category"], s["name"]))
    return unique


def main():
    sites = build_all_sites()
    # Stats
    cats = {}
    for s in sites:
        c = s["category"]
        cats[c] = cats.get(c, 0) + 1

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sites, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(sites)} sites to {OUTPUT}")
    print("Categories:")
    for k, v in sorted(cats.items()):
        print(f"  {k}: {v}")
    # Count enrichment
    with_ar = sum(1 for s in sites if s["name_ar"])
    with_coords = sum(1 for s in sites if s["has_coordinates"])
    with_img = sum(1 for s in sites if s["has_image"])
    with_desc = sum(1 for s in sites if len(s["description"]) > 50)
    print(f"With Arabic name: {with_ar}/{len(sites)}")
    print(f"With coordinates: {with_coords}/{len(sites)}")
    print(f"With image: {with_img}/{len(sites)}")
    print(f"With description: {with_desc}/{len(sites)}")


if __name__ == "__main__":
    main()
