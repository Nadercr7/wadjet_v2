"""Rate limiter instance — shared across all API routers."""

import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _get_real_ip(request: Request) -> str:
    """Extract client IP using configurable trusted proxy depth.

    TRUSTED_PROXY_DEPTH controls how many rightmost X-Forwarded-For entries
    are trusted (added by known reverse proxies like Render, Cloudflare).
    - depth=0: ignore X-Forwarded-For entirely (direct connection)
    - depth=1: trust one proxy hop (e.g. Render) — take 1st from right
    - depth=N: trust N proxy hops — take Nth from right
    """
    from app.config import settings

    depth = settings.trusted_proxy_depth

    if depth == 0:
        return get_remote_address(request)

    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded:
        return get_remote_address(request)

    ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
    if not ips:
        return get_remote_address(request)

    # Take the Nth-from-right IP (rightmost N entries are from trusted proxies,
    # so the one just before them is the real client IP)
    index = max(0, len(ips) - depth)
    return ips[index]


limiter = Limiter(key_func=_get_real_ip)
