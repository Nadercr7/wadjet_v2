r"""Validate a YOLO-format detection dataset.

Checks:
  - Image-label pairing (every image has a label file)
  - Label format correctness (class_id cx cy w h)
  - Bounding box validity (within [0,1], reasonable sizes)
  - Class distribution
  - Image size statistics
  - Source distribution (if source prefix present)
  - Generates visual previews with annotations

Usage:
    # Activate dataprep-env first:
    #   & scripts\dataprep-env\Scripts\Activate.ps1

    # Validate merged dataset:
    python scripts/validate_dataset.py \
        --dataset data/detection/merged \
        --preview 20

    # Validate single source:
    python scripts/validate_dataset.py \
        --dataset data/detection/v1_raw \
        --preview 5
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def find_images_labels(dataset_dir: Path) -> tuple[list[Path], list[Path]]:
    """Find image and label directories (supports both flat and split layouts).

    Supports:
        dataset/images/ + dataset/labels/           (flat)
        dataset/images/train/ + dataset/labels/train/  (split)
    """
    images_dir = dataset_dir / "images"
    labels_dir = dataset_dir / "labels"

    image_files = []
    label_files = []

    if not images_dir.exists():
        return [], []

    # Check if split layout (train/val/test subdirs)
    splits = [d for d in images_dir.iterdir() if d.is_dir()]
    if splits:
        for split_dir in sorted(splits):
            split_name = split_dir.name
            for img in sorted(split_dir.iterdir()):
                if img.suffix.lower() in SUPPORTED_EXTS:
                    image_files.append(img)
                    lbl = labels_dir / split_name / f"{img.stem}.txt"
                    label_files.append(lbl)
    else:
        # Flat layout
        for img in sorted(images_dir.iterdir()):
            if img.suffix.lower() in SUPPORTED_EXTS:
                image_files.append(img)
                lbl = labels_dir / f"{img.stem}.txt"
                label_files.append(lbl)

    return image_files, label_files


def parse_yolo_label(label_path: Path) -> list[dict]:
    """Parse a YOLO label file. Returns list of boxes."""
    boxes = []
    if not label_path.exists():
        return boxes

    text = label_path.read_text(encoding="utf-8").strip()
    if not text:
        return boxes

    for line_num, line in enumerate(text.split("\n"), 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            boxes.append({"error": f"Line {line_num}: expected 5 values, got {len(parts)}", "raw": line})
            continue

        try:
            class_id = int(parts[0])
            cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            boxes.append({
                "class_id": class_id,
                "cx": cx, "cy": cy, "w": w, "h": h,
                "line": line_num,
            })
        except ValueError:
            boxes.append({"error": f"Line {line_num}: invalid numbers", "raw": line})

    return boxes


def validate_box(box: dict) -> list[str]:
    """Validate a single YOLO bounding box. Returns list of issues."""
    issues = []

    if "error" in box:
        return [box["error"]]

    cx, cy, w, h = box["cx"], box["cy"], box["w"], box["h"]

    # Range checks
    for name, val in [("cx", cx), ("cy", cy), ("w", w), ("h", h)]:
        if val < 0 or val > 1:
            issues.append(f"Line {box['line']}: {name}={val:.4f} out of [0,1]")

    # Size checks
    area = w * h
    if area < 0.0001:
        issues.append(f"Line {box['line']}: tiny box (area={area:.6f})")
    if area > 0.90:
        issues.append(f"Line {box['line']}: huge box (area={area:.4f})")

    # Aspect ratio (very narrow/tall boxes are suspicious)
    if w > 0 and h > 0:
        ratio = max(w / h, h / w)
        if ratio > 20:
            issues.append(f"Line {box['line']}: extreme aspect ratio ({ratio:.1f})")

    return issues


def draw_validation_preview(image_path: Path, boxes: list[dict], output_path: Path):
    """Draw annotated preview with color-coded boxes."""
    img = cv2.imread(str(image_path))
    if img is None:
        return
    ih, iw = img.shape[:2]

    for box in boxes:
        if "error" in box:
            continue

        cx, cy, bw, bh = box["cx"], box["cy"], box["w"], box["h"]
        x1 = int((cx - bw / 2) * iw)
        y1 = int((cy - bh / 2) * ih)
        x2 = int((cx + bw / 2) * iw)
        y2 = int((cy + bh / 2) * ih)

        area = bw * bh
        if area < 0.005:
            color = (0, 165, 255)  # Orange — small
        elif area > 0.5:
            color = (0, 0, 255)  # Red — large
        else:
            color = (0, 215, 55)  # Green — normal

        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

    cv2.imwrite(str(output_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85])


def validate_dataset(dataset_dir: Path, preview_count: int = 0) -> dict:
    """Run full validation on a YOLO dataset."""
    print(f"Validating dataset: {dataset_dir}")

    image_files, label_files = find_images_labels(dataset_dir)

    if not image_files:
        print("ERROR: No images found")
        return {"error": "No images found"}

    print(f"  Found {len(image_files)} images")

    # Stats
    stats = {
        "total_images": len(image_files),
        "missing_labels": 0,
        "empty_labels": 0,
        "images_with_boxes": 0,
        "total_boxes": 0,
        "total_issues": 0,
        "issues": [],
        "class_distribution": defaultdict(int),
        "boxes_per_image": [],
        "box_areas": [],
        "image_sizes": [],
        "sources": defaultdict(int),
        "split_counts": defaultdict(int),
    }

    preview_dir = None
    if preview_count > 0:
        preview_dir = dataset_dir / "validation_previews"
        preview_dir.mkdir(parents=True, exist_ok=True)

    preview_idx = 0

    for i, (img_path, lbl_path) in enumerate(zip(image_files, label_files)):
        # Split tracking
        if img_path.parent.name in {"train", "val", "test"}:
            stats["split_counts"][img_path.parent.name] += 1

        # Source tracking (from filename prefix)
        name = img_path.stem
        parts = name.split("_", 1)
        if len(parts) == 2:
            stats["sources"][parts[0]] += 1

        # Image size
        img = cv2.imread(str(img_path))
        if img is not None:
            h, w = img.shape[:2]
            stats["image_sizes"].append((w, h))

        # Label validation
        if not lbl_path.exists():
            stats["missing_labels"] += 1
            stats["issues"].append(f"Missing label: {lbl_path.name}")
            stats["total_issues"] += 1
            stats["boxes_per_image"].append(0)
            continue

        boxes = parse_yolo_label(lbl_path)

        if not boxes:
            stats["empty_labels"] += 1
            stats["boxes_per_image"].append(0)
            continue

        valid_boxes = [b for b in boxes if "error" not in b]
        stats["images_with_boxes"] += 1
        stats["total_boxes"] += len(valid_boxes)
        stats["boxes_per_image"].append(len(valid_boxes))

        for box in boxes:
            if "error" in box:
                stats["issues"].append(f"{lbl_path.name}: {box['error']}")
                stats["total_issues"] += 1
            else:
                stats["class_distribution"][box["class_id"]] += 1
                stats["box_areas"].append(box["w"] * box["h"])

                box_issues = validate_box(box)
                for issue in box_issues:
                    stats["issues"].append(f"{lbl_path.name}: {issue}")
                    stats["total_issues"] += 1

        # Preview
        if preview_dir and preview_idx < preview_count and valid_boxes:
            preview_path = preview_dir / f"{img_path.stem}_val.jpg"
            draw_validation_preview(img_path, valid_boxes, preview_path)
            preview_idx += 1

    # Compute summary stats
    bpi = stats["boxes_per_image"]
    areas = stats["box_areas"]
    sizes = stats["image_sizes"]

    summary = {
        "total_images": stats["total_images"],
        "images_with_boxes": stats["images_with_boxes"],
        "empty_labels": stats["empty_labels"],
        "missing_labels": stats["missing_labels"],
        "total_boxes": stats["total_boxes"],
        "total_issues": stats["total_issues"],
        "boxes_per_image": {
            "mean": round(np.mean(bpi), 1) if bpi else 0,
            "median": round(float(np.median(bpi)), 1) if bpi else 0,
            "min": min(bpi) if bpi else 0,
            "max": max(bpi) if bpi else 0,
        },
        "box_area": {
            "mean": round(np.mean(areas), 4) if areas else 0,
            "median": round(float(np.median(areas)), 4) if areas else 0,
            "min": round(min(areas), 6) if areas else 0,
            "max": round(max(areas), 4) if areas else 0,
        },
        "image_sizes": {
            "mean_w": round(np.mean([s[0] for s in sizes])) if sizes else 0,
            "mean_h": round(np.mean([s[1] for s in sizes])) if sizes else 0,
            "min_w": min(s[0] for s in sizes) if sizes else 0,
            "min_h": min(s[1] for s in sizes) if sizes else 0,
            "max_w": max(s[0] for s in sizes) if sizes else 0,
            "max_h": max(s[1] for s in sizes) if sizes else 0,
        },
        "class_distribution": dict(stats["class_distribution"]),
        "sources": dict(stats["sources"]),
        "split_counts": dict(stats["split_counts"]),
    }

    # Write report
    report_path = dataset_dir / "validation_report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"  Total images:      {summary['total_images']}")
    print(f"  With boxes:        {summary['images_with_boxes']}")
    print(f"  Empty labels:      {summary['empty_labels']}")
    print(f"  Missing labels:    {summary['missing_labels']}")
    print(f"  Total boxes:       {summary['total_boxes']}")
    print(f"  Avg boxes/image:   {summary['boxes_per_image']['mean']}")
    print(f"  Median boxes/img:  {summary['boxes_per_image']['median']}")
    print(f"  Box area (mean):   {summary['box_area']['mean']}")
    print(f"  Issues found:      {summary['total_issues']}")

    if summary["class_distribution"]:
        print(f"\n  Class distribution:")
        for cls_id, count in sorted(summary["class_distribution"].items()):
            print(f"    Class {cls_id}: {count} boxes")

    if summary["split_counts"]:
        print(f"\n  Split counts:")
        for split, count in sorted(summary["split_counts"].items()):
            print(f"    {split}: {count}")

    if summary["sources"]:
        print(f"\n  Sources:")
        for src, count in sorted(summary["sources"].items(), key=lambda x: -x[1]):
            print(f"    {src}: {count}")

    if stats["total_issues"] > 0:
        print(f"\n  First 20 issues:")
        for issue in stats["issues"][:20]:
            print(f"    - {issue}")

    status = "PASS" if stats["total_issues"] == 0 else "WARN"
    if stats["missing_labels"] > len(image_files) * 0.1:
        status = "FAIL"

    print(f"\n  Status: {status}")
    print(f"  Report: {report_path}")
    print(f"{'='*60}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Validate a YOLO-format detection dataset"
    )
    parser.add_argument("--dataset", required=True, type=Path,
                        help="Dataset directory (with images/ + labels/)")
    parser.add_argument("--preview", type=int, default=0,
                        help="Number of preview images to generate (0=none)")

    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"ERROR: Dataset directory does not exist: {args.dataset}")
        sys.exit(1)

    validate_dataset(args.dataset, preview_count=args.preview)


if __name__ == "__main__":
    main()
