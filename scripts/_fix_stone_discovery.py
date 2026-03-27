"""Fix stone texture discovery in classifier v2 notebook."""
import json

path = "planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier_v2.ipynb"
with open(path) as f:
    nb = json.load(f)

cell = nb["cells"][4]  # Config & data discovery cell
src = "".join(cell["source"])

# Find the stone discovery section and replace it
old_marker = "# Auto-discover stone textures\nSTONE_DIR = None\nfor name in os.listdir"
idx = src.find(old_marker)
if idx < 0:
    print("ERROR: Could not find stone discovery section")
    # Debug: show nearby text
    idx2 = src.find("stone texture")
    if idx2 >= 0:
        print(f"Found 'stone texture' at {idx2}")
        print(repr(src[idx2:idx2+500]))
    exit(1)

# Find the end of the stone discovery block (the print statements after)
end_marker = 'print(f"DATA_ROOT:  {DATA_ROOT}")'
end_idx = src.find(end_marker)
if end_idx < 0:
    print("ERROR: Could not find end marker")
    exit(1)

old_block = src[idx:end_idx]

new_block = """# Auto-discover stone textures (search all levels + extract zips)
STONE_DIR = None
for root, dirs, files in os.walk("/kaggle/input"):
    depth = root.replace("/kaggle/input", "").count(os.sep)
    if depth > 4:
        dirs.clear()
        continue
    stone_files = [f for f in files if f.startswith("stone_") and f.endswith((".jpg", ".png"))]
    if len(stone_files) > 50:
        STONE_DIR = root
        break
    # Check for zips containing stone textures
    for f in files:
        if f.endswith(".zip") and "stone" in f.lower():
            import zipfile as _zf
            zpath = os.path.join(root, f)
            extract_to = "/kaggle/working/stone_textures"
            os.makedirs(extract_to, exist_ok=True)
            with _zf.ZipFile(zpath, "r") as zf:
                zf.extractall(extract_to)
            stone_extracted = [x for x in os.listdir(extract_to) if x.startswith("stone_") and x.endswith((".jpg", ".png"))]
            if len(stone_extracted) > 50:
                STONE_DIR = extract_to
                break
    if STONE_DIR:
        break

"""

src = src[:idx] + new_block + src[end_idx:]
cell["source"] = [src]

with open(path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Fixed stone texture discovery in {path}")
