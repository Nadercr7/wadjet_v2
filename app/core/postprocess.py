"""H3.9 — Glyph detection post-processing: NMS tuning, confidence filtering, box merging.

ONNX-based inference pipeline with configurable post-processing for
hieroglyph bounding box detection using the YOLOv8s model.
"""

import numpy as np
import onnxruntime as ort
import cv2
from pathlib import Path
from dataclasses import dataclass, field

# ── Default tuning parameters ────────────────────────────────
CONF_THRESHOLD = 0.10       # Minimum detection confidence (lowered for stone inscriptions)
NMS_IOU_THRESHOLD = 0.45    # NMS IoU overlap threshold
MIN_BOX_AREA_RATIO = 0.0005 # Minimum box area as fraction of image area
MAX_BOX_AREA_RATIO = 0.40   # Maximum box area as fraction of image area (raised for cartouches)
MIN_BOX_DIM = 10            # Minimum box dimension in pixels (at original scale)
MAX_ASPECT_RATIO = 5.0      # Maximum width/height or height/width ratio
MERGE_IOU_THRESHOLD = 0.65  # IoU threshold for merging overlapping detections
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
    """Configurable post-processing parameters."""
    conf_threshold: float = CONF_THRESHOLD
    nms_iou_threshold: float = NMS_IOU_THRESHOLD
    min_box_area_ratio: float = MIN_BOX_AREA_RATIO
    max_box_area_ratio: float = MAX_BOX_AREA_RATIO
    min_box_dim: int = MIN_BOX_DIM
    max_aspect_ratio: float = MAX_ASPECT_RATIO
    merge_iou_threshold: float = MERGE_IOU_THRESHOLD


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

    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, tuple[int, int], float, float]:
        """Resize + normalize image for YOLO input. Returns (blob, orig_shape, scale_x, scale_y)."""
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
        """Apply confidence filter, NMS, size filter, and merge overlapping boxes."""
        orig_h, orig_w = orig_shape
        img_area = orig_h * orig_w

        # output shape: [1, 5, 8400] → transpose to [8400, 5]
        preds = output[0].T  # (8400, 5)

        # Extract components: cx, cy, w, h, conf
        cx, cy, w, h, conf = preds[:, 0], preds[:, 1], preds[:, 2], preds[:, 3], preds[:, 4]

        # 1. Confidence filter
        mask = conf >= self.config.conf_threshold
        cx, cy, w, h, conf = cx[mask], cy[mask], w[mask], h[mask], conf[mask]

        if len(conf) == 0:
            return []

        # Convert to x1y1x2y2 in model input space
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2

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

        # 2. NMS
        boxes = np.stack([x1, y1, x2, y2], axis=1).astype(np.float32)
        scores = conf.astype(np.float32)
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(),
            scores.tolist(),
            self.config.conf_threshold,
            self.config.nms_iou_threshold,
        )
        if len(indices) == 0:
            return []
        indices = np.array(indices).flatten()

        detections = []
        for i in indices:
            det = Detection(
                x1=float(x1[i]), y1=float(y1[i]),
                x2=float(x2[i]), y2=float(y2[i]),
                confidence=float(conf[i]),
            )

            # 3. Size filter
            if det.area < img_area * self.config.min_box_area_ratio:
                continue
            if det.area > img_area * self.config.max_box_area_ratio:
                continue
            if det.width < self.config.min_box_dim or det.height < self.config.min_box_dim:
                continue
            if det.aspect_ratio > self.config.max_aspect_ratio:
                continue

            detections.append(det)

        # 4. Merge heavily overlapping boxes
        detections = self._merge_overlapping(detections)

        # Sort by confidence descending
        detections.sort(key=lambda d: d.confidence, reverse=True)

        return detections

    def _merge_overlapping(self, detections: list[Detection]) -> list[Detection]:
        """Merge boxes with IoU above merge threshold — keep the higher-confidence one."""
        if len(detections) <= 1:
            return detections

        # Sort by confidence so we keep best ones
        detections.sort(key=lambda d: d.confidence, reverse=True)
        merged = []
        used = set()

        for i, det_i in enumerate(detections):
            if i in used:
                continue
            # Check against remaining detections
            for j in range(i + 1, len(detections)):
                if j in used:
                    continue
                iou = self._compute_iou(det_i, detections[j])
                if iou >= self.config.merge_iou_threshold:
                    # Merge: expand box to cover both, keep higher confidence
                    det_i = Detection(
                        x1=min(det_i.x1, detections[j].x1),
                        y1=min(det_i.y1, detections[j].y1),
                        x2=max(det_i.x2, detections[j].x2),
                        y2=max(det_i.y2, detections[j].y2),
                        confidence=max(det_i.confidence, detections[j].confidence),
                    )
                    used.add(j)
            merged.append(det_i)

        return merged

    @staticmethod
    def _compute_iou(a: Detection, b: Detection) -> float:
        """Compute IoU between two detections."""
        ix1 = max(a.x1, b.x1)
        iy1 = max(a.y1, b.y1)
        ix2 = min(a.x2, b.x2)
        iy2 = min(a.y2, b.y2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        union = a.area + b.area - inter
        if union <= 0:
            return 0.0
        return inter / union

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


def evaluate_nms_params(
    detector: GlyphDetector,
    image_dir: Path,
    label_dir: Path,
    conf_range: tuple = (0.15, 0.50, 0.05),
    iou_range: tuple = (0.30, 0.60, 0.05),
) -> dict:
    """Grid search over conf/iou thresholds to find optimal post-processing params.

    Returns dict with best params and per-config results.
    """
    images = sorted(image_dir.glob("*.jpg"))
    results = []

    for conf in np.arange(*conf_range):
        for iou in np.arange(*iou_range):
            detector.config.conf_threshold = float(conf)
            detector.config.nms_iou_threshold = float(iou)

            total_tp, total_fp, total_fn = 0, 0, 0

            for img_path in images:
                label_path = label_dir / img_path.with_suffix(".txt").name
                if not label_path.exists():
                    continue

                # Get predictions
                preds = detector.detect_from_file(img_path)
                img = cv2.imread(str(img_path))
                img_h, img_w = img.shape[:2]

                # Load ground truth (YOLO format)
                gt_boxes = []
                for line in label_path.read_text().strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.strip().split()
                    cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                    gx1 = (cx - w / 2) * img_w
                    gy1 = (cy - h / 2) * img_h
                    gx2 = (cx + w / 2) * img_w
                    gy2 = (cy + h / 2) * img_h
                    gt_boxes.append((gx1, gy1, gx2, gy2))

                # Match predictions to GT (greedy matching, IoU > 0.5)
                matched_gt = set()
                tp = 0
                for pred in preds:
                    best_iou = 0
                    best_gt_idx = -1
                    for gi, gt in enumerate(gt_boxes):
                        if gi in matched_gt:
                            continue
                        iou = _box_iou(
                            (pred.x1, pred.y1, pred.x2, pred.y2), gt
                        )
                        if iou > best_iou:
                            best_iou = iou
                            best_gt_idx = gi
                    if best_iou >= 0.5 and best_gt_idx >= 0:
                        tp += 1
                        matched_gt.add(best_gt_idx)

                fp = len(preds) - tp
                fn = len(gt_boxes) - tp
                total_tp += tp
                total_fp += fp
                total_fn += fn

            precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
            recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            results.append({
                "conf": round(float(conf), 2),
                "iou": round(float(iou), 2),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "tp": total_tp,
                "fp": total_fp,
                "fn": total_fn,
            })

    # Find best by F1
    best = max(results, key=lambda r: r["f1"])

    return {
        "best": best,
        "all_results": results,
        "num_images": len(images),
    }


def _box_iou(a: tuple, b: tuple) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0
