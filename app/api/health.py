import asyncio
import logging

from fastapi import APIRouter, Request
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

_VERSION = "3.0.0-beta"


async def _check_db() -> dict:
    """Check DB connectivity and schema integrity. Returns status dict."""
    from app.db.database import async_session

    info: dict = {"connected": False, "tables": [], "users_columns": [], "error": None}
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
        info["connected"] = True
        # Check which tables exist
        rows = await session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ))
        info["tables"] = [r[0] for r in rows]
        # Check users table columns (detect missing oauth columns)
        if "users" in info["tables"]:
            cols = await session.execute(text("PRAGMA table_info(users)"))
            info["users_columns"] = [r[1] for r in cols]
    return info


@router.get("/health")
async def health_check(request: Request):
    """Health check — returns version, DB status, and available AI services."""
    # DB connectivity + schema check (with timeout to prevent hangs)
    db_info: dict = {}
    db_error = None
    try:
        db_info = await asyncio.wait_for(_check_db(), timeout=3.0)
    except Exception as e:
        db_error = f"{type(e).__name__}: {e}"
        logger.warning("Health check: DB unreachable — %s", db_error)

    db_ok = db_info.get("connected", False)

    # Check for missing critical columns
    expected_cols = {"google_id", "auth_provider", "email_verified", "avatar_url"}
    actual_cols = set(db_info.get("users_columns", []))
    missing_cols = expected_cols - actual_cols if actual_cols else set()

    # AI service availability
    services = {}
    for name in ("gemini", "grok", "groq", "translator"):
        services[name] = getattr(request.app.state, name, None) is not None

    status = "ok"
    if not db_ok:
        status = "degraded"
    elif missing_cols:
        status = "schema_outdated"

    return {
        "status": status,
        "version": _VERSION,
        "database": {
            "connected": db_ok,
            "tables": db_info.get("tables", []),
            "users_columns": db_info.get("users_columns", []),
            "missing_columns": sorted(missing_cols) if missing_cols else [],
            "error": db_error,
        },
        "services": services,
    }
