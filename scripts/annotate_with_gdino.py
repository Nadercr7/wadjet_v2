r"""Auto-annotate images with GroundingDINO (via transformers) -> YOLO format.

Usage:
    # Activate dataprep-env first:
    #   & scripts\dataprep-env\Scripts\Activate.ps1

    # Annotate V1 raw images:
    python scripts/annotate_with_gdino.py \
        --input "D:\Personal attachements\Projects\Final_Horus\Wadjet\hieroglyph_model\data\raw\detection_images" \
        --output "data/detection/v1_raw" \
        --prompts "hieroglyph" "Egyptian hieroglyphic sign" "carved symbol on stone"

    # Annotate scraped museum images:
    python scripts/annotate_with_gdino.py \
        --input "data/detection/scraped_raw" \
        --output "data/detection/scraped_annotated"

    # Preview only (no file writes):
    python scripts/annotate_with_gdino.py --input ... --output ... --preview 10

Output structure:
    output_dir/
        images/        ← copied/symlinked images
        labels/        ← YOLO .txt files (class_id cx cy w h, normalized)
        previews/      ← annotated images for QA (if --preview)
        metadata.json  ← annotation stats and per-image metadata
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

# ── Constants ──
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
DEFAULT_PROMPTS = ["hieroglyph", "Egyptian hieroglyphic sign", "carved symbol"]
DEFAULT_BOX_THRESHOLD = 0.20
DEFAULT_TEXT_THRESHOLD = 0.15
MODEL_ID = "IDEA-Research/grounding-dino-base"

# Minimum box dimension (fraction of image) to filter noise
MIN_BOX_FRAC = 0.008  # 0.8% of image dimension
MAX_BOX_FRAC = 0.60   # 60% of image — probably not a single glyph


def load_model(model_id: str = MODEL_ID, device: str = "cpu"):
    """Load GroundingDINO model and processor."""
    print(f"Loading model: {model_id} (device={device})...")
    t0 = time.time()
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)
    model.eval()
    print(f"  Model loaded in {time.time() - t0:.1f}s")
    return model, processor, device


def detect_hieroglyphs(
    model,
    processor,
    device: str,
    image: Image.Image,
    prompts: list[str],
    box_threshold: float = DEFAULT_BOX_THRESHOLD,
    text_threshold: float = DEFAULT_TEXT_THRESHOLD,
) -> list[dict]:
    """Run GroundingDINO on a single image with multiple text prompts.

    Returns list of dicts: {x1, y1, x2, y2, confidence, label}
    Coordinates are in pixel space (not normalized).
    """
    w, h = image.size
    all_boxes = []

    # Downscale very large images for GroundingDINO (attention is O(n^2) on pixels)
    MAX_DIM = 1200
    scale = 1.0
    proc_image = image
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        proc_image = image.resize((new_w, new_h), Image.LANCZOS)

    pw, ph = proc_image.size

    for prompt in prompts:
        # GroundingDINO expects period-terminated prompts
        text = prompt if prompt.endswith(".") else prompt + "."

        inputs = processor(images=proc_image, text=text, return_tensors="pt").to(device)

        with torch.no_grad():
            outputs = model(**inputs)

        results = processor.post_process_grounded_object_detection(
            outputs,
            inputs["input_ids"],
            text_threshold=text_threshold,
            target_sizes=[(ph, pw)],
        )[0]

        for box, score, label in zip(
            results["boxes"].cpu().numpy(),
            results["scores"].cpu().numpy(),
            results["labels"],
        ):
            if float(score) < box_threshold:
                continue
            x1, y1, x2, y2 = box.tolist()
            # Scale back to original image coordinates
            if scale != 1.0:
                x1 /= scale
                y1 /= scale
                x2 /= scale
                y2 /= scale
            all_boxes.append({
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "confidence": float(score),
                "label": label,
            })

    # Deduplicate overlapping boxes from different prompts (NMS)
    if all_boxes:
        all_boxes = _nms_boxes(all_boxes, iou_threshold=0.5)

    # Size filter
    all_boxes = _filter_by_size(all_boxes, w, h)

    return all_boxes


def _nms_boxes(boxes: list[dict], iou_threshold: float = 0.5) -> list[dict]:
    """Simple NMS across multi-prompt detections."""
    if not boxes:
        return boxes

    # Sort by confidence descending
    boxes.sort(key=lambda b: b["confidence"], reverse=True)

    coords = np.array([[b["x1"], b["y1"], b["x2"], b["y2"]] for b in boxes], dtype=np.float32)
    scores = np.array([b["confidence"] for b in boxes], dtype=np.float32)

    indices = cv2.dnn.NMSBoxes(
        coords.tolist(), scores.tolist(),
        score_threshold=0.0, nms_threshold=iou_threshold,
    )
    if len(indices) == 0:
        return []

    indices = np.array(indices).flatten()
    return [boxes[i] for i in indices]


def _filter_by_size(
    boxes: list[dict], img_w: int, img_h: int,
) -> list[dict]:
    """Remove boxes that are too small or too large."""
    filtered = []
    for b in boxes:
        bw = b["x2"] - b["x1"]
        bh = b["y2"] - b["y1"]
        # Fraction of image
        frac_w = bw / img_w
        frac_h = bh / img_h
        if frac_w < MIN_BOX_FRAC or frac_h < MIN_BOX_FRAC:
            continue
        if frac_w > MAX_BOX_FRAC and frac_h > MAX_BOX_FRAC:
            continue
        # Extreme aspect ratio filter
        aspect = max(bw, bh) / (min(bw, bh) + 1e-6)
        if aspect > 8.0:
            continue
        filtered.append(b)
    return filtered


def boxes_to_yolo(boxes: list[dict], img_w: int, img_h: int) -> list[str]:
    """Convert pixel-space boxes to YOLO format lines.

    Format: class_id cx cy w h (all normalized 0-1)
    Single class: class_id = 0 always.
    """
    lines = []
    for b in boxes:
        cx = ((b["x1"] + b["x2"]) / 2) / img_w
        cy = ((b["y1"] + b["y2"]) / 2) / img_h
        w = (b["x2"] - b["x1"]) / img_w
        h = (b["y2"] - b["y1"]) / img_h
        # Clamp to [0, 1]
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        w = max(0.0, min(1.0, w))
        h = max(0.0, min(1.0, h))
        lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


def draw_preview(image_path: Path, boxes: list[dict], output_path: Path) -> None:
    """Draw bounding boxes on image and save for visual QA."""
    img = cv2.imread(str(image_path))
    if img is None:
        return

    for i, b in enumerate(boxes):
        x1, y1, x2, y2 = int(b["x1"]), int(b["y1"]), int(b["x2"]), int(b["y2"])
        conf = b["confidence"]
        color = (0, 215, 55) if conf >= 0.4 else (0, 165, 255)  # Green / Orange
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = f"#{i} {conf:.2f}"
        cv2.putText(img, label, (x1, max(12, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    cv2.imwrite(str(output_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85])


def process_directory(
    input_dir: Path,
    output_dir: Path,
    model,
    processor,
    device: str,
    prompts: list[str],
    box_threshold: float,
    text_threshold: float,
    preview_count: int = 0,
    copy_images: bool = True,
    limit: int = 0,
) -> dict:
    """Process all images in a directory.

    Returns metadata dict with stats.
    """
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    if preview_count > 0:
        previews_dir = output_dir / "previews"
        previews_dir.mkdir(parents=True, exist_ok=True)

    # Find all images
    image_files = sorted([
        f for f in input_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTS
    ])

    if not image_files:
        print(f"No images found in {input_dir}")
        return {"total": 0}

    if limit > 0:
        image_files = image_files[:limit]

    print(f"Found {len(image_files)} images in {input_dir}")
    print(f"Prompts: {prompts}")
    print(f"Thresholds: box={box_threshold}, text={text_threshold}")
    print()

    stats = {
        "total_images": len(image_files),
        "annotated_images": 0,
        "empty_images": 0,
        "total_boxes": 0,
        "avg_boxes_per_image": 0,
        "avg_confidence": 0,
        "prompts": prompts,
        "box_threshold": box_threshold,
        "text_threshold": text_threshold,
        "model": MODEL_ID,
        "per_image": {},
    }

    all_confidences = []
    preview_idx = 0
    skipped_existing = 0

    for i, img_path in enumerate(image_files):
        # Resume support — skip if label already exists
        stem = img_path.stem
        label_path = labels_dir / f"{stem}.txt"
        if label_path.exists():
            skipped_existing += 1
            continue

        # Progress
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1}/{len(image_files)}] {img_path.name}... (skipped={skipped_existing})", flush=True)

        try:
            pil_image = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"  SKIP {img_path.name}: {e}")
            continue

        w, h = pil_image.size

        # Detect
        t0 = time.time()
        boxes = detect_hieroglyphs(
            model, processor, device, pil_image, prompts,
            box_threshold, text_threshold,
        )
        dt = time.time() - t0

        # Write YOLO label
        yolo_lines = boxes_to_yolo(boxes, w, h)
        label_path.write_text("\n".join(yolo_lines) + ("\n" if yolo_lines else ""),
                              encoding="utf-8")

        # Copy image
        if copy_images:
            dest = images_dir / img_path.name
            if not dest.exists():
                shutil.copy2(img_path, dest)

        # Preview
        if preview_count > 0 and preview_idx < preview_count and boxes:
            preview_path = output_dir / "previews" / f"{stem}_preview.jpg"
            draw_preview(img_path, boxes, preview_path)
            preview_idx += 1

        # Stats
        n_boxes = len(boxes)
        if n_boxes > 0:
            stats["annotated_images"] += 1
            stats["total_boxes"] += n_boxes
            confs = [b["confidence"] for b in boxes]
            all_confidences.extend(confs)
        else:
            stats["empty_images"] += 1

        stats["per_image"][stem] = {
            "boxes": n_boxes,
            "avg_conf": round(np.mean([b["confidence"] for b in boxes]), 4) if boxes else 0,
            "time_s": round(dt, 2),
            "width": w,
            "height": h,
        }

    # Final stats
    if stats["annotated_images"] > 0:
        stats["avg_boxes_per_image"] = round(
            stats["total_boxes"] / stats["annotated_images"], 1
        )
    if all_confidences:
        stats["avg_confidence"] = round(float(np.mean(all_confidences)), 4)

    # Write metadata
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary
    print()
    print("=" * 60)
    print(f"  Total images:     {stats['total_images']}")
    print(f"  With detections:  {stats['annotated_images']}")
    print(f"  Empty (no boxes): {stats['empty_images']}")
    print(f"  Total boxes:      {stats['total_boxes']}")
    print(f"  Avg boxes/image:  {stats['avg_boxes_per_image']}")
    print(f"  Avg confidence:   {stats['avg_confidence']}")
    print(f"  Output dir:       {output_dir}")
    print("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Auto-annotate images with GroundingDINO → YOLO format"
    )
    parser.add_argument("--input", required=True, type=Path,
                        help="Input directory with images")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output directory for images/ + labels/")
    parser.add_argument("--prompts", nargs="+", default=DEFAULT_PROMPTS,
                        help="Text prompts for detection")
    parser.add_argument("--box-threshold", type=float, default=DEFAULT_BOX_THRESHOLD,
                        help=f"Detection confidence threshold (default: {DEFAULT_BOX_THRESHOLD})")
    parser.add_argument("--text-threshold", type=float, default=DEFAULT_TEXT_THRESHOLD,
                        help=f"Text matching threshold (default: {DEFAULT_TEXT_THRESHOLD})")
    parser.add_argument("--preview", type=int, default=0,
                        help="Number of preview images to generate (0=none)")
    parser.add_argument("--no-copy", action="store_true",
                        help="Don't copy images to output dir (just write labels)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only first N images (0=all)")
    parser.add_argument("--device", default="cpu",
                        help="Device (cpu or cuda)")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input directory does not exist: {args.input}")
        sys.exit(1)

    model, processor, device = load_model(MODEL_ID, args.device)

    process_directory(
        input_dir=args.input,
        output_dir=args.output,
        model=model,
        processor=processor,
        device=device,
        prompts=args.prompts,
        box_threshold=args.box_threshold,
        text_threshold=args.text_threshold,
        preview_count=args.preview,
        copy_images=not args.no_copy,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
