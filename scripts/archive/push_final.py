"""Push both kernels to their target slugs. They'll queue and run once GPU quota resets."""
import json
import os
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

notebooks = [
    {
        "dir": "planning/model-rebuild/notebooks/hieroglyph",
        "slug": "naderelakany/wadjet-hieroglyph-classifier-onnx",
        "title": "Wadjet Hieroglyph Classifier ONNX",
        "code_file": "hieroglyph_classifier.ipynb",
        "datasets": ["naderelakany/wadjet-tfrecords"],
    },
    {
        "dir": "planning/model-rebuild/notebooks/landmark",
        "slug": "naderelakany/wadjet-landmark-classifier-onnx", 
        "title": "Wadjet Landmark Classifier ONNX",
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

    # Write updated metadata
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
        if "quota" in error.lower():
            print(f"  => Kernel code uploaded but can't run yet (GPU quota depleted)")
            print(f"  => Go to https://www.kaggle.com/code/{nb['slug']} and run manually when quota resets")
    else:
        print(f"  SUCCESS — ref={ref}, version={ver}")
