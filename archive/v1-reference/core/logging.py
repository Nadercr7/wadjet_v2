"""
Wadjet AI — Structured Logging Configuration.

Configures ``structlog`` with:
- **Development**: coloured, human-friendly console output.
- **Production**: JSON lines for machine parsing.

Usage::

    from app.core.logging import get_logger

    logger = get_logger()
    logger.info("landmark_identified", name="Sphinx", confidence=0.95)
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config import get_settings


def setup_logging() -> None:
    """Initialise structlog + stdlib logging.

    Call **once** at application startup (before any log output).
    """
    settings = get_settings()

    is_json = settings.log_format == "json" or not settings.is_development
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # --- shared processors (run for every log event) ---
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_json:
        # Production: JSON lines
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Development: coloured console
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # --- configure stdlib root logger so uvicorn / third-party logs also flow
    #     through structlog formatting ---
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Quieten noisy third-party loggers
    for noisy in ("uvicorn.access", "httpcore", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger.

    Parameters
    ----------
    name:
        Optional logger name (defaults to the calling module).
    """
    return structlog.get_logger(name)
