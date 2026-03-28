"""
Wadjet AI - Request ID Context.

Provides a thin accessor around structlog.contextvars so that any module
can retrieve the current request's trace ID without needing access to the
``Request`` object.

Usage::

    from app.core.request_context import get_request_id

    rid = get_request_id()  # returns active UUID or "unknown"
"""

from __future__ import annotations

import structlog


def get_request_id() -> str:
    """Return the request ID bound in the current context.

    Falls back to ``"unknown"`` when called outside a request scope
    (e.g. during startup or in a background task without context).
    """
    ctx: dict = structlog.contextvars.get_contextvars()
    return ctx.get("request_id", "unknown")
