"""Populate images[] in expanded_sites.json from wiki text data.

Reads data/text/*.json → extracts wikipedia.en.thumbnail + original_image
Matches by slug → sets images[] with proper caption and source.
For children without direct wiki match, tries parent's wiki image.

Usage:
    python scripts/populate_images.py [--dry-run]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SITES_FILE = ROOT / "data" / "expanded_sites.json"
WIKI_DIR = ROOT / "data" / "text"


def _load_wiki_images() -> dict:
    """Return {slug: {thumbnail, original_image, title}} from wiki data."""
    result = {}
    for f in sorted(WIKI_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        wp = data.get("wikipedia", {}).get("en", {})
        thumb = wp.get("thumbnail", "")
        orig = wp.get("original_image", "")
        if thumb or orig:
            result[data.get("slug", f.stem)] = {
                "thumbnail": thumb,
                "original_image": orig,
                "title": wp.get("title", data.get("slug", f.stem)),
            }
    return result


def _build_image_entry(wiki: dict, site_name: str) -> dict:
    """Create a single image entry from wiki data."""
    url = wiki.get("original_image") or wiki.get("thumbnail", "")
    if not url:
        return {}
    return {
        "url": url,
        "caption": site_name,
        "source": "Wikimedia Commons",
    }


def populate(dry_run: bool = False):
    sites = json.loads(SITES_FILE.read_text(encoding="utf-8"))
    wiki_images = _load_wiki_images()

    print(f"Sites: {len(sites)}, Wiki images available: {len(wiki_images)}")

    populated = 0
    skipped_has_images = 0
    no_match = 0
    parent_fallback = 0

    # Build slug→site map for parent lookups
    slug_map = {s["slug"]: s for s in sites}

    for site in sites:
        slug = site["slug"]

        # Skip if already has images
        if site.get("images"):
            skipped_has_images += 1
            continue

        # Try direct wiki match
        if slug in wiki_images:
            entry = _build_image_entry(wiki_images[slug], site["name"])
            if entry:
                site["images"] = [entry]
                populated += 1
                if dry_run:
                    print(f"  + {slug}: {entry['url'][:80]}...")
                continue

        # Try parent's wiki image for children
        parent_slug = site.get("parent_slug")
        if parent_slug and parent_slug in wiki_images:
            entry = _build_image_entry(wiki_images[parent_slug], site["name"])
            if entry:
                entry["caption"] = f"{site['name']} (at {slug_map.get(parent_slug, {}).get('name', parent_slug)})"
                site["images"] = [entry]
                parent_fallback += 1
                populated += 1
                if dry_run:
                    print(f"  ~ {slug} (from parent {parent_slug})")
                continue

        no_match += 1
        if dry_run:
            print(f"  ! {slug}: NO IMAGE")

    print(f"\nResults:")
    print(f"  Populated: {populated}")
    print(f"  Already had images: {skipped_has_images}")
    print(f"  Parent fallback: {parent_fallback}")
    print(f"  No match: {no_match}")

    if not dry_run:
        SITES_FILE.write_text(
            json.dumps(sites, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nWritten to {SITES_FILE}")
    else:
        print("\n[DRY RUN — no changes written]")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    populate(dry_run=dry_run)
