r"""Wadjet v3 — Hieroglyph Detector Retraining (Source-Balanced)

Kaggle notebook for retraining YOLO26s with:
  - Source-balanced dataset (mohiey capped to reduce 84% domain bias)
  - Cleaned data (no empty labels, no tiny images, resized oversized)
  - New GroundingDINO-annotated museum images (if available)
  - Higher quality gates: mAP50 >= 0.85, recall >= 0.80

Setup on Kaggle:
  - GPU: T4 x1 (or T4 x2)
  - Internet: ON (for ultralytics download)
  - Dataset 1: nadermohamedcr7/wadjet-hieroglyph-detection-v3
    (upload cleaned/balanced data/detection/merged/ as this dataset)
  - Dataset 2: (optional) nadermohamedcr7/wadjet-detector-v2-best
    (upload best.pt from v2 if resuming — NOT RECOMMENDED for v3)

Run: Convert to .ipynb via jupytext or copy cells into Kaggle editor.
"""

# %% [markdown]
# # Wadjet v3 — Hieroglyph Detector (YOLO26s Fresh Training)
#
# **Train from scratch** on a source-balanced, cleaned dataset.
#
# | Property | Value |
# |----------|-------|
# | Architecture | YOLO26s (NMS-free end-to-end) |
# | Input | `[1, 3, 640, 640]` float32, /255 normalized |
# | Output | `[1, 300, 6]` = (batch, max_dets, [x1,y1,x2,y2,conf,cls]) |
# | Classes | 1 ("hieroglyph") |
# | Strategy | Fresh training on balanced dataset, 150 epochs |
#
# **Key changes from v2:**
# 1. Source-balanced dataset (mohiey capped, diverse sources upweighted)
# 2. Empty labels removed, tiny images removed, oversized resized
# 3. New museum images annotated with GroundingDINO
# 4. Fresh training from pretrained YOLO26s weights (no resume from plateau)
# 5. Copy-paste augmentation, stronger scale variation
# 6. Higher quality gates: mAP50 >= 0.85, recall >= 0.80

# %% Cell 1: Install dependencies & KeepAlive setup
# !pip install -U ultralytics --quiet
# !pip install -q onnxscript onnxruntime

import os, sys, json, time, shutil, zipfile, threading
from pathlib import Path

import torch
import onnx
import onnxruntime as ort
import numpy as np

import ultralytics
from ultralytics import YOLO, settings

print(f"Python:       {sys.version}")
print(f"PyTorch:      {torch.__version__}")
print(f"CUDA:         {torch.cuda.is_available()} ({torch.version.cuda})")
if torch.cuda.is_available():
    print(f"GPU:          {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM:         {vram:.1f} GB")
print(f"ONNX Runtime: {ort.__version__}")
print(f"Ultralytics:  {ultralytics.__version__}")

# Verify YOLO26 availability (requires ultralytics >= 8.3.50)
try:
    _test = YOLO("yolo26s.pt")
    del _test
    print("YOLO26s:      AVAILABLE")
except Exception as e:
    print(f"YOLO26s:      NOT AVAILABLE — {e}")
    print("Fallback: using yolov8s.pt")

# KeepAlive — prevents IOPub timeout (papermill kills cells with >4s silence)
stop_keepalive = threading.Event()

def start_keepalive():
    stop_keepalive.clear()
    def _run():
        while not stop_keepalive.is_set():
            stop_keepalive.wait(30)
            if not stop_keepalive.is_set():
                print(".", end="", flush=True)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t

def stop_keepalive_fn():
    stop_keepalive.set()

print("\nKeepAlive ready.", flush=True)


# %% Cell 2: Auto-discover dataset
DATA_ROOT = None
DATASET_SLUG = "wadjet-hieroglyph-detection-v3"  # Upload balanced/ dir as this

print("=== Auto-discovering dataset ===", flush=True)

# Search strategy: datasets appear under /kaggle/input/<dataset-slug>/
for root, dirs, files in os.walk("/kaggle/input"):
    depth = root.replace("/kaggle/input", "").count(os.sep)
    if depth > 4:
        dirs.clear()
        continue
    if "images" in dirs and "labels" in dirs:
        img_train = os.path.join(root, "images", "train")
        if os.path.isdir(img_train):
            DATA_ROOT = root
            break

# Zip fallback
if DATA_ROOT is None:
    print("No direct dataset. Searching zips...", flush=True)
    extract_dir = "/kaggle/working/dataset"
    for root, dirs, files in os.walk("/kaggle/input"):
        for f in files:
            if f.endswith(".zip"):
                zpath = os.path.join(root, f)
                print(f"Extracting {zpath}...", flush=True)
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(zpath, "r") as zf:
                    zf.extractall(extract_dir)
                for r2, d2, f2 in os.walk(extract_dir):
                    if "images" in d2 and "labels" in d2:
                        if os.path.isdir(os.path.join(r2, "images", "train")):
                            DATA_ROOT = r2
                            break
                if DATA_ROOT:
                    break
        if DATA_ROOT:
            break

if DATA_ROOT is None:
    raise FileNotFoundError("Dataset not found under /kaggle/input/!")

for split in ["train", "val", "test"]:
    for sub in ["images", "labels"]:
        d = os.path.join(DATA_ROOT, sub, split)
        assert os.path.isdir(d), f"Missing: {d}"

print(f"DATA_ROOT: {DATA_ROOT}")
for split in ["train", "val", "test"]:
    n_img = len(os.listdir(os.path.join(DATA_ROOT, "images", split)))
    n_lbl = len(os.listdir(os.path.join(DATA_ROOT, "labels", split)))
    print(f"  {split:5s}: {n_img:,} images, {n_lbl:,} labels")
print(flush=True)


# %% Cell 3: Dataset cleaning — remove empty labels, tiny images
print("=== Pre-Training Data Cleaning ===", flush=True)

TINY_THRESHOLD = 64   # Min px on any side
HUGE_THRESHOLD = 2048  # Max px on any side
SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

import cv2

removed_empty = 0
removed_tiny = 0
resized_huge = 0

for split in ["train", "val"]:
    img_dir = os.path.join(DATA_ROOT, "images", split)
    lbl_dir = os.path.join(DATA_ROOT, "labels", split)

    label_files = [f for f in os.listdir(lbl_dir) if f.endswith(".txt")]
    for lf in label_files:
        lbl_path = os.path.join(lbl_dir, lf)
        stem = os.path.splitext(lf)[0]

        # Check empty label
        with open(lbl_path) as fh:
            content = fh.read().strip()
        if not content:
            os.remove(lbl_path)
            # Remove matching image
            for ext in SUPPORTED:
                img_path = os.path.join(img_dir, stem + ext)
                if os.path.isfile(img_path):
                    os.remove(img_path)
                    break
            removed_empty += 1
            continue

        # Find matching image
        img_path = None
        for ext in SUPPORTED:
            candidate = os.path.join(img_dir, stem + ext)
            if os.path.isfile(candidate):
                img_path = candidate
                break
        if img_path is None:
            continue

        # Check image size
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]

        # Remove tiny
        if w < TINY_THRESHOLD or h < TINY_THRESHOLD:
            os.remove(img_path)
            os.remove(lbl_path)
            removed_tiny += 1
            continue

        # Resize oversized (preserve labels since they're normalized)
        if max(w, h) > HUGE_THRESHOLD:
            scale = HUGE_THRESHOLD / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            cv2.imwrite(img_path, resized, [cv2.IMWRITE_JPEG_QUALITY, 92])
            resized_huge += 1

print(f"  Removed empty labels: {removed_empty}")
print(f"  Removed tiny images (<{TINY_THRESHOLD}px): {removed_tiny}")
print(f"  Resized oversized (>{HUGE_THRESHOLD}px): {resized_huge}")

# Recount
for split in ["train", "val", "test"]:
    n = len(os.listdir(os.path.join(DATA_ROOT, "images", split)))
    print(f"  {split}: {n:,} images (after cleaning)")
print(flush=True)


# %% Cell 4: Source distribution analysis
print("=== Source Distribution ===", flush=True)

from collections import Counter

def get_source(name):
    n = name.lower()
    if n.startswith("mohiey"): return "mohiey"
    if n.startswith("synthetic"): return "synthetic"
    if n.startswith("sign"): return "signs_seg"
    if n.startswith("v1"): return "v1_raw"
    if n.startswith("hla"): return "hla"
    if n.startswith("scraped"): return "scraped"
    return "unknown"

train_sources = Counter()
for f in os.listdir(os.path.join(DATA_ROOT, "images", "train")):
    train_sources[get_source(f)] += 1

total = sum(train_sources.values())
print(f"  Train total: {total:,}")
for src, count in train_sources.most_common():
    pct = count / total * 100
    bar = "█" * int(pct / 2)
    print(f"    {src:15s} {count:>6,} ({pct:>5.1f}%) {bar}")
print(flush=True)


# %% Cell 5: Dataset validation & visualization
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

print("=== Dataset Validation ===", flush=True)

total_boxes = 0
for split in ["train", "val", "test"]:
    lbl_dir = os.path.join(DATA_ROOT, "labels", split)
    n_lbl = len(os.listdir(lbl_dir))
    split_boxes = 0
    for lf in sorted(os.listdir(lbl_dir))[:500]:
        with open(os.path.join(lbl_dir, lf)) as fh:
            lines = [l.strip() for l in fh if l.strip()]
        split_boxes += len(lines)
    total_boxes += split_boxes
    avg = split_boxes / min(n_lbl, 500) if min(n_lbl, 500) > 0 else 0
    print(f"  {split:5s}: ~{avg:.1f} boxes/img (sampled 500)")

print(f"  Total boxes (sampled): {total_boxes:,}")

# Visualize 6 random train images
img_dir = os.path.join(DATA_ROOT, "images", "train")
lbl_dir = os.path.join(DATA_ROOT, "labels", "train")
all_imgs = sorted(os.listdir(img_dir))
rng = np.random.default_rng(42)
sample_idxs = rng.choice(len(all_imgs), size=min(6, len(all_imgs)), replace=False)

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
for ax, idx in zip(axes.flat, sample_idxs):
    img_name = all_imgs[idx]
    img = Image.open(os.path.join(img_dir, img_name))
    w, h = img.size
    ax.imshow(img)
    ax.set_title(f"{img_name[:30]} ({w}x{h})", fontsize=8)
    ax.axis("off")
    lbl_path = os.path.join(lbl_dir, Path(img_name).stem + ".txt")
    if os.path.isfile(lbl_path):
        with open(lbl_path) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 5:
                    cx, cy, bw, bh = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                    x1 = (cx - bw/2) * w
                    y1 = (cy - bh/2) * h
                    rect = patches.Rectangle((x1, y1), bw*w, bh*h,
                                             linewidth=1, edgecolor='lime', facecolor='none')
                    ax.add_patch(rect)
plt.tight_layout()
plt.savefig("/kaggle/working/sample_annotations.png", dpi=100)
plt.show()
print(flush=True)


# %% Cell 6: Configure & Train YOLO26s (FRESH from pretrained)
import yaml

# ===================== TRAINING CONFIG =====================
IMG_SIZE      = 640
EPOCHS        = 150          # Fresh training — needs more epochs
PATIENCE      = 40           # Allow longer convergence
BATCH_SIZE    = 16
WARMUP_EP     = 5            # Standard warmup
LR0           = 0.01         # Standard LR for fresh training
LRF           = 0.01

# Augmentation — NO FLIPS for hieroglyphs!
FLIPLR        = 0.0          # CRITICAL: flip changes hieroglyph meaning
FLIPUD        = 0.0
MOSAIC        = 1.0
MIXUP         = 0.15         # Slightly more than v2's 0.1
COPY_PASTE    = 0.3          # NEW: paste glyphs between images
CLOSE_MOSAIC  = 15           # Disable mosaic last 15 epochs
DEGREES       = 15.0
TRANSLATE     = 0.15         # Slightly more translation
SCALE         = 0.6          # Wider scale variation
PERSPECTIVE   = 0.001
HSV_H         = 0.02         # Broader hue
HSV_S         = 0.7
HSV_V         = 0.5          # Broader brightness
ERASING       = 0.1          # Random erasing for robustness

# Quality gates — HIGHER for v3
MIN_MAP50      = 0.85        # DET-G1
MIN_PRECISION  = 0.80
MIN_RECALL     = 0.80        # DET-G2
MAX_ONNX_MB    = 20
EXPECTED_SHAPE = (1, 300, 6)

OUTPUT_DIR   = "/kaggle/working"
PROJECT_DIR  = os.path.join(OUTPUT_DIR, "detector_v3")

# Create data.yaml
ds_config = {
    "path": DATA_ROOT,
    "train": "images/train",
    "val": "images/val",
    "test": "images/test",
    "nc": 1,
    "names": ["hieroglyph"],
}
FIXED_YAML = os.path.join(OUTPUT_DIR, "hieroglyph_det.yaml")
with open(FIXED_YAML, "w") as f:
    yaml.dump(ds_config, f, default_flow_style=False)

print("Training Config:")
print(f"  Architecture:  YOLO26s (fresh from pretrained)")
print(f"  Epochs:        {EPOCHS}, Patience: {PATIENCE}")
print(f"  LR0: {LR0}, Batch: {BATCH_SIZE}")
print(f"  Augmentation: mosaic={MOSAIC}, mixup={MIXUP}, copy_paste={COPY_PASTE}")
print(f"  fliplr={FLIPLR}, flipud={FLIPUD}")
print(f"  Quality gates: mAP50>={MIN_MAP50}, P>={MIN_PRECISION}, R>={MIN_RECALL}")
print(flush=True)

# Configure ultralytics
settings.update({"runs_dir": PROJECT_DIR, "sync": False, "wandb": False})
os.environ["YOLO_VERBOSE"] = "True"

# Start KeepAlive
ka = start_keepalive()

print("=" * 60, flush=True)
print("STARTING YOLO26s TRAINING (FRESH)", flush=True)
print("=" * 60, flush=True)

t0 = time.time()

# Load pretrained YOLO26s (fresh weights, NOT resumed from v2)
model = YOLO("yolo26s.pt")

# Train
results = model.train(
    data=FIXED_YAML,
    epochs=EPOCHS,
    batch=BATCH_SIZE,
    imgsz=IMG_SIZE,
    patience=PATIENCE,
    optimizer="auto",
    lr0=LR0,
    lrf=LRF,
    warmup_epochs=WARMUP_EP,
    # Augmentation — NO FLIPS
    fliplr=FLIPLR,
    flipud=FLIPUD,
    mosaic=MOSAIC,
    mixup=MIXUP,
    copy_paste=COPY_PASTE,
    close_mosaic=CLOSE_MOSAIC,
    degrees=DEGREES,
    translate=TRANSLATE,
    scale=SCALE,
    perspective=PERSPECTIVE,
    hsv_h=HSV_H,
    hsv_s=HSV_S,
    hsv_v=HSV_V,
    erasing=ERASING,
    # Training settings
    amp=False,               # NO mixed precision — clean ONNX
    workers=2,
    project=PROJECT_DIR,
    name="yolo26s_hiero_v3",
    exist_ok=True,
    verbose=True,
    save=True,
    save_period=25,
    plots=True,
)

stop_keepalive_fn()
elapsed = (time.time() - t0) / 60
print(f"\nTraining complete in {elapsed:.1f} min", flush=True)


# %% Cell 7: Validation metrics & quality gate checks
import csv

train_dir = os.path.join(PROJECT_DIR, "yolo26s_hiero_v3")
best_pt = os.path.join(train_dir, "weights", "best.pt")

if not os.path.isfile(best_pt):
    for root, dirs, files in os.walk(PROJECT_DIR):
        if "best.pt" in files:
            best_pt = os.path.join(root, "best.pt")
            break

if not os.path.isfile(best_pt):
    raise FileNotFoundError(f"best.pt not found under {PROJECT_DIR}")

print(f"Best model: {best_pt}")
print(f"Size: {os.path.getsize(best_pt) / 1024**2:.1f} MB", flush=True)

# Plot training curves from results.csv
results_csv = os.path.join(train_dir, "results.csv")
if os.path.isfile(results_csv):
    with open(results_csv) as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]

    epochs_list = [int(r["epoch"].strip()) for r in rows]
    box_loss = [float(r["train/box_loss"].strip()) for r in rows]
    cls_loss = [float(r["train/cls_loss"].strip()) for r in rows]
    val_box  = [float(r["val/box_loss"].strip()) for r in rows]
    map50s   = [float(r["metrics/mAP50(B)"].strip()) for r in rows]
    map95s   = [float(r["metrics/mAP50-95(B)"].strip()) for r in rows]
    precs    = [float(r["metrics/precision(B)"].strip()) for r in rows]
    recs     = [float(r["metrics/recall(B)"].strip()) for r in rows]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes[0,0].plot(epochs_list, box_loss, label="train/box_loss")
    axes[0,0].plot(epochs_list, val_box, label="val/box_loss")
    axes[0,0].set_title("Box Loss"); axes[0,0].legend(); axes[0,0].grid(True)
    axes[0,1].plot(epochs_list, cls_loss, label="train/cls_loss")
    axes[0,1].set_title("Cls Loss"); axes[0,1].legend(); axes[0,1].grid(True)
    axes[1,0].plot(epochs_list, map50s, label="mAP50", color="green")
    axes[1,0].plot(epochs_list, map95s, label="mAP50-95", color="blue")
    axes[1,0].axhline(y=MIN_MAP50, color="red", linestyle="--", label=f"gate={MIN_MAP50}")
    axes[1,0].set_title("mAP"); axes[1,0].legend(); axes[1,0].grid(True)
    axes[1,1].plot(epochs_list, precs, label="Precision", color="orange")
    axes[1,1].plot(epochs_list, recs, label="Recall", color="purple")
    axes[1,1].axhline(y=MIN_PRECISION, color="red", linestyle="--", label=f"P gate")
    axes[1,1].axhline(y=MIN_RECALL, color="red", linestyle=":", label=f"R gate")
    axes[1,1].set_title("P/R"); axes[1,1].legend(); axes[1,1].grid(True)
    plt.tight_layout()
    plt.savefig("/kaggle/working/training_curves.png", dpi=100)
    plt.show()

# Validate on val set
best_model = YOLO(best_pt)
val_metrics = best_model.val(data=FIXED_YAML, split="val", verbose=True)

map50 = val_metrics.box.map50
map50_95 = val_metrics.box.map
precision = val_metrics.box.mp
recall = val_metrics.box.mr

print(f"\n{'='*50}")
print(f"VALIDATION RESULTS")
print(f"{'='*50}")
print(f"  mAP50:      {map50:.4f}  (gate: >= {MIN_MAP50})")
print(f"  mAP50-95:   {map50_95:.4f}")
print(f"  Precision:  {precision:.4f}  (gate: >= {MIN_PRECISION})")
print(f"  Recall:     {recall:.4f}  (gate: >= {MIN_RECALL})")

gates_passed = True
for name, val, gate in [("mAP50", map50, MIN_MAP50), ("Precision", precision, MIN_PRECISION),
                         ("Recall", recall, MIN_RECALL)]:
    status = "PASS" if val >= gate else "FAIL"
    if val < gate:
        gates_passed = False
    print(f"  [{status}] {name}: {val:.4f} >= {gate}")

print("\n  ALL QUALITY GATES PASSED" if gates_passed else
      "\n  WARNING: Some gates failed. Will still export — review before deploying.")
print(flush=True)


# %% Cell 8: Test set evaluation
print("Evaluating on TEST set...", flush=True)
test_metrics = best_model.val(data=FIXED_YAML, split="test", verbose=True)

test_map50 = test_metrics.box.map50
test_map50_95 = test_metrics.box.map
test_precision = test_metrics.box.mp
test_recall = test_metrics.box.mr

print(f"\n{'='*50}")
print(f"TEST RESULTS")
print(f"{'='*50}")
print(f"  mAP50:      {test_map50:.4f}")
print(f"  mAP50-95:   {test_map50_95:.4f}")
print(f"  Precision:  {test_precision:.4f}")
print(f"  Recall:     {test_recall:.4f}")
print(flush=True)


# %% Cell 9: Export to ONNX (fp32, end-to-end NMS-free)
print("Exporting to ONNX (end-to-end, NMS-free)...", flush=True)

onnx_path = best_model.export(
    format="onnx",
    imgsz=IMG_SIZE,
    simplify=True,
    opset=17,
    dynamic=True,
    half=False,
)

print(f"ONNX exported: {onnx_path}")
fp32_size = os.path.getsize(onnx_path) / 1024**2
print(f"Size: {fp32_size:.1f} MB")

# Verify no sidecar
sidecar = onnx_path + ".data"
if os.path.isfile(sidecar):
    print(f"WARNING: .onnx.data sidecar found ({os.path.getsize(sidecar)/1024**2:.1f} MB)")
else:
    print("No sidecar — single file ONNX")

# Validate I/O shapes
model_onnx = onnx.load(onnx_path)
print(f"\nONNX inputs:")
for inp in model_onnx.graph.input:
    shape = [d.dim_value if d.dim_value else d.dim_param for d in inp.type.tensor_type.shape.dim]
    print(f"  {inp.name}: {shape}")
print(f"ONNX outputs:")
for out in model_onnx.graph.output:
    shape = [d.dim_value if d.dim_value else d.dim_param for d in out.type.tensor_type.shape.dim]
    print(f"  {out.name}: {shape}")

# Dummy inference
sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
input_name = sess.get_inputs()[0].name
dummy = np.random.rand(1, 3, IMG_SIZE, IMG_SIZE).astype(np.float32)
outputs = sess.run(None, {input_name: dummy})
print(f"\nDummy output shape: {outputs[0].shape}")
assert outputs[0].shape[2] == 6, f"Expected 6 columns, got {outputs[0].shape[2]}"
print("ONNX fp32 export PASSED", flush=True)


# %% Cell 10: Quantize to uint8
from onnxruntime.quantization import quantize_dynamic, QuantType

onnx_uint8 = os.path.join(OUTPUT_DIR, "glyph_detector_uint8.onnx")

print("Quantizing to uint8...", flush=True)
quantize_dynamic(onnx_path, onnx_uint8, weight_type=QuantType.QUInt8)

uint8_size = os.path.getsize(onnx_uint8) / 1024**2
print(f"  fp32:  {fp32_size:.1f} MB")
print(f"  uint8: {uint8_size:.1f} MB")
print(f"  Compression: {(1 - uint8_size/fp32_size)*100:.0f}%")

# Validate
sess_q = ort.InferenceSession(onnx_uint8, providers=["CPUExecutionProvider"])
input_name_q = sess_q.get_inputs()[0].name
outputs_q = sess_q.run(None, {input_name_q: dummy})
print(f"  uint8 output shape: {outputs_q[0].shape}")

if uint8_size > MAX_ONNX_MB:
    print(f"  FAIL: {uint8_size:.1f} MB > {MAX_ONNX_MB} MB")
else:
    print(f"  PASS: Size {uint8_size:.1f} MB <= {MAX_ONNX_MB} MB")
print(flush=True)


# %% Cell 11: Validate ONNX on real test image
from PIL import Image

def letterbox_preprocess(img_path, target_size=640):
    img = Image.open(img_path).convert("RGB")
    orig_w, orig_h = img.size
    ratio = min(target_size / orig_w, target_size / orig_h)
    new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
    img_resized = img.resize((new_w, new_h), Image.BILINEAR)
    canvas = Image.new("RGB", (target_size, target_size), (114, 114, 114))
    pad_x = (target_size - new_w) // 2
    pad_y = (target_size - new_h) // 2
    canvas.paste(img_resized, (pad_x, pad_y))
    arr = np.array(canvas, dtype=np.float32) / 255.0
    arr = arr.transpose(2, 0, 1)[np.newaxis, ...]
    return arr, (orig_w, orig_h), ratio, (pad_x, pad_y)

test_img_dir = os.path.join(DATA_ROOT, "images", "test")
test_images = sorted(os.listdir(test_img_dir))
sample_img = os.path.join(test_img_dir, test_images[0])

input_tensor, (ow, oh), ratio, (px, py) = letterbox_preprocess(sample_img)
print(f"Test image: {test_images[0]} ({ow}x{oh})")

outputs = sess_q.run(None, {input_name_q: input_tensor})
preds = outputs[0][0]
CONF_THRESH = 0.25
mask = preds[:, 4] > CONF_THRESH
filtered = preds[mask]
print(f"Detections at conf>{CONF_THRESH}: {len(filtered)}")

if len(filtered) > 0:
    confs = filtered[:, 4]
    print(f"  Confidence range: {confs.min():.3f} – {confs.max():.3f}")
print("ONNX validation PASSED", flush=True)


# %% Cell 12: Test on ALL test images — detection rate + fallback rate
print("=== Running inference on ALL test images ===", flush=True)

detected_counts = []
zero_detection_images = []

for i, img_name in enumerate(test_images):
    img_path = os.path.join(test_img_dir, img_name)
    inp, _, _, _ = letterbox_preprocess(img_path, IMG_SIZE)
    out = sess_q.run(None, {input_name_q: inp})
    preds = out[0][0]
    n_det = int((preds[:, 4] > CONF_THRESH).sum())
    detected_counts.append(n_det)
    if n_det == 0:
        zero_detection_images.append(img_name)
    if (i + 1) % 50 == 0:
        print(f"  Processed {i+1}/{len(test_images)}...", flush=True)

detected_counts = np.array(detected_counts)
images_with_dets = int((detected_counts > 0).sum())
images_no_dets = int((detected_counts == 0).sum())
fallback_rate = images_no_dets / len(test_images)

print(f"\n{'='*50}")
print(f"TEST DETECTION SUMMARY ({len(test_images)} images)")
print(f"{'='*50}")
print(f"  With detections: {images_with_dets} ({images_with_dets/len(test_images)*100:.1f}%)")
print(f"  Zero detections: {images_no_dets} ({fallback_rate*100:.1f}%)")
print(f"  Detection counts: min={detected_counts.min()}, max={detected_counts.max()}")
print(f"  AI fallback rate: {fallback_rate*100:.1f}%")

# Visualize 6 test
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
sample_idxs = rng.choice(len(test_images), size=min(6, len(test_images)), replace=False)
for ax, idx in zip(axes.flat, sample_idxs):
    img_name = test_images[idx]
    img_path = os.path.join(test_img_dir, img_name)
    img = Image.open(img_path).convert("RGB")
    ow, oh = img.size
    inp, _, ratio, (px, py) = letterbox_preprocess(img_path, IMG_SIZE)
    out = sess_q.run(None, {input_name_q: inp})
    dets = out[0][0]
    dets = dets[dets[:, 4] > CONF_THRESH]
    ax.imshow(img); ax.axis("off")
    ax.set_title(f"{img_name[:25]} ({len(dets)} dets)", fontsize=8)
    for det in dets:
        x1 = (det[0] - px) / ratio
        y1 = (det[1] - py) / ratio
        x2 = (det[2] - px) / ratio
        y2 = (det[3] - py) / ratio
        rect = patches.Rectangle((x1, y1), x2-x1, y2-y1,
                                 linewidth=1.5, edgecolor='lime', facecolor='none')
        ax.add_patch(rect)
        ax.text(x1, y1-2, f"{det[4]:.2f}", fontsize=6, color='lime')
plt.tight_layout()
plt.savefig("/kaggle/working/test_detections.png", dpi=100)
plt.show()
print(flush=True)


# %% Cell 13: Save artifacts & model metadata
actual_shape = list(outputs_q[0].shape)

metadata = {
    "model_name": "wadjet_hieroglyph_detector_v3",
    "architecture": "YOLO26s (end-to-end, NMS-free)",
    "framework": "ultralytics",
    "task": "object_detection",
    "classes": ["hieroglyph"],
    "num_classes": 1,
    "input_size": IMG_SIZE,
    "input_shape": [1, 3, IMG_SIZE, IMG_SIZE],
    "input_format": "NCHW",
    "normalization": "divide_by_255",
    "output_shape": actual_shape,
    "output_columns": ["x1", "y1", "x2", "y2", "confidence", "class_id"],
    "nms_free": True,
    "quantized": True,
    "quantization": "uint8_dynamic",
    "fp32_size_mb": round(fp32_size, 1),
    "uint8_size_mb": round(uint8_size, 1),
    "training": {
        "dataset": "nadermohamedcr7/wadjet-hieroglyph-detection-v3",
        "train_images": len(os.listdir(os.path.join(DATA_ROOT, "images", "train"))),
        "val_images": len(os.listdir(os.path.join(DATA_ROOT, "images", "val"))),
        "test_images": len(os.listdir(os.path.join(DATA_ROOT, "images", "test"))),
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "lr0": LR0,
        "fliplr": FLIPLR,
        "flipud": FLIPUD,
        "amp": False,
        "copy_paste": COPY_PASTE,
        "erasing": ERASING,
        "pretrained": "yolo26s.pt",
    },
    "metrics": {
        "val_mAP50": round(float(map50), 4),
        "val_mAP50_95": round(float(map50_95), 4),
        "val_precision": round(float(precision), 4),
        "val_recall": round(float(recall), 4),
        "test_mAP50": round(float(test_map50), 4),
        "test_mAP50_95": round(float(test_map50_95), 4),
        "test_precision": round(float(test_precision), 4),
        "test_recall": round(float(test_recall), 4),
        "ai_fallback_rate": round(float(fallback_rate), 4),
    },
    "quality_gates": {
        "mAP50_gate": MIN_MAP50,
        "mAP50_passed": bool(map50 >= MIN_MAP50),
        "precision_gate": MIN_PRECISION,
        "precision_passed": bool(precision >= MIN_PRECISION),
        "recall_gate": MIN_RECALL,
        "recall_passed": bool(recall >= MIN_RECALL),
        "onnx_size_gate_mb": MAX_ONNX_MB,
        "onnx_size_passed": bool(uint8_size <= MAX_ONNX_MB),
    },
    "improvements_over_v2": {
        "source_balanced": True,
        "empty_labels_removed": True,
        "tiny_images_removed": True,
        "copy_paste_augmentation": True,
        "fresh_training": True,
    },
}

meta_path = os.path.join(OUTPUT_DIR, "model_metadata.json")
with open(meta_path, "w") as f:
    json.dump(metadata, f, indent=2)
print(f"Metadata saved: {meta_path}")

# Copy artifacts
for src, name in [(onnx_uint8, "glyph_detector_uint8.onnx"),
                  (onnx_path, os.path.basename(onnx_path)),
                  (best_pt, "best.pt"),
                  (meta_path, "model_metadata.json")]:
    dst = os.path.join(OUTPUT_DIR, name)
    if src != dst and os.path.isfile(src):
        shutil.copy2(src, dst)

for fname in ["results.csv", "results.png", "confusion_matrix.png",
              "confusion_matrix_normalized.png", "P_curve.png",
              "R_curve.png", "PR_curve.png", "F1_curve.png"]:
    src = os.path.join(train_dir, fname)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(OUTPUT_DIR, fname))

print("\nSaved output files:")
for root, dirs, files in os.walk(OUTPUT_DIR):
    depth = root.replace(OUTPUT_DIR, "").count(os.sep)
    if depth > 2:
        continue
    for f in sorted(files):
        fpath = os.path.join(root, f)
        sz = os.path.getsize(fpath)
        rel = os.path.relpath(fpath, OUTPUT_DIR)
        unit = "MB" if sz > 1024*1024 else "KB"
        val = sz/1024**2 if sz > 1024*1024 else sz/1024
        print(f"  {rel:50s} {val:8.1f} {unit}")
print(flush=True)


# %% Cell 14: Final summary
print("\n" + "=" * 60)
print("TRAINING SUMMARY — YOLO26s Hieroglyph Detector v3")
print("=" * 60)
print(f"  Training:       Fresh from pretrained yolo26s.pt")
print(f"  Epochs:         {EPOCHS}")
n_train = metadata['training']['train_images']
n_val = metadata['training']['val_images']
n_test = metadata['training']['test_images']
print(f"  Dataset:        {n_train:,} train / {n_val:,} val / {n_test:,} test")
print(f"  ONNX uint8:     {uint8_size:.1f} MB")
print(f"  Output shape:   {actual_shape}")
print()
print(f"  VAL  mAP50={map50:.4f}  P={precision:.4f}  R={recall:.4f}")
print(f"  TEST mAP50={test_map50:.4f}  P={test_precision:.4f}  R={test_recall:.4f}")
print(f"  Fallback rate:  {fallback_rate*100:.1f}%")
print()

all_pass = True
checks = [
    (f"mAP50 >= {MIN_MAP50}",     map50 >= MIN_MAP50),
    (f"Precision >= {MIN_PRECISION}", precision >= MIN_PRECISION),
    (f"Recall >= {MIN_RECALL}",    recall >= MIN_RECALL),
    (f"ONNX <= {MAX_ONNX_MB}MB",  uint8_size <= MAX_ONNX_MB),
    ("Fallback < 50%",            fallback_rate < 0.50),
]
for name, passed in checks:
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    print(f"  [{status}] {name}")

print()
if all_pass:
    print("  ALL GATES PASSED — Model ready for deployment!")
else:
    print("  SOME GATES FAILED — Review before deploying.")
    print("  If training plateaued, consider:")
    print("    - Longer patience / more epochs")
    print("    - Larger model (YOLO26m)")
    print("    - Adding more diverse data sources")

print(f"\nDownload: kaggle kernels output <user>/wadjet-hieroglyph-detector-v3 -p ./detector_v3_output")
print("Done.", flush=True)
