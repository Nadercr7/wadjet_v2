"""Fix notebook kernelspec for Kaggle compatibility, then re-push both kernels."""
import json
import os

NOTEBOOKS = [
    "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb",
    "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb",
]

KERNELSPEC = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3"
}

LANGUAGE_INFO = {
    "name": "python",
    "version": "3.10.0",
    "mimetype": "text/x-python",
    "codemirror_mode": {"name": "ipython", "version": 3},
    "pygments_lexer": "ipython3",
    "nbconvert_exporter": "python",
    "file_extension": ".py"
}

for nb_path in NOTEBOOKS:
    print(f"Fixing: {nb_path}")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    nb["metadata"]["kernelspec"] = KERNELSPEC
    nb["metadata"]["language_info"] = LANGUAGE_INFO

    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)

    print(f"  kernelspec added, {len(nb['cells'])} cells")

print("\nNow re-pushing...")

from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()

KERNEL_DIRS = [
    ("hieroglyph", "planning/model-rebuild/notebooks/hieroglyph"),
    ("landmark", "planning/model-rebuild/notebooks/landmark"),
]

for name, kdir in KERNEL_DIRS:
    print(f"\nPushing {name}...")
    result = api.kernels_push(kdir)
    error = getattr(result, "_error", None) or (result.get("error") if isinstance(result, dict) else None)
    ref = getattr(result, "_ref", "") or (result.get("ref", "") if isinstance(result, dict) else "")
    ver = getattr(result, "_version_number", None) or (result.get("versionNumber") if isinstance(result, dict) else None)

    if error:
        print(f"  ERROR: {error}")
    else:
        print(f"  OK — ref={ref}, version={ver}")
