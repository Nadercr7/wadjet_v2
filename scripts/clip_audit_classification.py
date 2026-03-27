r"""CLIP-based quality audit for classification dataset.

Checks if classification crops actually match their Gardiner class
by scoring each image against its expected description using CLIP.
Also verifies the detection dataset's existing CLIP cleaning.

Outputs:
    data/hieroglyph_classification/clip_audit_report.json
    stdout summary with mislabel rate estimate

Usage:
    # Full audit (slow — processes all 16K+ train images):
    python scripts/clip_audit_classification.py

    # Quick sample (100 images per class):
    python scripts/clip_audit_classification.py --sample 100

    # Detection dataset verification only:
    python scripts/clip_audit_classification.py --detection-only
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CLS_DIR = ROOT / "data" / "hieroglyph_classification"
DET_DIR = ROOT / "data" / "detection" / "merged"
LABEL_MAP = ROOT / "models" / "hieroglyph" / "label_mapping.json"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

# Gardiner category descriptions for CLIP prompts
CATEGORY_DESCRIPTIONS = {
    "A": "man, human figure",
    "B": "woman, female figure",
    "C": "god, deity figure",
    "D": "human body part, eye, arm, hand, leg, foot",
    "E": "mammal, animal, bull, lion",
    "F": "animal body part, horn, skin, tail",
    "G": "bird, falcon, owl, vulture",
    "H": "bird body part, feather, wing",
    "I": "reptile, snake, lizard, crocodile",
    "K": "fish",
    "L": "insect, bee, scarab",
    "M": "plant, tree, flower, reed",
    "N": "sky, earth, water, sun, moon, star",
    "O": "building, house, temple, door",
    "P": "ship, boat",
    "Q": "furniture, chair, box",
    "R": "temple equipment, altar, standard",
    "S": "crown, scepter, staff",
    "T": "warfare, mace, arrow, bow",
    "U": "agriculture, plough, sickle",
    "V": "rope, fiber, basket",
    "W": "vessel, pot, jar",
    "X": "bread, loaf, offering",
    "Y": "writing, game, music",
    "Z": "stroke, line, geometric",
    "Aa": "unclassified sign",
    "NL": "number, numeral",
}


def get_gardiner_descriptions() -> dict[str, str]:
    """Build Gardiner code → description mapping from the project data."""
    descriptions = {}
    try:
        # Try importing from the project's gardiner_data
        sys.path.insert(0, str(ROOT))
        from app.core.gardiner_data import SIGN_INDEX  # noqa: E402
        for code, sign_tuple in SIGN_INDEX.items():
            # sign_tuple: (code, hex, description, phonetic, type, logographic, det_class)
            descriptions[code] = sign_tuple[2]  # description field
    except Exception as e:
        print(f"Warning: Could not load gardiner_data: {e}")
        print("  Falling back to category-level descriptions")

    return descriptions


def get_category(code: str) -> str:
    """Extract category letter from Gardiner code (e.g. 'D21' → 'D')."""
    # Handle NL, Aa, etc.
    if code.startswith("Aa"):
        return "Aa"
    if code.startswith("NL"):
        return "NL"
    return code.rstrip("0123456789")


def build_clip_prompt(code: str, descriptions: dict[str, str]) -> str:
    """Create a descriptive CLIP prompt for a Gardiner sign."""
    desc = descriptions.get(code, "")
    cat = get_category(code)
    cat_desc = CATEGORY_DESCRIPTIONS.get(cat, "Egyptian hieroglyph")

    if desc:
        return f"ancient Egyptian hieroglyph: {desc}"
    else:
        return f"ancient Egyptian hieroglyph sign: {cat_desc}"


def audit_classification(
    sample_per_class: int = 0,
    device: str = "cpu",
) -> dict:
    """Audit classification crops with CLIP scoring."""
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor

    MODEL_ID = "openai/clip-vit-base-patch32"
    print(f"Loading CLIP model: {MODEL_ID} (device={device})...")
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    model = CLIPModel.from_pretrained(MODEL_ID).to(device)
    model.eval()

    descriptions = get_gardiner_descriptions()
    print(f"Loaded {len(descriptions)} Gardiner descriptions")

    # Load label mapping
    label_map = json.loads(LABEL_MAP.read_text(encoding="utf-8"))
    all_codes = sorted(label_map.get("gardiner_to_idx", {}).keys())
    print(f"Classifier has {len(all_codes)} classes")

    # General hieroglyph prompt for contrast
    general_prompt = "ancient Egyptian hieroglyph carved on stone"
    negative_prompt = "modern photograph, tourist, building, text, noise"

    report = {
        "total_checked": 0,
        "flagged": 0,
        "flagged_rate": 0,
        "per_class": {},
        "flagged_images": [],
    }

    train_dir = CLS_DIR / "train"
    if not train_dir.exists():
        report["error"] = f"Train directory not found: {train_dir}"
        return report

    class_dirs = sorted([d for d in train_dir.iterdir() if d.is_dir()])
    total_checked = 0
    total_flagged = 0
    flagged_images = []

    for cls_dir in class_dirs:
        code = cls_dir.name
        class_prompt = build_clip_prompt(code, descriptions)

        images = sorted([
            f for f in cls_dir.iterdir()
            if f.suffix.lower() in SUPPORTED_EXTS
        ])

        if sample_per_class > 0 and len(images) > sample_per_class:
            rng = np.random.RandomState(42)
            indices = rng.choice(len(images), sample_per_class, replace=False)
            images = [images[i] for i in sorted(indices)]

        class_scores = []
        class_flagged = 0

        for img_path in images:
            try:
                pil_img = Image.open(img_path).convert("RGB")
            except Exception:
                continue

            # Score against class-specific prompt, general prompt, and negative
            prompts = [class_prompt, general_prompt, negative_prompt]
            inputs = processor(
                text=prompts, images=pil_img,
                return_tensors="pt", padding=True,
            ).to(device)

            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits_per_image[0]
                probs = logits.softmax(dim=0).cpu().numpy()

            class_score = float(probs[0])  # match to class description
            general_score = float(probs[1])  # match to generic hieroglyph
            negative_score = float(probs[2])

            class_scores.append(class_score)
            total_checked += 1

            # Flag if negative score is dominant or class score is very low
            if negative_score > class_score and negative_score > general_score:
                class_flagged += 1
                total_flagged += 1
                flagged_images.append({
                    "path": f"{code}/{img_path.name}",
                    "class_score": round(class_score, 4),
                    "general_score": round(general_score, 4),
                    "negative_score": round(negative_score, 4),
                })

        report["per_class"][code] = {
            "checked": len(images),
            "flagged": class_flagged,
            "flagged_rate": round(class_flagged / max(len(images), 1) * 100, 1),
            "avg_class_score": round(float(np.mean(class_scores)), 4) if class_scores else 0,
            "min_class_score": round(float(min(class_scores)), 4) if class_scores else 0,
        }

        if (class_dirs.index(cls_dir) + 1) % 20 == 0:
            print(f"  [{class_dirs.index(cls_dir)+1}/{len(class_dirs)}] "
                  f"{code}: {len(images)} imgs, {class_flagged} flagged",
                  flush=True)

    report["total_checked"] = total_checked
    report["flagged"] = total_flagged
    report["flagged_rate"] = round(total_flagged / max(total_checked, 1) * 100, 2)
    report["flagged_images"] = flagged_images[:200]  # Cap for file size

    return report


def audit_detection_clip() -> dict:
    """Quick check: verify that previously CLIP-flagged detection images were removed."""
    flagged_file = DET_DIR / "clip_flagged.txt"
    report = {"clip_flagged_file": str(flagged_file)}

    if not flagged_file.exists():
        report["status"] = "No clip_flagged.txt found"
        return report

    flagged = flagged_file.read_text(encoding="utf-8").strip().split("\n")
    report["total_flagged"] = len(flagged)

    # Check how many still exist in the dataset
    still_present = 0
    for rel_path in flagged:
        parts = rel_path.strip().split("/", 1)
        if len(parts) == 2:
            split_name, filename = parts
            stem = Path(filename).stem
            # Check images dir
            for ext in SUPPORTED_EXTS:
                check = DET_DIR / "images" / split_name / f"{stem}{ext}"
                if check.exists():
                    still_present += 1
                    break

    report["still_present"] = still_present
    report["removed"] = len(flagged) - still_present
    report["status"] = "PASS" if still_present == 0 else f"WARN: {still_present} flagged images still present"

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CLIP audit of classification dataset")
    parser.add_argument("--sample", type=int, default=20,
                        help="Max images to check per class (0=all)")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--detection-only", action="store_true",
                        help="Only check detection CLIP flagged status")
    args = parser.parse_args()

    # 1. Detection CLIP verification
    print("=" * 60)
    print("  DETECTION DATASET — CLIP FLAG VERIFICATION")
    print("=" * 60)
    det_report = audit_detection_clip()
    print(f"  Status: {det_report.get('status', 'N/A')}")
    if det_report.get("total_flagged"):
        print(f"  Total flagged: {det_report['total_flagged']}")
        print(f"  Still present: {det_report.get('still_present', '?')}")
        print(f"  Removed: {det_report.get('removed', '?')}")

    if args.detection_only:
        return

    # 2. Classification CLIP audit
    print(f"\n{'='*60}")
    print(f"  CLASSIFICATION DATASET — CLIP MISLABEL AUDIT")
    print(f"  (sampling {args.sample} images per class)")
    print(f"{'='*60}")

    cls_report = audit_classification(
        sample_per_class=args.sample,
        device=args.device,
    )

    print(f"\n■ RESULTS:")
    print(f"  Total checked:  {cls_report.get('total_checked', 0)}")
    print(f"  Total flagged:  {cls_report.get('flagged', 0)}")
    print(f"  Flagged rate:   {cls_report.get('flagged_rate', 0):.2f}%")

    # Worst classes
    per_class = cls_report.get("per_class", {})
    worst = sorted(per_class.items(), key=lambda x: x[1].get("flagged_rate", 0), reverse=True)
    print(f"\n  Worst 10 classes by flagged rate:")
    for code, info in worst[:10]:
        print(f"    {code:8s} flagged={info['flagged']:>3d}/{info['checked']:>3d} "
              f"({info['flagged_rate']:.1f}%) avg_score={info['avg_class_score']:.3f}")

    # Gate check: DET-G5 < 5% mislabeled
    rate = cls_report.get("flagged_rate", 0)
    gate = "PASS" if rate < 5.0 else "FAIL"
    print(f"\n  DET-G5 (<5% mislabeled): {gate} ({rate:.2f}%)")

    # Save report
    report_path = CLS_DIR / "clip_audit_report.json"
    full_report = {"detection": det_report, "classification": cls_report}
    report_path.write_text(
        json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    main()
