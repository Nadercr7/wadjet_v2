r"""Scrape hieroglyph images from museum APIs and open collections.

Each museum is implemented as a separate spider class. All spiders:
- Download high-res images
- Save per-image metadata (source, license, URL)
- Support resume (skip already-downloaded images)
- Respect rate limits

Usage:
    # Activate dataprep-env first:
    #   & scripts\dataprep-env\Scripts\Activate.ps1

    # Run all spiders:
    python scripts/scrape_museums.py --output "data/detection/scraped" --all

    # Run specific spider:
    python scripts/scrape_museums.py --output "data/detection/scraped" --spider met

    # List available spiders:
    python scripts/scrape_museums.py --list

    # Limit downloads per spider (for testing):
    python scripts/scrape_museums.py --output "data/detection/scraped" --spider met --limit 50

Museums with public REST APIs (no auth needed):
    met         Metropolitan Museum of Art (CC0, ~800-1000 images)
    wikimedia   Wikimedia Commons (CC BY-SA / PD, ~400-500)
    brooklyn    Brooklyn Museum (needs API key, CC0, ~100-150)
    europeana   Europeana (needs API key, ~100-150)

Museums needing web scraping (future, requires Scrapling/browser-use):
    british     British Museum IIIF
    louvre      Louvre Collections
    museo_egizio Museo Egizio Turin
"""

import argparse
import hashlib
import json
import random
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

# ---------------------------------------------------------------------------
# Base Spider
# ---------------------------------------------------------------------------

class MuseumSpider(ABC):
    """Base class for museum image scrapers."""

    name: str = "base"
    description: str = ""
    license: str = ""
    rate_limit: float = 1.0  # seconds between requests

    def __init__(self, output_dir: Path, limit: int = 0):
        self.output_dir = output_dir / self.name
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.limit = limit
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Wadjet-v2-Research/1.0 (academic hieroglyph detection research)"
        })
        self.downloaded = 0
        self.skipped = 0
        self.errors = 0
        self.metadata: list[dict] = []
        self._load_existing()

    def _load_existing(self):
        """Load existing metadata to support resume."""
        meta_path = self.output_dir / "metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.metadata = data.get("images", [])
            self._existing_ids = {m["source_id"] for m in self.metadata}
            print(f"  Resuming {self.name}: {len(self._existing_ids)} already downloaded")
        else:
            self._existing_ids = set()

    def _save_metadata(self):
        """Save metadata to disk."""
        meta_path = self.output_dir / "metadata.json"
        data = {
            "spider": self.name,
            "license": self.license,
            "total_images": len(self.metadata),
            "images": self.metadata,
        }
        meta_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _download_image(self, url: str, source_id: str, extra_meta: dict = None) -> bool:
        """Download an image and save it with metadata."""
        if source_id in self._existing_ids:
            self.skipped += 1
            return False

        if self.limit > 0 and self.downloaded >= self.limit:
            return False

        try:
            # Retry with backoff for rate limiting
            for attempt in range(3):
                resp = self.session.get(url, timeout=30, stream=True)
                if resp.status_code == 429:
                    wait = (attempt + 1) * 5
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                break
            else:
                self.errors += 1
                return False

            # Determine extension from content type or URL
            content_type = resp.headers.get("content-type", "")
            ext = ".jpg"
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            else:
                url_ext = Path(urlparse(url).path).suffix.lower()
                if url_ext in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
                    ext = url_ext

            # Safe filename from source_id
            safe_name = f"{self.name}_{source_id}{ext}"
            safe_name = safe_name.replace("/", "_").replace("\\", "_")
            dest = self.images_dir / safe_name

            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            entry = {
                "source_id": source_id,
                "filename": safe_name,
                "url": url,
                "spider": self.name,
                "license": self.license,
            }
            if extra_meta:
                entry.update(extra_meta)
            self.metadata.append(entry)
            self._existing_ids.add(source_id)

            self.downloaded += 1
            return True

        except Exception as e:
            self.errors += 1
            if self.errors <= 5:
                print(f"    ERROR downloading {source_id}: {e}")
            return False

    def _rate_wait(self):
        """Wait between requests to respect rate limits."""
        time.sleep(self.rate_limit)

    @abstractmethod
    def scrape(self):
        """Run the scraper. Implement in subclass."""
        ...

    def run(self):
        """Execute spider with progress tracking."""
        print(f"\n{'='*60}")
        print(f"  Spider: {self.name} — {self.description}")
        print(f"  License: {self.license}")
        print(f"  Output: {self.output_dir}")
        if self.limit > 0:
            print(f"  Limit: {self.limit}")
        print(f"{'='*60}\n")

        self.scrape()
        self._save_metadata()

        print(f"\n  --- {self.name} Summary ---")
        print(f"  Downloaded: {self.downloaded}")
        print(f"  Skipped (existing): {self.skipped}")
        print(f"  Errors: {self.errors}")
        print(f"  Total in collection: {len(self.metadata)}")


# ---------------------------------------------------------------------------
# Met Museum Spider (REST API, CC0)
# ---------------------------------------------------------------------------

class MetMuseumSpider(MuseumSpider):
    """Metropolitan Museum of Art — Open Access API.

    API docs: https://metmuseum.github.io/
    All CC0 images. No API key needed.
    """

    name = "met"
    description = "Metropolitan Museum of Art (CC0)"
    license = "CC0"
    rate_limit = 0.3  # Very generous API

    BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"

    SEARCH_QUERIES = [
        "Egyptian hieroglyph",
        "hieroglyphic inscription",
        "temple relief Egyptian",
        "papyrus Egyptian text",
        "Egyptian stela limestone",
        "Egyptian coffin",
        "ostracon",
        "Egyptian funerary relief",
        "sarcophagus Egyptian",
        "canopic",
        "cartouche",
        "Book of the Dead",
        "Theban tomb",
        "Deir el-Bahri",
        "Amarna",
    ]

    def scrape(self):
        all_object_ids = set()

        # Search with multiple queries
        for query in self.SEARCH_QUERIES:
            print(f"  Searching: '{query}'...")
            try:
                resp = self.session.get(
                    f"{self.BASE_URL}/search",
                    params={
                        "q": query,
                        "hasImages": "true",
                        "isPublicDomain": "true",
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                ids = data.get("objectIDs", []) or []
                print(f"    Found {len(ids)} objects")
                all_object_ids.update(ids)
                self._rate_wait()
            except Exception as e:
                print(f"    Search error: {e}")

        print(f"\n  Total unique objects: {len(all_object_ids)}")

        # Fetch each object and download primary image
        self._dept_skips = 0
        self._no_image = 0
        object_ids = list(all_object_ids)
        random.shuffle(object_ids)  # Shuffle to avoid ID-ordered dept clustering
        for i, obj_id in enumerate(object_ids):
            if self.limit > 0 and self.downloaded >= self.limit:
                break

            source_id = str(obj_id)
            if source_id in self._existing_ids:
                self.skipped += 1
                continue

            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(all_object_ids)}] downloaded={self.downloaded} dept_skip={self._dept_skips} no_img={self._no_image}", flush=True)

            try:
                resp = self.session.get(f"{self.BASE_URL}/objects/{obj_id}", timeout=30)
                resp.raise_for_status()
                obj = resp.json()

                image_url = obj.get("primaryImage", "")
                if not image_url:
                    self._no_image += 1
                    continue

                # Only download if Egyptian-related
                dept = obj.get("department", "")
                if dept and "Egyptian" not in dept:
                    self._dept_skips += 1
                    continue

                title = obj.get("title", "")
                medium = obj.get("medium", "")
                self._download_image(
                    image_url, source_id,
                    extra_meta={
                        "title": title,
                        "medium": medium,
                        "department": dept,
                        "object_url": obj.get("objectURL", ""),
                    }
                )
                self._rate_wait()

            except Exception:
                self.errors += 1


# ---------------------------------------------------------------------------
# Wikimedia Commons Spider (MediaWiki API)
# ---------------------------------------------------------------------------

class WikimediaSpider(MuseumSpider):
    """Wikimedia Commons — MediaWiki API.

    Search categories for Egyptian hieroglyph images.
    Most are CC BY-SA or Public Domain.
    """

    name = "wikimedia"
    description = "Wikimedia Commons (CC BY-SA / PD)"
    license = "CC BY-SA / Public Domain"
    rate_limit = 2.5  # Wikimedia rate-limits aggressively

    API_URL = "https://commons.wikimedia.org/w/api.php"

    CATEGORIES = [
        "Egyptian hieroglyphs",
        "Ancient Egyptian inscriptions",
        "Egyptian stelae",
        "Hieroglyphic luwian inscriptions",
        "Hieroglyphs",
        "Ancient Egyptian reliefs",
        "Temple of Karnak",
        "Medinet Habu",
        "Valley of the Kings",
        "Tombs in Deir el-Medina",
        "Ancient Egyptian funerary texts",
        "Book of the Dead",
        "Egyptian ostraca",
        "Rosetta Stone",
    ]

    def _get_category_members(self, category: str, max_items: int = 500) -> list[str]:
        """Get file names from a Wikimedia Commons category."""
        members = []
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmtype": "file",
            "cmlimit": "50",
            "format": "json",
        }

        while len(members) < max_items:
            try:
                resp = self.session.get(self.API_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                for m in data.get("query", {}).get("categorymembers", []):
                    title = m.get("title", "")
                    if title.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
                        members.append(title)

                # Pagination
                cont = data.get("continue", {})
                if "cmcontinue" in cont:
                    params["cmcontinue"] = cont["cmcontinue"]
                else:
                    break

                self._rate_wait()
            except Exception as e:
                print(f"    Category error ({category}): {e}")
                break

        return members

    def _get_image_url(self, file_title: str) -> str | None:
        """Get direct image URL from a file title."""
        try:
            resp = self.session.get(self.API_URL, params={
                "action": "query",
                "titles": file_title,
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "iiurlwidth": "1600",  # Get resized version if very large
                "format": "json",
            }, timeout=30)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                imageinfo = page.get("imageinfo", [{}])
                if imageinfo:
                    # Prefer thumburl (resized) for manageable file sizes
                    return imageinfo[0].get("thumburl") or imageinfo[0].get("url")
        except Exception:
            pass
        return None

    def scrape(self):
        all_files = set()

        for cat in self.CATEGORIES:
            print(f"  Category: '{cat}'...")
            members = self._get_category_members(cat)
            print(f"    Found {len(members)} files")
            all_files.update(members)

        print(f"\n  Total unique files: {len(all_files)}")

        for i, file_title in enumerate(sorted(all_files)):
            if self.limit > 0 and self.downloaded >= self.limit:
                break

            # Use MD5 of title as source_id
            source_id = hashlib.md5(file_title.encode()).hexdigest()[:12]
            if source_id in self._existing_ids:
                self.skipped += 1
                continue

            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(all_files)}] downloaded={self.downloaded}", flush=True)

            url = self._get_image_url(file_title)
            if url:
                self._download_image(
                    url, source_id,
                    extra_meta={"wiki_title": file_title}
                )
            self._rate_wait()


# ---------------------------------------------------------------------------
# Brooklyn Museum Spider (REST API)
# ---------------------------------------------------------------------------

class BrooklynMuseumSpider(MuseumSpider):
    """Brooklyn Museum — Public REST API.

    API docs: https://www.brooklynmuseum.org/opencollection/api
    Needs API key (free registration).
    """

    name = "brooklyn"
    description = "Brooklyn Museum (CC0)"
    license = "CC0 / Public Domain"
    rate_limit = 0.5

    BASE_URL = "https://www.brooklynmuseum.org/api/v2"

    def __init__(self, output_dir: Path, limit: int = 0, api_key: str = ""):
        super().__init__(output_dir, limit)
        self.api_key = api_key
        if api_key:
            self.session.headers["api_key"] = api_key

    def scrape(self):
        if not self.api_key:
            print("  WARNING: Brooklyn Museum API key not set. Use --brooklyn-key <key>")
            print("  Register at: https://www.brooklynmuseum.org/opencollection/api")
            return

        # Search Egyptian collection
        offset = 0
        page_size = 25

        while True:
            if self.limit > 0 and self.downloaded >= self.limit:
                break

            try:
                resp = self.session.get(
                    f"{self.BASE_URL}/object",
                    params={
                        "collection_id": 3,  # Egyptian
                        "has_images": 1,
                        "limit": page_size,
                        "offset": offset,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                objects = data.get("data", [])

                if not objects:
                    break

                for obj in objects:
                    obj_id = str(obj.get("id", ""))
                    images = obj.get("images", [])
                    if not images:
                        continue

                    # Get largest image
                    image_url = images[0].get("largest_derivative_url", "")
                    if not image_url:
                        continue

                    self._download_image(
                        image_url, obj_id,
                        extra_meta={
                            "title": obj.get("title", ""),
                            "medium": obj.get("medium", ""),
                        }
                    )
                    self._rate_wait()

                offset += page_size
                if (offset % 100) == 0:
                    print(f"  Offset {offset}, downloaded={self.downloaded}", flush=True)

            except Exception as e:
                print(f"  Page error at offset {offset}: {e}")
                break


# ---------------------------------------------------------------------------
# Europeana Spider (Search API)
# ---------------------------------------------------------------------------

class EuropeanaSpider(MuseumSpider):
    """Europeana — Cross-museum aggregator.

    API docs: https://pro.europeana.eu/page/search
    Needs API key (free registration).
    """

    name = "europeana"
    description = "Europeana aggregated collection"
    license = "Various (mostly PD/CC)"
    rate_limit = 0.5

    API_URL = "https://api.europeana.eu/record/v2/search.json"

    SEARCH_QUERIES = [
        "Egyptian hieroglyph",
        "Egyptian inscription stela",
        "ancient Egyptian relief",
        "hieroglyphic papyrus",
    ]

    def __init__(self, output_dir: Path, limit: int = 0, api_key: str = ""):
        super().__init__(output_dir, limit)
        self.api_key = api_key

    def scrape(self):
        if not self.api_key:
            print("  WARNING: Europeana API key not set. Use --europeana-key <key>")
            print("  Register at: https://pro.europeana.eu/page/get-api")
            return

        for query in self.SEARCH_QUERIES:
            if self.limit > 0 and self.downloaded >= self.limit:
                break

            print(f"  Searching: '{query}'...")
            start = 1
            rows = 50

            while True:
                if self.limit > 0 and self.downloaded >= self.limit:
                    break

                try:
                    resp = self.session.get(self.API_URL, params={
                        "wskey": self.api_key,
                        "query": query,
                        "media": "true",
                        "thumbnail": "true",
                        "qf": "TYPE:IMAGE",
                        "rows": rows,
                        "start": start,
                    }, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()

                    items = data.get("items", [])
                    if not items:
                        break

                    for item in items:
                        item_id = item.get("id", "").replace("/", "_")
                        if not item_id:
                            continue

                        # Try to get the largest image
                        image_url = None
                        edmIsShownBy = item.get("edmIsShownBy", [])
                        if edmIsShownBy:
                            image_url = edmIsShownBy[0]
                        else:
                            # Fall back to thumbnail
                            thumbnails = item.get("edmPreview", [])
                            if thumbnails:
                                image_url = thumbnails[0]

                        if not image_url:
                            continue

                        self._download_image(
                            image_url, item_id,
                            extra_meta={
                                "title": (item.get("title", [""])[0] if isinstance(item.get("title"), list) else item.get("title", "")),
                                "provider": (item.get("dataProvider", [""])[0] if isinstance(item.get("dataProvider"), list) else item.get("dataProvider", "")),
                            }
                        )
                        self._rate_wait()

                    start += rows
                    if start > data.get("totalResults", 0):
                        break

                except Exception as e:
                    print(f"    Search error ({query}): {e}")
                    break


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SPIDERS = {
    "met": MetMuseumSpider,
    "wikimedia": WikimediaSpider,
    "brooklyn": BrooklynMuseumSpider,
    "europeana": EuropeanaSpider,
}


def main():
    parser = argparse.ArgumentParser(
        description="Scrape hieroglyph images from museum APIs"
    )
    parser.add_argument("--output", type=Path, default=Path("data/detection/scraped"),
                        help="Output directory")
    parser.add_argument("--spider", type=str, default=None,
                        help="Run specific spider (met, wikimedia, brooklyn, europeana)")
    parser.add_argument("--all", action="store_true",
                        help="Run all spiders")
    parser.add_argument("--list", action="store_true",
                        help="List available spiders")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max images to download per spider (0=unlimited)")
    parser.add_argument("--brooklyn-key", type=str, default="",
                        help="Brooklyn Museum API key")
    parser.add_argument("--europeana-key", type=str, default="",
                        help="Europeana API key")

    args = parser.parse_args()

    if args.list:
        print("\nAvailable spiders:")
        for name, cls in SPIDERS.items():
            print(f"  {name:15s} — {cls.description}")
        print()
        return

    if not args.spider and not args.all:
        parser.print_help()
        print("\nUse --spider <name> or --all to start scraping.")
        return

    spiders_to_run = []

    if args.all:
        spiders_to_run = list(SPIDERS.keys())
    elif args.spider:
        if args.spider not in SPIDERS:
            print(f"ERROR: Unknown spider '{args.spider}'. Available: {list(SPIDERS.keys())}")
            sys.exit(1)
        spiders_to_run = [args.spider]

    total_downloaded = 0
    total_errors = 0

    for name in spiders_to_run:
        cls = SPIDERS[name]
        kwargs = {"output_dir": args.output, "limit": args.limit}

        if name == "brooklyn":
            kwargs["api_key"] = args.brooklyn_key
        elif name == "europeana":
            kwargs["api_key"] = args.europeana_key

        spider = cls(**kwargs)
        spider.run()
        total_downloaded += spider.downloaded
        total_errors += spider.errors

    print(f"\n{'='*60}")
    print(f"  TOTAL downloaded: {total_downloaded}")
    print(f"  TOTAL errors: {total_errors}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
