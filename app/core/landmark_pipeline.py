"""Landmark identification pipeline — ONNX inference wrapper.

Loads the EfficientNet-B0 uint8 ONNX model and returns predictions
with top-k results for a given image.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "landmark" / "landmark_classifier_uint8.onnx"
DEFAULT_LABEL_PATH = PROJECT_ROOT / "models" / "landmark" / "landmark_label_mapping.json"

INPUT_SIZE = 224


class LandmarkPipeline:
    """ONNX-based landmark classifier."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        label_path: str | Path | None = None,
    ) -> None:
        self._model_path = Path(model_path or DEFAULT_MODEL_PATH)
        self._label_path = Path(label_path or DEFAULT_LABEL_PATH)
        self._session = None
        self._labels: dict[int, str] = {}
        self._load_labels()

    def _load_labels(self) -> None:
        if not self._label_path.exists():
            logger.warning("Label mapping not found: %s", self._label_path)
            return
        with open(self._label_path, encoding="utf-8") as f:
            raw = json.load(f)
        self._labels = {int(k): v for k, v in raw.items()}

    def _get_session(self):
        if self._session is None:
            import onnxruntime as ort
            if not self._model_path.exists():
                raise FileNotFoundError(f"Model not found: {self._model_path}")
            self._session = ort.InferenceSession(
                str(self._model_path),
                providers=["CPUExecutionProvider"],
            )
        return self._session

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Resize + normalize + NCHW transpose."""
        img = cv2.resize(image, (INPUT_SIZE, INPUT_SIZE))
        img = img.astype(np.float32) / 255.0
        # HWC → CHW → NCHW
        img = img.transpose(2, 0, 1)[np.newaxis]
        return img

    def predict(self, image: np.ndarray, top_k: int = 3) -> dict:
        """Run inference on an image.

        Args:
            image: BGR numpy array (H, W, 3).
            top_k: Number of top predictions to return.

        Returns:
            dict with keys: slug, name, confidence, top3 (list of dicts).
        """
        session = self._get_session()
        input_name = session.get_inputs()[0].name
        tensor = self._preprocess(image)

        outputs = session.run(None, {input_name: tensor})
        logits = outputs[0][0]  # shape (52,)

        # Softmax
        exp = np.exp(logits - logits.max())
        probs = exp / exp.sum()

        # Top-k
        top_indices = np.argsort(probs)[::-1][:top_k]
        top_results = []
        for idx in top_indices:
            slug = self._labels.get(int(idx), f"unknown_{idx}")
            top_results.append({
                "slug": slug,
                "name": slug.replace("_", " ").title(),
                "confidence": round(float(probs[idx]), 4),
            })

        best = top_results[0]
        return {
            "slug": best["slug"],
            "name": best["name"],
            "confidence": best["confidence"],
            "top3": top_results,
        }

    @property
    def available(self) -> bool:
        return self._model_path.exists() and bool(self._labels)
