r"""Generate synthetic composite images for hieroglyph detection training.

Pastes individual glyph classification crops onto stone/wall texture backgrounds
in grid patterns that mimic real inscriptions. Each composite has known bounding
boxes since we control glyph placement.

Usage:
    # Activate dataprep-env first:
    #   & scripts\dataprep-env\Scripts\Activate.ps1

    # Generate 1000 composites:
    python scripts/generate_synthetic_composites.py \
        --glyphs "data/hieroglyph_classification/train" \
        --backgrounds "data/detection/stone_textures" \
        --output "data/detection/synthetic" \
        --count 1000 \
        --preview 10

    # Quick test (5 composites):
    python scripts/generate_synthetic_composites.py \
        --glyphs "data/hieroglyph_classification/train" \
        --backgrounds "data/detection/stone_textures" \
        --output "data/detection/synthetic_test" \
        --count 5 \
        --preview 5

Glyph directory should have subdirectories per class (standard classification layout):
    glyphs/A1/*.png
    glyphs/A2/*.png
    ...
"""

import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def collect_glyphs(glyphs_dir: Path) -> list[Path]:
    """Collect all glyph image paths from a classification dataset directory."""
    glyphs = []
    for subdir in sorted(glyphs_dir.iterdir()):
        if subdir.is_dir():
            for img in subdir.iterdir():
                if img.suffix.lower() in SUPPORTED_EXTS:
                    glyphs.append(img)
    # Also check flat directory
    if not glyphs:
        for img in glyphs_dir.iterdir():
            if img.suffix.lower() in SUPPORTED_EXTS:
                glyphs.append(img)
    return glyphs


def collect_backgrounds(bg_dir: Path) -> list[Path]:
    """Collect background texture images."""
    return sorted([
        f for f in bg_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTS
    ])


def load_glyph(glyph_path: Path, target_size: int) -> np.ndarray | None:
    """Load and resize a glyph image to target size."""
    img = cv2.imread(str(glyph_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None

    # Convert to 3-channel BGR if grayscale
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        # Has alpha — use it for blending later
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    img = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_AREA)
    return img


def apply_glyph_augmentation(glyph: np.ndarray, rng: random.Random) -> np.ndarray:
    """Apply random augmentation to a glyph crop."""
    h, w = glyph.shape[:2]

    # Random brightness adjustment
    factor = rng.uniform(0.7, 1.3)
    glyph = np.clip(glyph * factor, 0, 255).astype(np.uint8)

    # Random slight rotation (-10 to +10 degrees)
    angle = rng.uniform(-10, 10)
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    glyph = cv2.warpAffine(glyph, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    # Random noise
    if rng.random() < 0.3:
        noise = np.random.normal(0, 8, glyph.shape).astype(np.int16)
        glyph = np.clip(glyph.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return glyph


def color_match(foreground: np.ndarray, background_patch: np.ndarray) -> np.ndarray:
    """Simple color matching — shift glyph mean/std to match background."""
    fg = foreground.astype(np.float32)
    bg = background_patch.astype(np.float32)

    for c in range(3):
        fg_mean, fg_std = fg[:, :, c].mean(), max(fg[:, :, c].std(), 1e-5)
        bg_mean, bg_std = bg[:, :, c].mean(), max(bg[:, :, c].std(), 1e-5)
        fg[:, :, c] = (fg[:, :, c] - fg_mean) * (bg_std / fg_std) * 0.7 + bg_mean

    return np.clip(fg, 0, 255).astype(np.uint8)


def alpha_blend_glyph(background: np.ndarray, glyph: np.ndarray, x: int, y: int, alpha: float = 0.85):
    """Blend a glyph onto the background at position (x, y)."""
    gh, gw = glyph.shape[:2]
    bh, bw = background.shape[:2]

    # Bounds check
    if x < 0 or y < 0 or x + gw > bw or y + gh > bh:
        return

    # Edge feathering (soften glyph borders)
    mask = np.ones((gh, gw), dtype=np.float32) * alpha
    border = max(2, gh // 10)
    for i in range(border):
        fade = (i + 1) / border * alpha
        mask[i, :] = min(mask[i, :].min(), fade)
        mask[-(i + 1), :] = min(mask[-(i + 1), :].min(), fade)
        mask[:, i] = np.minimum(mask[:, i], fade)
        mask[:, -(i + 1)] = np.minimum(mask[:, -(i + 1)], fade)

    mask = mask[:, :, np.newaxis]

    bg_patch = background[y:y + gh, x:x + gw].astype(np.float32)
    fg = glyph.astype(np.float32)

    blended = bg_patch * (1 - mask) + fg * mask
    background[y:y + gh, x:x + gw] = np.clip(blended, 0, 255).astype(np.uint8)


def generate_composite(
    glyphs: list[Path],
    background_path: Path,
    output_size: tuple[int, int] = (640, 640),
    min_glyphs: int = 5,
    max_glyphs: int = 20,
    rng: random.Random = None,
) -> tuple[np.ndarray, list[tuple[float, float, float, float]]]:
    """Generate a single synthetic composite image with hieroglyphs on stone.

    Returns (image, [(cx, cy, w, h), ...]) in normalized YOLO format.
    """
    if rng is None:
        rng = random.Random()

    out_w, out_h = output_size

    # Load and resize background
    bg = cv2.imread(str(background_path))
    if bg is None:
        bg = np.full((out_h, out_w, 3), 128, dtype=np.uint8)
    else:
        bg = cv2.resize(bg, (out_w, out_h))

    # Decide number of glyphs
    n_glyphs = rng.randint(min_glyphs, max_glyphs)

    # Grid layout — arrange glyphs in columns (Egyptian reading order)
    glyph_size_base = rng.randint(30, 60)
    margin = max(5, glyph_size_base // 4)

    # Calculate grid dimensions
    cols = max(1, (out_w - margin) // (glyph_size_base + margin))
    rows = max(1, (out_h - margin) // (glyph_size_base + margin))

    # Select random positions in grid
    positions = []
    for r in range(rows):
        for c in range(cols):
            x = margin + c * (glyph_size_base + margin)
            y = margin + r * (glyph_size_base + margin)
            if x + glyph_size_base <= out_w and y + glyph_size_base <= out_h:
                positions.append((x, y))

    rng.shuffle(positions)
    positions = positions[:n_glyphs]

    boxes = []

    for x, y in positions:
        # Pick random glyph
        glyph_path = rng.choice(glyphs)

        # Vary size slightly
        size = glyph_size_base + rng.randint(-8, 8)
        size = max(20, min(size, min(out_w, out_h) // 3))

        glyph_img = load_glyph(glyph_path, size)
        if glyph_img is None:
            continue

        # Augment
        glyph_img = apply_glyph_augmentation(glyph_img, rng)

        # Color match to background patch
        bg_patch = bg[y:y + size, x:x + size]
        if bg_patch.shape[:2] == (size, size):
            glyph_img = color_match(glyph_img, bg_patch)

        # Blend onto background
        alpha_blend_glyph(bg, glyph_img, x, y, alpha=rng.uniform(0.7, 0.95))

        # Record YOLO bbox (normalized)
        cx = (x + size / 2) / out_w
        cy = (y + size / 2) / out_h
        bw = size / out_w
        bh = size / out_h
        boxes.append((cx, cy, bw, bh))

    # Apply global effects
    # Slight blur
    if rng.random() < 0.4:
        ksize = rng.choice([3, 5])
        bg = cv2.GaussianBlur(bg, (ksize, ksize), 0)

    # Brightness/contrast jitter
    alpha_g = rng.uniform(0.8, 1.2)  # contrast
    beta_g = rng.randint(-20, 20)  # brightness
    bg = np.clip(bg.astype(np.float32) * alpha_g + beta_g, 0, 255).astype(np.uint8)

    return bg, boxes


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic composite images for hieroglyph detection"
    )
    parser.add_argument("--glyphs", required=True, type=Path,
                        help="Directory with glyph classification crops (subdirs per class)")
    parser.add_argument("--backgrounds", required=True, type=Path,
                        help="Directory with stone/wall texture images")
    parser.add_argument("--output", required=True, type=Path,
                        help="Output directory for images/ + labels/")
    parser.add_argument("--count", type=int, default=1000,
                        help="Number of composites to generate (default: 1000)")
    parser.add_argument("--size", type=int, default=640,
                        help="Output image size (default: 640)")
    parser.add_argument("--min-glyphs", type=int, default=5,
                        help="Min glyphs per composite (default: 5)")
    parser.add_argument("--max-glyphs", type=int, default=20,
                        help="Max glyphs per composite (default: 20)")
    parser.add_argument("--preview", type=int, default=0,
                        help="Number of preview images with boxes drawn (0=none)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")

    args = parser.parse_args()

    if not args.glyphs.exists():
        print(f"ERROR: Glyphs directory does not exist: {args.glyphs}")
        sys.exit(1)
    if not args.backgrounds.exists():
        print(f"ERROR: Backgrounds directory does not exist: {args.backgrounds}")
        sys.exit(1)

    glyphs = collect_glyphs(args.glyphs)
    backgrounds = collect_backgrounds(args.backgrounds)

    print(f"Glyphs: {len(glyphs)} images from {args.glyphs}")
    print(f"Backgrounds: {len(backgrounds)} images from {args.backgrounds}")

    if not glyphs:
        print("ERROR: No glyph images found")
        sys.exit(1)
    if not backgrounds:
        print("ERROR: No background images found")
        sys.exit(1)

    # Output dirs
    images_dir = args.output / "images"
    labels_dir = args.output / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    preview_dir = None
    if args.preview > 0:
        preview_dir = args.output / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    total_boxes = 0

    for i in range(args.count):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"  [{i+1}/{args.count}] generating...", flush=True)

        bg_path = rng.choice(backgrounds)
        img, boxes = generate_composite(
            glyphs, bg_path,
            output_size=(args.size, args.size),
            min_glyphs=args.min_glyphs,
            max_glyphs=args.max_glyphs,
            rng=rng,
        )

        stem = f"synthetic_{i:05d}"

        # Save image
        cv2.imwrite(str(images_dir / f"{stem}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])

        # Save YOLO label
        lines = [f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for cx, cy, w, h in boxes]
        (labels_dir / f"{stem}.txt").write_text(
            "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
        )

        total_boxes += len(boxes)

        # Preview
        if preview_dir and i < args.preview:
            preview = img.copy()
            ih, iw = preview.shape[:2]
            for cx, cy, bw, bh in boxes:
                x1 = int((cx - bw / 2) * iw)
                y1 = int((cy - bh / 2) * ih)
                x2 = int((cx + bw / 2) * iw)
                y2 = int((cy + bh / 2) * ih)
                cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 215, 55), 2)
            cv2.imwrite(str(preview_dir / f"{stem}_preview.jpg"), preview, [cv2.IMWRITE_JPEG_QUALITY, 85])

    # Metadata
    meta = {
        "total_composites": args.count,
        "total_boxes": total_boxes,
        "avg_boxes_per_image": round(total_boxes / max(1, args.count), 1),
        "output_size": args.size,
        "min_glyphs": args.min_glyphs,
        "max_glyphs": args.max_glyphs,
        "glyph_source": str(args.glyphs),
        "background_source": str(args.backgrounds),
        "seed": args.seed,
    }
    (args.output / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  Generated: {args.count} composites")
    print(f"  Total boxes: {total_boxes}")
    print(f"  Avg boxes/image: {total_boxes / max(1, args.count):.1f}")
    print(f"  Output: {args.output}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
