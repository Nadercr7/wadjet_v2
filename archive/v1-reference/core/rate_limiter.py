"""
Wadjet AI — Rate Limiting Configuration.

Provides a pre-configured SlowAPI limiter with per-endpoint limit decorators.
Uses the client's real IP address as the key function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

if TYPE_CHECKING:
    from starlette.requests import Request

# ---------------------------------------------------------------------------
# Key function — extract real client IP (respects X-Forwarded-For behind proxy)
# ---------------------------------------------------------------------------


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting reverse-proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the chain is the real client
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# ---------------------------------------------------------------------------
# Limiter singleton
# ---------------------------------------------------------------------------

_settings = get_settings()

limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=[_settings.rate_limit_default],
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# Per-endpoint limit strings (importable for use as decorators)
# ---------------------------------------------------------------------------

RATE_LIMIT_IDENTIFY: str = _settings.rate_limit_identify  # 30/minute
RATE_LIMIT_CHAT: str = _settings.rate_limit_chat  # 20/minute
RATE_LIMIT_RECOMMENDATIONS: str = _settings.rate_limit_recommendations  # 60/minute
RATE_LIMIT_DEFAULT: str = _settings.rate_limit_default  # 100/minute
