"""Push actual training notebooks with fresh slugs to debug."""
import json
import os
import shutil
import tempfile
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

# Test 1: Push our actual hieroglyph notebook with a fresh slug
test_dir = os.path.join(tempfile.gettempdir(), "kaggle_real_push")
os.makedirs(test_dir, exist_ok=True)

# Copy actual notebook
src_nb = "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"
shutil.copy2(src_nb, os.path.join(test_dir, "hieroglyph_classifier.ipynb"))

# Create FRESH metadata with a different slug
meta = {
    "id": "naderelakany/wadjet-hiero-onnx-v2",
    "title": "Wadjet Hiero ONNX V2",
    "code_file": "hieroglyph_classifier.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": True,
    "enable_internet": True,
    "dataset_sources": ["naderelakany/wadjet-tfrecords"],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": []
}

with open(os.path.join(test_dir, "kernel-metadata.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

print("Pushing real hieroglyph notebook with fresh slug...")
result = api.kernels_push(test_dir)
error = getattr(result, "_error", None)
ref = getattr(result, "_ref", "")
ver = getattr(result, "_version_number", None)

if error:
    print(f"ERROR: {error}")
    
    # Try without dataset_sources to isolate the issue
    print("\nRetrying without dataset_sources...")
    meta["dataset_sources"] = []
    meta["id"] = "naderelakany/wadjet-hiero-onnx-v3"
    meta["title"] = "Wadjet Hiero ONNX V3"
    with open(os.path.join(test_dir, "kernel-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    
    result2 = api.kernels_push(test_dir)
    error2 = getattr(result2, "_error", None)
    ref2 = getattr(result2, "_ref", "")
    ver2 = getattr(result2, "_version_number", None)
    
    if error2:
        print(f"ERROR without datasets: {error2}")
    else:
        print(f"SUCCESS without datasets — ref={ref2}, version={ver2}")
        print("=> The dataset_sources are NOT the issue. The notebook content itself is the problem.")
else:
    print(f"SUCCESS — ref={ref}, version={ver}")

shutil.rmtree(test_dir, ignore_errors=True)
