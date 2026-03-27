"""Grid search over confidence thresholds for glyph detection.

Moved from app/core/postprocess.py — debug utility, not production code.

Usage:
    python scripts/evaluate_conf_threshold.py --images data/detection/val/images --labels data/detection/val/labels
"""

from pathlib import Path

import cv2
import numpy as np

from app.core.postprocess import GlyphDetector, _box_iou


def evaluate_conf_threshold(
    detector: GlyphDetector,
    image_dir: Path,
    label_dir: Path,
    conf_range: tuple = (0.05, 0.50, 0.05),
) -> dict:
    """Grid search over confidence thresholds to find optimal post-processing params.

    Returns dict with best params and per-config results.
    """
    images = sorted(image_dir.glob("*.jpg"))
    results = []

    for conf in np.arange(*conf_range):
        detector.config.conf_threshold = float(conf)

        total_tp, total_fp, total_fn = 0, 0, 0

        for img_path in images:
            label_path = label_dir / img_path.with_suffix(".txt").name
            if not label_path.exists():
                continue

            preds = detector.detect_from_file(img_path)
            img = cv2.imread(str(img_path))
            img_h, img_w = img.shape[:2]

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
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
        })

    best = max(results, key=lambda r: r["f1"])

    return {
        "best": best,
        "all_results": results,
        "num_images": len(images),
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--images", required=True, help="Image directory")
    parser.add_argument("--labels", required=True, help="Label directory (YOLO format)")
    parser.add_argument("--model", default="models/hieroglyph/detector/glyph_detector_uint8.onnx")
    args = parser.parse_args()

    det = GlyphDetector(args.model)
    result = evaluate_conf_threshold(det, Path(args.images), Path(args.labels))
    print(json.dumps(result, indent=2))
