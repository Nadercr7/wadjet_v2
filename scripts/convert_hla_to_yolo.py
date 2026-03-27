r"""Convert COCO-format hieroglyph datasets to YOLO single-class format.

Supports:
  - HLA Dataset (897 images, COCO JSON with polygon annotations)
  - Signs Segmentation dataset (300 images, individual sign polygons)
  - Any COCO-format dataset with segmentation/bbox annotations

Usage:
    # Activate dataprep-env first:
    #   & scripts\dataprep-env\Scripts\Activate.ps1

    # Convert HLA dataset:
    python scripts/convert_hla_to_yolo.py \
        --images "path/to/hla/images" \
        --coco-json "path/to/hla/annotations.json" \
        --output "data/detection/hla" \
        --preview 5

    # Convert Signs Segmentation dataset:
    python scripts/convert_hla_to_yolo.py \
        --images "path/to/signs_seg/images" \
        --coco-json "path/to/signs_seg/annotations.json" \
        --output "data/detection/signs_seg" \
        --preview 5

All classes are mapped to class 0 (hieroglyph) for single-class detection.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np


def load_coco(coco_path: Path) -> dict:
    """Load and validate COCO JSON annotations."""
    with open(coco_path, "r", encoding="utf-8") as f:
        coco = json.load(f)

    required = {"images", "annotations"}
    missing = required - set(coco.keys())
    if missing:
        print(f"ERROR: COCO JSON missing keys: {missing}")
        sys.exit(1)

    print(f"  Categories: {[c['name'] for c in coco.get('categories', [])]}")
    print(f"  Images: {len(coco['images'])}")
    print(f"  Annotations: {len(coco['annotations'])}")
    return coco


def coco_to_yolo_boxes(coco: dict) -> dict[int, list[tuple[float, float, float, float]]]:
    """Extract YOLO-format bboxes from COCO annotations.

    Returns {image_id: [(cx, cy, w, h), ...]} with normalized coords.
    """
    # Build image lookup: id → {width, height}
    img_lookup = {}
    for img in coco["images"]:
        img_lookup[img["id"]] = {
            "width": img["width"],
            "height": img["height"],
            "file_name": img["file_name"],
        }

    # Process annotations
    boxes_by_image: dict[int, list[tuple[float, float, float, float]]] = {}

    for ann in coco["annotations"]:
        img_id = ann["image_id"]
        if img_id not in img_lookup:
            continue

        img_info = img_lookup[img_id]
        iw, ih = img_info["width"], img_info["height"]

        # Get bbox — prefer explicit bbox, fall back to segmentation
        bbox = None

        if "bbox" in ann and ann["bbox"]:
            # COCO bbox = [x, y, width, height] in pixels
            x, y, w, h = ann["bbox"]
            bbox = (x, y, w, h)
        elif "segmentation" in ann and ann["segmentation"]:
            seg = ann["segmentation"]
            if isinstance(seg, list) and len(seg) > 0:
                # Polygon format: [[x1, y1, x2, y2, ...]]
                all_points = []
                for poly in seg:
                    if isinstance(poly, list):
                        xs = poly[0::2]
                        ys = poly[1::2]
                        all_points.extend(zip(xs, ys))
                if all_points:
                    xs, ys = zip(*all_points)
                    x_min, x_max = min(xs), max(xs)
                    y_min, y_max = min(ys), max(ys)
                    bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

        if bbox is None:
            continue

        x, y, w, h = bbox
        if w <= 0 or h <= 0 or iw <= 0 or ih <= 0:
            continue

        # Convert to YOLO: normalized cx, cy, w, h
        cx = (x + w / 2) / iw
        cy = (y + h / 2) / ih
        nw = w / iw
        nh = h / ih

        # Clamp to [0, 1]
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        nw = max(0.001, min(1.0, nw))
        nh = max(0.001, min(1.0, nh))

        if img_id not in boxes_by_image:
            boxes_by_image[img_id] = []
        boxes_by_image[img_id].append((cx, cy, nw, nh))

    return boxes_by_image


def draw_preview(image_path: Path, yolo_boxes: list[tuple], output_path: Path):
    """Draw YOLO boxes on an image and save preview."""
    img = cv2.imread(str(image_path))
    if img is None:
        return
    h, w = img.shape[:2]

    for cx, cy, bw, bh in yolo_boxes:
        x1 = int((cx - bw / 2) * w)
        y1 = int((cy - bh / 2) * h)
        x2 = int((cx + bw / 2) * w)
        y2 = int((cy + bh / 2) * h)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 215, 55), 2)

    cv2.imwrite(str(output_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85])


def process_dataset(
    images_dir: Path,
    coco_path: Path,
    output_dir: Path,
    preview_count: int = 0,
    copy_images: bool = True,
    min_box_frac: float = 0.005,
    max_box_frac: float = 0.80,
) -> dict:
    """Convert COCO dataset to YOLO format.

    Args:
        images_dir: Directory containing the images
        coco_path: Path to COCO JSON annotations
        output_dir: Output directory (images/ + labels/ + previews/)
        preview_count: Number of preview images to generate
        copy_images: Whether to copy images to output dir
        min_box_frac: Min box area as fraction of image (filter tiny)
        max_box_frac: Max box area as fraction of image (filter huge)
    """
    # Load COCO
    print(f"Loading COCO annotations from {coco_path}...")
    coco = load_coco(coco_path)

    # Create output dirs
    out_images = output_dir / "images"
    out_labels = output_dir / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    if preview_count > 0:
        out_previews = output_dir / "previews"
        out_previews.mkdir(parents=True, exist_ok=True)

    # Convert
    boxes_by_image = coco_to_yolo_boxes(coco)

    # Build image_id → file_name mapping
    id_to_file = {img["id"]: img["file_name"] for img in coco["images"]}

    stats = {
        "total_images": len(coco["images"]),
        "annotated_images": 0,
        "empty_images": 0,
        "total_boxes": 0,
        "filtered_small": 0,
        "filtered_large": 0,
        "source": str(coco_path),
        "per_image": {},
    }

    preview_idx = 0

    for img_entry in coco["images"]:
        img_id = img_entry["id"]
        file_name = img_entry["file_name"]
        stem = Path(file_name).stem

        # Find the image file (try multiple extensions)
        img_path = images_dir / file_name
        if not img_path.exists():
            # Try without subdirectory
            img_path = images_dir / Path(file_name).name
        if not img_path.exists():
            continue

        # Get boxes for this image
        raw_boxes = boxes_by_image.get(img_id, [])

        # Size filter
        filtered_boxes = []
        for cx, cy, bw, bh in raw_boxes:
            area = bw * bh
            if area < min_box_frac:
                stats["filtered_small"] += 1
                continue
            if area > max_box_frac:
                stats["filtered_large"] += 1
                continue
            filtered_boxes.append((cx, cy, bw, bh))

        # Write YOLO label (class 0 for all)
        label_path = out_labels / f"{stem}.txt"
        lines = [f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for cx, cy, w, h in filtered_boxes]
        label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

        # Copy image
        if copy_images:
            dest = out_images / img_path.name
            if not dest.exists():
                shutil.copy2(img_path, dest)

        # Preview
        if preview_count > 0 and preview_idx < preview_count and filtered_boxes:
            preview_path = output_dir / "previews" / f"{stem}_preview.jpg"
            draw_preview(img_path, filtered_boxes, preview_path)
            preview_idx += 1

        # Stats
        n = len(filtered_boxes)
        if n > 0:
            stats["annotated_images"] += 1
            stats["total_boxes"] += n
        else:
            stats["empty_images"] += 1

        stats["per_image"][stem] = {"boxes": n}

    # Final stats
    if stats["annotated_images"] > 0:
        stats["avg_boxes_per_image"] = round(
            stats["total_boxes"] / stats["annotated_images"], 1
        )
    else:
        stats["avg_boxes_per_image"] = 0

    # Write metadata
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary
    print()
    print("=" * 60)
    print(f"  Total images:      {stats['total_images']}")
    print(f"  With detections:   {stats['annotated_images']}")
    print(f"  Empty (no boxes):  {stats['empty_images']}")
    print(f"  Total boxes:       {stats['total_boxes']}")
    print(f"  Avg boxes/image:   {stats['avg_boxes_per_image']}")
    print(f"  Filtered (small):  {stats['filtered_small']}")
    print(f"  Filtered (large):  {stats['filtered_large']}")
    print(f"  Output dir:        {output_dir}")
    print("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Convert COCO-format hieroglyph annotations to YOLO single-class format"
    )
    parser.add_argument("--images", required=True, type=Path,
                        help="Directory containing images")
    parser.add_argument("--coco-json", required=True, type=Path,
                        help="Path to COCO JSON annotation file")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output directory for images/ + labels/")
    parser.add_argument("--preview", type=int, default=0,
                        help="Number of preview images to generate (0=none)")
    parser.add_argument("--no-copy", action="store_true",
                        help="Don't copy images to output dir (just write labels)")
    parser.add_argument("--min-box-frac", type=float, default=0.005,
                        help="Min box area as fraction of image (default: 0.005)")
    parser.add_argument("--max-box-frac", type=float, default=0.80,
                        help="Max box area as fraction of image (default: 0.80)")

    args = parser.parse_args()

    if not args.images.exists():
        print(f"ERROR: Images directory does not exist: {args.images}")
        sys.exit(1)
    if not args.coco_json.exists():
        print(f"ERROR: COCO JSON does not exist: {args.coco_json}")
        sys.exit(1)

    process_dataset(
        images_dir=args.images,
        coco_path=args.coco_json,
        output_dir=args.output,
        preview_count=args.preview,
        copy_images=not args.no_copy,
        min_box_frac=args.min_box_frac,
        max_box_frac=args.max_box_frac,
    )


if __name__ == "__main__":
    main()
