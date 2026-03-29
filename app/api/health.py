import asyncio
import logging

from fastapi import APIRouter, Request
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

_VERSION = "3.0.0-beta"


async def _check_db() -> bool:
    from app.db.database import async_session

    async with async_session() as session:
        await session.execute(text("SELECT 1"))
    return True


@router.get("/health")
async def health_check(request: Request):
    """Health check — returns version, DB status, and available AI services."""
    # DB connectivity (with timeout to prevent hangs)
    db_ok = False
    try:
        db_ok = await asyncio.wait_for(_check_db(), timeout=3.0)
    except Exception:
        logger.warning("Health check: DB unreachable")

    # AI service availability
    services = {}
    for name in ("gemini", "grok", "groq", "translator"):
        services[name] = getattr(request.app.state, name, None) is not None

    return {
        "status": "ok" if db_ok else "degraded",
        "version": _VERSION,
        "database": "connected" if db_ok else "unavailable",
        "services": services,
    }
