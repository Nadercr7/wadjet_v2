"""
Wadjet AI — Health Check Service.

Provides application health status including:
- Model availability (file exists on disk)
- Gemini API readiness (keys configured)
- Uptime tracking
- Aggregate status derivation (ok / degraded / unhealthy)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from app.api.schemas.common import HealthResponse

if TYPE_CHECKING:
    from app.config import Settings

# Module-level startup timestamp — set once when the module is first imported.
_STARTUP_TIME: float = time.monotonic()


def get_uptime_seconds() -> float:
    """Return seconds elapsed since the application started."""
    return round(time.monotonic() - _STARTUP_TIME, 2)


def check_model_loaded(settings: Settings) -> bool:
    """Check whether the Keras model is loaded in memory.

    Falls back to file-exists check if the DI layer has not been
    initialised yet (e.g. during early startup).
    """
    from app.dependencies import get_classifier

    classifier = get_classifier()
    if classifier is not None:
        return True

    # Fallback: check file on disk
    model_path = settings.base_dir / settings.model_path
    return Path(model_path).is_file()


def check_gemini_available(settings: Settings) -> bool:
    """Check whether the Gemini service is initialised.

    First checks whether the DI layer has a live ``GeminiService``
    instance; falls back to verifying that at least one API key is
    configured in settings.
    """
    from app.dependencies import get_gemini_service

    service = get_gemini_service()
    if service is not None:
        return service.available

    # Fallback: at least one key configured
    return len(settings.gemini_api_keys) > 0


def _derive_status(
    *, model_loaded: bool, gemini_available: bool, quota_degraded: bool = False
) -> str:
    """Derive overall service status from component checks.

    - ``ok``        - everything is operational
    - ``degraded``  - at least one non-critical subsystem is down, or quota near limit
    - ``unhealthy`` - a critical subsystem is unavailable
    """
    if model_loaded and gemini_available and not quota_degraded:
        return "ok"
    if model_loaded or gemini_available:
        return "degraded"
    return "unhealthy"


def build_health_response(settings: Settings) -> HealthResponse:
    """Run all health checks and return a structured response."""
    model_loaded = check_model_loaded(settings)
    gemini_available = check_gemini_available(settings)

    # Phase 3.14 — check quota status
    quota_degraded = False
    from app.dependencies import get_gemini_service

    svc = get_gemini_service()
    if svc is not None:
        quota_degraded = svc.quota.is_degraded

    status = _derive_status(
        model_loaded=model_loaded,
        gemini_available=gemini_available,
        quota_degraded=quota_degraded,
    )

    return HealthResponse(
        status=status,
        model_loaded=model_loaded,
        gemini_available=gemini_available,
        uptime_seconds=get_uptime_seconds(),
        version=settings.app_version,
        environment=settings.environment,
    )
