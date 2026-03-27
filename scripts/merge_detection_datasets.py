r"""Merge multiple YOLO-format detection datasets into one unified dataset.

Handles:
  - Merging images/ and labels/ from multiple source directories
  - Perceptual hash deduplication (cross-source)
  - Train/val/test splitting (80/15/5) stratified by source
  - Hand-picked real stone test set (if provided)
  - YOLO dataset.yaml generation

Usage:
    # Activate dataprep-env first:
    #   & scripts\dataprep-env\Scripts\Activate.ps1

    # Merge all sources:
    python scripts/merge_detection_datasets.py \
        --sources data/detection/v1_raw data/detection/hla data/detection/scraped_annotated data/detection/synthetic \
        --output data/detection/merged \
        --test-images path/to/handpicked_test_images/

    # Custom split ratios:
    python scripts/merge_detection_datasets.py \
        --sources data/detection/v1_raw data/detection/hla \
        --output data/detection/merged \
        --train-ratio 0.80 --val-ratio 0.15 --test-ratio 0.05

Each source directory must have:
    images/    — image files
    labels/    — matching YOLO .txt label files
"""

import argparse
import hashlib
import json
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def compute_phash(image_path: Path, hash_size: int = 8) -> int:
    """Compute perceptual hash of an image for deduplication. Returns int."""
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return -1
    resized = cv2.resize(img, (hash_size + 1, hash_size))
    diff = resized[:, 1:] > resized[:, :-1]
    bits = diff.flatten()
    return int("".join(str(int(b)) for b in bits), 2)


def hamming_distance_int(a: int, b: int) -> int:
    """Hamming distance between two integer hashes."""
    return bin(a ^ b).count("1")


def _collect_flat(src: Path, source_name: str, forced_split: str = None) -> list[dict]:
    """Collect image-label pairs from a flat images/+labels/ directory."""
    images_dir = src / "images"
    labels_dir = src / "labels"
    if not images_dir.exists():
        print(f"  WARNING: {images_dir} does not exist, skipping")
        return []
    entries = []
    for img_path in sorted(images_dir.iterdir()):
        if img_path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        stem = img_path.stem
        label_path = labels_dir / f"{stem}.txt" if labels_dir.exists() else None
        has_label = label_path and label_path.exists()
        entries.append({
            "image_path": img_path,
            "label_path": label_path if has_label else None,
            "source": source_name,
            "stem": stem,
            "forced_split": forced_split,
        })
    return entries


def collect_sources(source_dirs: list[Path], presplit_dirs: list[Path] = None) -> list[dict]:
    """Collect all image-label pairs from source directories.

    Args:
        source_dirs: Flat sources (each with images/ + labels/), to be split.
        presplit_dirs: Pre-split sources with train/valid(val)/test subdirs.
            Images keep their original split assignment.
    """
    entries = []

    # Flat sources
    for src in source_dirs:
        entries.extend(_collect_flat(src, src.name))

    # Pre-split sources
    for src in (presplit_dirs or []):
        source_name = src.name
        found_any = False
        for split_dir in sorted(src.iterdir()):
            if not split_dir.is_dir():
                continue
            name = split_dir.name.lower()
            if name in ("train", "val", "valid", "test"):
                split_tag = "val" if name == "valid" else name
                sub = _collect_flat(split_dir, source_name, forced_split=split_tag)
                entries.extend(sub)
                found_any = True
        if not found_any:
            print(f"  WARNING: {src} has no train/val/test subdirs, treating as flat")
            entries.extend(_collect_flat(src, source_name))

    return entries


def deduplicate(entries: list[dict], threshold: int = 5) -> list[dict]:
    """Remove near-duplicate images using perceptual hashing.

    Uses bucket-based approach for speed with large datasets:
    exact-match hash dict + bit-flip neighbors for threshold <= 5.
    """
    n = len(entries)
    print(f"  Computing perceptual hashes for {n} images...")

    # Phase 1: compute all hashes
    hashed = []
    for i, entry in enumerate(entries):
        if (i + 1) % 2000 == 0:
            print(f"    [{i+1}/{n}] hashing...")
        ph = compute_phash(entry["image_path"])
        hashed.append((entry, ph))

    # Phase 2: exact-hash dedup (fast, handles identical images)
    seen_exact: dict[int, int] = {}  # hash -> index in unique
    unique = []
    exact_dupes = 0
    for entry, ph in hashed:
        if ph == -1:
            unique.append(entry)
            continue
        if ph in seen_exact:
            exact_dupes += 1
            continue
        seen_exact[ph] = len(unique)
        unique.append(entry)

    print(f"  Exact dedup: {n} → {len(unique)} ({exact_dupes} exact duplicates)")

    if threshold == 0:
        return unique

    # Phase 3: near-duplicate dedup (threshold > 0)
    # For datasets >10k, use sampling to keep runtime reasonable
    if len(unique) > 10000 and threshold > 0:
        print(f"  Near-dedup on {len(unique)} unique images (sampled check)...")
        hash_list = sorted(seen_exact.keys())
        near_dupes = set()
        # Check neighbors with <= threshold bit flips via sorted order
        for i in range(len(hash_list) - 1):
            if i in near_dupes:
                continue
            for j in range(i + 1, min(i + 50, len(hash_list))):
                if j in near_dupes:
                    continue
                if hamming_distance_int(hash_list[i], hash_list[j]) <= threshold:
                    # Remove the later one
                    idx = seen_exact[hash_list[j]]
                    near_dupes.add(j)
        if near_dupes:
            remove_indices = {seen_exact[hash_list[j]] for j in near_dupes}
            unique = [e for i, e in enumerate(unique) if i not in remove_indices]
            print(f"  Near-dedup removed {len(near_dupes)} more → {len(unique)} final")
    else:
        # Small dataset: full pairwise check is fine
        hash_items = list(seen_exact.items())
        remove_indices = set()
        for i in range(len(hash_items)):
            if hash_items[i][1] in remove_indices:
                continue
            for j in range(i + 1, len(hash_items)):
                if hash_items[j][1] in remove_indices:
                    continue
                if hamming_distance_int(hash_items[i][0], hash_items[j][0]) <= threshold:
                    remove_indices.add(hash_items[j][1])
        if remove_indices:
            unique = [e for i, e in enumerate(unique) if i not in remove_indices]
            print(f"  Near-dedup removed {len(remove_indices)} more → {len(unique)} final")

    return unique


def split_dataset(
    entries: list[dict],
    train_ratio: float = 0.80,
    val_ratio: float = 0.15,
    test_ratio: float = 0.05,
    test_images_dir: Path = None,
    seed: int = 42,
) -> dict[str, list[dict]]:
    """Split entries into train/val/test, stratified by source.

    Entries with a 'forced_split' key keep their assigned split (from presplit sources).
    Other entries are split by ratio, stratified by source.
    """
    random.seed(seed)

    splits = {"train": [], "val": [], "test": []}

    # Separate forced vs. free entries
    forced = [e for e in entries if e.get("forced_split")]
    free = [e for e in entries if not e.get("forced_split")]

    for entry in forced:
        splits[entry["forced_split"]].append(entry)

    # Group free entries by source for stratification
    by_source = defaultdict(list)
    for entry in free:
        by_source[entry["source"]].append(entry)

    # Handle hand-picked test images
    test_stems = set()
    if test_images_dir and test_images_dir.exists():
        for img in test_images_dir.iterdir():
            if img.suffix.lower() in SUPPORTED_EXTS:
                test_stems.add(img.stem)

    for source, source_entries in by_source.items():
        random.shuffle(source_entries)

        # Pull out hand-picked test images first
        handpicked = [e for e in source_entries if e["stem"] in test_stems]
        remaining = [e for e in source_entries if e["stem"] not in test_stems]

        splits["test"].extend(handpicked)

        # Split remaining
        n = len(remaining)
        n_test = max(1, int(n * test_ratio)) if n > 10 else 0
        n_val = max(1, int(n * val_ratio)) if n > 5 else 0
        n_train = n - n_val - n_test

        splits["train"].extend(remaining[:n_train])
        splits["val"].extend(remaining[n_train:n_train + n_val])
        splits["test"].extend(remaining[n_train + n_val:])

    # Shuffle each split
    for split in splits.values():
        random.shuffle(split)

    return splits


def write_split(entries: list[dict], output_dir: Path, split_name: str) -> dict:
    """Write images and labels for a split to output directory."""
    images_dir = output_dir / "images" / split_name
    labels_dir = output_dir / "labels" / split_name
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    stats = {"images": 0, "with_labels": 0, "total_boxes": 0, "sources": defaultdict(int)}

    for entry in entries:
        src_img = entry["image_path"]
        stem = entry["stem"]
        source = entry["source"]

        # Copy image (add source prefix to avoid name collisions)
        new_name = f"{source}_{src_img.name}"
        new_stem = f"{source}_{stem}"

        dest_img = images_dir / new_name
        if not dest_img.exists():
            shutil.copy2(src_img, dest_img)

        # Copy label
        label_path = entry["label_path"]
        dest_label = labels_dir / f"{new_stem}.txt"
        if label_path and label_path.exists():
            shutil.copy2(label_path, dest_label)
            # Count boxes
            n_boxes = sum(1 for line in label_path.read_text().strip().split("\n") if line.strip())
            stats["total_boxes"] += n_boxes
            stats["with_labels"] += 1
        else:
            # Write empty label file
            dest_label.write_text("", encoding="utf-8")

        stats["images"] += 1
        stats["sources"][source] += 1

    return stats


def write_yaml(output_dir: Path, nc: int = 1, names: list[str] = None):
    """Write YOLO dataset.yaml config."""
    if names is None:
        names = ["hieroglyph"]

    yaml_content = f"""# Wadjet Hieroglyph Detection Dataset
# Auto-generated by merge_detection_datasets.py

path: .
train: images/train
val: images/val
test: images/test

nc: {nc}
names: {names}
"""
    (output_dir / "hieroglyph_det.yaml").write_text(yaml_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Merge multiple YOLO detection datasets into one"
    )
    parser.add_argument("--sources", nargs="+", required=True, type=Path,
                        help="Source directories (each with images/ + labels/)")
    parser.add_argument("--presplit", nargs="*", type=Path, default=[],
                        help="Pre-split sources (with train/val/test subdirs)")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output directory for merged dataset")
    parser.add_argument("--train-ratio", type=float, default=0.80)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.05)
    parser.add_argument("--test-images", type=Path, default=None,
                        help="Directory with hand-picked test images (added to test set)")
    parser.add_argument("--no-dedup", action="store_true",
                        help="Skip perceptual hash deduplication")
    parser.add_argument("--dedup-threshold", type=int, default=5,
                        help="Hamming distance threshold for dedup (default: 5)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for split")

    args = parser.parse_args()

    # Validate ratios
    total_ratio = args.train_ratio + args.val_ratio + args.test_ratio
    if abs(total_ratio - 1.0) > 0.01:
        print(f"ERROR: Split ratios must sum to 1.0. Got {total_ratio:.2f}")
        sys.exit(1)

    # Collect all entries
    print("Collecting sources...")
    entries = collect_sources(args.sources, presplit_dirs=args.presplit)
    print(f"  Total entries: {len(entries)}")
    forced = sum(1 for e in entries if e.get("forced_split"))
    if forced:
        print(f"  Pre-split entries: {forced} (will keep their assigned split)")

    if not entries:
        print("ERROR: No images found in any source directory")
        sys.exit(1)

    # Source breakdown
    source_counts = defaultdict(int)
    for e in entries:
        source_counts[e["source"]] += 1
    for src, count in sorted(source_counts.items()):
        print(f"    {src}: {count}")

    # Dedup
    if not args.no_dedup:
        entries = deduplicate(entries, threshold=args.dedup_threshold)

    # Split
    print("\nSplitting dataset...")
    splits = split_dataset(
        entries,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        test_images_dir=args.test_images,
        seed=args.seed,
    )
    for split_name, split_entries in splits.items():
        print(f"  {split_name}: {len(split_entries)}")

    # Write splits
    print("\nWriting output...")
    all_stats = {}
    for split_name, split_entries in splits.items():
        print(f"  Writing {split_name}...")
        stats = write_split(split_entries, args.output, split_name)
        all_stats[split_name] = stats

    # Write YAML
    write_yaml(args.output)

    # Write metadata
    meta = {
        "total_images": len(entries),
        "splits": {
            k: {"images": v["images"], "total_boxes": v["total_boxes"], "sources": dict(v["sources"])}
            for k, v in all_stats.items()
        },
        "source_counts": dict(source_counts),
        "dedup": not args.no_dedup,
        "seed": args.seed,
    }
    (args.output / "dataset_metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    # Summary
    print(f"\n{'='*60}")
    for split_name, stats in all_stats.items():
        print(f"  {split_name:6s}: {stats['images']:5d} images, {stats['total_boxes']:6d} boxes")
    total_imgs = sum(s["images"] for s in all_stats.values())
    total_boxes = sum(s["total_boxes"] for s in all_stats.values())
    print(f"  {'TOTAL':6s}: {total_imgs:5d} images, {total_boxes:6d} boxes")
    print(f"  Output: {args.output}")
    print(f"  YAML:   {args.output / 'hieroglyph_det.yaml'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
