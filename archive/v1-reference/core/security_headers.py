"""
Wadjet AI — Security Headers Middleware.

Adds hardened HTTP headers to every response to mitigate common
web vulnerabilities (XSS, click-jacking, MIME-sniffing, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

# ---------------------------------------------------------------------------
# Content Security Policy
# ---------------------------------------------------------------------------
# CDN sources used by the landing page:
#   - cdn.tailwindcss.com   (TailwindCSS)
#   - unpkg.com             (HTMX)
#   - cdn.jsdelivr.net      (TensorFlow.js, WASM backend)
#   - fonts.googleapis.com  (Google Fonts CSS)
#   - fonts.gstatic.com     (Google Fonts files)
#
# 'unsafe-inline' is required for Tailwind's inline config <script> block.
# When we move to a build step we can replace it with a nonce/hash.
# 'unsafe-eval' is required by TensorFlow.js WebGL backend.

_CSP_DIRECTIVES: dict[str, str] = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net",
    "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src": "'self' https://fonts.gstatic.com",
    "img-src": "'self' data: blob:",
    "connect-src": "'self' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com blob:",
    "media-src": "'self' blob:",
    "frame-ancestors": "'self' https://huggingface.co https://*.hf.space",
    "base-uri": "'self'",
    "form-action": "'self'",
    "object-src": "'none'",
    "worker-src": "'self' blob:",
}

_CSP_HEADER: str = "; ".join(f"{k} {v}" for k, v in _CSP_DIRECTIVES.items())

# ---------------------------------------------------------------------------
# Static security headers applied to every response
# ---------------------------------------------------------------------------
_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(self \"https://huggingface.co\" \"https://*.hf.space\"), microphone=(), geolocation=()",
    "Content-Security-Policy": _CSP_HEADER,
    "Cross-Origin-Opener-Policy": "same-origin",
}


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every HTTP response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
