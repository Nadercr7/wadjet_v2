"""Pre-generate all story chapter images locally using Cloudflare FLUX/SDXL.

Usage:
    python scripts/pregenearte_story_images.py

Requires .env with CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.image_service import generate_story_image, CACHE_DIR, _cache_key


async def main():
    stories_dir = Path("data/stories")
    total = 0
    generated = 0
    skipped = 0
    failed = 0

    for story_file in sorted(stories_dir.glob("*.json")):
        story_id = story_file.stem
        with open(story_file, encoding="utf-8") as f:
            story = json.load(f)

        chapters = story.get("chapters", [])
        for idx, chapter in enumerate(chapters):
            prompt = chapter.get("scene_image_prompt", "")
            if not prompt:
                continue

            total += 1
            key = _cache_key(story_id, idx, prompt)
            cache_path = CACHE_DIR / f"{key}.png"

            if cache_path.exists():
                print(f"  [SKIP] {story_id} ch{idx} (cached)")
                skipped += 1
                continue

            print(f"  [GEN]  {story_id} ch{idx} ...", end=" ", flush=True)
            url = await generate_story_image(prompt, story_id, idx)
            if url:
                print("OK")
                generated += 1
            else:
                print("FAILED")
                failed += 1

            # Small delay to avoid rate limits
            await asyncio.sleep(1)

    print(f"\nDone: {total} total, {skipped} cached, {generated} generated, {failed} failed")


if __name__ == "__main__":
    asyncio.run(main())
