"""Fix both training notebooks for Kaggle re-push (v3).

Issues found in v2 run:
1. HIEROGLYPH: `pip install tf2onnx onnxruntime` fails when DNS is down
   -> Use conditional install, fall back to pre-installed versions
2. HIEROGLYPH: Dataset glob returns 0 files even after flat layout fix
   -> Add debug cell to list actual directory contents
3. LANDMARK: EfficientNetV2B0 weight download fails (DNS)
   -> Already has retry; just needs the pip fix too
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HIERO_NB = ROOT / "planning" / "model-rebuild" / "notebooks" / "hieroglyph" / "hieroglyph_classifier.ipynb"
LAND_NB = ROOT / "planning" / "model-rebuild" / "notebooks" / "landmark" / "landmark_classifier.ipynb"


def make_diagnostic_cell():
    """Create a diagnostic cell that lists dataset contents."""
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# ============================================================\n",
            "# Dataset Mount Diagnostic\n",
            "# ============================================================\n",
            "import os, subprocess\n",
            "\n",
            "# Check internet connectivity\n",
            "print('=== Network Check ===')\n",
            "ret = os.system('ping -c 1 -W 2 google.com > /dev/null 2>&1')\n",
            "print(f'Internet: {\"OK\" if ret == 0 else \"DOWN (DNS failure)\"}')\n",
            "\n",
            "# List /kaggle/input\n",
            "print('\\n=== /kaggle/input ===')\n",
            "if os.path.exists('/kaggle/input'):\n",
            "    for d in sorted(os.listdir('/kaggle/input')):\n",
            "        full = os.path.join('/kaggle/input', d)\n",
            "        if os.path.isdir(full):\n",
            "            files = os.listdir(full)\n",
            "            print(f'  {d}/ ({len(files)} items)')\n",
            "            for f in sorted(files)[:10]:\n",
            "                fpath = os.path.join(full, f)\n",
            "                if os.path.isdir(fpath):\n",
            "                    subfiles = os.listdir(fpath)\n",
            "                    print(f'    {f}/ ({len(subfiles)} items)')\n",
            "                    for sf in sorted(subfiles)[:5]:\n",
            "                        print(f'      {sf}')\n",
            "                else:\n",
            "                    sz = os.path.getsize(fpath)\n",
            "                    print(f'    {f} ({sz:,} bytes)')\n",
            "            if len(files) > 10:\n",
            "                print(f'    ... +{len(files)-10} more')\n",
            "        else:\n",
            "            print(f'  {d} (file)')\n",
            "else:\n",
            "    print('  /kaggle/input does NOT exist!')\n",
        ],
    }


def make_safe_pip_cell():
    """Create a safe pip install cell that handles DNS failures."""
    return [
        "# ============================================================\n",
        "# Install & Import\n",
        "# ============================================================\n",
        "# Conditional install — skip if DNS is down (packages may be pre-installed)\n",
        "import subprocess, sys\n",
        "\n",
        "def safe_install(*packages):\n",
        "    for pkg in packages:\n",
        "        try:\n",
        "            __import__(pkg.replace('-', '_'))\n",
        "            print(f'  {pkg}: already installed')\n",
        "        except ImportError:\n",
        "            print(f'  {pkg}: installing...')\n",
        "            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])\n",
        "\n",
        "safe_install('tf2onnx', 'onnxruntime')\n",
        "\n",
        "import glob\n",
        "import json\n",
        "import math\n",
        "import numpy as np\n",
        "import tensorflow as tf\n",
    ]


def fix_hieroglyph():
    """Fix hieroglyph notebook."""
    with open(HIERO_NB, encoding="utf-8") as f:
        nb = json.load(f)

    # Insert diagnostic cell after Cell 0 (markdown title)
    diag = make_diagnostic_cell()
    # Check if there's already a diagnostic cell
    cell1_src = "".join(nb["cells"][1].get("source", []))
    if "Dataset Mount Diagnostic" not in cell1_src:
        nb["cells"].insert(1, diag)
        print("  Inserted diagnostic cell at position 1")
        # Cell indices shift by 1 now
        config_idx = 2
        install_idx = 3
    else:
        print("  Diagnostic cell already present")
        config_idx = 2
        install_idx = 3

    # Fix Cell install_idx: Replace pip install with safe_install
    install_cell = nb["cells"][install_idx]
    old_src = "".join(install_cell.get("source", []))
    if "!pip install" in old_src:
        new_src = make_safe_pip_cell()
        # Keep keras import if present
        if "import keras" in old_src:
            new_src.append("import keras\n")
        new_src.append("from pathlib import Path\n")
        new_src.append("\n")
        new_src.append("tf.random.set_seed(SEED)\n")
        new_src.append("np.random.seed(SEED)\n")
        install_cell["source"] = new_src
        print("  Fixed Install & Import cell (safe_install)")

    with open(HIERO_NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("  ✅ Hieroglyph notebook saved")


def fix_landmark():
    """Fix landmark notebook."""
    with open(LAND_NB, encoding="utf-8") as f:
        nb = json.load(f)

    # Insert diagnostic cell after Cell 0
    cell1_src = "".join(nb["cells"][1].get("source", []))
    if "Dataset Mount Diagnostic" not in cell1_src:
        nb["cells"].insert(1, make_diagnostic_cell())
        print("  Inserted diagnostic cell at position 1")
        install_idx = 3
    else:
        print("  Diagnostic cell already present")
        install_idx = 3

    # Fix Install cell
    install_cell = nb["cells"][install_idx]
    old_src = "".join(install_cell.get("source", []))
    if "!pip install" in old_src:
        new_src = make_safe_pip_cell()
        new_src.append("from pathlib import Path\n")
        new_src.append("\n")
        new_src.append("tf.random.set_seed(SEED)\n")
        new_src.append("np.random.seed(SEED)\n")
        install_cell["source"] = new_src
        print("  Fixed Install & Import cell (safe_install)")

    with open(LAND_NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("  ✅ Landmark notebook saved")


if __name__ == "__main__":
    print("=== Fixing Hieroglyph ===")
    fix_hieroglyph()
    print("\n=== Fixing Landmark ===")
    fix_landmark()
    print("\nDone. Ready to re-push.")
