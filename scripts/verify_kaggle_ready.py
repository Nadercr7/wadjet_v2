"""Verify all artifacts are ready for Kaggle upload."""
import os, json
from pathlib import Path

root = Path("D:/Personal attachements/Projects/Final_Horus/Wadjet-v2")

# 1. Balanced detection dataset
bal = root / "data" / "detection" / "balanced"
print("=== BALANCED DETECTION DATASET ===")
for split in ["train", "val", "test"]:
    img_dir = bal / "images" / split
    lbl_dir = bal / "labels" / split
    n_img = len(list(img_dir.iterdir())) if img_dir.exists() else 0
    n_lbl = len(list(lbl_dir.iterdir())) if lbl_dir.exists() else 0
    print(f"  {split:5s}: {n_img:,} images, {n_lbl:,} labels")
yaml_path = bal / "data.yaml"
print(f"  data.yaml: {yaml_path.exists()}")
log_path = bal / "balance_log.json"
if log_path.exists():
    log = json.loads(log_path.read_text())
    mc = log.get("mohiey_cap", "?")
    ft = log.get("final_train", "?")
    print(f"  balance_log: mohiey_cap={mc}, final_train={ft}")

total = sum(f.stat().st_size for f in bal.rglob("*") if f.is_file())
print(f"  Total size: {total / 1024**3:.2f} GB")

# 2. Stone textures
print("\n=== STONE TEXTURES ===")
for d in ["stone_textures", "stone_textures_good", "stone_textures_new"]:
    p = root / "data" / "detection" / d
    if p.exists():
        files = [f for f in p.iterdir() if f.is_file()]
        total_sz = sum(f.stat().st_size for f in files)
        print(f"  {d}: {len(files)} files, {total_sz / 1024**2:.1f} MB")

# 3. Notebooks
print("\n=== NOTEBOOKS ===")
for nb in [
    "planning/model-rebuild/pytorch/detector/hieroglyph_detector_v3.ipynb",
    "planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier_v2.ipynb",
]:
    p = root / nb
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        n_cells = len(data["cells"])
        n_code = sum(1 for c in data["cells"] if c["cell_type"] == "code")
        print(f"  {p.name}: {n_cells} cells ({n_code} code)")
    else:
        print(f"  {p.name}: MISSING!")

# 4. Kernel metadata
print("\n=== KERNEL METADATA ===")
for km in [
    "planning/model-rebuild/pytorch/detector/kernel-metadata-v3.json",
    "planning/model-rebuild/pytorch/hieroglyph/kernel-metadata-v2.json",
]:
    p = root / km
    if p.exists():
        data = json.loads(p.read_text())
        print(f"  {p.name}:")
        print(f"    id: {data['id']}")
        print(f"    code_file: {data['code_file']}")
        print(f"    datasets: {data['dataset_sources']}")
        print(f"    gpu: {data['enable_gpu']}, internet: {data['enable_internet']}")
    else:
        print(f"  {p.name}: MISSING!")

# 5. Kaggle CLI
print("\n=== KAGGLE CLI ===")
kaggle = root / ".venv" / "Scripts" / "kaggle.exe"
print(f"  kaggle.exe: {kaggle.exists()}")
