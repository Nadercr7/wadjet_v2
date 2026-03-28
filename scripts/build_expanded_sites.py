"""Build expanded_sites.json from per-category data modules + section children.

Usage:
    python scripts/build_expanded_sites.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# ── base category modules ──
from sites_data.pharaonic_pyramids import SITES as PYRAMIDS
from sites_data.pharaonic_temples import SITES as TEMPLES
from sites_data.pharaonic_tombs import SITES as TOMBS
from sites_data.pharaonic_monuments import SITES as MONUMENTS
from sites_data.pharaonic_cities import SITES as CITIES
from sites_data.islamic import SITES as ISLAMIC
from sites_data.coptic import SITES as COPTIC
from sites_data.greco_roman import SITES as GRECO
from sites_data.museums import SITES as MUSEUMS
from sites_data.natural import SITES as NATURAL
from sites_data.modern import SITES as MODERN
from sites_data.resort import SITES as RESORT
from sites_data.experiences import SITES as EXPERIENCES

# ── child-section modules ──
from sites_data.gem_sections import GEM_CHILDREN
from sites_data.egyptian_museum_sections import EGYPTIAN_MUSEUM_CHILDREN
from sites_data.karnak_sections import KARNAK_CHILDREN
from sites_data.giza_sections import GIZA_CHILDREN
from sites_data.valley_of_kings_sections import VALLEY_OF_KINGS_CHILDREN
from sites_data.abu_simbel_sections import ABU_SIMBEL_CHILDREN
from sites_data.saqqara_sections import SAQQARA_CHILDREN
from sites_data.luxor_temple_sections import LUXOR_TEMPLE_CHILDREN
from sites_data.islamic_cairo_sections import ISLAMIC_CAIRO_CHILDREN
from sites_data.coptic_cairo_sections import COPTIC_CAIRO_CHILDREN
from sites_data.dahshur_memphis_sections import DAHSHUR_CHILDREN, MEMPHIS_CHILDREN
from sites_data.natural_sections import SIWA_CHILDREN, WHITE_DESERT_CHILDREN
from sites_data.citadel_sections import CITADEL_CHILDREN
from sites_data.hatshepsut_sections import HATSHEPSUT_CHILDREN
from sites_data.temple_sections import (
    PHILAE_CHILDREN, DENDERA_CHILDREN, EDFU_CHILDREN, KOM_OMBO_CHILDREN,
)
from sites_data.cultural_sections import (
    NMEC_CHILDREN, BIBLIOTHECA_CHILDREN, KHAN_EL_KHALILI_CHILDREN,
    ABYDOS_CHILDREN, ST_CATHERINE_CHILDREN,
)

ALL_CHILDREN = (
    GEM_CHILDREN + EGYPTIAN_MUSEUM_CHILDREN + KARNAK_CHILDREN
    + GIZA_CHILDREN + VALLEY_OF_KINGS_CHILDREN + ABU_SIMBEL_CHILDREN
    + SAQQARA_CHILDREN + LUXOR_TEMPLE_CHILDREN + ISLAMIC_CAIRO_CHILDREN
    + COPTIC_CAIRO_CHILDREN + DAHSHUR_CHILDREN + MEMPHIS_CHILDREN
    + SIWA_CHILDREN + WHITE_DESERT_CHILDREN
    + CITADEL_CHILDREN + HATSHEPSUT_CHILDREN
    + PHILAE_CHILDREN + DENDERA_CHILDREN + EDFU_CHILDREN + KOM_OMBO_CHILDREN
    + NMEC_CHILDREN + BIBLIOTHECA_CHILDREN + KHAN_EL_KHALILI_CHILDREN
    + ABYDOS_CHILDREN + ST_CATHERINE_CHILDREN
)

OUT = Path(__file__).parent.parent / "data" / "expanded_sites.json"


# Top-level sites that should be marked as 'featured' (famous + must-visit)
_FEATURED_SLUGS = {
    # Pharaonic
    "great_pyramids_of_giza", "abu_simbel", "valley_of_the_kings",
    "karnak_temple", "luxor_temple", "hatshepsut_temple",
    "saqqara_necropolis", "pyramid_of_djoser", "dahshur_necropolis",
    "dendera_temple", "edfu_temple", "philae_temple", "abydos_temple",
    "kom_ombo_temple", "temple_of_hatshepsut",
    # Islamic
    "islamic_cairo", "cairo_citadel", "khan_el_khalili",
    "al_azhar_mosque", "mosque_of_muhammad_ali",
    # Coptic
    "coptic_cairo", "saint_catherine_monastery",
    # Greco-Roman
    "bibliotheca_alexandrina", "citadel_of_qaitbay",
    # Museum
    "grand_egyptian_museum", "egyptian_museum",
    "national_museum_of_egyptian_civilization", "nmec",
    # Natural
    "siwa_oasis", "white_desert", "red_sea_coral_reefs",
    # Modern
    "aswan_high_dam", "cairo_tower",
    # Experiences
    "nile_cruise", "hot_air_balloon_luxor",
    # New additions
    "abu_mena", "blue_hole_dahab", "aga_khan_mausoleum",
}


def _normalise(site: dict) -> dict:
    """Ensure every site has the full schema with defaults."""
    site.setdefault("parent_slug", None)
    site.setdefault("children_slugs", [])
    site.setdefault("images", [])
    site.setdefault("sections", [])
    # Auto-feature well-known sites
    if site["slug"] in _FEATURED_SLUGS:
        site["featured"] = True
    else:
        site.setdefault("featured", False)
    return site


def build():
    # base sites
    all_sites = (
        PYRAMIDS + TEMPLES + TOMBS + MONUMENTS + CITIES
        + ISLAMIC + COPTIC + GRECO + MUSEUMS + NATURAL + MODERN + RESORT
        + EXPERIENCES
    )

    # add children
    all_sites += ALL_CHILDREN

    # Deduplicate by slug
    seen = set()
    unique = []
    for s in all_sites:
        s = _normalise(s)
        if s["slug"] not in seen:
            seen.add(s["slug"])
            unique.append(s)

    # Wire parent → children_slugs
    slug_map = {s["slug"]: s for s in unique}
    for s in unique:
        parent = s.get("parent_slug")
        if parent and parent in slug_map:
            p = slug_map[parent]
            if s["slug"] not in p["children_slugs"]:
                p["children_slugs"].append(s["slug"])

    # Sort: featured first, then category, then name
    unique.sort(key=lambda s: (not s.get("featured", False), s["category"], s["name"]))

    # Stats
    top_level = [s for s in unique if not s.get("parent_slug")]
    children = [s for s in unique if s.get("parent_slug")]
    print(f"Total sites: {len(unique)}  (top-level: {len(top_level)}, children: {len(children)})")
    cats = {}
    for s in unique:
        cats[s["category"]] = cats.get(s["category"], 0) + 1
    for c, n in sorted(cats.items()):
        print(f"  {c}: {n}")
    parents_with_children = [s["slug"] for s in unique if s["children_slugs"]]
    print(f"Sites with children: {len(parents_with_children)}")
    for p in parents_with_children:
        print(f"  {p} → {len(slug_map[p]['children_slugs'])} children")

    OUT.write_text(json.dumps(unique, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written to {OUT}")


if __name__ == "__main__":
    build()
