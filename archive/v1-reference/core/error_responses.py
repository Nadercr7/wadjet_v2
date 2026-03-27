"""Wadjet AI — Error Response Standards.

Centralised error-code registry and OpenAPI ``responses`` helpers
so that every endpoint documents its possible errors in Swagger/ReDoc.

Usage in endpoint routers::

    from app.core.error_responses import ERRORS_400_422, ERRORS_404

    @router.post("/identify", responses={**ERRORS_400_422, **ERRORS_404})
    async def identify_landmark(...): ...

The module also exposes a flat ``ERROR_CODES`` dict mapping every
machine-readable code to its HTTP status and human description, which
is inserted into the OpenAPI schema as an ``x-error-codes`` extension.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Master error-code registry
# ---------------------------------------------------------------------------

ERROR_CODES: dict[str, dict[str, str | int]] = {
    # 400 — Bad Request
    "BAD_REQUEST": {
        "status": 400,
        "description": "The request was malformed or contained invalid data.",
    },
    # 401 — Unauthorized
    "UNAUTHORIZED": {
        "status": 401,
        "description": "Authentication credentials are missing or invalid.",
    },
    # 403 — Forbidden
    "FORBIDDEN": {
        "status": 403,
        "description": "You do not have permission to access this resource.",
    },
    "INVALID_IMAGE": {
        "status": 400,
        "description": "The uploaded file is not a valid image (corrupt, wrong format, or too small).",
    },
    # 404 — Not Found
    "NOT_FOUND": {
        "status": 404,
        "description": "The requested resource does not exist.",
    },
    "LANDMARK_NOT_FOUND": {
        "status": 404,
        "description": "The model could not identify a landmark in the uploaded image.",
    },
    "ATTRACTION_NOT_FOUND": {
        "status": 404,
        "description": "No attraction matches the given slug or class name.",
    },
    # 405 — Method Not Allowed
    "METHOD_NOT_ALLOWED": {
        "status": 405,
        "description": "The HTTP method is not allowed for this endpoint.",
    },
    # 408 — Request Timeout
    "REQUEST_TIMEOUT": {
        "status": 408,
        "description": "The server timed out waiting for the request to complete.",
    },
    # 409 — Conflict
    "CONFLICT": {
        "status": 409,
        "description": "The request conflicts with the current state of the resource.",
    },
    # 413 — Payload Too Large
    "FILE_TOO_LARGE": {
        "status": 413,
        "description": "The uploaded file exceeds the maximum allowed size (10 MB).",
    },
    # 415 — Unsupported Media Type
    "UNSUPPORTED_MEDIA_TYPE": {
        "status": 415,
        "description": "The uploaded file type is not supported (allowed: JPEG, PNG, WebP).",
    },
    # 422 — Validation Error
    "VALIDATION_ERROR": {
        "status": 422,
        "description": "Request body or query parameters failed schema validation.",
    },
    # 429 — Rate Limited
    "RATE_LIMITED": {
        "status": 429,
        "description": "Too many requests. Please slow down and retry after the indicated period.",
    },
    "GEMINI_RATE_LIMITED": {
        "status": 429,
        "description": "The Gemini AI service rate limit has been reached. Retry shortly.",
    },
    # 500 — Internal Server Error
    "INTERNAL_ERROR": {
        "status": 500,
        "description": "An unexpected server error occurred. The request ID can be used for support.",
    },
    "MODEL_ERROR": {
        "status": 500,
        "description": "The classification model encountered an internal error.",
    },
    # 502 — Bad Gateway
    "GEMINI_ERROR": {
        "status": 502,
        "description": "The Gemini AI service is temporarily unavailable.",
    },
    # 503 — Service Unavailable
    "MODEL_NOT_LOADED": {
        "status": 503,
        "description": "The classification model has not been loaded yet. Try again later.",
    },
}

# ---------------------------------------------------------------------------
# Shared OpenAPI ``responses`` snippets
# ---------------------------------------------------------------------------
# Each value is a dict suitable for merging into a router decorator's
# ``responses=`` parameter.  Keys are HTTP status codes; values follow
# the OpenAPI Response Object schema.

_ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {"type": "boolean", "example": True},
        "code": {"type": "string", "example": "ERROR_CODE"},
        "message": {"type": "string", "example": "Human-readable message."},
        "request_id": {"type": "string", "example": "550e8400-e29b-41d4-a716-446655440000"},
    },
    "required": ["error", "code", "message", "request_id"],
}


def _resp(status: int, description: str) -> dict:
    """Build a single OpenAPI response entry."""
    return {
        status: {
            "description": description,
            "content": {
                "application/json": {
                    "schema": _ERROR_SCHEMA,
                }
            },
        }
    }


# ── Reusable response groups ────────────────────

ERRORS_422: dict[int, dict] = {
    **_resp(422, "Validation Error - request body or parameters failed schema validation."),
}

ERRORS_429: dict[int, dict] = {
    **_resp(429, "Rate Limited - too many requests."),
}

ERRORS_500: dict[int, dict] = {
    **_resp(500, "Internal Server Error - unexpected failure."),
}

ERRORS_400: dict[int, dict] = {
    **_resp(400, "Bad Request - malformed or invalid input."),
}

ERRORS_404: dict[int, dict] = {
    **_resp(404, "Not Found - the requested resource does not exist."),
}

ERRORS_413: dict[int, dict] = {
    **_resp(413, "Payload Too Large - file exceeds 10 MB limit."),
}

ERRORS_415: dict[int, dict] = {
    **_resp(415, "Unsupported Media Type - file type not allowed."),
}

ERRORS_503: dict[int, dict] = {
    **_resp(503, "Service Unavailable - model not loaded yet."),
}

# ── Composite groups for common endpoint patterns ─

ERRORS_COMMON: dict[int, dict] = {
    **ERRORS_422,
    **ERRORS_429,
    **ERRORS_500,
}
"""422 + 429 + 500 — baseline errors any endpoint can produce."""

ERRORS_UPLOAD: dict[int, dict] = {
    **ERRORS_400,
    **ERRORS_413,
    **ERRORS_415,
    **ERRORS_422,
    **ERRORS_429,
    **ERRORS_500,
    **ERRORS_503,
}
"""Full set for file-upload endpoints (identify)."""

ERRORS_DETAIL: dict[int, dict] = {
    **ERRORS_404,
    **ERRORS_422,
    **ERRORS_429,
    **ERRORS_500,
}
"""404 + baseline — for single-resource detail endpoints."""
