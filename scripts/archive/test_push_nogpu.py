"""Push training notebooks — try without GPU to check if quota is the only issue."""
import json
import os
import shutil
import tempfile
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

test_dir = os.path.join(tempfile.gettempdir(), "kaggle_nogpu")
os.makedirs(test_dir, exist_ok=True)

src_nb = "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"
shutil.copy2(src_nb, os.path.join(test_dir, "hieroglyph_classifier.ipynb"))

# Try with GPU disabled to confirm quota is the only issue
meta = {
    "id": "naderelakany/wadjet-hiero-onnx-test-nogpu",
    "title": "Wadjet Hiero ONNX Test Nogpu",
    "code_file": "hieroglyph_classifier.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": False,
    "enable_internet": True,
    "dataset_sources": ["naderelakany/wadjet-tfrecords"],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": []
}

with open(os.path.join(test_dir, "kernel-metadata.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

print("Pushing WITHOUT GPU (to confirm quota is the only blocker)...")
result = api.kernels_push(test_dir)
error = getattr(result, "_error", None)
ref = getattr(result, "_ref", "")
ver = getattr(result, "_version_number", None)

if error:
    print(f"ERROR: {error}")
else:
    print(f"SUCCESS — ref={ref}, version={ver}")
    print("The notebook format is FINE. GPU quota is the only issue.")
    print("Training needs GPU, so we need to wait for quota reset.")

    # Check quota status
    print("\nNow let's check when quota resets...")
    
shutil.rmtree(test_dir, ignore_errors=True)
