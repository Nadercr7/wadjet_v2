import json
import os
import traceback
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_BASE = Path(__file__).parent.parent.parent


@router.get("/health")
async def health_check():
    expanded = _BASE / "data" / "expanded_sites.json"
    data_dir = _BASE / "data"

    # Try actually loading the file the same way explore.py does
    load_result = "not attempted"
    load_count = 0
    load_error = None
    load_first_slug = None
    if expanded.exists():
        try:
            sites = json.loads(expanded.read_text(encoding="utf-8"))
            load_count = len(sites)
            load_result = "ok"
            if sites:
                load_first_slug = sites[0].get("slug", "no-slug")
                # Check children
                parents = [s for s in sites if s.get("children_slugs")]
                load_result = f"ok, {len(parents)} parents with children"
        except Exception as e:
            load_result = "failed"
            load_error = f"{type(e).__name__}: {e}"

    # Also try importing from explore module
    explore_load_result = "not attempted"
    explore_count = 0
    try:
        from app.api.explore import _load_expanded_sites
        data = _load_expanded_sites()
        explore_count = len(data)
        explore_load_result = f"ok, {explore_count} sites"
    except Exception as e:
        explore_load_result = f"failed: {type(e).__name__}: {e}"

    return {
        "status": "ok",
        "version": "2.0.0",
        "base_dir": str(_BASE),
        "data_dir_exists": data_dir.exists(),
        "data_dir_contents": sorted(os.listdir(data_dir)) if data_dir.exists() else [],
        "expanded_sites_exists": expanded.exists(),
        "expanded_sites_size": expanded.stat().st_size if expanded.exists() else 0,
        "direct_load": load_result,
        "direct_load_count": load_count,
        "direct_first_slug": load_first_slug,
        "explore_module_load": explore_load_result,
        "explore_module_count": explore_count,
    }
