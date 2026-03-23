"""Show second line of each cell (the title comment) for both notebooks."""
import json

for name, path in [
    ("HIEROGLYPH", "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"),
    ("LANDMARK", "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb"),
]:
    nb = json.load(open(path, encoding="utf-8"))
    print(f"\n=== {name} ({len(nb['cells'])} cells) ===")
    for i, c in enumerate(nb["cells"]):
        lines = "".join(c.get("source", [])).split("\n")
        # Get first meaningful line (skip empty/separator lines)
        title = ""
        for ln in lines:
            ln = ln.strip()
            if ln and not ln.startswith("# ==="):
                title = ln[:100]
                break
        print(f"  Cell {i:2d} [{c['cell_type']:8s}]: {title}")
