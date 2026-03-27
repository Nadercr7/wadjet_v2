"""
prepare_hieroglyph_data.py
==========================
Prepares the hieroglyph classification dataset for Kaggle upload.

Steps:
  1. Copy v1 splits/classification/ as base
  2. Augment the 16 under-represented classes to TARGET_MIN images
  3. Write clean train/val/test split to data/hieroglyph_classification/
  4. Save dataset_stats.json

Usage:
    python scripts/prepare_hieroglyph_data.py --dry-run   # show what would happen
    python scripts/prepare_hieroglyph_data.py             # execute

IMPORTANT – hieroglyphs are direction-sensitive!
  NO HorizontalFlip is used in augmentation.
"""

import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path

import albumentations as A
import numpy as np
from PIL import Image

# ── Paths ────────────────────────────────────────────────────────────────────
V1_SPLITS = Path(
    r"D:\Personal attachements\Projects\Final_Horus\Wadjet"
    r"\hieroglyph_model\data\splits\classification"
)
OUTPUT_ROOT = Path("data/hieroglyph_classification")

# ── Config ───────────────────────────────────────────────────────────────────
TARGET_MIN = 80          # minimum images per class AFTER augmentation
RANDOM_SEED = 42

# Augmentation pipeline — NO HorizontalFlip (direction-sensitive!)
AUGMENT = A.Compose([
    A.Rotate(limit=12, border_mode=0, p=0.7),
    A.RandomBrightnessContrast(brightness_limit=0.25, contrast_limit=0.25, p=0.6),
    A.GaussNoise(p=0.4),
    A.Affine(scale=(0.85, 1.15), translate_percent=0.05, shear=(-5, 5), p=0.5),
    A.RandomGamma(gamma_limit=(80, 120), p=0.3),
])

# ── Helpers ──────────────────────────────────────────────────────────────────

def file_md5(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_image_np(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def save_image_np(arr: np.ndarray, path: Path) -> None:
    Image.fromarray(arr).save(path)


def collect_split(split_dir: Path) -> dict[str, list[Path]]:
    """Returns {class_name: [image_paths]} for a split directory."""
    result: dict[str, list[Path]] = {}
    if not split_dir.exists():
        return result
    for cls_dir in sorted(split_dir.iterdir()):
        if cls_dir.is_dir():
            imgs = [p for p in cls_dir.iterdir()
                    if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
            if imgs:
                result[cls_dir.name] = imgs
    return result


def copy_split(split_data: dict[str, list[Path]], dest: Path, label: str,
               dry_run: bool) -> dict[str, int]:
    counts: dict[str, int] = {}
    total = sum(len(v) for v in split_data.values())
    print(f"  Copying {label}: {len(split_data)} classes, {total} images ...")
    for cls_name, paths in split_data.items():
        cls_dest = dest / cls_name
        if not dry_run:
            cls_dest.mkdir(parents=True, exist_ok=True)
        for src in paths:
            dst = cls_dest / src.name
            if not dry_run:
                shutil.copy2(src, dst)
        counts[cls_name] = len(paths)
    return counts


def augment_class(train_dest: Path, cls_name: str, current_count: int,
                  target: int, dry_run: bool,
                  src_cls_dir: Path | None = None) -> int:
    """Generates augmented images until class reaches `target` count."""
    needed = target - current_count
    cls_dir = train_dest / cls_name
    # In dry-run mode the dest dir doesn't exist yet — read from source
    search_dir = src_cls_dir if (dry_run and src_cls_dir is not None) else cls_dir
    existing = [p for p in search_dir.iterdir()
                if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if not existing:
        print(f"    WARNING: No images found for {cls_name}, skipping.")
        return 0

    generated = 0
    random.seed(RANDOM_SEED)
    idx = 0
    while generated < needed:
        src = random.choice(existing)
        aug_name = f"aug_{generated:04d}_{src.stem}.jpg"
        dst = cls_dir / aug_name
        if not dry_run:
            img = load_image_np(src)
            result = AUGMENT(image=img)
            save_image_np(result["image"], dst)
        generated += 1
        idx += 1
    return generated


def compute_stats(split_data: dict[str, int]) -> dict:
    counts = list(split_data.values())
    return {
        "total": sum(counts),
        "classes": len(counts),
        "min": min(counts),
        "max": max(counts),
        "avg": round(sum(counts) / len(counts), 1),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool) -> None:
    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n{'='*60}")
    print(f"  {mode}Hieroglyph Data Preparation")
    print(f"  Source : {V1_SPLITS}")
    print(f"  Output : {OUTPUT_ROOT}")
    print(f"  Target : >={TARGET_MIN} images per class (train)")
    print(f"{'='*60}\n")

    if not V1_SPLITS.exists():
        print(f"ERROR: v1 splits not found at {V1_SPLITS}")
        print("  Make sure the Wadjet v1 project is at the expected path.")
        return

    # Load source splits
    src_train = collect_split(V1_SPLITS / "train")
    src_val   = collect_split(V1_SPLITS / "val")
    src_test  = collect_split(V1_SPLITS / "test")

    print(f"Source train: {len(src_train)} classes, "
          f"{sum(len(v) for v in src_train.values())} images")
    print(f"Source val  : {len(src_val)} classes, "
          f"{sum(len(v) for v in src_val.values())} images")
    print(f"Source test : {len(src_test)} classes, "
          f"{sum(len(v) for v in src_test.values())} images")

    # Identify weak classes
    weak = {cls: len(imgs) for cls, imgs in src_train.items()
            if len(imgs) < TARGET_MIN}
    if weak:
        print(f"\nWARNING: {len(weak)} classes below {TARGET_MIN} images (will augment):")
        for cls, cnt in sorted(weak.items(), key=lambda x: x[1]):
            print(f"  {cls}: {cnt} → {TARGET_MIN}")
    else:
        print(f"\nOK All classes have >={TARGET_MIN} images -- no augmentation needed.")

    dest_train = OUTPUT_ROOT / "train"
    dest_val   = OUTPUT_ROOT / "val"
    dest_test  = OUTPUT_ROOT / "test"

    if not dry_run:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    # Copy splits
    print("\n--- Copying splits ---")
    train_counts = copy_split(src_train, dest_train, "train", dry_run)
    val_counts   = copy_split(src_val,   dest_val,   "val",   dry_run)
    test_counts  = copy_split(src_test,  dest_test,  "test",  dry_run)

    # Augment weak classes in train
    if weak:
        print(f"\n--- Augmenting {len(weak)} weak classes ---")
        for cls_name, current_count in sorted(weak.items(), key=lambda x: x[1]):
            src_cls = V1_SPLITS / "train" / cls_name
            n_generated = augment_class(dest_train, cls_name, current_count,
                                        TARGET_MIN, dry_run, src_cls_dir=src_cls)
            if not dry_run:
                train_counts[cls_name] += n_generated
            print(f"  {cls_name}: {current_count} + {n_generated} aug → "
                  f"{current_count + n_generated}")

    # Stats
    stats = {
        "train": compute_stats(train_counts),
        "val":   compute_stats(val_counts),
        "test":  compute_stats(test_counts),
        "augmented_classes": list(weak.keys()),
        "target_min": TARGET_MIN,
    }

    print("\n--- Final stats ---")
    for split_name, s in stats.items():
        if isinstance(s, dict):
            print(f"  {split_name}: classes={s['classes']}, total={s['total']}, "
                  f"min={s['min']}, max={s['max']}, avg={s['avg']}")

    if not dry_run:
        stats_path = OUTPUT_ROOT / "dataset_stats.json"
        stats_path.write_text(json.dumps(stats, indent=2))
        print(f"\nDone! Stats written to {stats_path}")
        print(f"Done! Dataset ready at: {OUTPUT_ROOT}")
    else:
        print("\n[DRY-RUN] No files were modified. Re-run without --dry-run to execute.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare hieroglyph classification dataset")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without making changes")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
