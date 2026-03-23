"""
Copy assets from Wadjet v1 to Wadjet v2.

Usage:
    python scripts/copy_assets.py              # Dry run (show what would be copied)
    python scripts/copy_assets.py --execute    # Actually copy files
"""

import argparse
import shutil
from pathlib import Path

# Paths
V1 = Path(r"D:\Personal attachements\Projects\Final_Horus\Wadjet")
V2 = Path(r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2")

# Asset mapping: (v1_source, v2_destination)
# Files
FILE_ASSETS = [
    # --- ML Models ---
    # Hieroglyph detector (ONNX)
    (
        V1 / "hieroglyph_model/models/detection/glyph_detector_uint8.onnx",
        V2 / "models/hieroglyph/detector/glyph_detector_uint8.onnx",
    ),
    # Hieroglyph classifier (TF.js) — copied as directory below
    # Hieroglyph classifier (Keras, server-side)
    (
        V1 / "hieroglyph_model/models/classification/efficientnet_v2s.keras",
        V2 / "models/hieroglyph/classifier_keras/efficientnet_v2s.keras",
    ),
    # Label mapping
    (
        V1 / "hieroglyph_model/data/processed/label_mapping.json",
        V2 / "models/hieroglyph/label_mapping.json",
    ),
    # --- Translation data ---
    (
        V1 / "hieroglyph_model/data/translation/corpus.jsonl",
        V2 / "data/translation/corpus.jsonl",
    ),
    (
        V1 / "hieroglyph_model/data/translation/corpus.index",
        V2 / "data/translation/corpus.index",
    ),
    (
        V1 / "hieroglyph_model/data/translation/corpus_ids.json",
        V2 / "data/translation/corpus_ids.json",
    ),
    # --- Fonts ---
    (
        V1 / "hieroglyph_model/data/reference/fonts/NotoSansEgyptianHieroglyphs-Regular.ttf",
        V2 / "app/static/fonts/NotoSansEgyptianHieroglyphs-Regular.ttf",
    ),
    # --- Python source (adapt after copy) ---
    (
        V1 / "hieroglyph_model/src/pipeline/pipeline.py",
        V2 / "app/core/hieroglyph_pipeline.py",
    ),
    (
        V1 / "hieroglyph_model/src/transliteration/gardiner_mapping.py",
        V2 / "app/core/gardiner.py",
    ),
    (
        V1 / "hieroglyph_model/src/transliteration/engine.py",
        V2 / "app/core/transliteration.py",
    ),
    (
        V1 / "hieroglyph_model/src/transliteration/reading_order.py",
        V2 / "app/core/reading_order.py",
    ),
    (
        V1 / "hieroglyph_model/src/translation/rag_translator.py",
        V2 / "app/core/rag_translator.py",
    ),
    (
        V1 / "hieroglyph_model/src/detection/postprocess.py",
        V2 / "app/core/postprocess.py",
    ),
    (
        V1 / "app/core/gemini_service.py",
        V2 / "app/core/gemini_service.py",
    ),
    (
        V1 / "app/core/thoth_chat.py",
        V2 / "app/core/thoth_chat.py",
    ),
    (
        V1 / "app/core/attractions_data.py",
        V2 / "app/core/landmarks.py",
    ),
    (
        V1 / "app/core/hieroglyphs_data.py",
        V2 / "app/core/hieroglyphs_data.py",
    ),
    # --- JS pipeline ---
    (
        V1 / "app/static/js/hieroglyph-pipeline.js",
        V2 / "app/static/js/hieroglyph-pipeline.js",
    ),
]

# Directory copies (recursive)
DIR_ASSETS = [
    # TF.js hieroglyph classifier (model.json + shards)
    (
        V1 / "hieroglyph_model/models/tfjs_uint8",
        V2 / "models/hieroglyph/classifier",
    ),
    # Landmark TF.js model
    (
        V1 / "app/static/model",
        V2 / "models/landmark/tfjs",
    ),
    # Landmark metadata JSONs
    (
        V1 / "data/metadata",
        V2 / "data/metadata",
    ),
    # Landmark text descriptions
    (
        V1 / "data/text",
        V2 / "data/text",
    ),
    # Embeddings (bge-m3 for FAISS)
    (
        V1 / "hieroglyph_model/data/embeddings",
        V2 / "data/translation/embeddings",
    ),
]


def copy_file(src: Path, dst: Path, *, execute: bool) -> str:
    """Copy a single file. Returns status string."""
    if not src.exists():
        return f"  MISSING  {src}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    size_mb = src.stat().st_size / (1024 * 1024)
    if execute:
        shutil.copy2(src, dst)
        return f"  COPIED   {src.name} ({size_mb:.1f} MB) -> {dst.relative_to(V2)}"
    return f"  WOULD COPY  {src.name} ({size_mb:.1f} MB) -> {dst.relative_to(V2)}"


def copy_dir(src: Path, dst: Path, *, execute: bool) -> str:
    """Copy a directory recursively. Returns status string."""
    if not src.exists():
        return f"  MISSING  {src}"
    file_count = sum(1 for _ in src.rglob("*") if _.is_file())
    total_mb = sum(f.stat().st_size for f in src.rglob("*") if f.is_file()) / (1024 * 1024)
    if execute:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return f"  COPIED   {src.name}/ ({file_count} files, {total_mb:.1f} MB) -> {dst.relative_to(V2)}"
    return f"  WOULD COPY  {src.name}/ ({file_count} files, {total_mb:.1f} MB) -> {dst.relative_to(V2)}"


def main():
    parser = argparse.ArgumentParser(description="Copy v1 assets to v2")
    parser.add_argument("--execute", action="store_true", help="Actually copy (default is dry run)")
    args = parser.parse_args()

    mode = "EXECUTING" if args.execute else "DRY RUN"
    print(f"\n{'=' * 60}")
    print(f"  Wadjet v1 -> v2 Asset Copy ({mode})")
    print(f"{'=' * 60}")
    print(f"  Source: {V1}")
    print(f"  Target: {V2}")
    print()

    # Files
    print("--- Files ---")
    for src, dst in FILE_ASSETS:
        print(copy_file(src, dst, execute=args.execute))

    # Directories
    print("\n--- Directories ---")
    for src, dst in DIR_ASSETS:
        print(copy_dir(src, dst, execute=args.execute))

    if not args.execute:
        print(f"\n  This was a dry run. Run with --execute to copy.")
    else:
        print(f"\n  Done! Assets copied to {V2}")
    print()


if __name__ == "__main__":
    main()
