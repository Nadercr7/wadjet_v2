"""
Wadjet AI — Request Logging Middleware.

Logs every HTTP request with structured fields:
- method, path, status_code, duration_ms, client_ip
- Binds ``request_id`` into structlog context-vars so every log line
  emitted while handling a request carries the same trace ID.

Note: ``request_id`` generation/injection is done here as a lightweight
precursor; Phase 1.9 will expand it with a dedicated X-Request-ID header
flow.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger: structlog.stdlib.BoundLogger = structlog.get_logger("wadjet.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status and duration for every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()

        # Bind request_id into structlog context so downstream code inherits it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Stash on request.state for endpoint access
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_error",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown",
                duration_ms=round(duration_ms, 2),
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000

        # Inject tracing header into response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        # Choose log level based on status code
        status = response.status_code
        log = logger.warning if status >= 400 else logger.info

        log(
            "request_handled",
            method=request.method,
            path=request.url.path,
            status_code=status,
            duration_ms=round(duration_ms, 2),
            client_ip=request.client.host if request.client else "unknown",
        )

        return response
