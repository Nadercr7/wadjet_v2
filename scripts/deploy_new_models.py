r"""Deploy new models from Kaggle output into the project.

After Kaggle training finishes:
1. Download outputs (detector onnx + metadata, classifier onnx + mapping)
2. Run this script to back up old models and install new ones
3. Run `python scripts/test_model_export.py --new-detector ... --new-classifier ...` to validate

Usage:
    # Dry run (shows what would change):
    python scripts/deploy_new_models.py \
        --detector-dir path/to/detector_output/ \
        --classifier-dir path/to/classifier_output/ \
        --dry-run

    # Execute:
    python scripts/deploy_new_models.py \
        --detector-dir path/to/detector_output/ \
        --classifier-dir path/to/classifier_output/
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Deployment targets
DET_TARGET = ROOT / "models" / "hieroglyph" / "detector"
CLS_TARGET = ROOT / "models" / "hieroglyph" / "classifier"

# Expected files from Kaggle output
DETECTOR_FILES = [
    "glyph_detector_uint8.onnx",
    "glyph_detector_fp32.onnx",
    "model_metadata.json",
]
CLASSIFIER_FILES = [
    "hieroglyph_classifier_uint8.onnx",
    "hieroglyph_classifier.onnx",
    "label_mapping.json",
    "model_metadata.json",
]


def backup_dir(target: Path, dry_run: bool) -> Path | None:
    """Create timestamped backup of existing model directory."""
    if not target.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = target.parent / f"{target.name}_backup_{ts}"
    if dry_run:
        print(f"  [DRY] Would back up {target.name}/ → {backup.name}/")
    else:
        shutil.copytree(target, backup)
        print(f"  Backed up {target.name}/ → {backup.name}/")
    return backup


def deploy_files(src_dir: Path, target: Path, expected: list[str], dry_run: bool) -> list[str]:
    """Copy expected files from source to target."""
    deployed = []
    missing = []
    for fname in expected:
        src = src_dir / fname
        dst = target / fname
        if not src.exists():
            # Also check if it's nested one level (Kaggle sometimes wraps)
            candidates = list(src_dir.rglob(fname))
            if candidates:
                src = candidates[0]
            else:
                missing.append(fname)
                continue
        if dry_run:
            print(f"  [DRY] Would copy {src.name} → {dst}")
        else:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  Copied {src.name} ({src.stat().st_size / 1024 / 1024:.1f} MB)")
        deployed.append(fname)

    if missing:
        print(f"  ⚠️  Missing: {', '.join(missing)}")

    return deployed


def validate_onnx(model_path: Path) -> bool:
    """Quick validation that ONNX loads."""
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        inp = sess.get_inputs()[0]
        out = sess.get_outputs()[0]
        print(f"    ✓ {model_path.name}: input={inp.shape} → output={out.shape}")
        return True
    except Exception as e:
        print(f"    ✗ {model_path.name}: {e}")
        return False


def validate_label_map(path: Path, expected_classes: int = 171) -> bool:
    """Validate label mapping has expected number of classes."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        idx2g = data.get("idx_to_gardiner", data)
        count = len(idx2g)
        ok = count == expected_classes
        print(f"    {'✓' if ok else '✗'} {path.name}: {count} classes (expected {expected_classes})")
        return ok
    except Exception as e:
        print(f"    ✗ {path.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Deploy new models from Kaggle output")
    parser.add_argument("--detector-dir", type=Path, default=None,
                        help="Directory containing new detector ONNX + metadata")
    parser.add_argument("--classifier-dir", type=Path, default=None,
                        help="Directory containing new classifier ONNX + mapping")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without doing it")
    args = parser.parse_args()

    if not args.detector_dir and not args.classifier_dir:
        parser.error("At least one of --detector-dir or --classifier-dir required")

    print("=" * 60)
    print("  WADJET MODEL DEPLOYMENT")
    print("=" * 60)
    if args.dry_run:
        print("  MODE: DRY RUN (no changes)\n")

    # Deploy detector
    if args.detector_dir:
        print("\n■ Detector")
        if not args.detector_dir.exists():
            print(f"  ERROR: {args.detector_dir} not found")
        else:
            backup_dir(DET_TARGET, args.dry_run)
            deployed = deploy_files(args.detector_dir, DET_TARGET, DETECTOR_FILES, args.dry_run)
            if not args.dry_run and deployed:
                print("  Validating...")
                for f in deployed:
                    if f.endswith(".onnx"):
                        validate_onnx(DET_TARGET / f)

    # Deploy classifier
    if args.classifier_dir:
        print("\n■ Classifier")
        if not args.classifier_dir.exists():
            print(f"  ERROR: {args.classifier_dir} not found")
        else:
            backup_dir(CLS_TARGET, args.dry_run)
            deployed = deploy_files(args.classifier_dir, CLS_TARGET, CLASSIFIER_FILES, args.dry_run)
            if not args.dry_run and deployed:
                print("  Validating...")
                for f in deployed:
                    if f.endswith(".onnx"):
                        validate_onnx(CLS_TARGET / f)
                lm = CLS_TARGET / "label_mapping.json"
                if lm.exists():
                    validate_label_map(lm)

    # Reminder
    print(f"\n{'='*60}")
    print("  NEXT STEPS")
    print(f"{'='*60}")
    print("  1. Run: python scripts/test_model_export.py")
    if args.detector_dir:
        print(f"     --new-detector {DET_TARGET / 'glyph_detector_uint8.onnx'}")
    if args.classifier_dir:
        print(f"     --new-classifier {CLS_TARGET / 'hieroglyph_classifier_uint8.onnx'}")
        print(f"     --new-label-map {CLS_TARGET / 'label_mapping.json'}")
    print("  2. Run: python scripts/test_before_after.py")
    print("  3. Test full scan: uvicorn app.main:app → upload image → verify results")
    print("  4. Update SW cache version in base.html + sw.js")


if __name__ == "__main__":
    main()
