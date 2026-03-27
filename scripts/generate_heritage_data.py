"""Generate expanded Egyptian heritage site data (200+ sites).

Uses Wikipedia API to fetch real data for Egyptian landmarks, temples,
mosques, churches, museums, nature reserves, and other heritage sites.

Usage:
    python scripts/generate_heritage_data.py --dry-run     # Preview what will be generated
    python scripts/generate_heritage_data.py --execute      # Generate and save files
    python scripts/generate_heritage_data.py --execute --skip-existing  # Skip already-existing files

Output:
    data/text/{slug}.json       — Wikipedia text data
    data/expanded_sites.json    — Master list of all generated sites
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEXT_DIR = PROJECT_ROOT / "data" / "text"
OUTPUT_FILE = PROJECT_ROOT / "data" / "expanded_sites.json"

# ── Comprehensive list of Egyptian heritage sites ──
# Organized by category. Each entry: (wikipedia_title, slug, category, city/region)

SITES: list[tuple[str, str, str, str]] = [
    # === PHARAONIC TEMPLES & MONUMENTS ===
    ("Great Pyramid of Giza", "great_pyramid_of_giza", "Pharaonic", "Giza"),
    ("Pyramid of Khafre", "pyramid_of_khafre", "Pharaonic", "Giza"),
    ("Pyramid of Menkaure", "pyramid_of_menkaure", "Pharaonic", "Giza"),
    ("Great Sphinx of Giza", "great_sphinx_of_giza", "Pharaonic", "Giza"),
    ("Step Pyramid of Djoser", "step_pyramid_of_djoser", "Pharaonic", "Saqqara"),
    ("Pyramid of Unas", "pyramid_of_unas", "Pharaonic", "Saqqara"),
    ("Bent Pyramid", "bent_pyramid", "Pharaonic", "Dahshur"),
    ("Red Pyramid", "red_pyramid", "Pharaonic", "Dahshur"),
    ("Karnak", "karnak_temple", "Pharaonic", "Luxor"),
    ("Luxor Temple", "luxor_temple", "Pharaonic", "Luxor"),
    ("Valley of the Kings", "valley_of_the_kings", "Pharaonic", "Luxor"),
    ("Valley of the Queens", "valley_of_the_queens", "Pharaonic", "Luxor"),
    ("Mortuary Temple of Hatshepsut", "temple_of_hatshepsut", "Pharaonic", "Luxor"),
    ("Ramesseum", "ramesseum", "Pharaonic", "Luxor"),
    ("Medinet Habu", "medinet_habu", "Pharaonic", "Luxor"),
    ("Colossi of Memnon", "colossi_of_memnon", "Pharaonic", "Luxor"),
    ("Abu Simbel temples", "abu_simbel", "Pharaonic", "Aswan"),
    ("Philae", "philae_temple", "Pharaonic", "Aswan"),
    ("Temple of Kom Ombo", "kom_ombo_temple", "Pharaonic", "Aswan"),
    ("Temple of Edfu", "edfu_temple", "Pharaonic", "Edfu"),
    ("Temple of Esna", "esna_temple", "Pharaonic", "Esna"),
    ("Dendera Temple complex", "dendera_temple", "Pharaonic", "Qena"),
    ("Abydos, Egypt", "abydos_temple", "Pharaonic", "Sohag"),
    ("Unfinished obelisk", "unfinished_obelisk", "Pharaonic", "Aswan"),
    ("Temple of Kalabsha", "kalabsha_temple", "Pharaonic", "Aswan"),
    ("Deir el-Medina", "deir_el_medina", "Pharaonic", "Luxor"),
    ("Tomb of Nefertari", "tomb_of_nefertari", "Pharaonic", "Luxor"),
    ("KV62", "tomb_of_tutankhamun", "Pharaonic", "Luxor"),
    ("KV17", "tomb_of_seti_i", "Pharaonic", "Luxor"),
    ("Serapeum of Saqqara", "serapeum_of_saqqara", "Pharaonic", "Saqqara"),
    ("Memphis, Egypt", "memphis_ruins", "Pharaonic", "Giza"),
    ("Meidum", "meidum_pyramid", "Pharaonic", "Beni Suef"),
    ("Temple of Hibis", "temple_of_hibis", "Pharaonic", "Kharga Oasis"),
    ("Wadi el-Sebua", "wadi_el_sebua", "Pharaonic", "Aswan"),
    ("Amada", "temple_of_amada", "Pharaonic", "Aswan"),
    ("Temple of Derr", "temple_of_derr", "Pharaonic", "Aswan"),
    ("Beni Hasan", "beni_hasan", "Pharaonic", "Minya"),
    ("Tell el-Amarna", "tell_el_amarna", "Pharaonic", "Minya"),
    ("Temple of Seti I (Abydos)", "temple_of_seti_i_abydos", "Pharaonic", "Sohag"),
    ("Tanis", "tanis", "Pharaonic", "Sharqia"),
    ("Temple of Luxor", "avenue_of_sphinxes", "Pharaonic", "Luxor"),

    # === ISLAMIC HERITAGE ===
    ("Al-Azhar Mosque", "al_azhar_mosque", "Islamic", "Cairo"),
    ("Mosque of Ibn Tulun", "ibn_tulun_mosque", "Islamic", "Cairo"),
    ("Al-Hakim Mosque", "al_hakim_mosque", "Islamic", "Cairo"),
    ("Sultan Hassan Mosque", "sultan_hassan_mosque", "Islamic", "Cairo"),
    ("Al-Rifa'i Mosque", "al_rifai_mosque", "Islamic", "Cairo"),
    ("Mosque of Muhammad Ali", "muhammad_ali_mosque", "Islamic", "Cairo"),
    ("Mosque of Amr ibn al-As", "amr_ibn_al_as_mosque", "Islamic", "Cairo"),
    ("Al-Azhar Park", "al_azhar_park", "Islamic", "Cairo"),
    ("Khan el-Khalili", "khan_el_khalili", "Islamic", "Cairo"),
    ("Al-Muizz li-Din Allah Street", "al_muizz_street", "Islamic", "Cairo"),
    ("Bab Zuweila", "bab_zuweila", "Islamic", "Cairo"),
    ("Cairo Citadel", "cairo_citadel", "Islamic", "Cairo"),
    ("Mosque of al-Zahir Baybars", "baybars_mosque", "Islamic", "Cairo"),
    ("Madrasa of al-Salih Ayyub", "madrasa_al_salih_ayyub", "Islamic", "Cairo"),
    ("Complex of Sultan al-Ghuri", "sultan_al_ghuri_complex", "Islamic", "Cairo"),
    ("Wikala of al-Ghuri", "wikala_al_ghuri", "Islamic", "Cairo"),
    ("Bayt Al-Suhaymi", "bayt_al_suhaymi", "Islamic", "Cairo"),
    ("Al-Hussein Mosque", "al_hussein_mosque", "Islamic", "Cairo"),
    ("Mosque of Qalawun", "qalawun_complex", "Islamic", "Cairo"),
    ("Barquq Mosque", "barquq_mosque", "Islamic", "Cairo"),

    # === COPTIC & CHRISTIAN ===
    ("Hanging Church", "hanging_church", "Coptic", "Cairo"),
    ("Church of St. Sergius and Bacchus (Cairo)", "saints_sergius_and_bacchus_church", "Coptic", "Cairo"),
    ("Coptic Museum", "coptic_museum", "Coptic", "Cairo"),
    ("Saint Catherine's Monastery", "saint_catherine_monastery", "Coptic", "Sinai"),
    ("Monastery of Saint Anthony", "monastery_of_saint_anthony", "Coptic", "Red Sea"),
    ("Monastery of Saint Paul the Anchorite", "monastery_of_saint_paul", "Coptic", "Red Sea"),
    ("White Monastery", "white_monastery", "Coptic", "Sohag"),
    ("Red Monastery", "red_monastery", "Coptic", "Sohag"),
    ("Wadi El Natrun", "wadi_el_natrun", "Coptic", "Beheira"),

    # === GRECO-ROMAN ===
    ("Bibliotheca Alexandrina", "bibliotheca_alexandrina", "Greco-Roman", "Alexandria"),
    ("Citadel of Qaitbay", "qaitbay_citadel", "Greco-Roman", "Alexandria"),
    ("Catacombs of Kom El Shoqafa", "catacombs_kom_el_shoqafa", "Greco-Roman", "Alexandria"),
    ("Pompey's Pillar (column)", "pompey_pillar", "Greco-Roman", "Alexandria"),
    ("Stanley Bridge, Alexandria", "stanley_bridge", "Modern", "Alexandria"),
    ("Montaza Palace", "montaza_palace", "Modern", "Alexandria"),
    ("Roman amphitheatre of Alexandria", "roman_amphitheatre_alexandria", "Greco-Roman", "Alexandria"),
    ("Graeco-Roman Museum", "greco_roman_museum", "Greco-Roman", "Alexandria"),
    ("El Alamein War Cemetery", "el_alamein_war_cemetery", "Modern", "Marsa Matruh"),

    # === MUSEUMS ===
    ("Egyptian Museum", "egyptian_museum", "Museum", "Cairo"),
    ("Grand Egyptian Museum", "grand_egyptian_museum", "Museum", "Giza"),
    ("National Museum of Egyptian Civilization", "nmec", "Museum", "Cairo"),
    ("Luxor Museum", "luxor_museum", "Museum", "Luxor"),
    ("Nubia Museum", "nubia_museum", "Museum", "Aswan"),
    ("Museum of Islamic Art, Cairo", "museum_of_islamic_art", "Museum", "Cairo"),
    ("Manial Palace", "manial_palace", "Museum", "Cairo"),
    ("Abdeen Palace", "abdeen_palace", "Museum", "Cairo"),
    ("Royal Jewelry Museum", "royal_jewelry_museum", "Museum", "Alexandria"),

    # === NATURE & DESERT ===
    ("White Desert", "white_desert", "Nature", "Farafra Oasis"),
    ("Black Desert (Egypt)", "black_desert", "Nature", "Bahariya Oasis"),
    ("Siwa Oasis", "siwa_oasis", "Nature", "Siwa"),
    ("Bahariya Oasis", "bahariya_oasis", "Nature", "Bahariya Oasis"),
    ("Farafra", "farafra_oasis", "Nature", "Farafra Oasis"),
    ("Dakhla Oasis", "dakhla_oasis", "Nature", "Dakhla Oasis"),
    ("Kharga Oasis", "kharga_oasis", "Nature", "Kharga Oasis"),
    ("Wadi El Hitan", "wadi_el_hitan", "Nature", "Fayoum"),
    ("Fayoum Oasis", "fayoum_oasis", "Nature", "Fayoum"),
    ("Lake Qarun", "lake_qarun", "Nature", "Fayoum"),
    ("Ras Muhammad", "ras_muhammad", "Nature", "Sinai"),
    ("Wadi Rayan", "wadi_rayan", "Nature", "Fayoum"),
    ("Colored Canyon", "colored_canyon", "Nature", "Sinai"),
    ("Tiran Island", "tiran_island", "Nature", "Sinai"),
    ("Dahab", "dahab", "Nature", "Sinai"),
    ("Lake Nasser", "lake_nasser", "Nature", "Aswan"),

    # === MODERN & URBAN ===
    ("Cairo Tower", "cairo_tower", "Modern", "Cairo"),
    ("Baron Empain Palace", "baron_empain_palace", "Modern", "Cairo"),
    ("Ben Ezra Synagogue", "ben_ezra_synagogue", "Historic", "Cairo"),
    ("Saladin Citadel of Cairo", "saladin_citadel", "Historic", "Cairo"),
    ("City of the Dead (Cairo)", "city_of_the_dead", "Historic", "Cairo"),
    ("Gezira Island", "gezira_island", "Modern", "Cairo"),
    ("Zamalek", "zamalek", "Modern", "Cairo"),
    ("Islamic Cairo", "islamic_cairo", "Historic", "Cairo"),
    ("Aswan Dam", "aswan_dam", "Modern", "Aswan"),
    ("Suez Canal", "suez_canal", "Modern", "Suez"),
    ("Nile Corniche Cairo", "nile_corniche", "Modern", "Cairo"),

    # === SINAI ===
    ("Mount Sinai", "mount_sinai", "Historic", "Sinai"),
    ("Sharm El Sheikh", "sharm_el_sheikh", "Modern", "Sinai"),
    ("Hurghada", "hurghada", "Modern", "Red Sea"),
    ("Ain Sokhna", "ain_sokhna", "Modern", "Suez"),
    ("Nuweiba", "nuweiba", "Nature", "Sinai"),
    ("Taba, Egypt", "taba", "Nature", "Sinai"),

    # === ADDITIONAL PHARAONIC ===
    ("Lahun", "lahun_pyramid", "Pharaonic", "Fayoum"),
    ("Hawara", "hawara_pyramid", "Pharaonic", "Fayoum"),
    ("Abu Rawash", "abu_rawash", "Pharaonic", "Giza"),
    ("Dahshur", "dahshur_necropolis", "Pharaonic", "Giza"),
    ("Saqqara", "saqqara_necropolis", "Pharaonic", "Giza"),
    ("Mastaba of Ti", "mastaba_of_ti", "Pharaonic", "Saqqara"),
    ("Tombs of the Nobles", "tombs_of_the_nobles_luxor", "Pharaonic", "Luxor"),
    ("Temple of Isis (Philae)", "temple_of_isis_philae", "Pharaonic", "Aswan"),
    ("Elephantine", "elephantine_island", "Pharaonic", "Aswan"),
    ("Kitchener's Island", "kitchener_island_aswan", "Nature", "Aswan"),
    ("Temple of Mandulis", "temple_of_mandulis", "Pharaonic", "Aswan"),
    ("Crocodilopolis", "crocodilopolis", "Pharaonic", "Fayoum"),
    ("Per-Ramesses", "per_ramesses", "Pharaonic", "Sharqia"),
    ("Bubastis", "bubastis", "Pharaonic", "Sharqia"),

    # === UNESCO WORLD HERITAGE ===
    ("Historic Cairo", "historic_cairo", "Historic", "Cairo"),
    ("Ancient Thebes with its Necropolis", "ancient_thebes", "Pharaonic", "Luxor"),
    ("Nubian Monuments from Abu Simbel to Philae", "nubian_monuments", "Pharaonic", "Aswan"),
    ("Saint Catherine Area", "saint_catherine_area", "Nature", "Sinai"),

    # === FORTS & MILITARY ===
    ("Fort of Babylon (Egypt)", "babylon_fortress", "Greco-Roman", "Cairo"),
    ("Qasr Ibrim", "qasr_ibrim", "Historic", "Aswan"),
    ("Rosetta (city)", "rosetta_city", "Historic", "Beheira"),
]


WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"


def _fetch_wiki_summary(title: str) -> dict | None:
    """Fetch summary data from Wikipedia REST API."""
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"{WIKI_API}{encoded}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Wadjet-v2/1.0 (heritage app)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("  Failed to fetch '%s': %s", title, e)
        return None


def _build_site_data(wiki_title: str, slug: str, category: str, region: str) -> dict:
    """Build a site data dict from Wikipedia API response."""
    summary = _fetch_wiki_summary(wiki_title)
    if not summary:
        return {
            "slug": slug,
            "category": category,
            "region": region,
            "wikipedia": {
                "en": {
                    "title": wiki_title,
                    "extract": "",
                    "description": "",
                    "coordinates": None,
                    "thumbnail": "",
                    "original_image": "",
                    "wikipedia_url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(wiki_title.replace(' ', '_'), safe='')}",
                }
            },
        }

    coords = summary.get("coordinates")
    coord_dict = None
    if coords:
        coord_dict = {"lat": coords.get("lat"), "lon": coords.get("lon")}

    thumbnail = ""
    if summary.get("thumbnail"):
        thumbnail = summary["thumbnail"].get("source", "")

    original_image = ""
    if summary.get("originalimage"):
        original_image = summary["originalimage"].get("source", "")

    return {
        "slug": slug,
        "category": category,
        "region": region,
        "wikipedia": {
            "en": {
                "title": summary.get("title", wiki_title),
                "extract": summary.get("extract", ""),
                "description": summary.get("description", ""),
                "coordinates": coord_dict,
                "thumbnail": thumbnail,
                "original_image": original_image,
                "wikipedia_url": summary.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate expanded Egyptian heritage site data")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--execute", action="store_true", help="Generate and save files")
    parser.add_argument("--skip-existing", action="store_true", help="Skip slugs that already have data")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    existing = {f.stem for f in TEXT_DIR.glob("*.json")} if args.skip_existing else set()

    logger.info("Heritage sites to generate: %d", len(SITES))
    logger.info("Existing text files: %d", len(existing))

    if args.dry_run:
        new_count = 0
        for wiki_title, slug, category, region in SITES:
            status = "SKIP" if slug in existing else "NEW"
            if status == "NEW":
                new_count += 1
            print(f"  [{status}] {slug:40s} <- {wiki_title} ({category}, {region})")
        logger.info("Would generate %d new files (skip %d existing)", new_count, len(SITES) - new_count)
        return

    # Execute mode
    generated = []
    skipped = 0
    failed = 0

    for i, (wiki_title, slug, category, region) in enumerate(SITES):
        if slug in existing:
            skipped += 1
            continue

        logger.info("[%d/%d] Fetching: %s ...", i + 1, len(SITES), slug)
        site_data = _build_site_data(wiki_title, slug, category, region)

        # Save individual text file
        out_path = TEXT_DIR / f"{slug}.json"
        try:
            out_path.write_text(json.dumps(site_data, indent=2, ensure_ascii=False), encoding="utf-8")
            generated.append(site_data)
            logger.info("  ✓ Saved %s", out_path.name)
        except Exception as e:
            logger.error("  ✗ Failed to save %s: %s", slug, e)
            failed += 1

        # Rate-limit Wikipedia API
        time.sleep(0.3)

    # Save master list
    master = []
    for f in sorted(TEXT_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            en = data.get("wikipedia", {}).get("en", {})
            master.append({
                "slug": data.get("slug", f.stem),
                "name": en.get("title", f.stem.replace("_", " ").title()),
                "category": data.get("category", ""),
                "region": data.get("region", ""),
                "description": en.get("description", ""),
                "has_image": bool(en.get("thumbnail") or en.get("original_image")),
                "has_coordinates": bool(en.get("coordinates")),
            })
        except Exception:
            pass

    OUTPUT_FILE.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("=" * 60)
    logger.info("Done! Generated: %d, Skipped: %d, Failed: %d", len(generated), skipped, failed)
    logger.info("Total sites in master list: %d", len(master))
    logger.info("Master list: %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()
