"""
Wadjet AI — Analytics Middleware (Phase 7.16).

Lightweight middleware that records:
  1. Page views for tracked HTML routes (GET 2xx)
  2. Feature usage for recognised API endpoints (POST 2xx)
  3. Language usage from chat/quiz/itinerary/hieroglyph requests

Runs after ``RequestLoggingMiddleware`` (which sets ``request_id``),
appends JSONL events for privacy-friendly server-side analytics.

No cookies, no fingerprinting, no PII — just route + timestamp.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

# Lazy import to avoid circular deps at module load time.
_svc = None


def _get_svc():
    global _svc
    if _svc is None:
        from app.core.analytics_service import AnalyticsService

        _svc = AnalyticsService()
    return _svc


# API paths → feature name mapping
_API_FEATURES: dict[str, str] = {
    "/api/v1/identify": "upload",
    "/api/v1/identify/enrich": "enrich",
    "/api/v1/identify/caption": "caption",
    "/api/v1/identify/spatial": "spatial",
    "/api/v1/identify/similar": "similar",
    "/api/v1/chat": "chat",
    "/api/v1/chat/stream": "chat_stream",
    "/api/v1/quiz/question": "quiz",
    "/api/v1/quiz/generate": "quiz_generate",
    "/api/v1/itinerary/generate": "itinerary",
    "/api/v1/hieroglyphs/translate": "hieroglyph_translate",
    "/api/v1/hieroglyphs/explain": "hieroglyph_explain",
    "/api/v1/compare": "compare",
    "/api/v1/feedback/identification": "feedback_vote",
    "/api/v1/feedback/rating": "feedback_rating",
    "/api/v1/feedback/general": "feedback_general",
}


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Record page views and feature usage analytics."""

    # Prefixes to skip entirely
    _SKIP_PREFIXES = ("/static/", "/sw.js", "/health", "/robots", "/sitemap")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        path = request.url.path

        # Skip static assets / system endpoints
        if any(path.startswith(p) for p in self._SKIP_PREFIXES):
            return response

        # Only track successful responses (2xx)
        if response.status_code < 200 or response.status_code >= 300:
            return response

        try:
            svc = _get_svc()

            if request.method == "GET" and not path.startswith("/api/"):
                # ── Page view recording ──────────────────
                await svc.record_page_view(path)

            elif request.method == "POST":
                # ── Feature usage recording ──────────────
                feature = _API_FEATURES.get(path)
                if feature:
                    await svc.record_feature(feature)

        except Exception:
            pass  # analytics must never break the request

        return response
