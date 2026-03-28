"""Push both kernels with FRESH slugs (avoiding corrupted old ones)."""
import json
import os
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

notebooks = [
    {
        "dir": "planning/model-rebuild/notebooks/hieroglyph",
        "slug": "naderelakany/wadjet-v2-hieroglyph-onnx",
        "title": "Wadjet V2 Hieroglyph ONNX",
        "code_file": "hieroglyph_classifier.ipynb",
        "datasets": ["naderelakany/wadjet-tfrecords"],
    },
    {
        "dir": "planning/model-rebuild/notebooks/landmark",
        "slug": "naderelakany/wadjet-v2-landmark-onnx",
        "title": "Wadjet V2 Landmark ONNX",
        "code_file": "landmark_classifier.ipynb",
        "datasets": ["naderelakany/wadjet-tfrecords"],
    },
]

for nb in notebooks:
    meta = {
        "id": nb["slug"],
        "title": nb["title"],
        "code_file": nb["code_file"],
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": nb["datasets"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }

    meta_path = os.path.join(nb["dir"], "kernel-metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Pushing {nb['slug']}...")
    result = api.kernels_push(nb["dir"])
    error = getattr(result, "_error", None)
    ref = getattr(result, "_ref", "")
    ver = getattr(result, "_version_number", None)

    if error:
        print(f"  ERROR: {error}")
    else:
        print(f"  SUCCESS — ref={ref}, version={ver}")
        print(f"  URL: https://www.kaggle.com/code/{nb['slug']}")
