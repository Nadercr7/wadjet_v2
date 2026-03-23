"""Final verification of all fixes in both notebooks."""
import json

HIERO = r"planning\model-rebuild\pytorch\hieroglyph\hieroglyph_classifier.ipynb"
LAND  = r"planning\model-rebuild\pytorch\landmark\landmark_classifier.ipynb"


def verify(path, label):
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    print(f"=== {label} ===")

    c1 = "".join(nb["cells"][1]["source"])
    print(f"  Cell  1: onnxruntime install: {'YES' if 'onnxruntime' in c1 else 'NO'}")
    print(f"           onnxscript install:  {'YES' if 'onnxscript' in c1 else 'NO'}")

    c9 = "".join(nb["cells"][9]["source"])
    print(f"  Cell  9: KeepAliveCallback:   {'YES' if 'class KeepAliveCallback' in c9 else 'NO'}")

    for ci in [10, 11]:
        src = "".join(nb["cells"][ci]["source"])
        print(f"  Cell {ci}: KeepAliveCallback(): {'YES' if 'KeepAliveCallback()' in src else 'NO'}"
              f"  progress_bar=False: {'YES' if 'enable_progress_bar=False' in src else 'NO'}")

    c12 = "".join(nb["cells"][12]["source"])
    print(f"  Cell 12: labels= fix:         {'YES' if 'labels=' in c12 else 'NO'}")

    c13 = "".join(nb["cells"][13]["source"])
    print(f"  Cell 13: opset_version=18:    {'YES' if 'opset_version=18' in c13 else 'NO'}")
    print(f"           dynamo=False:        {'YES' if 'dynamo=False' in c13 else 'NO'}")
    print(f"           opset 17 leftover:   {'PROBLEM!' if 'opset_version=17' in c13 else 'CLEAN'}")


verify(HIERO, "HIEROGLYPH")
print()
verify(LAND, "LANDMARK")
