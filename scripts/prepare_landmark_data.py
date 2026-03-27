"""
prepare_landmark_data.py
========================
Prepares the landmark classification dataset for Kaggle upload.

Steps:
  1. Copy v1 splits/train|val|test/ as base (52 classes)
  2. Merge matching images from eg-landmarks Kaggle dataset
  3. Augment train classes below TARGET_MIN to reach TARGET_MIN
  4. Write clean split to data/landmark_classification/
  5. Save dataset_stats.json

Usage:
    python scripts/prepare_landmark_data.py --dry-run   # show what would happen
    python scripts/prepare_landmark_data.py             # execute

NOTE: Horizontal flip IS allowed for landmarks (symmetry does not affect label).
"""

import argparse
import json
import random
import shutil
from pathlib import Path

import albumentations as A
import numpy as np
from PIL import Image

# ── Paths ────────────────────────────────────────────────────────────────────
V1_SPLITS = Path(
    r"D:\Personal attachements\Projects\Final_Horus\Wadjet\data\splits"
)
EG_LANDMARKS = Path("data/downloads/eg-landmarks/images")
OUTPUT_ROOT = Path("data/landmark_classification")

# ── Config ───────────────────────────────────────────────────────────────────
TARGET_MIN = 300      # minimum train images per class after augmentation
RANDOM_SEED = 42

# Augmentation pipeline — h-flip IS fine for landmarks
AUGMENT = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.Rotate(limit=15, border_mode=0, p=0.6),
    A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.6),
    A.RandomShadow(p=0.2),
    A.GaussNoise(p=0.3),
    A.Affine(scale=(0.85, 1.15), translate_percent=0.05, p=0.4),
    A.RandomGamma(gamma_limit=(80, 120), p=0.3),
    A.CLAHE(p=0.2),
])

# ── Class mapping: eg-landmarks folder → our v1 class name ───────────────────
# Only entries where eg-landmarks has useful images (>20 per folder)

EG_TO_V1: dict[str, str] = {
    "Siwa":                                       "siwa_oasis",
    "Temple_of_Kom_Ombo":                         "kom_ombo_temple",
    "Great_Hypostyle_Hall_of_Karnak":             "karnak_temple",
    "Muizz_Street":                               "al_muizz_street",
    "Colossi_of_Memnon":                          "colossi_of_memnon",
    "Montaza_Palace":                             "montaza_palace",
    "Saint_Catherine's_Monastery,_Mount_Sinai":   "saint_catherine_monastery",
    "Bibliotheca_Alexandrina":                    "bibliotheca_alexandrina",
    "Pyramid_of_Djoser":                          "pyramid_of_djoser",
    "Unfinished_obelisk_in_Aswan":                "unfinished_obelisk",
    "Mortuary_Temple_of_Hatshepsut":              "temple_of_hatshepsut",
    "Temple_of_Isis_in_Philae":                   "philae_temple",
    "Kiosk_of_Trajan_in_Philae":                  "philae_temple",
    "Ramesseum":                                  "ramesseum",
    "Khan_el-Khalili":                            "khan_el_khalili",
    "Al-Azhar_Park_(Cairo)":                      "al_azhar_park",
    "Aswan_High_Dam":                             "aswan_high_dam",
    "Hanging_Church_(Cairo)":                     "hanging_church",
    "Giza_Plateau":                               "great_pyramids_of_giza",
    "Great_Pyramid_of_Giza":                      "great_pyramids_of_giza",
    "Giza_pyramid_complex":                       "great_pyramids_of_giza",
    "Bent_Pyramid":                               "bent_pyramid",
    "Luxor_Temple":                               "luxor_temple",
    "Great_Sphinx_of_Giza":                       "great_sphinx_of_giza",
    "Deir_el-Medina":                             "deir_el_medina",
    "Deir_el-Bahari":                             "temple_of_hatshepsut",
    "Citadel_of_Qaitbay":                         "citadel_of_qaitbay",
    "Pompey's_Pillar,_Alexandria":                "pompeys_pillar",
    "Bab_Zuwayla":                                "bab_zuweila",
    "Cairo_Citadel":                              "cairo_citadel",
    "Edfu_Temple":                                "edfu_temple",
    "Egyptian_Museum_(Cairo)":                    "egyptian_museum_cairo",
    "Grand_Egyptian_Museum":                      "grand_egyptian_museum",
    "Red_Pyramid":                                "red_pyramid",
    "Mosque_of_Ibn_Tulun":                        "ibn_tulun_mosque",
    "Muhammad_Ali_Mosque":                        "muhammad_ali_mosque",
    "Karnak_precinct_of_Amun-Ra":                 "karnak_temple",
    "Dendera_Temple_complex":                     "dendera_temple",
    "Valley_of_the_Queens":                       "valley_of_the_queens",
    "Tomb_of_Nefertari":                          "tomb_of_nefertari",
    "Baron_Empain_Palace":                        "baron_empain_palace",
    "Kom_el-Shoqafa":                             "catacombs_of_kom_el_shoqafa",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_image_np(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def save_image_np(arr: np.ndarray, path: Path) -> None:
    Image.fromarray(arr).save(path)


def collect_split(split_dir: Path) -> dict[str, list[Path]]:
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
            if not dry_run and not dst.exists():
                shutil.copy2(src, dst)
        counts[cls_name] = len(paths)
    return counts


def merge_eg_landmarks(train_dest: Path, dry_run: bool) -> dict[str, int]:
    """Copy matching eg-landmarks images into train destination."""
    added: dict[str, int] = {}
    if not EG_LANDMARKS.exists():
        print("  WARNING: eg-landmarks folder not found, skipping merge.")
        return added

    for eg_cls, v1_cls in EG_TO_V1.items():
        eg_dir = EG_LANDMARKS / eg_cls
        if not eg_dir.exists():
            continue
        imgs = [p for p in eg_dir.iterdir()
                if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        if not imgs:
            continue

        cls_dest = train_dest / v1_cls
        if not dry_run:
            cls_dest.mkdir(parents=True, exist_ok=True)

        n_added = 0
        for src in imgs:
            # prefix to avoid name collisions
            dst = cls_dest / f"eg_{eg_cls[:10]}_{src.name}"
            if not dry_run and not dst.exists():
                shutil.copy2(src, dst)
            n_added += 1

        added[v1_cls] = added.get(v1_cls, 0) + n_added

    total_added = sum(added.values())
    print(f"  Merged {total_added} images from eg-landmarks into "
          f"{len(added)} classes.")
    return added


def augment_class(train_dest: Path, cls_name: str, current_count: int,
                  target: int, dry_run: bool,
                  src_cls_dir: Path | None = None) -> int:
    needed = target - current_count
    if needed <= 0:
        return 0
    cls_dir = train_dest / cls_name
    search_dir = src_cls_dir if (dry_run and src_cls_dir is not None) else cls_dir
    existing = [p for p in search_dir.iterdir()
                if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if not existing:
        print(f"    WARNING: No images found for {cls_name}, skipping.")
        return 0

    generated = 0
    random.seed(RANDOM_SEED)
    while generated < needed:
        src = random.choice(existing)
        dst = cls_dir / f"aug_{generated:04d}_{src.stem}.jpg"
        if not dry_run:
            img = load_image_np(src)
            result = AUGMENT(image=img)
            save_image_np(result["image"], dst)
        generated += 1
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
    print(f"  {mode}Landmark Data Preparation")
    print(f"  Source : {V1_SPLITS}")
    print(f"  Extra  : {EG_LANDMARKS}")
    print(f"  Output : {OUTPUT_ROOT}")
    print(f"  Target : >={TARGET_MIN} images per class (train)")
    print(f"{'='*60}\n")

    if not V1_SPLITS.exists():
        print(f"ERROR: v1 splits not found at {V1_SPLITS}")
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

    dest_train = OUTPUT_ROOT / "train"
    dest_val   = OUTPUT_ROOT / "val"
    dest_test  = OUTPUT_ROOT / "test"

    if not dry_run:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    # Copy base splits
    print("\n--- Copying v1 splits ---")
    train_counts = copy_split(src_train, dest_train, "train", dry_run)
    val_counts   = copy_split(src_val,   dest_val,   "val",   dry_run)
    test_counts  = copy_split(src_test,  dest_test,  "test",  dry_run)

    # Merge eg-landmarks into train
    print("\n--- Merging eg-landmarks ---")
    eg_added = merge_eg_landmarks(dest_train, dry_run)
    for cls_name, n in eg_added.items():
        train_counts[cls_name] = train_counts.get(cls_name, 0) + n

    # Identify classes still below TARGET_MIN
    weak = {cls: cnt for cls, cnt in train_counts.items() if cnt < TARGET_MIN}
    if weak:
        print(f"\nWARNING: {len(weak)} classes below {TARGET_MIN} (will augment):")
        for cls, cnt in sorted(weak.items(), key=lambda x: x[1]):
            print(f"  {cls}: {cnt} -> {TARGET_MIN}")
    else:
        print(f"\nOK: All classes have >={TARGET_MIN} images.")

    # Augment weak classes
    if weak:
        print(f"\n--- Augmenting {len(weak)} weak classes ---")
        for cls_name, current_count in sorted(weak.items(), key=lambda x: x[1]):
            src_cls = V1_SPLITS / "train" / cls_name
            n_gen = augment_class(
                dest_train, cls_name, current_count,
                TARGET_MIN, dry_run,
                src_cls_dir=src_cls if src_cls.exists() else None,
            )
            if not dry_run:
                train_counts[cls_name] += n_gen
            print(f"  {cls_name}: {current_count} + {n_gen} aug -> "
                  f"{current_count + n_gen}")

    # Stats
    stats = {
        "train": compute_stats(train_counts),
        "val":   compute_stats(val_counts),
        "test":  compute_stats(test_counts),
        "augmented_classes": list(weak.keys()),
        "eg_landmarks_merged": eg_added,
        "target_min": TARGET_MIN,
    }

    print("\n--- Final stats ---")
    for split_name in ("train", "val", "test"):
        s = stats[split_name]
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
    parser = argparse.ArgumentParser(description="Prepare landmark classification dataset")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without making changes")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
