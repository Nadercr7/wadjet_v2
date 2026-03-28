"""H3.9 — Glyph detection post-processing: confidence filtering, size filtering, IoU dedup.

ONNX-based inference pipeline with configurable post-processing for
hieroglyph bounding box detection using the YOLO26s model (NMS-free).
Includes greedy IoU suppression to remove residual overlapping detections.
"""

import numpy as np
import onnxruntime as ort
import cv2
from pathlib import Path
from dataclasses import dataclass, field

# ── Default tuning parameters ────────────────────────────────
CONF_THRESHOLD = 0.10       # Minimum detection confidence (lowered for stone inscriptions)
MIN_BOX_AREA_RATIO = 0.0005 # Minimum box area as fraction of image area
MAX_BOX_AREA_RATIO = 0.10   # Maximum box area as fraction of image area
MIN_BOX_DIM = 10            # Minimum box dimension in pixels (at original scale)
MAX_ASPECT_RATIO = 5.0      # Maximum width/height or height/width ratio
DEDUP_IOU_THRESHOLD = 0.25  # IoU threshold for greedy dedup (suppress overlapping boxes)
INPUT_SIZE = 640             # Model input size


@dataclass
class Detection:
    """Single glyph detection."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int = 0

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def aspect_ratio(self) -> float:
        if self.height == 0:
            return float("inf")
        return max(self.width / self.height, self.height / self.width)

    def to_dict(self) -> dict:
        return {
            "x1": round(self.x1, 1),
            "y1": round(self.y1, 1),
            "x2": round(self.x2, 1),
            "y2": round(self.y2, 1),
            "confidence": round(self.confidence, 4),
            "class_id": self.class_id,
        }


@dataclass
class PostProcessConfig:
    """Configurable post-processing parameters (NMS-free model)."""
    conf_threshold: float = CONF_THRESHOLD
    min_box_area_ratio: float = MIN_BOX_AREA_RATIO
    max_box_area_ratio: float = MAX_BOX_AREA_RATIO
    min_box_dim: int = MIN_BOX_DIM
    max_aspect_ratio: float = MAX_ASPECT_RATIO
    dedup_iou_threshold: float = DEDUP_IOU_THRESHOLD


class GlyphDetector:
    """ONNX-based glyph detector with post-processing."""

    def __init__(self, model_path: str | Path, config: PostProcessConfig | None = None):
        self.model_path = Path(model_path)
        self.config = config or PostProcessConfig()
        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name

    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, tuple[int, int], float, int, int]:
        """Resize + normalize image for YOLO input. Returns (blob, orig_shape, scale, pad_x, pad_y)."""
        orig_h, orig_w = image.shape[:2]

        # Letterbox resize to INPUT_SIZE x INPUT_SIZE
        scale = min(INPUT_SIZE / orig_w, INPUT_SIZE / orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad to square
        canvas = np.full((INPUT_SIZE, INPUT_SIZE, 3), 114, dtype=np.uint8)
        pad_x, pad_y = (INPUT_SIZE - new_w) // 2, (INPUT_SIZE - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

        # HWC→CHW, normalize, add batch dim
        blob = canvas.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]

        return blob, (orig_h, orig_w), scale, pad_x, pad_y

    def postprocess(
        self,
        output: np.ndarray,
        orig_shape: tuple[int, int],
        scale: float,
        pad_x: int,
        pad_y: int,
    ) -> list[Detection]:
        """Parse YOLO26s NMS-free output [1, 300, 6] and apply filters."""
        orig_h, orig_w = orig_shape
        img_area = orig_h * orig_w

        # output shape: [1, 300, 6] → [300, 6]
        # columns: x1, y1, x2, y2, confidence, class_id
        preds = output[0]  # (300, 6)

        # 1. Confidence filter
        conf = preds[:, 4]
        mask = conf >= self.config.conf_threshold
        preds = preds[mask]

        if len(preds) == 0:
            return []

        # Coordinates are in 640×640 letterboxed input space
        x1 = preds[:, 0]
        y1 = preds[:, 1]
        x2 = preds[:, 2]
        y2 = preds[:, 3]

        # Rescale to original image coordinates
        x1 = (x1 - pad_x) / scale
        y1 = (y1 - pad_y) / scale
        x2 = (x2 - pad_x) / scale
        y2 = (y2 - pad_y) / scale

        # Clip to image bounds
        x1 = np.clip(x1, 0, orig_w)
        y1 = np.clip(y1, 0, orig_h)
        x2 = np.clip(x2, 0, orig_w)
        y2 = np.clip(y2, 0, orig_h)

        # 2. Size filter + build Detection objects
        detections = []
        for i in range(len(preds)):
            det = Detection(
                x1=float(x1[i]), y1=float(y1[i]),
                x2=float(x2[i]), y2=float(y2[i]),
                confidence=float(preds[i, 4]),
                class_id=int(preds[i, 5]),
            )

            if det.area < img_area * self.config.min_box_area_ratio:
                continue
            if det.area > img_area * self.config.max_box_area_ratio:
                continue
            if det.width < self.config.min_box_dim or det.height < self.config.min_box_dim:
                continue
            if det.aspect_ratio > self.config.max_aspect_ratio:
                continue

            detections.append(det)

        # Sort by confidence descending
        detections.sort(key=lambda d: d.confidence, reverse=True)

        # 3. Greedy IoU dedup — suppress overlapping boxes the model missed
        detections = self._greedy_nms(detections, self.config.dedup_iou_threshold)

        # 4. Containment suppression — if a large box fully contains a smaller one,
        #    suppress the larger box (it's a region detection, not a single glyph)
        detections = self._suppress_containers(detections)

        return detections

    @staticmethod
    def _suppress_containers(detections: list[Detection]) -> list[Detection]:
        """Remove large boxes that fully contain smaller high-confidence boxes."""
        if len(detections) < 2:
            return detections
        suppressed = set()
        for i, big in enumerate(detections):
            if i in suppressed:
                continue
            for j, small in enumerate(detections):
                if j == i or j in suppressed:
                    continue
                # Check if small is fully contained inside big
                if (big.x1 <= small.x1 and big.y1 <= small.y1 and
                        big.x2 >= small.x2 and big.y2 >= small.y2):
                    # big contains small — suppress the bigger box if it's >4x the area
                    if big.area > small.area * 4:
                        suppressed.add(i)
                        break
        return [d for i, d in enumerate(detections) if i not in suppressed]

    @staticmethod
    def _greedy_nms(detections: list[Detection], iou_threshold: float) -> list[Detection]:
        """Greedy NMS: keep highest-confidence box, suppress overlapping ones."""
        if not detections:
            return []
        keep = []
        suppressed = set()
        for i, det_i in enumerate(detections):
            if i in suppressed:
                continue
            keep.append(det_i)
            for j in range(i + 1, len(detections)):
                if j in suppressed:
                    continue
                iou = _box_iou(
                    (det_i.x1, det_i.y1, det_i.x2, det_i.y2),
                    (detections[j].x1, detections[j].y1, detections[j].x2, detections[j].y2),
                )
                if iou >= iou_threshold:
                    suppressed.add(j)
        return keep

    def detect(self, image: np.ndarray) -> list[Detection]:
        """Run full detection pipeline: preprocess → inference → postprocess."""
        blob, orig_shape, scale, pad_x, pad_y = self.preprocess(image)
        output = self.session.run(None, {self.input_name: blob})[0]
        return self.postprocess(output, orig_shape, scale, pad_x, pad_y)

    def detect_from_file(self, image_path: str | Path) -> list[Detection]:
        """Load image and run detection."""
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        return self.detect(image)


def _box_iou(a: tuple, b: tuple) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0
