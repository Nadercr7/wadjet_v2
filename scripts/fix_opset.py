"""
Fix v12 issues in both notebooks:
1. Cell 13: Change opset_version=17 to opset_version=18 (PyTorch 2.10 minimum)
2. Cell 14: Already loads ort after pip install fix — check LoadLibrary path
"""
import json

HIERO = r"planning\model-rebuild\pytorch\hieroglyph\hieroglyph_classifier.ipynb"
LAND  = r"planning\model-rebuild\pytorch\landmark\landmark_classifier.ipynb"


def fix_notebook(path, label):
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Fix 1: Cell 13 — change opset 17 to 18
    cell13 = nb["cells"][13]["source"]
    new_cell13 = []
    for line in cell13:
        new_cell13.append(
            line.replace("opset_version=17", "opset_version=18")
        )
    nb["cells"][13]["source"] = new_cell13
    old13 = "".join(cell13)
    new13 = "".join(new_cell13)
    if old13 != new13:
        print(f"  Cell 13: opset_version 17 -> 18")
    else:
        print(f"  Cell 13: no change needed")

    # Fix 2: Check cell 16 metadata also mentions opset 17
    cell16 = nb["cells"][16]["source"]
    new_cell16 = []
    for line in cell16:
        new_cell16.append(
            line.replace('"opset_version": 17', '"opset_version": 18')
        )
    nb["cells"][16]["source"] = new_cell16
    old16 = "".join(cell16)
    new16 = "".join(new_cell16)
    if old16 != new16:
        print(f"  Cell 16: metadata opset 17 -> 18")
    else:
        print(f"  Cell 16: no change needed")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"  Written: {path}")


print("=== HIEROGLYPH ===")
fix_notebook(HIERO, "HIEROGLYPH")
print("\n=== LANDMARK ===")
fix_notebook(LAND, "LANDMARK")
print("\nDone!")
