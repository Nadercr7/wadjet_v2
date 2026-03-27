"""Fix training notebooks for Kaggle re-push.

Hieroglyph: flat file layout (train_*.tfrecord in root, not train/ subdir)
Landmark: add retry for weight download (DNS flakiness)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HIERO_NB = ROOT / "planning" / "model-rebuild" / "notebooks" / "hieroglyph" / "hieroglyph_classifier.ipynb"
LAND_NB = ROOT / "planning" / "model-rebuild" / "notebooks" / "landmark" / "landmark_classifier.ipynb"


def fix_hieroglyph():
    """Fix hieroglyph notebook for flat dataset layout."""
    with open(HIERO_NB, encoding="utf-8") as f:
        nb = json.load(f)

    # Fix Cell 1: Data paths — point all dirs to DATA_DIR (flat layout)
    cell1 = nb["cells"][1]
    cell1["source"][5] = '# Data paths — files are flat: train_*.tfrecord etc.\n'
    cell1["source"][7] = 'TRAIN_DIR = DATA_DIR  # flat layout: train_*.tfrecord in root\n'
    cell1["source"][8] = 'VAL_DIR = DATA_DIR    # flat layout: val_*.tfrecord in root\n'
    cell1["source"][9] = 'TEST_DIR = DATA_DIR   # flat layout: test_*.tfrecord in root\n'

    # Fix Cell 4: load_dataset — add split_prefix parameter for flat glob
    cell4 = nb["cells"][4]
    new_source = []
    for line in cell4["source"]:
        if "def load_dataset(split_dir" in line:
            line = 'def load_dataset(split_dir, batch_size=BATCH_SIZE, augment=False, shuffle=False, split_prefix=None):\n'
        elif '"""Load TFRecords from a split directory."""' in line:
            line = '    """Load TFRecords from a directory. If split_prefix given, glob split_prefix_*.tfrecord."""\n'
        elif 'files = sorted(glob.glob(os.path.join(split_dir,' in line:
            new_source.append('    pattern = f"{split_prefix}_*.tfrecord" if split_prefix else "*.tfrecord"\n')
            line = '    files = sorted(glob.glob(os.path.join(split_dir, pattern)))\n'
        new_source.append(line)
    cell4["source"] = new_source

    # Fix Cell 7 (or whichever has load_dataset calls) — add split_prefix args
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        if "train_ds = load_dataset(TRAIN_DIR" in src:
            cell["source"] = [
                line.replace(
                    "load_dataset(TRAIN_DIR, augment=True, shuffle=True)",
                    'load_dataset(TRAIN_DIR, augment=True, shuffle=True, split_prefix="train")',
                ).replace(
                    "load_dataset(VAL_DIR, augment=False, shuffle=False)",
                    'load_dataset(VAL_DIR, augment=False, shuffle=False, split_prefix="val")',
                ).replace(
                    "load_dataset(TEST_DIR, augment=False, shuffle=False)",
                    'load_dataset(TEST_DIR, augment=False, shuffle=False, split_prefix="test")',
                )
                for line in cell["source"]
            ]

    # Fix the class weight counting cell that also calls load_dataset
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        if "load_dataset(TRAIN_DIR, batch_size=512" in src:
            cell["source"] = [
                line.replace(
                    "load_dataset(TRAIN_DIR, batch_size=512, augment=False, shuffle=False)",
                    'load_dataset(TRAIN_DIR, batch_size=512, augment=False, shuffle=False, split_prefix="train")',
                )
                for line in cell["source"]
            ]

    # Also fix the data exploration cell that globs directly
    for cell in nb["cells"]:
        new_src = []
        for line in cell.get("source", []):
            if 'glob.glob(os.path.join(TRAIN_DIR, "*.tfrecord"))' in line:
                line = line.replace(
                    'glob.glob(os.path.join(TRAIN_DIR, "*.tfrecord"))',
                    'glob.glob(os.path.join(TRAIN_DIR, "train_*.tfrecord"))',
                )
            if 'glob.glob(os.path.join(VAL_DIR, "*.tfrecord"))' in line:
                line = line.replace(
                    'glob.glob(os.path.join(VAL_DIR, "*.tfrecord"))',
                    'glob.glob(os.path.join(VAL_DIR, "val_*.tfrecord"))',
                )
            if 'glob.glob(os.path.join(TEST_DIR, "*.tfrecord"))' in line:
                line = line.replace(
                    'glob.glob(os.path.join(TEST_DIR, "*.tfrecord"))',
                    'glob.glob(os.path.join(TEST_DIR, "test_*.tfrecord"))',
                )
            new_src.append(line)
        cell["source"] = new_src

    with open(HIERO_NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("✅ Hieroglyph notebook fixed (flat file layout)")


def fix_landmark():
    """Fix landmark notebook: add retry for weight download."""
    with open(LAND_NB, encoding="utf-8") as f:
        nb = json.load(f)

    # Find the cell with build_model that calls EfficientNetV2B0
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        if "def build_model(" in src and "EfficientNetV2B0" in src:
            # Wrap the backbone creation in a retry loop
            new_source = []
            for line in cell["source"]:
                if "def build_model(" in line:
                    # Add retry import and wrapper before the function
                    new_source.append("import time as _time\n")
                    new_source.append("\n")
                    new_source.append("def _retry_load(fn, retries=3, delay=10):\n")
                    new_source.append("    for attempt in range(retries):\n")
                    new_source.append("        try:\n")
                    new_source.append("            return fn()\n")
                    new_source.append("        except Exception as e:\n")
                    new_source.append('            print(f"  Attempt {attempt+1}/{retries} failed: {e}")\n')
                    new_source.append("            if attempt < retries - 1:\n")
                    new_source.append('                print(f"  Retrying in {delay}s...")\n')
                    new_source.append("                _time.sleep(delay)\n")
                    new_source.append("    raise RuntimeError(f'Failed after {retries} attempts')\n")
                    new_source.append("\n")
                new_source.append(line)
            cell["source"] = new_source
            break

    # Now wrap the actual EfficientNetV2B0 call in retry
    for cell in nb["cells"]:
        new_source = []
        for line in cell.get("source", []):
            if "tf.keras.applications.EfficientNetV2B0(" in line and "backbone = " in line:
                # Replace direct call with retry-wrapped call
                indent = line[:len(line) - len(line.lstrip())]
                new_source.append(f"{indent}backbone = _retry_load(lambda: tf.keras.applications.EfficientNetV2B0(\n")
                # Skip this line but we need to find the closing paren
                continue
            new_source.append(line)
        cell["source"] = new_source

    # Actually, that approach is fragile with multi-line calls. Let me use a simpler approach:
    # Just add a retry wrapper around the entire build_model call instead.
    # Revert the above and do it differently.

    # Re-read fresh
    with open(LAND_NB, encoding="utf-8") as f:
        nb = json.load(f)

    # Find the model build cell and add a pre-download retry step
    for i, cell in enumerate(nb["cells"]):
        src = "".join(cell.get("source", []))
        if "def build_model(" in src and "EfficientNetV2B0" in src:
            # Prepend a weight pre-download with retry before the function def
            retry_code = [
                "# Pre-download EfficientNetV2B0 weights with retry (Kaggle DNS can be flaky)\n",
                "import time as _time\n",
                "for _attempt in range(5):\n",
                "    try:\n",
                "        _test_backbone = tf.keras.applications.EfficientNetV2B0(\n",
                "            input_shape=(224, 224, 3), include_top=False, weights='imagenet'\n",
                "        )\n",
                "        del _test_backbone\n",
                '        print("✅ EfficientNetV2B0 weights downloaded successfully")\n',
                "        break\n",
                "    except Exception as _e:\n",
                '        print(f"  Weight download attempt {_attempt+1}/5 failed: {_e}")\n',
                "        if _attempt < 4:\n",
                '            print(f"  Retrying in 15s...")\n',
                "            _time.sleep(15)\n",
                "        else:\n",
                '            raise RuntimeError("Failed to download EfficientNetV2B0 weights after 5 attempts") from _e\n',
                "\n",
            ]
            cell["source"] = retry_code + cell["source"]
            break

    with open(LAND_NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("✅ Landmark notebook fixed (weight download retry)")


if __name__ == "__main__":
    fix_hieroglyph()
    fix_landmark()
    print("\nDone. Ready to re-push.")
