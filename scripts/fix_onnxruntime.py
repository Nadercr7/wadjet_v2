"""Add onnxruntime to pip install cell in both notebooks."""
import json

HIERO = r"planning\model-rebuild\pytorch\hieroglyph\hieroglyph_classifier.ipynb"
LAND  = r"planning\model-rebuild\pytorch\landmark\landmark_classifier.ipynb"

NEW_CELL1 = [
    "# lightning is pre-installed on Kaggle as pytorch_lightning\n",
    "# onnxscript is needed by PyTorch 2.10+ for torch.onnx.export\n",
    "# onnxruntime is needed for ONNX validation and quantization\n",
    "import subprocess, sys\n",
    "subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'onnxscript', 'onnxruntime'])",
]

for path, label in [(HIERO, "HIEROGLYPH"), (LAND, "LANDMARK")]:
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    nb["cells"][1]["source"] = NEW_CELL1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"{label}: Cell 1 updated with onnxruntime install")

print("Done!")
