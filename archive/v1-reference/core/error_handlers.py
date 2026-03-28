"""
Wadjet AI — Global Exception Handlers.

Registers FastAPI exception handlers that convert any raised exception
into a consistent Rule A5 ``ErrorResponse`` JSON body and log the
incident with full stack trace.  Browser requests (``Accept: text/html``)
receive themed HTML error pages instead of JSON.

Usage in ``main.py``::

    from app.core.error_handlers import register_error_handlers
    register_error_handlers(app)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.core.exceptions import WadjetError
from app.core.request_context import get_request_id

if TYPE_CHECKING:
    from pydantic import ValidationError as PydanticValidationError
    from starlette.responses import Response

logger: structlog.stdlib.BoundLogger = structlog.get_logger("wadjet.errors")

# Templates instance for HTML error pages
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# Error templates that exist on disk (checked once at import time)
_ERROR_TEMPLATES: set[int] = set()
for _code in (404, 429, 500):
    if (_TEMPLATES_DIR / "errors" / f"{_code}.html").is_file():
        _ERROR_TEMPLATES.add(_code)


def _wants_html(request: Request) -> bool:
    """Return *True* if the client prefers an HTML response (browser)."""
    accept = request.headers.get("accept", "")
    # Browsers send "text/html" prominently; API clients typically don't
    return "text/html" in accept


def _html_error_response(
    request: Request,
    *,
    status_code: int,
    request_id: str,
    retry_after: int | None = None,
) -> HTMLResponse | None:
    """Return a themed HTML error page if a template exists, else *None*."""
    if status_code not in _ERROR_TEMPLATES:
        return None
    try:
        ctx = {
            "request": request,
            "request_id": request_id,
        }
        if retry_after is not None:
            ctx["retry_after"] = retry_after
        return _templates.TemplateResponse(
            f"errors/{status_code}.html",
            ctx,
            status_code=status_code,
        )
    except Exception:
        logger.warning("error_template_render_failed", status_code=status_code)
        return None


def _get_request_id(request: Request) -> str:
    """Return the request ID from context-vars (preferred) or request.state."""
    rid = get_request_id()
    if rid != "unknown":
        return rid
    return getattr(request.state, "request_id", "unknown")


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    """Build a Rule A5 compliant error JSON response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "code": code,
            "message": message,
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# Handler implementations
# ---------------------------------------------------------------------------


async def _handle_wadjet_error(request: Request, exc: WadjetError) -> JSONResponse:
    """Handle all custom Wadjet domain exceptions."""
    request_id = _get_request_id(request)

    logger.warning(
        "domain_error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        request_id=request_id,
    )

    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=request_id,
    )


async def _handle_http_exception(
    request: Request, exc: HTTPException | StarletteHTTPException
) -> Response:
    """Handle FastAPI / Starlette ``HTTPException`` (404, 405, etc.)."""
    request_id = _get_request_id(request)

    # If the detail is already a dict (e.g. from upload_security), use it
    if isinstance(exc.detail, dict):
        body = {**exc.detail, "request_id": request_id}
        return JSONResponse(status_code=exc.status_code, content=body)

    code = _status_to_code(exc.status_code)
    message = str(exc.detail) if exc.detail else "An error occurred."

    logger.warning(
        "http_error",
        code=code,
        message=message,
        status_code=exc.status_code,
        path=request.url.path,
        request_id=request_id,
    )

    # Serve themed HTML page to browsers
    if _wants_html(request):
        html = _html_error_response(request, status_code=exc.status_code, request_id=request_id)
        if html is not None:
            return html

    return _error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        request_id=request_id,
    )


async def _handle_validation_error(
    request: Request,
    exc: RequestValidationError | PydanticValidationError,
) -> JSONResponse:
    """Handle Pydantic / FastAPI request validation errors (422)."""
    request_id = _get_request_id(request)

    # Build a readable summary from Pydantic errors
    errors = exc.errors() if hasattr(exc, "errors") else []
    details = "; ".join(
        f"{' → '.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg', '')}" for e in errors
    )
    message = f"Request validation failed: {details}" if details else "Request validation failed."

    logger.warning(
        "validation_error",
        error_count=len(errors),
        details=details,
        path=request.url.path,
        request_id=request_id,
    )

    return _error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message=message,
        request_id=request_id,
    )


async def _handle_unhandled_exception(request: Request, exc: Exception) -> Response:
    """Catch-all for unexpected exceptions — log with traceback."""
    request_id = _get_request_id(request)
    settings = get_settings()

    logger.exception(
        "unhandled_error",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        request_id=request_id,
    )

    # Serve themed HTML page to browsers
    if _wants_html(request):
        html = _html_error_response(request, status_code=500, request_id=request_id)
        if html is not None:
            return html

    # In production, hide internal details
    message = (
        str(exc)
        if settings.is_development
        else "An internal server error occurred. Please try again later."
    )

    return _error_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message=message,
        request_id=request_id,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    408: "REQUEST_TIMEOUT",
    409: "CONFLICT",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


def _status_to_code(status: int) -> str:
    return _STATUS_CODE_MAP.get(status, f"HTTP_{status}")


# ---------------------------------------------------------------------------
# Public registration function
# ---------------------------------------------------------------------------


def register_error_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app instance."""
    app.add_exception_handler(WadjetError, _handle_wadjet_error)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unhandled_exception)  # type: ignore[arg-type]


async def handle_rate_limit_exceeded(request: Request, exc: Exception) -> Response:
    """Custom 429 handler — serves a themed HTML countdown page to browsers."""
    request_id = _get_request_id(request)

    # Parse Retry-After from the exception (slowapi sets it)
    retry_after = 30  # sensible default
    if hasattr(exc, "detail") and isinstance(exc.detail, str):
        # slowapi detail is "Rate limit exceeded: X per Y"
        pass
    if hasattr(exc, "headers") and isinstance(exc.headers, dict):
        try:
            retry_after = int(exc.headers.get("Retry-After", 30))
        except (TypeError, ValueError):
            retry_after = 30

    logger.warning(
        "rate_limited",
        path=request.url.path,
        retry_after=retry_after,
        request_id=request_id,
    )

    # Serve themed HTML page to browsers
    if _wants_html(request):
        html = _html_error_response(
            request, status_code=429, request_id=request_id, retry_after=retry_after
        )
        if html is not None:
            html.headers["Retry-After"] = str(retry_after)
            return html

    return JSONResponse(
        status_code=429,
        content={
            "error": True,
            "code": "RATE_LIMITED",
            "message": "Too many requests. Please slow down.",
            "request_id": request_id,
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )
