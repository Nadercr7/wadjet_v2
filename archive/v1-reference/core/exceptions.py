"""
Wadjet AI — Custom Exception Classes.

Domain-specific exceptions that map cleanly to HTTP error responses.
Each carries a machine-readable ``code`` (UPPER_SNAKE_CASE) and a
human-readable ``message`` so the global handler can return a
consistent Rule A5 ``ErrorResponse``.
"""

from __future__ import annotations


class WadjetError(Exception):
    """Base exception for all Wadjet domain errors.

    Parameters
    ----------
    message:
        Human-readable description shown to the client.
    code:
        Machine-readable error code (UPPER_SNAKE_CASE).
    status_code:
        HTTP status code to return (default 500).
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        *,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Model / Classification errors
# ---------------------------------------------------------------------------


class ModelError(WadjetError):
    """Raised when the Keras model fails (load, predict, shape mismatch)."""

    def __init__(
        self,
        message: str = "Model prediction failed.",
        *,
        code: str = "MODEL_ERROR",
        status_code: int = 500,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class ModelNotLoadedError(ModelError):
    """Raised when an endpoint requires the model but it isn't loaded yet."""

    def __init__(self, message: str = "Classification model is not loaded.") -> None:
        super().__init__(message, code="MODEL_NOT_LOADED", status_code=503)


# ---------------------------------------------------------------------------
# Gemini API errors
# ---------------------------------------------------------------------------


class GeminiError(WadjetError):
    """Raised when a Gemini API call fails."""

    def __init__(
        self,
        message: str = "Gemini AI service is temporarily unavailable.",
        *,
        code: str = "GEMINI_ERROR",
        status_code: int = 502,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class GeminiRateLimitError(GeminiError):
    """Raised when Gemini returns a 429 rate-limit response."""

    def __init__(
        self, message: str = "AI service rate limit reached. Please try again shortly."
    ) -> None:
        super().__init__(message, code="GEMINI_RATE_LIMITED", status_code=429)


# ---------------------------------------------------------------------------
# Validation / input errors
# ---------------------------------------------------------------------------


class ValidationError(WadjetError):
    """Raised for business-logic validation failures (not Pydantic)."""

    def __init__(
        self,
        message: str = "Validation failed.",
        *,
        code: str = "VALIDATION_ERROR",
        status_code: int = 422,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class ImageValidationError(ValidationError):
    """Raised for image-specific validation issues."""

    def __init__(self, message: str = "Invalid image file.") -> None:
        super().__init__(message, code="INVALID_IMAGE", status_code=400)


# ---------------------------------------------------------------------------
# Not-found errors
# ---------------------------------------------------------------------------


class LandmarkNotFoundError(WadjetError):
    """Raised when the model cannot identify a landmark in the image."""

    def __init__(self, message: str = "Could not identify a landmark in this image.") -> None:
        super().__init__(message, code="LANDMARK_NOT_FOUND", status_code=404)


class AttractionNotFoundError(WadjetError):
    """Raised when a requested attraction doesn't exist in the database."""

    def __init__(self, message: str = "Attraction not found.") -> None:
        super().__init__(message, code="ATTRACTION_NOT_FOUND", status_code=404)
