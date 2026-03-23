"""Fix landmark notebook: replace hardcoded DATA_ROOT with auto-discovery."""
import json

nb_path = "planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

NEW_BLOCK = r'''# Kaggle dataset paths — auto-discover mount point
OUT_DIR   = "/kaggle/working"

# Discover the actual dataset mount path
print("\n── /kaggle/input/ contents ──")
for name in sorted(os.listdir("/kaggle/input")):
    full = os.path.join("/kaggle/input", name)
    tag = "DIR" if os.path.isdir(full) else "FILE"
    print(f"  {tag}: {name}")

# Search for train directory
DATA_ROOT = None
for name in os.listdir("/kaggle/input"):
    candidate = os.path.join("/kaggle/input", name)
    if os.path.isdir(candidate):
        children = os.listdir(candidate)
        if "train" in children:
            DATA_ROOT = candidate
            break
        for child in children:
            sub = os.path.join(candidate, child)
            if os.path.isdir(sub) and "train" in os.listdir(sub):
                DATA_ROOT = sub
                break
        if DATA_ROOT:
            break

if DATA_ROOT is None:
    for root, dirs, files in os.walk("/kaggle/input"):
        if "train" in dirs and "val" in dirs:
            DATA_ROOT = root
            break

if DATA_ROOT is None:
    raise FileNotFoundError("Could not find train/val/test dirs under /kaggle/input/")

print(f"\nDATA_ROOT = {DATA_ROOT}")
print(f"Contents: {sorted(os.listdir(DATA_ROOT))}")

TRAIN_DIR = os.path.join(DATA_ROOT, "train")
VAL_DIR   = os.path.join(DATA_ROOT, "val")
TEST_DIR  = os.path.join(DATA_ROOT, "test")'''

for i, cell in enumerate(nb["cells"]):
    src = cell.get("source", "")
    if isinstance(src, list):
        src = "".join(src)
    if "DATA_ROOT" in src and "Kaggle dataset paths" in src:
        print(f"Found config cell at index {i}")
        lines = src.split("\n")
        new_lines = []
        skip = False
        inserted = False
        for line in lines:
            if "Kaggle dataset paths" in line and not inserted:
                skip = True
                inserted = True
                new_lines.append(NEW_BLOCK)
                continue
            if skip:
                if line.startswith("DEVICE") or "DEVICE" in line:
                    skip = False
                    new_lines.append(line)
                continue
            new_lines.append(line)
        cell["source"] = "\n".join(new_lines)
        print("Replaced DATA_ROOT block")
        break

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("Saved!")
