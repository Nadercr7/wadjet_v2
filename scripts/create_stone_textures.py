r"""Generate synthetic stone/wall texture images for composite backgrounds.

Creates varied stone textures using multi-frequency noise, realistic color
palettes, and weathering effects that mimic Egyptian temple walls, limestone,
sandstone, granite, and papyrus surfaces.

Usage:
    python scripts/create_stone_textures.py \
        --output "data/detection/stone_textures" \
        --count 200
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


# Egyptian stone color palettes (BGR format for OpenCV)
# Each palette has: base color, warm shift, cool shift, grain color, contrast range
PALETTES = {
    "limestone_light": {
        "base": np.array([205, 210, 218], dtype=np.float32),
        "warm": np.array([0, 8, 15], dtype=np.float32),
        "cool": np.array([8, 0, -5], dtype=np.float32),
        "var": 35, "grain": 18,
    },
    "limestone_warm": {
        "base": np.array([165, 185, 200], dtype=np.float32),
        "warm": np.array([-5, 10, 20], dtype=np.float32),
        "cool": np.array([10, 0, -8], dtype=np.float32),
        "var": 30, "grain": 15,
    },
    "sandstone_yellow": {
        "base": np.array([130, 180, 210], dtype=np.float32),
        "warm": np.array([-10, 5, 15], dtype=np.float32),
        "cool": np.array([8, -5, -10], dtype=np.float32),
        "var": 40, "grain": 20,
    },
    "sandstone_orange": {
        "base": np.array([105, 155, 200], dtype=np.float32),
        "warm": np.array([-8, 8, 18], dtype=np.float32),
        "cool": np.array([10, -3, -10], dtype=np.float32),
        "var": 35, "grain": 18,
    },
    "sandstone_pink": {
        "base": np.array([145, 165, 195], dtype=np.float32),
        "warm": np.array([-5, 5, 20], dtype=np.float32),
        "cool": np.array([8, -3, -8], dtype=np.float32),
        "var": 30, "grain": 16,
    },
    "granite_grey": {
        "base": np.array([125, 130, 135], dtype=np.float32),
        "warm": np.array([-3, 3, 8], dtype=np.float32),
        "cool": np.array([5, -2, -5], dtype=np.float32),
        "var": 25, "grain": 22,
    },
    "granite_rose": {
        "base": np.array([120, 130, 155], dtype=np.float32),
        "warm": np.array([-5, 5, 15], dtype=np.float32),
        "cool": np.array([8, -3, -8], dtype=np.float32),
        "var": 28, "grain": 20,
    },
    "papyrus_aged": {
        "base": np.array([145, 190, 215], dtype=np.float32),
        "warm": np.array([-8, 5, 12], dtype=np.float32),
        "cool": np.array([5, -3, -8], dtype=np.float32),
        "var": 35, "grain": 12,
    },
    "papyrus_dark": {
        "base": np.array([110, 150, 175], dtype=np.float32),
        "warm": np.array([-5, 8, 15], dtype=np.float32),
        "cool": np.array([8, -3, -10], dtype=np.float32),
        "var": 30, "grain": 14,
    },
    "mud_brick": {
        "base": np.array([95, 135, 165], dtype=np.float32),
        "warm": np.array([-5, 8, 15], dtype=np.float32),
        "cool": np.array([8, -3, -8], dtype=np.float32),
        "var": 30, "grain": 25,
    },
    "alabaster": {
        "base": np.array([215, 225, 235], dtype=np.float32),
        "warm": np.array([0, 5, 10], dtype=np.float32),
        "cool": np.array([5, 0, -3], dtype=np.float32),
        "var": 20, "grain": 10,
    },
    "basalt_dark": {
        "base": np.array([65, 68, 72], dtype=np.float32),
        "warm": np.array([-3, 3, 8], dtype=np.float32),
        "cool": np.array([5, -2, -5], dtype=np.float32),
        "var": 18, "grain": 15,
    },
}


def fractal_noise(h: int, w: int, octaves: int, rng: np.random.Generator,
                  base_scale: int = 4) -> np.ndarray:
    """Multi-octave fractal noise with visible detail at all scales."""
    result = np.zeros((h, w), dtype=np.float32)
    amplitude = 1.0

    for octave in range(octaves):
        freq = base_scale * (2 ** octave)
        # Use enough resolution to see detail
        nh = max(4, min(h, freq))
        nw = max(4, min(w, freq))
        noise = rng.standard_normal((nh, nw)).astype(np.float32)
        upscaled = cv2.resize(noise, (w, h), interpolation=cv2.INTER_CUBIC)
        result += upscaled * amplitude
        amplitude *= 0.55  # Persistence — keep high-freq detail visible

    lo, hi = np.percentile(result, [2, 98])
    result = np.clip((result - lo) / (hi - lo + 1e-8), 0, 1)
    return result


def generate_stone_texture(
    width: int = 800,
    height: int = 800,
    palette_name: str = None,
    rng: np.random.Generator = None,
) -> np.ndarray:
    """Generate a realistic synthetic stone/wall texture."""
    if rng is None:
        rng = np.random.default_rng()

    if palette_name is None:
        palette_name = rng.choice(list(PALETTES.keys()))

    pal = PALETTES[palette_name]
    base = pal["base"].copy()
    warm = pal["warm"]
    cool = pal["cool"]
    var = pal["var"]
    grain_str = pal["grain"]

    # --- Layer 1: Large-scale color variation (geological veins) ---
    large_noise = fractal_noise(height, width, 3, rng, base_scale=3)

    # Warm/cool shift based on large noise
    img = np.zeros((height, width, 3), dtype=np.float32)
    for c in range(3):
        img[:, :, c] = base[c] + large_noise * warm[c] * 2 + (1 - large_noise) * cool[c] * 2

    # --- Layer 2: Medium-scale texture (stone grain / mineral patches) ---
    medium_noise = fractal_noise(height, width, 5, rng, base_scale=8)
    for c in range(3):
        img[:, :, c] += (medium_noise - 0.5) * var

    # --- Layer 3: Fine speckle (crystal/mineral grain) ---
    fine_noise = rng.standard_normal((height, width)).astype(np.float32)
    for c in range(3):
        # Slightly different noise per channel to avoid grey-only grain
        channel_noise = fine_noise + rng.standard_normal((height, width)).astype(np.float32) * 0.3
        img[:, :, c] += channel_noise * grain_str

    # --- Layer 4: Occasional dark mineral veins / cracks ---
    if rng.random() < 0.5:
        vein_noise = fractal_noise(height, width, 6, rng, base_scale=6)
        # Make veins only in narrow bands (threshold)
        vein_mask = (vein_noise > 0.48) & (vein_noise < 0.52)
        vein_mask = vein_mask.astype(np.float32)
        vein_mask = cv2.GaussianBlur(vein_mask, (3, 3), 0.8)
        darkness = rng.uniform(15, 40)
        for c in range(3):
            img[:, :, c] -= vein_mask * darkness

    # --- Layer 5: Weathering patches (uneven erosion) ---
    if rng.random() < 0.6:
        n_patches = rng.integers(2, 6)
        for _ in range(n_patches):
            cx = rng.integers(0, width)
            cy = rng.integers(0, height)
            rx = rng.integers(40, width // 3)
            ry = rng.integers(40, height // 3)
            # Elliptical patch
            Y, X = np.ogrid[:height, :width]
            dist = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2
            mask = np.clip(1.0 - dist, 0, 1).astype(np.float32)
            mask = cv2.GaussianBlur(mask, (0, 0), min(rx, ry) * 0.3)
            shift = rng.uniform(-20, 20)
            for c in range(3):
                img[:, :, c] += mask * (shift + rng.uniform(-5, 5))

    # --- Layer 6: Subtle pitting (small dark spots) ---
    if rng.random() < 0.5:
        pit_noise = rng.random((height // 4, width // 4)).astype(np.float32)
        pit_noise = (pit_noise < 0.03).astype(np.float32)  # Sparse dots
        pit_noise = cv2.resize(pit_noise, (width, height), interpolation=cv2.INTER_NEAREST)
        pit_noise = cv2.GaussianBlur(pit_noise, (5, 5), 1.0)
        for c in range(3):
            img[:, :, c] -= pit_noise * rng.uniform(20, 50)

    # --- Clamp and convert ---
    img = np.clip(img, 0, 255).astype(np.uint8)

    # --- Optional vignette (darker edges, subtle) ---
    if rng.random() < 0.35:
        cx, cy = width // 2, height // 2
        Y, X = np.ogrid[:height, :width]
        dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2).astype(np.float32)
        vignette = np.clip(1.0 - 0.15 * dist ** 2, 0.7, 1.0)
        img = np.clip(img.astype(np.float32) * vignette[:, :, np.newaxis], 0, 255).astype(np.uint8)

    return img


def main():
    parser = argparse.ArgumentParser(description="Generate stone texture backgrounds")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--count", type=int, default=200, help="Number of textures")
    parser.add_argument("--size", type=int, default=800, help="Image size (square)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    palette_names = list(PALETTES.keys())
    print(f"Generating {args.count} stone textures ({args.size}x{args.size}) -> {args.output}")
    print(f"Palettes: {', '.join(palette_names)}")

    for i in range(args.count):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  [{i+1}/{args.count}]...", flush=True)

        palette_name = rng.choice(palette_names)
        img = generate_stone_texture(args.size, args.size, palette_name, rng)
        cv2.imwrite(str(args.output / f"stone_{i:04d}_{palette_name}.jpg"), img,
                    [cv2.IMWRITE_JPEG_QUALITY, 92])

    print(f"\nDone. {args.count} textures saved to {args.output}")


if __name__ == "__main__":
    main()
