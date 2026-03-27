import os
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_BASE = Path(__file__).parent.parent.parent


@router.get("/health")
async def health_check():
    expanded = _BASE / "data" / "expanded_sites.json"
    data_dir = _BASE / "data"
    return {
        "status": "ok",
        "version": "2.0.0",
        "base_dir": str(_BASE),
        "data_dir_exists": data_dir.exists(),
        "data_dir_contents": sorted(os.listdir(data_dir)) if data_dir.exists() else [],
        "expanded_sites_exists": expanded.exists(),
        "expanded_sites_size": expanded.stat().st_size if expanded.exists() else 0,
    }
