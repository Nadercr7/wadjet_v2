"""Debug Kaggle kernel push — run directly."""
import json
import os
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()
print("Authenticated OK")

kernel_dir = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\planning\model-rebuild\notebooks\hieroglyph"

# Read metadata
with open(os.path.join(kernel_dir, "kernel-metadata.json")) as f:
    meta = json.load(f)
print(f"Metadata ID: {meta['id']}")
print(f"Code file: {meta['code_file']}")
print(f"GPU: {meta.get('enable_gpu')}, Internet: {meta.get('enable_internet')}")
print(f"Datasets: {meta.get('dataset_sources')}")

# Check notebook
nb_path = os.path.join(kernel_dir, meta["code_file"])
print(f"\nNotebook exists: {os.path.exists(nb_path)}")
with open(nb_path, encoding="utf-8") as f:
    nb = json.load(f)
cells = nb.get("cells", [])
print(f"Cells: {len(cells)}")
print(f"Kernelspec: {nb.get('metadata', {}).get('kernelspec', {})}")

# Push
print("\nPushing...")
result = api.kernels_push(kernel_dir)
print(f"Result: {result}")
print(f"Type: {type(result)}")

# Try to inspect result
if isinstance(result, dict):
    for k, v in result.items():
        print(f"  {k}: {v}")
elif hasattr(result, "__dict__"):
    for k, v in result.__dict__.items():
        print(f"  {k}: {v}")
else:
    # It might be a tuple or something
    try:
        for i, item in enumerate(result):
            print(f"  [{i}]: {item}")
    except TypeError:
        pass
