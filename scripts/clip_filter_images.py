r"""Filter images using CLIP similarity scoring.

Scores each image against reference text prompts and keeps only images
above a similarity threshold. Used to clean scraped museum/web images
by removing ads, maps, modern buildings, tourist selfies, etc.

Usage:
    # Activate dataprep-env first:
    #   & scripts\dataprep-env\Scripts\Activate.ps1

    # Filter scraped museum images:
    python scripts/clip_filter_images.py \
        --input "data/detection/scraped_raw" \
        --output "data/detection/scraped_filtered" \
        --threshold 0.25 \
        --preview 10

    # Dry-run (just show scores, don't copy):
    python scripts/clip_filter_images.py \
        --input "data/detection/scraped_raw" \
        --output "data/detection/scraped_filtered" \
        --dry-run
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

MODEL_ID = "openai/clip-vit-base-patch32"

DEFAULT_THRESHOLD = 0.25

# Positive prompts (hieroglyph content)
POSITIVE_PROMPTS = [
    "ancient Egyptian hieroglyph inscription on stone wall",
    "carved Egyptian hieroglyphs on temple",
    "Egyptian hieroglyphic text on artifact",
    "ancient Egyptian writing carved in stone",
]

# Negative prompts (things to reject)
NEGATIVE_PROMPTS = [
    "modern building exterior",
    "tourist selfie photograph",
    "museum floor plan or map",
    "advertisement or banner",
    "book cover or text page",
]


def load_clip(model_id: str, device: str) -> tuple:
    """Load CLIP model and processor."""
    print(f"Loading CLIP model: {model_id} (device={device})...")
    processor = CLIPProcessor.from_pretrained(model_id)
    model = CLIPModel.from_pretrained(model_id).to(device)
    model.eval()
    print(f"  Model loaded.")
    return model, processor


def score_image(
    model,
    processor,
    device: str,
    image: Image.Image,
    positive_prompts: list[str],
    negative_prompts: list[str],
) -> dict:
    """Score an image against positive and negative prompts.

    Returns dict with:
        positive_score: max similarity across positive prompts
        negative_score: max similarity across negative prompts
        net_score: positive_score - negative_score
        best_positive: text of best-matching positive prompt
        best_negative: text of best-matching negative prompt
    """
    all_prompts = positive_prompts + negative_prompts

    inputs = processor(
        text=all_prompts,
        images=image,
        return_tensors="pt",
        padding=True,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits_per_image[0]  # shape: [n_prompts]
        probs = logits.softmax(dim=0).cpu().numpy()

    n_pos = len(positive_prompts)
    pos_scores = probs[:n_pos]
    neg_scores = probs[n_pos:]

    best_pos_idx = int(np.argmax(pos_scores))
    best_neg_idx = int(np.argmax(neg_scores))

    return {
        "positive_score": float(pos_scores[best_pos_idx]),
        "negative_score": float(neg_scores[best_neg_idx]),
        "net_score": float(pos_scores[best_pos_idx] - neg_scores[best_neg_idx]),
        "best_positive": positive_prompts[best_pos_idx],
        "best_negative": negative_prompts[best_neg_idx],
        "all_positive_scores": [float(s) for s in pos_scores],
        "all_negative_scores": [float(s) for s in neg_scores],
    }


def process_directory(
    input_dir: Path,
    output_dir: Path,
    model,
    processor,
    device: str,
    threshold: float = DEFAULT_THRESHOLD,
    positive_prompts: list[str] = None,
    negative_prompts: list[str] = None,
    preview_count: int = 0,
    dry_run: bool = False,
    limit: int = 0,
) -> dict:
    """Score and filter all images in a directory."""
    if positive_prompts is None:
        positive_prompts = POSITIVE_PROMPTS
    if negative_prompts is None:
        negative_prompts = NEGATIVE_PROMPTS

    # Find images
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
    print(f"Threshold: {threshold}")
    print(f"Positive prompts: {positive_prompts}")
    print(f"Negative prompts: {negative_prompts}")
    print()

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "total_images": len(image_files),
        "kept": 0,
        "rejected": 0,
        "errors": 0,
        "threshold": threshold,
        "positive_prompts": positive_prompts,
        "negative_prompts": negative_prompts,
        "model": MODEL_ID,
        "scores": {},
    }

    for i, img_path in enumerate(image_files):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1}/{len(image_files)}] {img_path.name}...", flush=True)

        try:
            pil_image = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"  SKIP {img_path.name}: {e}")
            stats["errors"] += 1
            continue

        result = score_image(
            model, processor, device, pil_image,
            positive_prompts, negative_prompts,
        )

        keep = result["positive_score"] >= threshold
        status = "KEEP" if keep else "REJECT"

        if (i + 1) % 10 == 0 or i == 0 or not keep:
            print(f"    {status}: pos={result['positive_score']:.3f} "
                  f"neg={result['negative_score']:.3f} "
                  f"net={result['net_score']:.3f}")

        if keep:
            stats["kept"] += 1
            if not dry_run:
                dest = output_dir / img_path.name
                if not dest.exists():
                    shutil.copy2(img_path, dest)
        else:
            stats["rejected"] += 1

        stats["scores"][img_path.name] = {
            "positive_score": result["positive_score"],
            "negative_score": result["negative_score"],
            "net_score": result["net_score"],
            "kept": keep,
        }

    # Write metadata
    if not dry_run:
        meta_path = output_dir / "clip_filter_metadata.json"
        meta_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary
    print()
    print("=" * 60)
    print(f"  Total images:  {stats['total_images']}")
    print(f"  Kept:          {stats['kept']}")
    print(f"  Rejected:      {stats['rejected']}")
    print(f"  Errors:        {stats['errors']}")
    keep_pct = (stats['kept'] / max(1, stats['total_images'])) * 100
    print(f"  Keep rate:     {keep_pct:.1f}%")
    if not dry_run:
        print(f"  Output dir:    {output_dir}")
    else:
        print(f"  (dry-run — no files copied)")
    print("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Filter images using CLIP similarity scoring"
    )
    parser.add_argument("--input", required=True, type=Path,
                        help="Input directory with images")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output directory for kept images")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Min positive score to keep (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--preview", type=int, default=0,
                        help="(unused, reserved for future)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Just show scores, don't copy files")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only first N images (0=all)")
    parser.add_argument("--device", default="cpu",
                        help="Device (cpu or cuda)")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input directory does not exist: {args.input}")
        sys.exit(1)

    model, processor = load_clip(MODEL_ID, args.device)

    process_directory(
        input_dir=args.input,
        output_dir=args.output,
        model=model,
        processor=processor,
        device=args.device,
        threshold=args.threshold,
        dry_run=args.dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
