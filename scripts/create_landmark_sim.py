"""
Create a simulation (dry-run) notebook for the landmark classifier.
Same structure as the real notebook but:
- Uses only 10 images per class (subset)
- Trains for 1 epoch per phase
- Tests all post-training cells (ONNX export, validation, quantization, metadata)
- Runs in ~2-3 minutes total
"""
import json
import copy

REAL_NB = r"planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb"
SIM_NB  = r"planning/model-rebuild/pytorch/landmark/landmark_sim.ipynb"

with open(REAL_NB, "r", encoding="utf-8") as f:
    nb = json.load(f)

sim = copy.deepcopy(nb)

# ── Cell 0: Update title ──
sim["cells"][0]["source"] = [
    "# Wadjet — Landmark Classifier SIMULATION (Dry Run)\n",
    "\n",
    "**Purpose**: Quick dry-run to verify all cells execute without errors.\n",
    "Uses 10 images/class, 1 epoch/phase. Accuracy will be garbage — that's fine.\n",
    "\n",
    "Same architecture and pipeline as the real notebook:\n",
    "- EfficientNet-B0 (timm) → 52 classes\n",
    "- [1, 3, 224, 224] NCHW float32, values in [0.0, 1.0]\n",
    "- 2-phase training → ONNX export → quantization → metadata\n",
]

# ── Cell 3: Override config — 1 epoch, small batch ──
sim["cells"][3]["source"] = [
    "# ── Configuration (SIMULATION — tiny settings) ──────────────────\n",
    "INPUT_SIZE = 224\n",
    "NUM_CLASSES = 52\n",
    "BATCH_SIZE = 8         # Small batch for simulation\n",
    "NUM_WORKERS = 2\n",
    "\n",
    "# SIMULATION: 1 epoch each to test pipeline, not accuracy\n",
    "P1_EPOCHS = 1\n",
    "P1_LR = 1e-3\n",
    "P2_EPOCHS = 1\n",
    "P2_LR = 5e-5\n",
    "\n",
    "LABEL_SMOOTHING = 0.1\n",
    "\n",
    "# Kaggle dataset paths — auto-discover mount point\n",
    'OUT_DIR   = "/kaggle/working"\n',
    "\n",
    "# Discover the actual dataset mount path\n",
    'print("\\n── /kaggle/input/ contents ──")\n',
    'for name in sorted(os.listdir("/kaggle/input")):\n',
    '    full = os.path.join("/kaggle/input", name)\n',
    '    tag = "DIR" if os.path.isdir(full) else "FILE"\n',
    '    print(f"  {tag}: {name}")\n',
    "\n",
    "# Search for train directory\n",
    "DATA_ROOT = None\n",
    'for name in os.listdir("/kaggle/input"):\n',
    '    candidate = os.path.join("/kaggle/input", name)\n',
    "    if os.path.isdir(candidate):\n",
    "        children = os.listdir(candidate)\n",
    '        if "train" in children:\n',
    "            DATA_ROOT = candidate\n",
    "            break\n",
    "        for child in children:\n",
    "            sub = os.path.join(candidate, child)\n",
    '            if os.path.isdir(sub) and "train" in os.listdir(sub):\n',
    "                DATA_ROOT = sub\n",
    "                break\n",
    "        if DATA_ROOT:\n",
    "            break\n",
    "\n",
    "if DATA_ROOT is None:\n",
    '    for root, dirs, files in os.walk("/kaggle/input"):\n',
    '        if "train" in dirs and "val" in dirs:\n',
    "            DATA_ROOT = root\n",
    "            break\n",
    "\n",
    "if DATA_ROOT is None:\n",
    '    raise FileNotFoundError("Could not find train/val/test dirs under /kaggle/input/")\n',
    'print(f"\\nDATA_ROOT = {DATA_ROOT}")\n',
    'print(f"Contents: {sorted(os.listdir(DATA_ROOT))}")\n',
    "\n",
    'TRAIN_DIR = os.path.join(DATA_ROOT, "train")\n',
    'VAL_DIR   = os.path.join(DATA_ROOT, "val")\n',
    'TEST_DIR  = os.path.join(DATA_ROOT, "test")\n',
    'DEVICE = "cuda" if torch.cuda.is_available() else "cpu"\n',
    'print(f"Device: {DEVICE}")\n',
    'print(f"\\n** SIMULATION MODE: 1 epoch, 10 imgs/class **")\n',
]

# ── Cell 6: Subset the datasets after loading ──
sim["cells"][6]["source"] = [
    "# ── Datasets & DataLoaders (SIMULATION — 10 imgs/class) ─────────\n",
    "train_ds = ImageFolder(TRAIN_DIR, transform=train_transform)\n",
    "val_ds   = ImageFolder(VAL_DIR,   transform=val_transform)\n",
    "test_ds  = ImageFolder(TEST_DIR,  transform=val_transform)\n",
    "\n",
    "# Safety: remap val/test to use train's class_to_idx\n",
    "for ds, name in [(val_ds, 'val'), (test_ds, 'test')]:\n",
    "    old_classes = ds.classes\n",
    "    if set(old_classes) != set(train_ds.classes):\n",
    "        missing = set(train_ds.classes) - set(old_classes)\n",
    '        print(f"  {name}: remapping {len(old_classes)} -> {len(train_ds.classes)} classes (missing: {sorted(missing)})")\n',
    "    ds.class_to_idx = train_ds.class_to_idx\n",
    "    ds.classes = train_ds.classes\n",
    "    new_samples = []\n",
    "    for path, _old_idx in ds.samples:\n",
    "        class_name = os.path.basename(os.path.dirname(path))\n",
    "        new_idx = train_ds.class_to_idx.get(class_name)\n",
    "        if new_idx is not None:\n",
    "            new_samples.append((path, new_idx))\n",
    "    ds.samples = new_samples\n",
    "    ds.targets = [s[1] for s in new_samples]\n",
    "    ds.imgs = new_samples\n",
    "\n",
    "# ── SIMULATION: Subset to 10 images per class ──\n",
    "MAX_PER_CLASS = 10\n",
    "for ds, name in [(train_ds, 'train'), (val_ds, 'val'), (test_ds, 'test')]:\n",
    "    from collections import defaultdict\n",
    "    by_class = defaultdict(list)\n",
    "    for path, label in ds.samples:\n",
    "        by_class[label].append((path, label))\n",
    "    subset = []\n",
    "    for label, items in by_class.items():\n",
    "        subset.extend(items[:MAX_PER_CLASS])\n",
    "    ds.samples = subset\n",
    "    ds.targets = [s[1] for s in subset]\n",
    "    ds.imgs = subset\n",
    '    print(f"  {name}: subset to {len(subset)} images")\n',
    "\n",
    "train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,\n",
    "                          num_workers=NUM_WORKERS, pin_memory=True, drop_last=True)\n",
    "val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,\n",
    "                          num_workers=NUM_WORKERS, pin_memory=True)\n",
    "test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,\n",
    "                          num_workers=NUM_WORKERS, pin_memory=True)\n",
    "\n",
    "class_names = train_ds.classes\n",
    'assert len(class_names) == NUM_CLASSES, f"Expected {NUM_CLASSES} classes, got {len(class_names)}"\n',
    "\n",
    'print(f"\\nTrain: {len(train_ds):,} images, {len(class_names)} classes")\n',
    'print(f"Val:   {len(val_ds):,} images")\n',
    'print(f"Test:  {len(test_ds):,} images")\n',
    "\n",
    "sample, label = train_ds[0]\n",
    'print(f"\\nSample tensor: shape={sample.shape}, min={sample.min():.3f}, max={sample.max():.3f}")\n',
    'assert sample.shape == (3, INPUT_SIZE, INPUT_SIZE), f"Wrong shape: {sample.shape}"\n',
    'assert sample.min() >= 0.0 and sample.max() <= 1.0, f"Values must be in [0,1]!"\n',
    'print("Tensor assertions passed")\n',
]

# ── Cell 12: Lower gate threshold for simulation ──
# Replace "PASS" threshold — in sim we don't care about accuracy
cell12_src = "".join(sim["cells"][12]["source"])
cell12_src = cell12_src.replace("'PASS' if top1_acc >= 0.75 else 'BELOW 75% GATE'", "'SIM (accuracy irrelevant)'")
sim["cells"][12]["source"] = [l + "\n" if i < len(cell12_src.split("\n")) - 1 else l for i, l in enumerate(cell12_src.split("\n"))]

# ── Cell 15: Remove 8MB size assertion for sim ──
cell15_src = "".join(sim["cells"][15]["source"])
# EfficientNet-B0 quantized may be >8MB for landmarks, remove assertion for sim
cell15_src = cell15_src.replace(
    'assert uint8_size_mb <= 8.0, f"Model too large for browser: {uint8_size_mb:.1f} MB > 8 MB"',
    '# Size check skipped in simulation'
).replace(
    'print(f"Size check: {uint8_size_mb:.1f} MB ≤ 8 MB ✅")',
    'print(f"Size: {uint8_size_mb:.1f} MB (size check skipped in simulation)")'
)
sim["cells"][15]["source"] = [l + "\n" if i < len(cell15_src.split("\n")) - 1 else l for i, l in enumerate(cell15_src.split("\n"))]

# ── Cell 16: Add SIMULATION marker to final output ──
cell16_src = "".join(sim["cells"][16]["source"])
cell16_src = cell16_src.replace("TRAINING COMPLETE", "SIMULATION COMPLETE (dry-run)")
cell16_src = cell16_src.replace(
    "'PASS' if top1_acc >= 0.75 else 'FAIL'",
    "'SIM OK'"
)
sim["cells"][16]["source"] = [l + "\n" if i < len(cell16_src.split("\n")) - 1 else l for i, l in enumerate(cell16_src.split("\n"))]

with open(SIM_NB, "w", encoding="utf-8") as f:
    json.dump(sim, f, indent=1, ensure_ascii=False)

print(f"Simulation notebook created: {SIM_NB}")
print("Changes from real notebook:")
print("  Cell 0:  Title → 'SIMULATION (Dry Run)'")
print("  Cell 3:  P1_EPOCHS=1, P2_EPOCHS=1, BATCH_SIZE=8")
print("  Cell 6:  Subset datasets to 10 images/class")
print("  Cell 12: Gate check disabled (accuracy irrelevant)")
print("  Cell 15: Size assertion removed")
print("  Cell 16: Output says 'SIMULATION COMPLETE'")
print("All other cells (1,2,4,5,7,8,9,10,11,13,14) are IDENTICAL to real notebook")
