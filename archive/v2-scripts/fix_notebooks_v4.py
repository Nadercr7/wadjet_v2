"""Fix both training notebooks for no-internet Kaggle GPU (v4).

ROOT CAUSES from v3 logs:
1. Dataset path: /kaggle/input/datasets/naderelakany/<name> (not /kaggle/input/<name>)
2. Internet is persistently DOWN — pip install fails, weight downloads fail
3. tf2onnx is NOT pre-installed on Kaggle GPU image

SOLUTION:
- Auto-detect dataset path at runtime
- Remove all pip install calls (tf2onnx, onnxruntime)
- Save as SavedModel + Keras (skip ONNX export in notebook, do it locally)
- For landmark: skip pre-download retry, use weights cached in image or random init
- Keep enable_internet: true (Kaggle requires it for some GPU pods)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HIERO_NB = ROOT / "planning" / "model-rebuild" / "notebooks" / "hieroglyph" / "hieroglyph_classifier.ipynb"
LAND_NB  = ROOT / "planning" / "model-rebuild" / "notebooks" / "landmark"   / "landmark_classifier.ipynb"


def make_auto_detect_data_cell(dataset_slug, expected_files_prefix="train"):
    """Create a cell that auto-detects the dataset path."""
    return [
        "# ============================================================\n",
        "# Auto-Detect Dataset Path\n",
        "# ============================================================\n",
        "import os, glob\n",
        "\n",
        f"DATASET_SLUG = \"{dataset_slug}\"\n",
        "\n",
        "def find_dataset(slug):\n",
        "    \"\"\"Search /kaggle/input for the dataset, handling nested paths.\"\"\"\n",
        "    candidates = [\n",
        "        f'/kaggle/input/{slug}',                           # Standard\n",
        "        f'/kaggle/input/datasets/naderelakany/{slug}',     # Cross-user\n",
        "    ]\n",
        "    # Also search recursively\n",
        "    for root, dirs, files in os.walk('/kaggle/input'):\n",
        "        if os.path.basename(root) == slug:\n",
        "            candidates.append(root)\n",
        "    \n",
        "    for path in candidates:\n",
        "        if os.path.isdir(path):\n",
        "            contents = os.listdir(path)\n",
        "            print(f'  Found: {path} ({len(contents)} items)')\n",
        "            for f in sorted(contents)[:5]:\n",
        "                print(f'    {f}')\n",
        "            return path\n",
        "    \n",
        "    # Last resort: list everything under /kaggle/input\n",
        "    print('ERROR: Dataset not found. Contents of /kaggle/input:')\n",
        "    for root, dirs, files in os.walk('/kaggle/input'):\n",
        "        level = root.replace('/kaggle/input', '').count(os.sep)\n",
        "        indent = '  ' * level\n",
        "        print(f'{indent}{os.path.basename(root)}/')\n",
        "        for f in files[:5]:\n",
        "            print(f'{indent}  {f}')\n",
        "    raise FileNotFoundError(f'Dataset {slug} not found in /kaggle/input')\n",
        "\n",
        "DATA_DIR = find_dataset(DATASET_SLUG)\n",
        "print(f'\\nDATA_DIR = {DATA_DIR}')\n",
    ]


def make_imports_cell_hiero():
    """Hieroglyph install+import cell — NO pip install."""
    return [
        "# ============================================================\n",
        "# Import (no pip install — use pre-installed packages only)\n",
        "# ============================================================\n",
        "import glob\n",
        "import json\n",
        "import math\n",
        "import os\n",
        "import numpy as np\n",
        "import tensorflow as tf\n",
        "import keras\n",
        "from pathlib import Path\n",
        "\n",
        "tf.random.set_seed(SEED)\n",
        "np.random.seed(SEED)\n",
        "\n",
        "# Check if tf2onnx is available (for ONNX export at end)\n",
        "try:\n",
        "    import tf2onnx\n",
        "    HAS_TF2ONNX = True\n",
        "    print(f'tf2onnx available: {tf2onnx.__version__}')\n",
        "except ImportError:\n",
        "    HAS_TF2ONNX = False\n",
        "    print('tf2onnx NOT available — will save SavedModel for local ONNX conversion')\n",
        "\n",
        "try:\n",
        "    import onnxruntime\n",
        "    HAS_ORT = True\n",
        "    print(f'onnxruntime available: {onnxruntime.__version__}')\n",
        "except ImportError:\n",
        "    HAS_ORT = False\n",
        "    print('onnxruntime NOT available — will skip ONNX validation')\n",
    ]


def make_imports_cell_landmark():
    """Landmark install+import cell — NO pip install."""
    return [
        "# ============================================================\n",
        "# Import (no pip install — use pre-installed packages only)\n",
        "# ============================================================\n",
        "import glob\n",
        "import json\n",
        "import math\n",
        "import os\n",
        "import numpy as np\n",
        "import tensorflow as tf\n",
        "from pathlib import Path\n",
        "\n",
        "tf.random.set_seed(SEED)\n",
        "np.random.seed(SEED)\n",
        "\n",
        "try:\n",
        "    import tf2onnx\n",
        "    HAS_TF2ONNX = True\n",
        "    print(f'tf2onnx available: {tf2onnx.__version__}')\n",
        "except ImportError:\n",
        "    HAS_TF2ONNX = False\n",
        "    print('tf2onnx NOT available — will save SavedModel for local conversion')\n",
        "\n",
        "try:\n",
        "    import onnxruntime\n",
        "    HAS_ORT = True\n",
        "    print(f'onnxruntime available: {onnxruntime.__version__}')\n",
        "except ImportError:\n",
        "    HAS_ORT = False\n",
        "    print('onnxruntime NOT available — will skip ONNX validation')\n",
    ]


def make_onnx_export_cell(model_name, float_path_var, uint8_path_var):
    """ONNX export cell that falls back to SavedModel if tf2onnx unavailable."""
    return [
        "# ============================================================\n",
        "# ONNX Export (or SavedModel fallback)\n",
        "# ============================================================\n",
        f"SAVEDMODEL_PATH = os.path.join(OUTPUT_DIR, '{model_name}_savedmodel')\n",
        "\n",
        "if HAS_TF2ONNX:\n",
        f"    print('Exporting to ONNX via tf2onnx...')\n",
        f"    spec = (tf.TensorSpec((None, IMAGE_SIZE, IMAGE_SIZE, 3), tf.float32, name='input'),)\n",
        f"    model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)\n",
        f"    with open({float_path_var}, 'wb') as f:\n",
        f"        f.write(model_proto.SerializeToString())\n",
        f"    print(f'  Saved ONNX float32: {{{float_path_var}}}')\n",
        f"    print(f'  Size: {{os.path.getsize({float_path_var}) / 1024 / 1024:.1f}} MB')\n",
        "else:\n",
        "    print('tf2onnx not available. Saving as SavedModel for local conversion...')\n",
        f"    tf.saved_model.save(model, SAVEDMODEL_PATH)\n",
        f"    print(f'  Saved: {{SAVEDMODEL_PATH}}')\n",
        "    # Also save as .keras\n",
        f"    model.save(BEST_MODEL_PATH)\n",
        f"    print(f'  Saved .keras: {{BEST_MODEL_PATH}}')\n",
    ]


def make_onnx_quant_cell(float_path_var, uint8_path_var):
    """ONNX quantization cell that skips if onnxruntime unavailable."""
    return [
        "# ============================================================\n",
        "# ONNX uint8 Quantization (skip if unavailable)\n",
        "# ============================================================\n",
        "if HAS_TF2ONNX and HAS_ORT:\n",
        f"    from onnxruntime.quantization import quantize_dynamic, QuantType\n",
        f"    quantize_dynamic({float_path_var}, {uint8_path_var}, weight_type=QuantType.QUInt8)\n",
        f"    print(f'  Quantized ONNX: {{{uint8_path_var}}}')\n",
        f"    print(f'  Size: {{os.path.getsize({uint8_path_var}) / 1024 / 1024:.1f}} MB')\n",
        "else:\n",
        "    print('Skipping ONNX quantization (tf2onnx/onnxruntime not available)')\n",
        "    print('Will do ONNX conversion + quantization locally after download.')\n",
    ]


def make_validate_cell(uint8_path_var):
    """ONNX validation cell that skips gracefully."""
    return [
        "# ============================================================\n",
        "# Validate ONNX Model (skip if unavailable)\n",
        "# ============================================================\n",
        "if HAS_ORT and HAS_TF2ONNX:\n",
        f"    import onnxruntime as ort\n",
        f"    session = ort.InferenceSession({uint8_path_var}, providers=['CPUExecutionProvider'])\n",
        f"    input_meta = session.get_inputs()[0]\n",
        f"    output_meta = session.get_outputs()[0]\n",
        f"    print(f'Input:  {{input_meta.name}} shape={{input_meta.shape}} dtype={{input_meta.type}}')\n",
        f"    print(f'Output: {{output_meta.name}} shape={{output_meta.shape}} dtype={{output_meta.type}}')\n",
        f"    \n",
        f"    dummy = np.random.rand(1, IMAGE_SIZE, IMAGE_SIZE, 3).astype(np.float32)\n",
        f"    out = session.run(None, {{input_meta.name: dummy}})\n",
        f"    print(f'Test output shape: {{out[0].shape}}, sum: {{out[0].sum():.4f}}')\n",
        f"    print('✅ ONNX model validated successfully')\n",
        "else:\n",
        "    print('Skipping ONNX validation (packages not available)')\n",
    ]


def fix_hieroglyph():
    """Fix hieroglyph notebook for no-internet Kaggle."""
    with open(HIERO_NB, encoding="utf-8") as f:
        nb = json.load(f)

    cells = nb["cells"]
    print(f"  Original: {len(cells)} cells")

    # Find key cells by their title comments
    cell_map = {}
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        for key in ["Dataset Mount Diagnostic", "Configuration", "Install & Import",
                     "GPU + float32", "TFRecord Parsing", "Dataset Statistics",
                     "ONNX Export", "ONNX uint8 Quantization", "Validate ONNX"]:
            if key in src:
                cell_map[key] = i
                break

    print(f"  Cell map: {cell_map}")

    # 1. Replace diagnostic cell with auto-detect cell
    diag_idx = cell_map.get("Dataset Mount Diagnostic")
    if diag_idx is not None:
        cells[diag_idx]["source"] = make_auto_detect_data_cell("wadjet-hieroglyph-tfrecords")
        print("  Replaced diagnostic cell → auto-detect dataset")

    # 2. Fix Configuration cell: use DATA_DIR from auto-detect (remove hardcoded path)
    config_idx = cell_map.get("Configuration")
    if config_idx is not None:
        new_src = []
        for line in cells[config_idx]["source"]:
            if 'DATA_DIR = ' in line and '/kaggle/' in line:
                new_src.append('# DATA_DIR set by auto-detect cell above\n')
            elif line.strip().startswith('TRAIN_DIR') or line.strip().startswith('VAL_DIR') or line.strip().startswith('TEST_DIR'):
                new_src.append(line)  # Keep these
            else:
                new_src.append(line)
        cells[config_idx]["source"] = new_src
        print("  Fixed Configuration cell (DATA_DIR from auto-detect)")

    # 3. Replace Install & Import cell
    install_idx = cell_map.get("Install & Import")
    if install_idx is not None:
        cells[install_idx]["source"] = make_imports_cell_hiero()
        print("  Replaced Install cell (no pip install)")

    # 4. Replace ONNX Export cell
    onnx_idx = cell_map.get("ONNX Export")
    if onnx_idx is not None:
        cells[onnx_idx]["source"] = make_onnx_export_cell(
            "hieroglyph_classifier", "ONNX_FLOAT_PATH", "ONNX_UINT8_PATH"
        )
        print("  Replaced ONNX Export cell (SavedModel fallback)")

    # 5. Replace ONNX Quantization cell
    quant_idx = cell_map.get("ONNX uint8 Quantization")
    if quant_idx is not None:
        cells[quant_idx]["source"] = make_onnx_quant_cell("ONNX_FLOAT_PATH", "ONNX_UINT8_PATH")
        print("  Replaced ONNX Quantization cell (conditional)")

    # 6. Replace Validate cell
    val_idx = cell_map.get("Validate ONNX")
    if val_idx is not None:
        cells[val_idx]["source"] = make_validate_cell("ONNX_UINT8_PATH")
        print("  Replaced Validate cell (conditional)")

    # Ensure all cells have IDs (fixes nbformat warning)
    import uuid
    for c in cells:
        if "id" not in c:
            c["id"] = str(uuid.uuid4())[:8]

    with open(HIERO_NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("  ✅ Hieroglyph notebook saved")


def fix_landmark():
    """Fix landmark notebook for no-internet Kaggle."""
    with open(LAND_NB, encoding="utf-8") as f:
        nb = json.load(f)

    cells = nb["cells"]
    print(f"  Original: {len(cells)} cells")

    cell_map = {}
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        for key in ["Dataset Mount Diagnostic", "Configuration", "Install & Import",
                     "GPU + float32", "Pre-download EfficientNetV2B0",
                     "ONNX Export", "ONNX uint8 Quantization", "Validate ONNX"]:
            if key in src:
                cell_map[key] = i
                break

    print(f"  Cell map: {cell_map}")

    # 1. Replace diagnostic cell with auto-detect
    diag_idx = cell_map.get("Dataset Mount Diagnostic")
    if diag_idx is not None:
        cells[diag_idx]["source"] = make_auto_detect_data_cell("wadjet-tfrecords")
        print("  Replaced diagnostic cell → auto-detect dataset")

    # 2. Fix Configuration cell
    config_idx = cell_map.get("Configuration")
    if config_idx is not None:
        new_src = []
        for line in cells[config_idx]["source"]:
            if 'DATA_DIR = ' in line and '/kaggle/' in line:
                new_src.append('# DATA_DIR set by auto-detect cell above\n')
            else:
                new_src.append(line)
        cells[config_idx]["source"] = new_src
        print("  Fixed Configuration cell (DATA_DIR from auto-detect)")

    # 3. Replace Install cell
    install_idx = cell_map.get("Install & Import")
    if install_idx is not None:
        cells[install_idx]["source"] = make_imports_cell_landmark()
        print("  Replaced Install cell (no pip install)")

    # 4. Replace pre-download retry cell with simpler version
    retry_idx = cell_map.get("Pre-download EfficientNetV2B0")
    if retry_idx is not None:
        cells[retry_idx]["source"] = [
            "# ============================================================\n",
            "# Pre-load EfficientNetV2B0 backbone (use cached or random init)\n",
            "# ============================================================\n",
            "try:\n",
            "    _test = tf.keras.applications.EfficientNetV2B0(\n",
            "        input_shape=(224, 224, 3), include_top=False, weights='imagenet'\n",
            "    )\n",
            "    del _test\n",
            "    print('✅ EfficientNetV2B0 ImageNet weights loaded (cached)')\n",
            "    USE_PRETRAINED = True\n",
            "except Exception as e:\n",
            "    print(f'⚠ Could not load ImageNet weights: {e}')\n",
            "    print('  Will use random initialization (training from scratch)')\n",
            "    USE_PRETRAINED = False\n",
        ]
        print("  Replaced pre-download cell (cached or random init)")

    # 5. Fix build_model to handle no pretrained weights
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        if "def build_model(" in src and "EfficientNetV2B0" in src:
            new_source = []
            for line in c["source"]:
                if "weights='imagenet'" in line or 'weights="imagenet"' in line:
                    line = line.replace("weights='imagenet'", "weights='imagenet' if USE_PRETRAINED else None")
                    line = line.replace('weights="imagenet"', "weights='imagenet' if USE_PRETRAINED else None")
                new_source.append(line)
            c["source"] = new_source
            print(f"  Fixed build_model cell {i} (conditional weights)")
            break

    # 6. Replace ONNX export cell
    onnx_idx = cell_map.get("ONNX Export")
    if onnx_idx is not None:
        cells[onnx_idx]["source"] = make_onnx_export_cell(
            "landmark_classifier", "ONNX_FLOAT_PATH", "ONNX_UINT8_PATH"
        )
        print("  Replaced ONNX Export cell (SavedModel fallback)")

    # 7. Replace ONNX quantization cell
    quant_idx = cell_map.get("ONNX uint8 Quantization")
    if quant_idx is not None:
        cells[quant_idx]["source"] = make_onnx_quant_cell("ONNX_FLOAT_PATH", "ONNX_UINT8_PATH")
        print("  Replaced ONNX Quantization cell (conditional)")

    # 8. Check for separate validate cell or combined
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        if "Validate ONNX" in src:
            # Check if it's combined with save outputs
            if "Save" in src or "metadata" in src.lower():
                # Combined cell — add conditional check
                new_source = []
                in_onnx_section = False
                for line in c["source"]:
                    if "onnxruntime" in line or "ort.InferenceSession" in line:
                        if not in_onnx_section:
                            new_source.append("if HAS_ORT and HAS_TF2ONNX:\n")
                            in_onnx_section = True
                        new_source.append("    " + line)
                    elif in_onnx_section and line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                        in_onnx_section = False
                        new_source.append(line)
                    else:
                        if in_onnx_section:
                            new_source.append("    " + line)
                        else:
                            new_source.append(line)
                c["source"] = new_source
                print(f"  Fixed combined Validate+Save cell {i}")
            else:
                c["source"] = make_validate_cell("ONNX_UINT8_PATH")
                print(f"  Replaced Validate cell {i}")
            break

    # Ensure all cells have IDs
    import uuid
    for c in cells:
        if "id" not in c:
            c["id"] = str(uuid.uuid4())[:8]

    with open(LAND_NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("  ✅ Landmark notebook saved")


if __name__ == "__main__":
    print("=== Fixing Hieroglyph Notebook ===")
    fix_hieroglyph()
    print("\n=== Fixing Landmark Notebook ===")
    fix_landmark()
    print("\nDone. Notebooks ready for v4 push.")
