"""Show full source of specific cells in both notebooks."""
import json, sys

cells_to_show = [2, 3, 5]  # Install&Import, GPU verification, Dataset Stats

for name, path in [
    ("HIEROGLYPH", "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"),
    ("LANDMARK", "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb"),
]:
    nb = json.load(open(path, encoding="utf-8"))
    print(f"\n{'='*60}")
    print(f" {name}")
    print(f"{'='*60}")
    for ci in cells_to_show:
        if ci < len(nb["cells"]):
            src = "".join(nb["cells"][ci].get("source", []))
            print(f"\n--- Cell {ci} ---")
            print(src[:500])
            if len(src) > 500:
                print(f"  ... ({len(src)} chars total)")
