"""Rewrite Cell 4 of the detector notebook with deep recursive dataset discovery."""
import json

nb_path = r"planning/model-rebuild/pytorch/detector/hieroglyph_detector.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

new_source = r'''# Cell 4: Auto-discover dataset path (deep recursive Kaggle search)
# The uploaded dataset may be nested or zipped inside Kaggle input.

DATA_ROOT = None
YAML_PATH = None

# Deep listing of /kaggle/input for debugging
print("=== Kaggle /kaggle/input/ deep listing (max 4 levels) ===", flush=True)
for root, dirs, files in os.walk("/kaggle/input"):
    depth = root.replace("/kaggle/input", "").count(os.sep)
    if depth > 4:
        continue
    indent = "  " * depth
    print(f"{indent}{os.path.basename(root)}/", flush=True)
    subindent = "  " * (depth + 1)
    for fname in files[:10]:
        fpath = os.path.join(root, fname)
        sz = os.path.getsize(fpath)
        print(f"{subindent}{fname} ({sz} bytes)", flush=True)
    if len(files) > 10:
        print(f"{subindent}... and {len(files)-10} more files", flush=True)
print("=== End listing ===", flush=True)

# Strategy: walk ALL of /kaggle/input looking for images/ + labels/ or data.yaml
for root, dirs, files in os.walk("/kaggle/input"):
    if "images" in dirs and "labels" in dirs:
        # Check if images/train exists
        img_train = os.path.join(root, "images", "train")
        if os.path.isdir(img_train):
            DATA_ROOT = root
            if "data.yaml" in files:
                YAML_PATH = os.path.join(root, "data.yaml")
            break
    elif "data.yaml" in files and "images" in dirs:
        DATA_ROOT = root
        YAML_PATH = os.path.join(root, "data.yaml")
        break

# If still not found, look for zip files to extract
if DATA_ROOT is None:
    print("No direct dataset found. Searching for zip files...", flush=True)
    for root, dirs, files in os.walk("/kaggle/input"):
        for fname in files:
            if fname.endswith(".zip"):
                zip_path = os.path.join(root, fname)
                extract_dir = os.path.join(OUTPUT_DIR, "dataset")
                print(f"Found zip: {zip_path} ({os.path.getsize(zip_path)} bytes)", flush=True)
                print(f"Extracting to {extract_dir}...", flush=True)
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_dir)
                print("Extraction complete. Searching...", flush=True)
                for r2, d2, f2 in os.walk(extract_dir):
                    if "images" in d2 and "labels" in d2:
                        img_train = os.path.join(r2, "images", "train")
                        if os.path.isdir(img_train):
                            DATA_ROOT = r2
                            if "data.yaml" in f2:
                                YAML_PATH = os.path.join(r2, "data.yaml")
                            break
                if DATA_ROOT:
                    break
        if DATA_ROOT:
            break

# If we found DATA_ROOT but no YAML, search for data.yaml anywhere
if DATA_ROOT is not None and YAML_PATH is None:
    for root, dirs, files in os.walk("/kaggle/input"):
        if "data.yaml" in files:
            YAML_PATH = os.path.join(root, "data.yaml")
            break
    if YAML_PATH is None:
        # Check extracted dir too
        extracted = os.path.join(OUTPUT_DIR, "dataset")
        if os.path.isdir(extracted):
            for root, dirs, files in os.walk(extracted):
                if "data.yaml" in files:
                    YAML_PATH = os.path.join(root, "data.yaml")
                    break

# If STILL no YAML, create one
if DATA_ROOT is not None and YAML_PATH is None:
    print("No data.yaml found, creating one...", flush=True)
    YAML_PATH = os.path.join(OUTPUT_DIR, "data.yaml")
    import yaml
    yaml_content = {
        "path": DATA_ROOT,
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 1,
        "names": ["hieroglyph"]
    }
    with open(YAML_PATH, "w") as f:
        yaml.dump(yaml_content, f)

if DATA_ROOT is None:
    raise FileNotFoundError("Could not find dataset with images/ dir under /kaggle/input/")

print(f"\nDATA_ROOT: {DATA_ROOT}", flush=True)
print(f"YAML_PATH: {YAML_PATH}", flush=True)
print(f"Contents:  {os.listdir(DATA_ROOT)}", flush=True)
'''

# Convert to list of lines for notebook format
lines = new_source.split('\n')
source_lines = [line + '\n' for line in lines[:-1]]  # all but last empty
if lines[-1]:  # if last line not empty
    source_lines.append(lines[-1])

nb['cells'][4]['source'] = source_lines

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Cell 4 rewritten with {len(source_lines)} lines")
