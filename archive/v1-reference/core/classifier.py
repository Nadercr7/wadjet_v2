"""
Wadjet AI - Classifier Service.

Wraps the Keras model for Egyptian landmark classification.
Handles image preprocessing, prediction, and result formatting.

The loaded Keras model expects:
    - Input: (batch, 384, 384, 3), float32 pixels in [0, 255]
      (EfficientNetV2-S has a built-in preprocessing/rescaling layer)
    - Output: (batch, 52) softmax probabilities

Usage via dependency injection::

    from app.dependencies import get_classifier

    @router.post("/identify")
    async def identify(
        classifier: ClassifierService = Depends(get_classifier),
    ):
        result = classifier.predict(image_bytes)
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from app.core.exceptions import ImageValidationError, ModelError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = get_logger("wadjet.classifier")

# ── Constants ───────────────────────────────────
IMAGE_SIZE: int = 384
"""Target width/height the Keras model expects."""

NUM_CLASSES: int = 52
"""Number of output classes in the model."""

TOP_K: int = 5
"""Number of top predictions to return."""


# ── Result dataclasses ──────────────────────────
@dataclass(frozen=True, slots=True)
class Prediction:
    """A single class prediction with name and confidence."""

    class_name: str
    confidence: float


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Full classification result from the model."""

    class_name: str
    confidence: float
    top_k: list[Prediction]


# ── Preprocessing ───────────────────────────────


def _load_and_preprocess(image_bytes: bytes) -> NDArray[np.float32]:
    """Load raw bytes into a preprocessed numpy array.

    Steps:
        1. Open image from bytes via PIL.
        2. Convert to RGB (handles RGBA, grayscale, palette).
        3. Resize to 384x384 with high-quality Lanczos resampling.
        4. Convert to float32 numpy array with values in [0, 255].
           (EfficientNetV2-S includes a built-in preprocessing layer.)
        5. Add batch dimension -> shape (1, 384, 384, 3).

    Args:
        image_bytes: Raw image file content.

    Returns:
        Preprocessed array ready for ``model.predict()``.

    Raises:
        ImageValidationError: If bytes cannot be decoded as an image.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ImageValidationError("Cannot decode image bytes") from exc

    # Ensure RGB (model expects 3 channels)
    if img.mode != "RGB":
        img = img.convert("RGB")

    img = img.resize((IMAGE_SIZE, IMAGE_SIZE), Image.LANCZOS)

    # Keep values in [0, 255] — EfficientNetV2-S has a built-in
    # preprocessing layer that handles rescaling internally.
    arr: NDArray[np.float32] = np.asarray(img, dtype=np.float32)

    # (384, 384, 3) -> (1, 384, 384, 3)
    return np.expand_dims(arr, axis=0)


# ── Class labels ────────────────────────────────


def _load_class_labels() -> list[str]:
    """Import class labels from the model package.

    Returns:
        Ordered list of 52 class name strings.
    """
    from model.class_labels import class_names  # type: ignore[import-untyped]

    return list(class_names)


# Module-level cache so labels are loaded once.
CLASS_LABELS: list[str] = _load_class_labels()


# ── Classifier Service ──────────────────────────


class ClassifierService:
    """Egyptian landmark classifier backed by a Keras model.

    Instantiated once during app startup (lifespan) and provided
    to route handlers via ``Depends(get_classifier)``.

    Args:
        model: A compiled/loaded Keras model with the expected
               input/output shapes.
    """

    def __init__(self, model: object) -> None:
        self._model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, image_bytes: bytes) -> ClassificationResult:
        """Run classification on raw image bytes.

        Args:
            image_bytes: JPEG/PNG/WebP file content.

        Returns:
            ClassificationResult with top-1 class, confidence, and
            top-k predictions.

        Raises:
            ImageValidationError: If image cannot be decoded.
            ModelError: If the underlying Keras model fails.
        """
        preprocessed = _load_and_preprocess(image_bytes)

        try:
            predictions: NDArray[np.float32] = self._model.predict(  # type: ignore[union-attr]
                preprocessed,
                verbose=0,
            )
        except Exception as exc:
            logger.exception("model_predict_failed")
            raise ModelError("Model prediction failed") from exc

        # predictions shape: (1, 52) -- squeeze batch dim
        probs = predictions[0]

        return self._format_result(probs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_result(probs: NDArray[np.float32]) -> ClassificationResult:
        """Convert raw probability vector into a ClassificationResult.

        Args:
            probs: 1-D array of shape (52,) with softmax probabilities.

        Returns:
            Structured result with top-1 and top-k predictions.
        """
        # Indices sorted by descending probability
        top_indices = np.argsort(probs)[::-1][:TOP_K]

        top_k = [
            Prediction(
                class_name=CLASS_LABELS[int(idx)],
                confidence=round(float(probs[idx]), 6),
            )
            for idx in top_indices
        ]

        best = top_k[0]

        return ClassificationResult(
            class_name=best.class_name,
            confidence=best.confidence,
            top_k=top_k,
        )
