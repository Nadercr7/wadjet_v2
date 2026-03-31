"""H6.1: End-to-end hieroglyph pipeline.

Stages:
    1. Detection  (ONNX / YOLOv8s) → bounding boxes
    2. Classification  (ONNX / MobileNetV3-Small) → Gardiner codes
    3. Transliteration  (reading order + MdC notation)
    4. Translation  (RAG + Gemini, optional)

Usage:
    pipeline = HieroglyphPipeline()
    result = pipeline.process_image(image)
    print(result.transliteration)
    print(result.translation_en)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # Wadjet-v2/

# Default model paths (relative to project root)
DEFAULT_DETECTOR_PATH = PROJECT_ROOT / "models" / "hieroglyph" / "detector" / "glyph_detector_uint8.onnx"
DEFAULT_CLASSIFIER_PATH = PROJECT_ROOT / "models" / "hieroglyph" / "classifier" / "hieroglyph_classifier_uint8.onnx"
DEFAULT_LABEL_MAPPING_PATH = PROJECT_ROOT / "models" / "hieroglyph" / "classifier" / "label_mapping.json"

# Classification confidence below this is flagged as uncertain
LOW_CONFIDENCE_THRESHOLD = 0.3




@dataclass
class GlyphResult:
    """Single detected glyph with classification."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    gardiner_code: str
    class_confidence: float
    low_confidence: bool = False


@dataclass
class PipelineResult:
    """Full pipeline output."""
    # Stage 1: Detection
    num_detections: int = 0
    glyphs: list[GlyphResult] = field(default_factory=list)

    # Stage 2+3: Transliteration
    transliteration: str = ""
    gardiner_sequence: str = ""
    reading_direction: str = ""
    layout_mode: str = ""
    num_groups: int = 0
    num_lines: int = 0

    # Stage 4: Translation
    translation_en: str = ""
    translation_ar: str = ""
    translation_error: str = ""

    # Timing
    detection_ms: float = 0.0
    classification_ms: float = 0.0
    transliteration_ms: float = 0.0
    translation_ms: float = 0.0
    total_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_detections": self.num_detections,
            "glyphs": [
                {
                    "bbox": [g.x1, g.y1, g.x2, g.y2],
                    "detection_confidence": g.confidence,
                    "gardiner_code": g.gardiner_code,
                    "class_confidence": g.class_confidence,
                }
                for g in self.glyphs
            ],
            "transliteration": self.transliteration,
            "gardiner_sequence": self.gardiner_sequence,
            "reading_direction": self.reading_direction,
            "layout_mode": self.layout_mode,
            "translation_en": self.translation_en,
            "translation_ar": self.translation_ar,
            "translation_error": self.translation_error,
            "timing": {
                "detection_ms": round(self.detection_ms, 1),
                "classification_ms": round(self.classification_ms, 1),
                "transliteration_ms": round(self.transliteration_ms, 1),
                "translation_ms": round(self.translation_ms, 1),
                "total_ms": round(self.total_ms, 1),
            },
        }


class HieroglyphPipeline:
    """End-to-end pipeline: detect → classify → transliterate → translate."""

    def __init__(
        self,
        detector_path: str | Path | None = None,
        classifier_path: str | Path | None = None,
        label_mapping_path: str | Path | None = None,
        classifier_input_size: int = 128,
        detection_confidence_threshold: float | None = None,
        enable_translation: bool = True,
        gemini_model: str = "gemini-2.5-flash",
        top_k: int = 8,
    ) -> None:
        self._detector_path = Path(detector_path or DEFAULT_DETECTOR_PATH)
        self._classifier_path = Path(classifier_path or DEFAULT_CLASSIFIER_PATH)
        self._label_mapping_path = Path(label_mapping_path or DEFAULT_LABEL_MAPPING_PATH)
        self._classifier_input_size = classifier_input_size
        self._detection_confidence_threshold = detection_confidence_threshold
        self._enable_translation = enable_translation
        self._gemini_model = gemini_model
        self._top_k = top_k

        # Lazy-loaded components
        self._detector = None
        self._classifier = None
        self._idx_to_gardiner: dict[int, str] = {}
        self._transliteration_engine = None
        self._translator = None

        # Load label mapping (lightweight, always needed)
        self._load_label_mapping()

    def _load_label_mapping(self) -> None:
        with open(self._label_mapping_path, encoding="utf-8") as f:
            mapping = json.load(f)
        # Support both formats:
        #   wrapped: {"idx_to_gardiner": {"0": "A55", ...}}
        #   flat:    {"0": "A55", ...}
        raw = mapping.get("idx_to_gardiner", mapping)
        self._idx_to_gardiner = {int(k): v for k, v in raw.items()}

        # Initialize facing signs set for reading direction detection
        from app.core.reading_order import _init_model_facing_signs
        gardiner_to_idx = {v: int(k) for k, v in raw.items()}
        _init_model_facing_signs(gardiner_to_idx)

    def _get_detector(self):
        if self._detector is None:
            from app.core.postprocess import GlyphDetector, PostProcessConfig
            config = None
            if self._detection_confidence_threshold is not None:
                config = PostProcessConfig(conf_threshold=self._detection_confidence_threshold)
            self._detector = GlyphDetector(str(self._detector_path), config=config)
        return self._detector

    def _get_classifier(self):
        if self._classifier is None:
            import onnxruntime as ort
            self._classifier = ort.InferenceSession(
                str(self._classifier_path),
                providers=["CPUExecutionProvider"],
            )
            # Auto-detect input size from ONNX model
            # NCHW: [batch, C, H, W] → spatial at index 2
            input_shape = self._classifier.get_inputs()[0].shape
            if input_shape and len(input_shape) == 4 and isinstance(input_shape[2], int):
                self._classifier_input_size = input_shape[2]
        return self._classifier

    def _get_transliteration_engine(self):
        if self._transliteration_engine is None:
            from app.core.transliteration import TransliterationEngine
            self._transliteration_engine = TransliterationEngine(
                label_mapping_path=str(self._label_mapping_path)
            )
        return self._transliteration_engine

    def set_translator(self, translator) -> None:
        """Inject an externally-configured RAGTranslator (with full AI access)."""
        self._translator = translator

    def _get_translator(self):
        if self._translator is None and self._enable_translation:
            from app.core.rag_translator import RAGTranslator
            self._translator = RAGTranslator(
                top_k=self._top_k,
            )
        return self._translator

    # ── Stage 1: Detection ─────────────────────────────────────────

    def _detect(self, image: np.ndarray) -> list:
        """Detect glyph bounding boxes in image."""
        detector = self._get_detector()
        return detector.detect(image)

    # ── Stage 2: Classification ────────────────────────────────────

    def _classify_crops(
        self, image: np.ndarray, detections: list
    ) -> list[GlyphResult]:
        """Crop each detection, classify with ONNX classifier."""
        if not detections:
            return []

        session = self._get_classifier()
        input_name = session.get_inputs()[0].name
        size = self._classifier_input_size
        h, w = image.shape[:2]

        # Prepare all crops
        crops = []
        for det in detections:
            x1 = max(0, int(det.x1))
            y1 = max(0, int(det.y1))
            x2 = min(w, int(det.x2))
            y2 = min(h, int(det.y2))
            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            # BGR→RGB: OpenCV loads BGR but model was trained on RGB
            crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            crop = cv2.resize(crop, (size, size))
            crop = crop.astype(np.float32) / 255.0
            # HWC → CHW for NCHW ONNX model
            crop = crop.transpose(2, 0, 1)
            crops.append((det, crop))

        if not crops:
            return []

        # Batch predict via ONNX Runtime (NCHW format)
        batch = np.stack([c for _, c in crops])
        outputs = session.run(None, {input_name: batch})
        probs = outputs[0]

        # Verify model output matches label mapping (HIERO-009)
        assert probs.shape[-1] == len(self._idx_to_gardiner), (
            f"Model output classes {probs.shape[-1]} != label mapping {len(self._idx_to_gardiner)}"
        )

        # Apply softmax if logits (check if already normalized)
        if probs.shape[-1] > 1 and not np.allclose(probs.sum(axis=-1), 1.0, atol=0.1):
            exp = np.exp(probs - probs.max(axis=-1, keepdims=True))
            probs = exp / exp.sum(axis=-1, keepdims=True)

        results = []
        for (det, _), prob in zip(crops, probs):
            class_id = int(np.argmax(prob))
            class_conf = float(prob[class_id])
            gardiner = self._idx_to_gardiner.get(class_id, f"UNK_{class_id}")
            results.append(GlyphResult(
                x1=det.x1, y1=det.y1, x2=det.x2, y2=det.y2,
                confidence=det.confidence,
                class_id=class_id,
                gardiner_code=gardiner,
                class_confidence=class_conf,
                low_confidence=class_conf < LOW_CONFIDENCE_THRESHOLD,
            ))

        return results

    # ── Stage 3: Transliteration ───────────────────────────────────

    def _transliterate(self, glyphs: list[GlyphResult]) -> dict:
        """Convert classified glyphs to MdC transliteration."""
        if not glyphs:
            return {
                "transliteration": "",
                "gardiner_sequence": "",
                "direction": "UNKNOWN",
                "layout": "HORIZONTAL",
                "num_groups": 0,
                "num_lines": 0,
            }

        engine = self._get_transliteration_engine()

        raw_boxes = [
            {
                "x1": g.x1, "y1": g.y1, "x2": g.x2, "y2": g.y2,
                "class_id": g.class_id,
                "confidence": g.confidence,
                "gardiner_code": g.gardiner_code,
            }
            for g in glyphs
        ]

        result = engine.transliterate_from_raw(raw_boxes)

        return {
            "transliteration": result.mdc_transliteration,
            "gardiner_sequence": result.gardiner_sequence,
            "direction": result.direction.name if hasattr(result.direction, "name") else str(result.direction),
            "layout": result.layout.name if hasattr(result.layout, "name") else str(result.layout),
            "num_groups": result.num_groups,
            "num_lines": result.num_lines,
        }

    # ── Stage 4: Translation ───────────────────────────────────────

    def _translate(self, transliteration: str) -> dict:
        """Translate MdC transliteration to English/Arabic."""
        translator = self._get_translator()
        if translator is None or not transliteration:
            return {"en": "", "ar": "", "error": ""}

        result = translator.translate_bilingual(transliteration, max_retries=5)
        return {
            "en": result.get("english", ""),
            "ar": result.get("arabic", ""),
            "error": result.get("en_error", "") or result.get("ar_error", ""),
        }

    # ── Full Pipeline ──────────────────────────────────────────────

    def process_image(
        self,
        image: np.ndarray,
        translate: bool | None = None,
    ) -> PipelineResult:
        """Run the full pipeline on an image.

        Args:
            image: BGR or RGB numpy array (H, W, 3).
            translate: Override translation setting. None uses init default.

        Returns:
            PipelineResult with all stages' output.
        """
        do_translate = translate if translate is not None else self._enable_translation
        result = PipelineResult()
        t_total = time.time()

        # Stage 1: Detection
        t0 = time.time()
        try:
            detections = self._detect(image)
        except Exception as e:
            logger.error("Pipeline detection failed: %s", e)
            result.detection_ms = (time.time() - t0) * 1000
            result.translation_error = f"Detection failed: {e}"
            result.total_ms = (time.time() - t_total) * 1000
            return result
        result.detection_ms = (time.time() - t0) * 1000
        result.num_detections = len(detections)

        if not detections:
            result.total_ms = (time.time() - t_total) * 1000
            return result

        # Stage 2: Classification
        t0 = time.time()
        try:
            glyphs = self._classify_crops(image, detections)
        except Exception as e:
            logger.error("Pipeline classification failed: %s", e)
            result.classification_ms = (time.time() - t0) * 1000
            result.translation_error = f"Classification failed: {e}"
            result.total_ms = (time.time() - t_total) * 1000
            return result
        result.classification_ms = (time.time() - t0) * 1000
        result.glyphs = glyphs

        if not glyphs:
            result.total_ms = (time.time() - t_total) * 1000
            return result

        # Stage 3: Transliteration
        t0 = time.time()
        try:
            trans_result = self._transliterate(glyphs)
        except Exception as e:
            logger.error("Pipeline transliteration failed: %s", e)
            result.transliteration_ms = (time.time() - t0) * 1000
            result.translation_error = f"Transliteration failed: {e}"
            result.total_ms = (time.time() - t_total) * 1000
            return result
        result.transliteration_ms = (time.time() - t0) * 1000
        result.transliteration = trans_result["transliteration"]
        result.gardiner_sequence = trans_result["gardiner_sequence"]
        result.reading_direction = trans_result["direction"]
        result.layout_mode = trans_result["layout"]
        result.num_groups = trans_result["num_groups"]
        result.num_lines = trans_result["num_lines"]

        # Stage 4: Translation (optional)
        if do_translate and result.transliteration:
            t0 = time.time()
            try:
                translation = self._translate(result.transliteration)
            except Exception as e:
                logger.error("Pipeline translation failed: %s", e)
                result.translation_ms = (time.time() - t0) * 1000
                result.translation_error = f"Translation failed: {e}"
                result.total_ms = (time.time() - t_total) * 1000
                return result
            result.translation_ms = (time.time() - t0) * 1000
            result.translation_en = translation["en"]
            result.translation_ar = translation["ar"]
            result.translation_error = translation["error"]

        result.total_ms = (time.time() - t_total) * 1000
        return result

    def process_image_file(
        self,
        image_path: str | Path,
        translate: bool | None = None,
    ) -> PipelineResult:
        """Load an image from file and run the full pipeline."""
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")
        return self.process_image(image, translate=translate)
