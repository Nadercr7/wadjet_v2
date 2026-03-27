"""Fix both notebooks: rewrite cell 2 (onnxscript install) and cell 7 (datasets) properly."""
import json, os

DATASETS_CELL_HIERO = """# ── Datasets & DataLoaders ───────────────────────────────────────
train_ds = ImageFolder(TRAIN_DIR, transform=train_transform)
val_ds   = ImageFolder(VAL_DIR,   transform=val_transform)
test_ds  = ImageFolder(TEST_DIR,  transform=val_transform)

# CRITICAL: val/test may have fewer classes than train (e.g. 167 vs 171).
# ImageFolder assigns class indices by sorting directory names independently,
# which causes LABEL MISALIGNMENT between splits.
# Fix: remap val/test to use train's class_to_idx.
for ds, name in [(val_ds, 'val'), (test_ds, 'test')]:
    old_classes = ds.classes
    if set(old_classes) != set(train_ds.classes):
        missing = set(train_ds.classes) - set(old_classes)
        print(f"  {name}: remapping {len(old_classes)} -> {len(train_ds.classes)} classes (missing: {sorted(missing)})")
    ds.class_to_idx = train_ds.class_to_idx
    ds.classes = train_ds.classes
    new_samples = []
    for path, _old_idx in ds.samples:
        class_name = os.path.basename(os.path.dirname(path))
        new_idx = train_ds.class_to_idx.get(class_name)
        if new_idx is not None:
            new_samples.append((path, new_idx))
    ds.samples = new_samples
    ds.targets = [s[1] for s in new_samples]
    ds.imgs = new_samples

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                          num_workers=NUM_WORKERS, pin_memory=True, drop_last=True)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=True)

class_names = train_ds.classes
assert len(class_names) == NUM_CLASSES, f"Expected {NUM_CLASSES} classes, got {len(class_names)}"

print(f"Train: {len(train_ds):,} images, {len(class_names)} classes")
print(f"Val:   {len(val_ds):,} images")
print(f"Test:  {len(test_ds):,} images")
print(f"First 5 classes: {class_names[:5]}")
print(f"Last 5 classes:  {class_names[-5:]}")

sample, label = train_ds[0]
print(f"\\nSample tensor: shape={sample.shape}, min={sample.min():.3f}, max={sample.max():.3f}")
assert sample.shape == (3, INPUT_SIZE, INPUT_SIZE), f"Wrong shape: {sample.shape}"
assert sample.min() >= 0.0 and sample.max() <= 1.0, f"Values must be in [0,1]!"
print("Tensor assertions passed")"""

DATASETS_CELL_LANDMARK = """# ── Datasets & DataLoaders ───────────────────────────────────────
train_ds = ImageFolder(TRAIN_DIR, transform=train_transform)
val_ds   = ImageFolder(VAL_DIR,   transform=val_transform)
test_ds  = ImageFolder(TEST_DIR,  transform=val_transform)

# Safety: remap val/test to use train's class_to_idx (prevents label misalignment
# if any class is missing from a split)
for ds, name in [(val_ds, 'val'), (test_ds, 'test')]:
    old_classes = ds.classes
    if set(old_classes) != set(train_ds.classes):
        missing = set(train_ds.classes) - set(old_classes)
        print(f"  {name}: remapping {len(old_classes)} -> {len(train_ds.classes)} classes (missing: {sorted(missing)})")
    ds.class_to_idx = train_ds.class_to_idx
    ds.classes = train_ds.classes
    new_samples = []
    for path, _old_idx in ds.samples:
        class_name = os.path.basename(os.path.dirname(path))
        new_idx = train_ds.class_to_idx.get(class_name)
        if new_idx is not None:
            new_samples.append((path, new_idx))
    ds.samples = new_samples
    ds.targets = [s[1] for s in new_samples]
    ds.imgs = new_samples

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                          num_workers=NUM_WORKERS, pin_memory=True, drop_last=True)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=True)

class_names = train_ds.classes
assert len(class_names) == NUM_CLASSES, f"Expected {NUM_CLASSES} classes, got {len(class_names)}"

print(f"Train: {len(train_ds):,} images, {len(class_names)} classes")
print(f"Val:   {len(val_ds):,} images")
print(f"Test:  {len(test_ds):,} images")
print(f"First 5 classes: {class_names[:5]}")
print(f"Last 5 classes:  {class_names[-5:]}")

sample, label = train_ds[0]
print(f"\\nSample tensor: shape={sample.shape}, min={sample.min():.3f}, max={sample.max():.3f}")
assert sample.shape == (3, INPUT_SIZE, INPUT_SIZE), f"Wrong shape: {sample.shape}"
assert sample.min() >= 0.0 and sample.max() <= 1.0, f"Values must be in [0,1]!"
print("Tensor assertions passed")"""

INSTALL_CELL = """# lightning is pre-installed on Kaggle as pytorch_lightning
# onnxscript is needed by PyTorch 2.10+ for torch.onnx.export
import subprocess, sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'onnxscript'])"""


def fix_notebook(nb_path, datasets_source, install_source):
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    for i, cell in enumerate(nb["cells"]):
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)

        # Fix cell 2: install onnxscript
        if "lightning is pre-installed" in src:
            cell["source"] = install_source
            print(f"  Cell {i+1}: rewrote install cell")

        # Fix datasets cell
        if "Datasets & DataLoaders" in src:
            cell["source"] = datasets_source
            print(f"  Cell {i+1}: rewrote datasets cell")

    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"  Saved: {nb_path}")


print("Fixing hieroglyph notebook...")
fix_notebook(
    "planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier.ipynb",
    DATASETS_CELL_HIERO,
    INSTALL_CELL,
)

print("\nFixing landmark notebook...")
fix_notebook(
    "planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb",
    DATASETS_CELL_LANDMARK,
    INSTALL_CELL,
)

print("\nDone!")
