"""Shared FastAPI dependencies — injected via Depends()."""

from functools import lru_cache

from app.config import Settings


def get_settings() -> Settings:
    """Return the application settings singleton from config module."""
    from app.config import settings
    return settings


@lru_cache
def get_pipeline():
    """Return a cached HieroglyphPipeline singleton.

    Heavy init (ONNX, label mapping) happens on first call.
    Keras model + FAISS index are lazy-loaded on first scan.
    """
    from app.core.hieroglyph_pipeline import HieroglyphPipeline

    settings = get_settings()
    root = settings.project_root
    return HieroglyphPipeline(
        detector_path=root / settings.hieroglyph_detector_path,
        classifier_path=root / settings.hieroglyph_classifier_path,
        label_mapping_path=root / settings.label_mapping_path,
        detection_confidence_threshold=settings.detection_confidence_threshold,
        enable_translation=True,
    )
