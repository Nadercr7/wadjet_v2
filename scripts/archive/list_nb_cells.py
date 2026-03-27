"""List cells in both training notebooks."""
import json

for name, path in [
    ("HIEROGLYPH", "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"),
    ("LANDMARK", "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb"),
]:
    nb = json.load(open(path, encoding="utf-8"))
    print(f"\n=== {name} ({len(nb['cells'])} cells) ===")
    for i, c in enumerate(nb["cells"]):
        src = "".join(c.get("source", []))
        first_line = src.split("\n")[0][:100]
        print(f"  Cell {i} [{c['cell_type']}]: {first_line}")
