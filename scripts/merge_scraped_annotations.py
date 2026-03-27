r"""Merge newly annotated scraped images into the main detection dataset.

After running GroundingDINO annotation (locally or on Kaggle), this script:
  1. Validates the new annotations (non-empty labels, sane boxes)
  2. Copies images + labels into data/detection/merged/{images,labels}/train/
  3. Prefixes filenames with source tag (scraped_met_, scraped_wiki_)
  4. Updates merge_log.json
  5. Removes empty-label images from the dataset
  6. Resizes oversized images (>2048px) in-place

Usage:
    python scripts/merge_scraped_annotations.py \
        --annotated data/detection/scraped_annotated \
        --dry-run

    python scripts/merge_scraped_annotations.py \
        --annotated data/detection/scraped_annotated
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MERGED_DIR = ROOT / "data" / "detection" / "merged"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def validate_label(label_path: Path) -> tuple[bool, int]:
    """Check label file is valid YOLO format. Returns (valid, num_boxes)."""
    if not label_path.exists():
        return False, 0
    text = label_path.read_text(encoding="utf-8").strip()
    if not text:
        return False, 0
    boxes = 0
    for line in text.split("\n"):
        parts = line.strip().split()
        if len(parts) != 5:
            return False, 0
        try:
            vals = [float(p) for p in parts]
            # cls, cx, cy, w, h — all should be in [0,1] except cls
            if not (0 <= vals[1] <= 1 and 0 <= vals[2] <= 1 and
                    0 < vals[3] <= 1 and 0 < vals[4] <= 1):
                return False, 0
        except ValueError:
            return False, 0
        boxes += 1
    return True, boxes


def resize_if_needed(img_path: Path, max_dim: int = 2048) -> bool:
    """Resize image in-place if any dimension exceeds max_dim. Returns True if resized."""
    img = cv2.imread(str(img_path))
    if img is None:
        return False
    h, w = img.shape[:2]
    if max(h, w) <= max_dim:
        return False
    scale = max_dim / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(img_path), img_resized, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return True


def merge_source(
    annotated_dir: Path,
    source_name: str,
    prefix: str,
    target_split: str = "train",
    dry_run: bool = False,
) -> dict:
    """Merge one annotated source into the merged dataset."""
    img_dir = annotated_dir / source_name / "images"
    lbl_dir = annotated_dir / source_name / "labels"

    if not img_dir.exists():
        print(f"  SKIP: {img_dir} does not exist")
        return {"skipped": True}

    target_img_dir = MERGED_DIR / "images" / target_split
    target_lbl_dir = MERGED_DIR / "labels" / target_split

    images = sorted([
        f for f in img_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTS
    ])

    stats = {
        "total": len(images),
        "added": 0,
        "skipped_empty": 0,
        "skipped_invalid": 0,
        "skipped_exists": 0,
        "resized": 0,
        "total_boxes": 0,
    }

    for img_path in images:
        stem = img_path.stem
        lbl_path = lbl_dir / f"{stem}.txt"

        # Validate
        valid, n_boxes = validate_label(lbl_path)
        if not valid or n_boxes == 0:
            stats["skipped_empty" if n_boxes == 0 else "skipped_invalid"] += 1
            continue

        # Prefix filename to avoid collisions
        new_name = f"{prefix}{stem}{img_path.suffix.lower()}"
        target_img = target_img_dir / new_name
        target_lbl = target_lbl_dir / f"{prefix}{stem}.txt"

        if target_img.exists():
            stats["skipped_exists"] += 1
            continue

        if dry_run:
            print(f"    [DRY] {img_path.name} → {new_name} ({n_boxes} boxes)")
        else:
            shutil.copy2(img_path, target_img)
            shutil.copy2(lbl_path, target_lbl)

            # Resize if oversized
            if resize_if_needed(target_img):
                stats["resized"] += 1

        stats["added"] += 1
        stats["total_boxes"] += n_boxes

    return stats


def clean_empty_labels(dry_run: bool = False) -> int:
    """Remove images with empty label files from the merged dataset."""
    removed = 0
    for split in ("train", "val", "test"):
        lbl_dir = MERGED_DIR / "labels" / split
        img_dir = MERGED_DIR / "images" / split
        if not lbl_dir.exists():
            continue
        for lbl_path in sorted(lbl_dir.iterdir()):
            if lbl_path.suffix != ".txt":
                continue
            text = lbl_path.read_text(encoding="utf-8").strip()
            if not text:
                stem = lbl_path.stem
                # Find corresponding image
                img_path = None
                for ext in SUPPORTED_EXTS:
                    candidate = img_dir / f"{stem}{ext}"
                    if candidate.exists():
                        img_path = candidate
                        break
                if dry_run:
                    print(f"    [DRY] Remove empty: {split}/{lbl_path.name}")
                else:
                    lbl_path.unlink()
                    if img_path and img_path.exists():
                        img_path.unlink()
                removed += 1
    return removed


def resize_oversized(dry_run: bool = False, max_dim: int = 2048) -> int:
    """Resize all oversized images in the merged dataset."""
    resized = 0
    for split in ("train", "val", "test"):
        img_dir = MERGED_DIR / "images" / split
        if not img_dir.exists():
            continue
        for img_path in sorted(img_dir.iterdir()):
            if img_path.suffix.lower() not in SUPPORTED_EXTS:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            h, w = img.shape[:2]
            if max(h, w) > max_dim:
                if dry_run:
                    print(f"    [DRY] Resize: {split}/{img_path.name} ({w}x{h})")
                else:
                    resize_if_needed(img_path, max_dim)
                resized += 1
    return resized


def main():
    parser = argparse.ArgumentParser(description="Merge scraped annotations into merged dataset")
    parser.add_argument("--annotated", type=Path, default=ROOT / "data" / "detection" / "scraped_annotated",
                        help="Path to annotated scraped images (from GDino)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--clean-empty", action="store_true", help="Also remove empty labels from existing dataset")
    parser.add_argument("--resize-oversized", action="store_true", help="Also resize oversized images")
    args = parser.parse_args()

    print("=" * 60)
    print("  MERGE SCRAPED ANNOTATIONS")
    print("=" * 60)
    if args.dry_run:
        print("  *** DRY RUN — no files will be modified ***\n")

    # Merge Met
    print(f"\n■ Merging Met Museum images...")
    met_stats = merge_source(args.annotated, "met", "scraped_met_", dry_run=args.dry_run)
    print(f"  Added: {met_stats.get('added', 0)}, "
          f"Empty: {met_stats.get('skipped_empty', 0)}, "
          f"Boxes: {met_stats.get('total_boxes', 0)}")

    # Merge Wikimedia
    print(f"\n■ Merging Wikimedia images...")
    wiki_stats = merge_source(args.annotated, "wikimedia", "scraped_wiki_", dry_run=args.dry_run)
    print(f"  Added: {wiki_stats.get('added', 0)}, "
          f"Empty: {wiki_stats.get('skipped_empty', 0)}, "
          f"Boxes: {wiki_stats.get('total_boxes', 0)}")

    # Clean empty labels
    if args.clean_empty:
        print(f"\n■ Cleaning empty labels from merged dataset...")
        n_removed = clean_empty_labels(dry_run=args.dry_run)
        print(f"  Removed: {n_removed}")

    # Resize oversized
    if args.resize_oversized:
        print(f"\n■ Resizing oversized images (>2048px)...")
        n_resized = resize_oversized(dry_run=args.dry_run)
        print(f"  Resized: {n_resized}")

    # Update merge log
    total_added = met_stats.get("added", 0) + wiki_stats.get("added", 0)
    if not args.dry_run and total_added > 0:
        merge_log_path = MERGED_DIR / "merge_log.json"
        if merge_log_path.exists():
            log = json.loads(merge_log_path.read_text(encoding="utf-8"))
        else:
            log = {}
        log["scraped_met_added"] = met_stats.get("added", 0)
        log["scraped_wiki_added"] = wiki_stats.get("added", 0)
        log["scraped_total_boxes"] = (
            met_stats.get("total_boxes", 0) + wiki_stats.get("total_boxes", 0)
        )
        old_total = log.get("final_total", 0)
        log["final_total"] = old_total + total_added
        old_sources = log.get("sources", {})
        old_sources["scraped_met"] = met_stats.get("added", 0)
        old_sources["scraped_wiki"] = wiki_stats.get("added", 0)
        log["sources"] = old_sources
        merge_log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\n  Updated merge_log.json (new total: {log['final_total']})")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Total images added: {total_added}")
    print(f"  Total new boxes: {met_stats.get('total_boxes', 0) + wiki_stats.get('total_boxes', 0)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
