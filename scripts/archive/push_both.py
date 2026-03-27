"""Verify dataset access and push both kernels."""
from kaggle.api.kaggle_api_extended import KaggleApi
import json
import os

api = KaggleApi()
api.authenticate()
print(f"Authenticated as: {api.get_config_value('username')}")

# 1. Verify dataset access
print("\n=== Dataset Access ===")
for ds in ["naderelakany/wadjet-tfrecords", "naderelakany/wadjet-hieroglyph-tfrecords"]:
    try:
        files = api.dataset_list_files(ds)
        fl = files.files if hasattr(files, "files") else []
        names = [getattr(f, "name", "?") for f in fl]
        print(f"  {ds}: OK ({len(fl)} files)")
        for n in names[:3]:
            print(f"    {n}")
        if len(names) > 3:
            print(f"    ... +{len(names)-3} more")
    except Exception as e:
        print(f"  {ds}: FAILED - {e}")
        print("  => Cannot proceed. Make this dataset public first.")
        exit(1)

# 2. Fix hieroglyph notebook dataset reference
#    It needs BOTH datasets: wadjet-hieroglyph-tfrecords (hieroglyph data) 
#    and the path points to /kaggle/input/wadjet-tfrecords/classification
#    but the actual hieroglyph data is in wadjet-hieroglyph-tfrecords
print("\n=== Checking notebook DATA_DIR paths ===")

hiero_nb_path = "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"
with open(hiero_nb_path, "r", encoding="utf-8") as f:
    hiero_nb = json.load(f)

# Find the cell with DATA_DIR
for cell in hiero_nb["cells"]:
    src = cell.get("source", "")
    if isinstance(src, list):
        src = "".join(src)
    if "DATA_DIR" in src and "kaggle/input" in src:
        print(f"  Hieroglyph DATA_DIR: {[l.strip() for l in src.split(chr(10)) if 'DATA_DIR' in l and '=' in l]}")
        break

land_nb_path = "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb"
with open(land_nb_path, "r", encoding="utf-8") as f:
    land_nb = json.load(f)

for cell in land_nb["cells"]:
    src = cell.get("source", "")
    if isinstance(src, list):
        src = "".join(src)
    if "DATA_DIR" in src and "kaggle/input" in src:
        print(f"  Landmark DATA_DIR: {[l.strip() for l in src.split(chr(10)) if 'DATA_DIR' in l and '=' in l]}")
        break

# 3. Fix hieroglyph notebook: 
#    - dataset_sources needs wadjet-hieroglyph-tfrecords
#    - DATA_DIR should point to /kaggle/input/wadjet-hieroglyph-tfrecords
print("\n=== Fixing hieroglyph notebook ===")

# Fix DATA_DIR in notebook cells
fixed = False
for cell in hiero_nb["cells"]:
    src = cell.get("source", [])
    if isinstance(src, list):
        for i, line in enumerate(src):
            if 'DATA_DIR = "/kaggle/input/wadjet-tfrecords/classification"' in line:
                src[i] = line.replace(
                    '/kaggle/input/wadjet-tfrecords/classification',
                    '/kaggle/input/wadjet-hieroglyph-tfrecords'
                )
                print(f"  Fixed DATA_DIR in cell: {src[i].strip()}")
                fixed = True
    elif isinstance(src, str):
        if '/kaggle/input/wadjet-tfrecords/classification' in src:
            cell["source"] = src.replace(
                '/kaggle/input/wadjet-tfrecords/classification',
                '/kaggle/input/wadjet-hieroglyph-tfrecords'
            )
            print(f"  Fixed DATA_DIR in cell (string source)")
            fixed = True

if not fixed:
    print("  WARNING: Could not find DATA_DIR to fix!")

with open(hiero_nb_path, "w", encoding="utf-8") as f:
    json.dump(hiero_nb, f, indent=1, ensure_ascii=False)
print("  Notebook saved.")

# 4. Update kernel-metadata.json for hieroglyph
hiero_meta = {
    "id": "nadermohamedcr7/wadjet-v2-hieroglyph-onnx",
    "title": "Wadjet V2 Hieroglyph ONNX",
    "code_file": "hieroglyph_classifier.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": True,
    "enable_internet": True,
    "dataset_sources": ["naderelakany/wadjet-hieroglyph-tfrecords"],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
}
with open("planning/model-rebuild/notebooks/hieroglyph/kernel-metadata.json", "w", encoding="utf-8") as f:
    json.dump(hiero_meta, f, indent=2)
print("  Hieroglyph metadata updated.")

# 5. Update kernel-metadata.json for landmark
land_meta = {
    "id": "nadermohamedcr7/wadjet-v2-landmark-onnx",
    "title": "Wadjet V2 Landmark ONNX",
    "code_file": "landmark_classifier.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": True,
    "enable_internet": True,
    "dataset_sources": ["naderelakany/wadjet-tfrecords"],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
}
with open("planning/model-rebuild/notebooks/landmark/kernel-metadata.json", "w", encoding="utf-8") as f:
    json.dump(land_meta, f, indent=2)
print("  Landmark metadata updated.")

# 6. Push both kernels
print("\n=== Pushing Kernels ===")
for name, kdir in [
    ("hieroglyph", "planning/model-rebuild/notebooks/hieroglyph"),
    ("landmark", "planning/model-rebuild/notebooks/landmark"),
]:
    print(f"\nPushing {name}...")
    result = api.kernels_push(kdir)
    error = getattr(result, "_error", None)
    ref = getattr(result, "_ref", "")
    ver = getattr(result, "_version_number", None)
    if error:
        print(f"  ERROR: {error}")
    else:
        print(f"  SUCCESS — ref={ref}, version={ver}")

# 7. Check status immediately
print("\n=== Checking Status ===")
import time
time.sleep(5)
for ref in ["nadermohamedcr7/wadjet-v2-hieroglyph-onnx", "nadermohamedcr7/wadjet-v2-landmark-onnx"]:
    try:
        status = api.kernels_status(ref)
        state = status.get("status") if isinstance(status, dict) else getattr(status, "status", str(status))
        print(f"  {ref}: {state}")
    except Exception as e:
        print(f"  {ref}: {e}")
