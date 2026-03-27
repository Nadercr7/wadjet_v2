"""CLIP-based cleaning of merged YOLO detection dataset.

Scores every image against hieroglyph-positive and negative prompts.
Flags images below threshold for removal along with their labels.

Usage:
    # Dry-run (score and report, no deletions):
    python scripts/clip_clean_merged.py --dataset data/detection/merged --dry-run

    # Actually remove flagged images:
    python scripts/clip_clean_merged.py --dataset data/detection/merged --remove

    # Custom threshold:
    python scripts/clip_clean_merged.py --dataset data/detection/merged --threshold 0.20 --remove
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

MODEL_ID = "openai/clip-vit-base-patch32"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
DEFAULT_THRESHOLD = 0.20

# Positive prompts — things we WANT in the dataset
POSITIVE_PROMPTS = [
    "ancient Egyptian hieroglyph inscription carved in stone",
    "Egyptian hieroglyphic text on temple wall",
    "carved hieroglyphs on ancient Egyptian artifact",
    "stone tablet with Egyptian hieroglyphic writing",
    "ancient Egyptian relief with hieroglyphic symbols",
    "papyrus with Egyptian hieroglyphic script",
]

# Negative prompts — things we want to REJECT
NEGATIVE_PROMPTS = [
    "modern photograph of people or tourists",
    "landscape photograph without text or carvings",
    "blank wall or floor without inscriptions",
    "modern text document or book page",
    "photograph of modern building or city",
    "blurry or corrupted digital image",
    "painting or drawing that is not Egyptian",
    "food or drink photograph",
    "animal photograph without Egyptian context",
    "map or floor plan diagram",
]

# Sources known to be clean (skip them)
SKIP_PREFIXES = ("synthetic_",)


def load_clip(device: str):
    print(f"Loading CLIP model: {MODEL_ID} (device={device})...")
    t0 = time.time()
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    model = CLIPModel.from_pretrained(MODEL_ID).to(device)
    model.eval()
    print(f"  Model loaded in {time.time()-t0:.1f}s")
    return model, processor


def score_batch(model, processor, device, images, pos_prompts, neg_prompts):
    """Score a batch of PIL images. Returns list of dicts."""
    all_prompts = pos_prompts + neg_prompts
    n_pos = len(pos_prompts)

    inputs = processor(
        text=all_prompts,
        images=images,
        return_tensors="pt",
        padding=True,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        # logits_per_image: [batch, n_prompts]
        logits = outputs.logits_per_image
        probs = logits.softmax(dim=-1).cpu().numpy()

    results = []
    for i in range(len(images)):
        row = probs[i]
        pos_scores = row[:n_pos]
        neg_scores = row[n_pos:]
        best_pos = float(np.max(pos_scores))
        best_neg = float(np.max(neg_scores))
        results.append({
            "positive_score": best_pos,
            "negative_score": best_neg,
            "net_score": best_pos - best_neg,
        })
    return results


def collect_images(dataset_dir: Path):
    """Collect all image paths from train/val/test, grouped by split."""
    all_files = []
    for split in ("train", "val", "test"):
        img_dir = dataset_dir / "images" / split
        if not img_dir.exists():
            continue
        for f in sorted(img_dir.iterdir()):
            if f.suffix.lower() in SUPPORTED_EXTS:
                skip = any(f.name.startswith(p) for p in SKIP_PREFIXES)
                all_files.append((f, split, skip))
    return all_files


def main():
    parser = argparse.ArgumentParser(description="CLIP-clean merged YOLO dataset")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--dry-run", action="store_true",
                        help="Score and report only, don't remove")
    parser.add_argument("--remove", action="store_true",
                        help="Actually delete flagged images + labels")
    args = parser.parse_args()

    if not args.dry_run and not args.remove:
        print("ERROR: Specify --dry-run or --remove")
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, processor = load_clip(device)

    # Collect images
    all_files = collect_images(args.dataset)
    to_process = [(f, split) for f, split, skip in all_files if not skip]
    skipped = [(f, split) for f, split, skip in all_files if skip]
    print(f"Total images: {len(all_files)}")
    print(f"Skipping {len(skipped)} synthetic images (known clean)")
    print(f"Scoring {len(to_process)} images with CLIP...")
    print(f"Threshold: {args.threshold}")
    print(f"Batch size: {args.batch_size}")
    print()

    flagged = []
    scores_log = {}
    t0 = time.time()
    errors = 0

    for batch_start in range(0, len(to_process), args.batch_size):
        batch_files = to_process[batch_start:batch_start + args.batch_size]
        pil_images = []
        valid_entries = []

        for img_path, split in batch_files:
            try:
                img = Image.open(img_path).convert("RGB")
                # Resize large images to speed up CLIP
                w, h = img.size
                if max(w, h) > 512:
                    scale = 512 / max(w, h)
                    img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                pil_images.append(img)
                valid_entries.append((img_path, split))
            except Exception as e:
                print(f"  ERROR loading {img_path.name}: {e}")
                errors += 1

        if not pil_images:
            continue

        results = score_batch(
            model, processor, device,
            pil_images, POSITIVE_PROMPTS, NEGATIVE_PROMPTS,
        )

        for (img_path, split), result in zip(valid_entries, results):
            pos = result["positive_score"]
            neg = result["negative_score"]
            net = result["net_score"]
            keep = pos >= args.threshold

            scores_log[img_path.name] = {
                "split": split,
                "pos": round(pos, 4),
                "neg": round(neg, 4),
                "net": round(net, 4),
                "keep": keep,
            }

            if not keep:
                flagged.append((img_path, split))
                source = img_path.name.split("_")[0]
                print(f"  FLAGGED: {img_path.name} (pos={pos:.3f} neg={neg:.3f}) [{source}/{split}]")

        done = min(batch_start + args.batch_size, len(to_process))
        elapsed = time.time() - t0
        rate = done / elapsed if elapsed > 0 else 0
        eta = (len(to_process) - done) / rate if rate > 0 else 0
        if (done % (args.batch_size * 5) == 0) or done == len(to_process):
            print(f"  Progress: {done}/{len(to_process)} ({rate:.1f} img/s, ETA {eta/60:.0f}min)")

    # Summary
    print()
    print("=" * 60)
    print(f"  Total scored:  {len(to_process)}")
    print(f"  Skipped (syn): {len(skipped)}")
    print(f"  Errors:        {errors}")
    print(f"  Flagged:       {len(flagged)}")
    print(f"  Clean:         {len(to_process) - len(flagged) - errors}")
    print(f"  Time:          {time.time()-t0:.0f}s")
    print("=" * 60)

    # By source
    from collections import Counter
    source_flags = Counter()
    for f, _ in flagged:
        prefix = f.name.split("_")[0]
        source_flags[prefix] += 1
    if source_flags:
        print("\nFlagged by source:")
        for src, cnt in source_flags.most_common():
            print(f"  {src}: {cnt}")

    # By split
    split_flags = Counter()
    for f, s in flagged:
        split_flags[s] += 1
    if split_flags:
        print("\nFlagged by split:")
        for sp, cnt in split_flags.most_common():
            print(f"  {sp}: {cnt}")

    # Save scores
    log_path = args.dataset / "clip_scores.json"
    log_path.write_text(json.dumps(scores_log, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nScores saved to {log_path}")

    # Save flagged list
    flagged_path = args.dataset / "clip_flagged.txt"
    with open(flagged_path, "w", encoding="utf-8") as fh:
        for f, s in flagged:
            fh.write(f"{s}/{f.name}\n")
    print(f"Flagged list saved to {flagged_path}")

    # Remove if requested
    if args.remove and flagged:
        print(f"\nRemoving {len(flagged)} flagged images + labels...")
        removed = 0
        for img_path, split in flagged:
            # Remove image
            if img_path.exists():
                img_path.unlink()
            # Remove corresponding label
            lbl_path = args.dataset / "labels" / split / (img_path.stem + ".txt")
            if lbl_path.exists():
                lbl_path.unlink()
            removed += 1
        print(f"  Removed {removed} image+label pairs.")
    elif args.remove and not flagged:
        print("\nNo images to remove — dataset is clean!")

    # Report remaining counts
    if args.remove:
        print("\nRemaining counts:")
        for split in ("train", "val", "test"):
            img_dir = args.dataset / "images" / split
            if img_dir.exists():
                count = len([f for f in img_dir.iterdir() if f.suffix.lower() in SUPPORTED_EXTS])
                print(f"  {split}: {count}")


if __name__ == "__main__":
    main()
