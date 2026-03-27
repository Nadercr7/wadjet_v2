r"""Prepare a source-balanced detection dataset for Kaggle training.

Copies data/detection/merged/ to a new directory with source balancing:
  - Caps mohiey images to reduce from 84% to ~60% of training set
  - Keeps ALL non-mohiey sources (they're already underrepresented)
  - Removes empty labels and tiny images
  - Resizes oversized images to <=2048px

The output directory can be zipped and uploaded to Kaggle as a dataset.

Usage:
    # Preview (dry run):
    python scripts/prepare_balanced_dataset.py --dry-run

    # Execute:
    python scripts/prepare_balanced_dataset.py

    # Custom mohiey cap:
    python scripts/prepare_balanced_dataset.py --mohiey-cap 5000
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MERGED_DIR = ROOT / "data" / "detection" / "merged"
OUTPUT_DIR = ROOT / "data" / "detection" / "balanced"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
DEFAULT_MOHIEY_CAP = 5000  # Down from 8650
TINY_PX = 64
HUGE_PX = 2048


def get_source(name: str) -> str:
    n = name.lower()
    if n.startswith("mohiey"):
        return "mohiey"
    if n.startswith("synthetic"):
        return "synthetic"
    if n.startswith("sign"):
        return "signs_seg"
    if n.startswith("v1"):
        return "v1_raw"
    if n.startswith("hla"):
        return "hla"
    if n.startswith("scraped"):
        return "scraped"
    return "unknown"


def is_empty_label(lbl_path: Path) -> bool:
    if not lbl_path.exists():
        return True
    return not lbl_path.read_text(encoding="utf-8").strip()


def main():
    parser = argparse.ArgumentParser(description="Prepare balanced detection dataset")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mohiey-cap", type=int, default=DEFAULT_MOHIEY_CAP,
                        help=f"Max mohiey images in train (default: {DEFAULT_MOHIEY_CAP})")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    random.seed(42)
    np.random.seed(42)

    print("=" * 60)
    print("  PREPARE BALANCED DETECTION DATASET")
    print("=" * 60)
    if args.dry_run:
        print("  *** DRY RUN ***\n")

    # ── Analyze current distribution ──
    print("■ Current training distribution:")
    train_img_dir = MERGED_DIR / "images" / "train"
    train_lbl_dir = MERGED_DIR / "labels" / "train"

    all_images = sorted([
        f for f in train_img_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTS
    ])

    source_groups: dict[str, list[Path]] = {}
    for img_path in all_images:
        src = get_source(img_path.name)
        source_groups.setdefault(src, []).append(img_path)

    total = len(all_images)
    for src, imgs in sorted(source_groups.items(), key=lambda x: -len(x[1])):
        print(f"  {src:15s} {len(imgs):>6,} ({len(imgs)/total*100:>5.1f}%)")

    # ── Balance: cap mohiey ──
    print(f"\n■ Balancing: capping mohiey to {args.mohiey_cap}")

    selected_train: list[Path] = []
    for src, imgs in source_groups.items():
        if src == "mohiey" and len(imgs) > args.mohiey_cap:
            # Random subsample
            sampled = random.sample(imgs, args.mohiey_cap)
            selected_train.extend(sampled)
            print(f"  mohiey: {len(imgs)} → {args.mohiey_cap} (capped)")
        else:
            selected_train.extend(imgs)
            print(f"  {src}: {len(imgs)} (all kept)")

    # ── Filter: remove empty labels and tiny images ──
    filtered_train: list[Path] = []
    removed_empty = 0
    removed_tiny = 0

    for img_path in selected_train:
        stem = img_path.stem
        lbl_path = train_lbl_dir / f"{stem}.txt"

        # Skip empty labels
        if is_empty_label(lbl_path):
            removed_empty += 1
            continue

        # Skip tiny images (check without loading full image)
        if not args.dry_run:
            img = cv2.imread(str(img_path))
            if img is not None:
                h, w = img.shape[:2]
                if w < TINY_PX or h < TINY_PX:
                    removed_tiny += 1
                    continue

        filtered_train.append(img_path)

    print(f"\n  Removed empty labels: {removed_empty}")
    print(f"  Removed tiny (<{TINY_PX}px): {removed_tiny}")
    print(f"  Final train: {len(filtered_train)}")

    # ── New distribution ──
    new_sources = Counter()
    for img in filtered_train:
        new_sources[get_source(img.name)] += 1
    new_total = sum(new_sources.values())
    print(f"\n■ New distribution ({new_total} images):")
    for src, count in new_sources.most_common():
        print(f"  {src:15s} {count:>6,} ({count/new_total*100:>5.1f}%)")

    if args.dry_run:
        print("\n  DRY RUN — no files copied.")
        return

    # ── Copy to output ──
    output = args.output
    print(f"\n■ Copying to {output}")

    for split in ("train", "val", "test"):
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)

    # Copy train (balanced)
    resized = 0
    for img_path in filtered_train:
        stem = img_path.stem
        lbl_src = train_lbl_dir / f"{stem}.txt"
        img_dst = output / "images" / "train" / img_path.name
        lbl_dst = output / "labels" / "train" / f"{stem}.txt"

        shutil.copy2(img_path, img_dst)
        shutil.copy2(lbl_src, lbl_dst)

        # Resize oversized
        img = cv2.imread(str(img_dst))
        if img is not None:
            h, w = img.shape[:2]
            if max(h, w) > HUGE_PX:
                scale = HUGE_PX / max(h, w)
                nw, nh = int(w * scale), int(h * scale)
                img_resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(img_dst), img_resized, [cv2.IMWRITE_JPEG_QUALITY, 92])
                resized += 1

    print(f"  Train: {len(filtered_train)} images copied, {resized} resized")

    # Copy val and test unchanged (but clean empty/tiny)
    for split in ("val", "test"):
        src_img_dir = MERGED_DIR / "images" / split
        src_lbl_dir = MERGED_DIR / "labels" / split
        copied = 0
        for img_path in sorted(src_img_dir.iterdir()):
            if img_path.suffix.lower() not in SUPPORTED_EXTS:
                continue
            stem = img_path.stem
            lbl_path = src_lbl_dir / f"{stem}.txt"
            if is_empty_label(lbl_path):
                continue
            shutil.copy2(img_path, output / "images" / split / img_path.name)
            shutil.copy2(lbl_path, output / "labels" / split / f"{stem}.txt")
            copied += 1
        print(f"  {split}: {copied} images copied")

    # Write data.yaml
    data_yaml = {
        "path": ".",
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 1,
        "names": ["hieroglyph"],
    }
    import yaml
    yaml_path = output / "data.yaml"
    yaml_path.write_text(
        yaml.dump(data_yaml, default_flow_style=False), encoding="utf-8"
    )

    # Write balance log
    log = {
        "original_train": total,
        "balanced_train": len(filtered_train),
        "mohiey_cap": args.mohiey_cap,
        "removed_empty": removed_empty,
        "removed_tiny": removed_tiny,
        "resized_oversized": resized,
        "sources": dict(new_sources),
    }
    log_path = output / "balance_log.json"
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  data.yaml: {yaml_path}")
    print(f"  balance_log.json: {log_path}")
    print(f"\n  To upload: zip {output} and upload to Kaggle as dataset")
    print("Done.")


if __name__ == "__main__":
    main()
