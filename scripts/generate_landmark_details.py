"""Pre-generate AI landmark detail fields (highlights, tips, significance).

Iterates all 260 sites, calls Gemini for non-curated ones missing detail fields,
and saves results to data/landmark_enrichment_cache.json.

Usage:
    python scripts/generate_landmark_details.py              # Preview (dry-run)
    python scripts/generate_landmark_details.py --execute     # Generate with AI
    python scripts/generate_landmark_details.py --execute --limit 20  # First 20 only
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"
SITES_FILE = DATA_DIR / "expanded_sites.json"
CACHE_FILE = DATA_DIR / "landmark_enrichment_cache.json"


def _load_curated_slugs() -> set[str]:
    from app.core.landmarks import ATTRACTIONS, get_slug
    return {get_slug(a).replace("-", "_") for a in ATTRACTIONS}


def _load_cache() -> dict[str, dict]:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8",
    )


async def _generate_one(gemini, site: dict) -> dict | None:
    """Call Gemini to generate detail fields for one site."""
    name = site.get("name", "")
    city = site.get("region", "Egypt")
    category = site.get("category", "")
    period = site.get("period", "")
    desc = site.get("description", "")[:300]

    system = "You are an expert Egyptian history and travel guide."
    prompt = (
        f'For the Egyptian landmark "{name}" in {city}'
        f'{f" ({category}, {period})" if category else ""}:\n'
        f'Description: {desc}\n\n'
        f'Generate JSON with these fields:\n'
        f'{{\n'
        f'  "highlights": "3-5 key features as bullet points separated by |",\n'
        f'  "visiting_tips": "2-3 practical tips separated by |",\n'
        f'  "historical_significance": "1-2 sentences on why this site matters"\n'
        f'}}\n'
        f'Be concise, accurate, and informative. Use known historical facts.'
    )

    try:
        text = await gemini.generate_json(
            prompt,
            system_instruction=system,
            max_output_tokens=512,
        )
        result = json.loads(text) if isinstance(text, str) else text
        if result and isinstance(result, dict):
            return {
                "highlights": result.get("highlights", ""),
                "visiting_tips": result.get("visiting_tips", ""),
                "historical_significance": result.get("historical_significance", ""),
            }
    except Exception as e:
        print(f"    ERROR: {e}")
    return None


async def main(execute: bool, limit: int | None) -> None:
    sites = json.loads(SITES_FILE.read_text(encoding="utf-8"))
    curated = _load_curated_slugs()
    cache = _load_cache()

    # Find sites needing enrichment
    needs_enrichment = []
    for site in sites:
        slug = site["slug"]
        if slug in curated:
            continue  # Curated sites have handwritten data
        if slug in cache:
            continue  # Already cached
        needs_enrichment.append(site)

    print(f"Total sites: {len(sites)}")
    print(f"Curated (skip): {len(curated)}")
    print(f"Already cached: {len(cache)}")
    print(f"Need enrichment: {len(needs_enrichment)}")

    if limit:
        needs_enrichment = needs_enrichment[:limit]
        print(f"Limited to: {limit}")

    if not execute:
        print("\nDry run — add --execute to generate.")
        for s in needs_enrichment[:20]:
            print(f"  {s['slug']:40s} {s.get('region',''):15s} {s.get('category','')}")
        if len(needs_enrichment) > 20:
            print(f"  ... and {len(needs_enrichment) - 20} more")
        return

    # Initialize Gemini
    from app.config import Settings
    settings = Settings()
    keys = settings.gemini_keys_list
    if not keys:
        print("ERROR: No Gemini API keys in .env")
        return

    from app.core.gemini_service import GeminiService
    gemini = GeminiService(keys, default_model=settings.gemini_model)

    generated = 0
    failed = 0
    start = time.time()

    for i, site in enumerate(needs_enrichment, 1):
        slug = site["slug"]
        name = site.get("name", slug)
        print(f"[{i}/{len(needs_enrichment)}] {name}...", end=" ", flush=True)

        result = await _generate_one(gemini, site)
        if result:
            cache[slug] = result
            generated += 1
            print("OK")
        else:
            failed += 1
            print("FAILED")

        # Save every 10 to avoid losing progress
        if generated % 10 == 0:
            _save_cache(cache)

        # Small delay to avoid rate limits (17 keys = 255 RPM, but be gentle)
        await asyncio.sleep(0.3)

    _save_cache(cache)
    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s: {generated} generated, {failed} failed, {len(cache)} total cached")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate AI landmark detail fields")
    parser.add_argument("--execute", action="store_true", help="Actually call AI (default: dry run)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of sites to process")
    args = parser.parse_args()
    asyncio.run(main(args.execute, args.limit))
