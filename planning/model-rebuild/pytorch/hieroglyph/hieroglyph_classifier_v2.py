r"""Wadjet v2 — Hieroglyph Classifier with Stone-Texture Augmentation

Kaggle notebook for retraining MobileNetV3-Small with:
  - Stone-texture background augmentation (200 real textures)
  - Aggressive domain-gap augmentation (noise, blur, erosion, lighting)
  - Same 2-phase training (head → fine-tune) as v1
  - Higher real-stone accuracy target: ≥ 50%

Setup on Kaggle:
  - GPU: T4 x1
  - Internet: ON
  - Dataset 1: nadermohamedcr7/wadjet-hieroglyph-classification
    (upload data/hieroglyph_classification/ as this dataset)
  - Dataset 2: nadermohamedcr7/wadjet-stone-textures
    (upload data/detection/stone_textures/ as this dataset)
"""

# %% [markdown]
# # Wadjet v2 — Hieroglyph Classifier (Stone-Texture Augmentation)
#
# **MobileNetV3-Small → 171 Gardiner sign classes**
#
# | Property | Value |
# |----------|-------|
# | Architecture | MobileNetV3-Small (timm) |
# | Input | `[1, 3, 128, 128]` float32, /255 |
# | Output | `[1, 171]` softmax |
# | Training | 2-phase FocalLoss + class weights |
# | Key change | Stone texture backgrounds + aggressive augmentation |
#
# **Targets:**
# - Maintain test accuracy ≥ 98%
# - Real-stone accuracy ≥ 50% (from 5-15%)

# %% Cell 1: Install deps
import subprocess, sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'onnxscript', 'onnxruntime'])

# %% Cell 2: Imports
import os, json, math, time, warnings
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torchvision.datasets import ImageFolder
import timm
import pytorch_lightning as L
from sklearn.metrics import classification_report, top_k_accuracy_score
import albumentations as A
from albumentations.pytorch import ToTensorV2
from collections import Counter
import cv2
from PIL import Image
import onnx
import onnxruntime as ort

warnings.filterwarnings('ignore', category=UserWarning)

print(f"PyTorch {torch.__version__}")
print(f"CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# %% Cell 3: Config & data discovery
INPUT_SIZE   = 128
NUM_CLASSES  = 171
BATCH_SIZE   = 64
NUM_WORKERS  = 2

P1_EPOCHS    = 5     # Head-only phase
P1_LR        = 1e-3

P2_EPOCHS    = 40    # Fine-tune (more than v1's 30 to learn texture domain)
P2_LR        = 5e-5  # Slightly lower than v1's 1e-4

FOCAL_GAMMA  = 2.0
LABEL_SMOOTHING = 0.1
STONE_AUG_PROB  = 0.40  # 40% chance of stone-texture background

OUT_DIR = "/kaggle/working"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Auto-discover classification data
DATA_ROOT = None
for name in os.listdir("/kaggle/input"):
    candidate = os.path.join("/kaggle/input", name)
    if os.path.isdir(candidate):
        children = os.listdir(candidate)
        if "train" in children:
            DATA_ROOT = candidate
            break
        for child in children:
            sub = os.path.join(candidate, child)
            if os.path.isdir(sub) and "train" in os.listdir(sub):
                DATA_ROOT = sub
                break
        if DATA_ROOT:
            break

if DATA_ROOT is None:
    for root, dirs, files in os.walk("/kaggle/input"):
        if "train" in dirs and "val" in dirs:
            DATA_ROOT = root
            break

if DATA_ROOT is None:
    raise FileNotFoundError("Classification dataset not found!")

TRAIN_DIR = os.path.join(DATA_ROOT, "train")
VAL_DIR   = os.path.join(DATA_ROOT, "val")
TEST_DIR  = os.path.join(DATA_ROOT, "test")

# Auto-discover stone textures
STONE_DIR = None
for name in os.listdir("/kaggle/input"):
    candidate = os.path.join("/kaggle/input", name)
    if os.path.isdir(candidate):
        # Check for stone_*.jpg files
        files = os.listdir(candidate)
        stone_files = [f for f in files if f.startswith("stone_") and f.endswith(".jpg")]
        if len(stone_files) > 50:
            STONE_DIR = candidate
            break

print(f"DATA_ROOT:  {DATA_ROOT}")
print(f"STONE_DIR:  {STONE_DIR}")

for split, path in [("train", TRAIN_DIR), ("val", VAL_DIR), ("test", TEST_DIR)]:
    if os.path.exists(path):
        classes = sorted(os.listdir(path))
        total = sum(len(os.listdir(os.path.join(path, c))) for c in classes if os.path.isdir(os.path.join(path, c)))
        print(f"  {split:5s}: {total:>6,} images, {len(classes)} classes")

if STONE_DIR:
    stone_count = len([f for f in os.listdir(STONE_DIR)
                       if f.endswith((".jpg", ".png")) and f.startswith("stone_")])
    print(f"  stones: {stone_count} texture images")
else:
    print("  WARNING: No stone textures found — using synthetic fallback")


# %% Cell 4: Stone-texture augmentation pipeline
class StoneTextureBlender:
    """Blend a hieroglyph crop onto a random stone texture background.

    Simulates how hieroglyphs appear on real carved stone:
    - Alpha-blend glyph onto stone texture
    - Add edge erosion/dilation to simulate carving
    - Vary blend intensity for depth variation
    """

    def __init__(self, stone_dir, target_size=128):
        self.target_size = target_size
        self.textures = []
        if stone_dir and os.path.isdir(stone_dir):
            for f in os.listdir(stone_dir):
                if f.endswith((".jpg", ".png")) and f.startswith("stone_"):
                    self.textures.append(os.path.join(stone_dir, f))
        print(f"  StoneTextureBlender: loaded {len(self.textures)} textures")

    def __call__(self, image):
        """Apply to a numpy HWC uint8 image."""
        if not self.textures:
            return image

        # Load random texture
        tex_path = self.textures[np.random.randint(len(self.textures))]
        tex = cv2.imread(tex_path)
        if tex is None:
            return image
        tex = cv2.cvtColor(tex, cv2.COLOR_BGR2RGB)

        h, w = image.shape[:2]

        # Random crop from texture at same size
        th, tw = tex.shape[:2]
        if th < h or tw < w:
            tex = cv2.resize(tex, (max(w, tw), max(h, th)))
            th, tw = tex.shape[:2]
        y0 = np.random.randint(0, max(1, th - h))
        x0 = np.random.randint(0, max(1, tw - w))
        tex_crop = tex[y0:y0+h, x0:x0+w]

        # Convert glyph to grayscale for mask
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # Threshold to find glyph regions (dark = glyph on light background typically)
        # Adaptive threshold for varying backgrounds
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Optional: erode/dilate for carved stone effect
        if np.random.random() < 0.5:
            kernel_size = np.random.choice([1, 2, 3])
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            if np.random.random() < 0.5:
                mask = cv2.erode(mask, kernel, iterations=1)
            else:
                mask = cv2.dilate(mask, kernel, iterations=1)

        # Blend: darken stone where glyph is (simulates carved relief)
        mask_f = mask.astype(np.float32) / 255.0
        mask_3 = mask_f[:, :, np.newaxis]

        # Carving depth variation
        depth = np.random.uniform(0.3, 0.7)
        darkened = (tex_crop.astype(np.float32) * (1 - depth * mask_3)).clip(0, 255)

        # Add slight shadow at edges for 3D relief effect
        if np.random.random() < 0.3:
            blur_mask = cv2.GaussianBlur(mask_f, (5, 5), 2.0)
            shadow = blur_mask[:, :, np.newaxis] * 30
            darkened = (darkened - shadow).clip(0, 255)

        return darkened.astype(np.uint8)


# Initialize stone blender
stone_blender = StoneTextureBlender(STONE_DIR, INPUT_SIZE)

# Albumentations transform with stone texture
class AlbumentationsTransform:
    def __init__(self, transform, stone_blender=None, stone_prob=0.0):
        self.transform = transform
        self.stone_blender = stone_blender
        self.stone_prob = stone_prob

    def __call__(self, img):
        img_np = np.array(img)

        # Apply stone texture blending before other augmentations
        if self.stone_blender and np.random.random() < self.stone_prob:
            img_np = self.stone_blender(img_np)

        return self.transform(image=img_np)["image"]


# Training augmentation — much more aggressive than v1
train_aug = A.Compose([
    A.Resize(INPUT_SIZE, INPUT_SIZE),
    A.Rotate(limit=15, border_mode=0, p=0.5),  # Slightly more rotation
    A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.6),
    A.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15, hue=0.08, p=0.4),

    # Stone simulation augmentations (domain gap)
    A.OneOf([
        A.GaussNoise(std_range=(10.0 / 255.0, 40.0 / 255.0), p=1.0),
        A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
    ], p=0.4),
    A.OneOf([
        A.GaussianBlur(blur_limit=(3, 7), p=1.0),
        A.MotionBlur(blur_limit=(3, 7), p=1.0),
    ], p=0.3),
    A.ImageCompression(quality_range=(40, 90), p=0.2),  # JPEG artifacts
    A.RandomShadow(num_shadows_limit=(1, 2), shadow_dimension=4, p=0.2),  # Lighting
    A.CoarseDropout(num_holes_range=(1, 3), hole_height_range=(0.05, 0.15),
                    hole_width_range=(0.05, 0.15), fill="random", p=0.2),  # Occlusion

    A.Normalize(mean=(0.0, 0.0, 0.0), std=(1.0, 1.0, 1.0), max_pixel_value=255.0),
    ToTensorV2(),
])

val_aug = A.Compose([
    A.Resize(INPUT_SIZE, INPUT_SIZE),
    A.Normalize(mean=(0.0, 0.0, 0.0), std=(1.0, 1.0, 1.0), max_pixel_value=255.0),
    ToTensorV2(),
])

train_transform = AlbumentationsTransform(train_aug, stone_blender, STONE_AUG_PROB)
val_transform = AlbumentationsTransform(val_aug)


# %% Cell 5: Datasets & DataLoaders
train_ds = ImageFolder(TRAIN_DIR, transform=train_transform)
val_ds   = ImageFolder(VAL_DIR,   transform=val_transform)
test_ds  = ImageFolder(TEST_DIR,  transform=val_transform)

# Remap val/test to train's class_to_idx
for ds, name in [(val_ds, 'val'), (test_ds, 'test')]:
    old_classes = ds.classes
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
    print(f"  {name}: {len(new_samples)} samples remapped")

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                          num_workers=NUM_WORKERS, pin_memory=True, drop_last=True)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=True)

class_names = train_ds.classes
assert len(class_names) == NUM_CLASSES
print(f"  Classes: {NUM_CLASSES}, Train: {len(train_ds)}")


# %% Cell 6: Class weights + FocalLoss
class_counts = Counter()
for _, label in train_ds.samples:
    class_counts[label] += 1

total = sum(class_counts.values())
weights = []
for i in range(NUM_CLASSES):
    count = class_counts.get(i, 1)
    w = math.sqrt(total / (NUM_CLASSES * count))
    weights.append(w)

class_weights = torch.tensor(weights, dtype=torch.float32).to(DEVICE)

class FocalLoss(nn.Module):
    def __init__(self, weight=None, gamma=2.0, label_smoothing=0.1):
        super().__init__()
        self.gamma = gamma
        self.weight = weight
        self.label_smoothing = label_smoothing

    def forward(self, logits, targets):
        ce = F.cross_entropy(logits, targets, weight=self.weight,
                             label_smoothing=self.label_smoothing, reduction='none')
        pt = torch.exp(-ce)
        focal = ((1. - pt) ** self.gamma) * ce
        return focal.mean()

criterion = FocalLoss(weight=class_weights, gamma=FOCAL_GAMMA, label_smoothing=LABEL_SMOOTHING)


# %% Cell 7: Model + Lightning Module
class HieroglyphClassifier(L.LightningModule):
    def __init__(self, num_classes, lr, criterion, freeze_backbone=False):
        super().__init__()
        self.save_hyperparameters(ignore=['criterion'])
        self.criterion = criterion
        self.lr = lr
        self.model = timm.create_model('mobilenetv3_small_100',
                                       pretrained=True, num_classes=num_classes)
        if freeze_backbone:
            self._freeze_backbone()

    def _freeze_backbone(self):
        for name, param in self.model.named_parameters():
            if 'classifier' not in name:
                param.requires_grad = False

    def unfreeze_top(self, fraction=0.7):
        params = [(n, p) for n, p in self.model.named_parameters()
                  if 'classifier' not in n]
        n_unfreeze = int(len(params) * fraction)
        for name, param in params[-n_unfreeze:]:
            param.requires_grad = True

    def forward(self, x):
        return self.model(x)

    def _shared_step(self, batch, stage):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        preds = logits.argmax(dim=1)
        acc = (preds == y).float().mean()
        self.log(f"{stage}_loss", loss, prog_bar=True)
        self.log(f"{stage}_acc", acc, prog_bar=True)
        return loss

    def training_step(self, batch, batch_idx):
        return self._shared_step(batch, "train")

    def validation_step(self, batch, batch_idx):
        return self._shared_step(batch, "val")

    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, self.parameters()),
            lr=self.lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.trainer.max_epochs)
        return [optimizer], [scheduler]


class KeepAliveCallback(L.Callback):
    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        if batch_idx % 10 == 0:
            print(".", end="", flush=True)
    def on_validation_end(self, trainer, pl_module):
        metrics = trainer.callback_metrics
        acc = metrics.get("val_acc", 0)
        print(f" val_acc={acc:.4f}", flush=True)


# %% Cell 8: Phase 1 — Head training (backbone frozen)
model = HieroglyphClassifier(
    num_classes=NUM_CLASSES, lr=P1_LR,
    criterion=criterion, freeze_backbone=True
)

print("=" * 60)
print("PHASE 1: Head-only training (backbone frozen)")
print("=" * 60)

trainer_p1 = L.Trainer(
    max_epochs=P1_EPOCHS,
    accelerator="auto",
    precision="32-true",
    callbacks=[
        L.callbacks.ModelCheckpoint(
            dirpath=os.path.join(OUT_DIR, "checkpoints"),
            monitor="val_acc", mode="max", save_top_k=1,
            filename="best-p1-{epoch}-{val_acc:.4f}"),
        KeepAliveCallback(),
    ],
    logger=False,
    enable_progress_bar=False,
)
trainer_p1.fit(model, train_loader, val_loader)


# %% Cell 9: Phase 2 — Fine-tune top 70%
print("=" * 60)
print("PHASE 2: Fine-tune top 70% of backbone")
print("=" * 60)

model.unfreeze_top(fraction=0.7)
model.lr = P2_LR

trainer_p2 = L.Trainer(
    max_epochs=P2_EPOCHS,
    accelerator="auto",
    precision="32-true",
    callbacks=[
        L.callbacks.ModelCheckpoint(
            dirpath=os.path.join(OUT_DIR, "checkpoints"),
            monitor="val_acc", mode="max", save_top_k=1,
            filename="best-p2-{epoch}-{val_acc:.4f}"),
        L.callbacks.EarlyStopping(monitor="val_acc", patience=10, mode="max"),
        KeepAliveCallback(),
    ],
    logger=False,
    enable_progress_bar=False,
)
trainer_p2.fit(model, train_loader, val_loader)


# %% Cell 10: Test set evaluation
print("\n" + "=" * 60)
print("TEST SET EVALUATION")
print("=" * 60)

model.eval()
model.to(DEVICE)
all_preds, all_labels, all_probs = [], [], []
with torch.no_grad():
    for x, y in test_loader:
        x = x.to(DEVICE)
        logits = model(x)
        probs = F.softmax(logits, dim=1).cpu().numpy()
        preds = logits.argmax(dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_labels.extend(y.numpy())
        all_probs.extend(probs)

all_preds = np.array(all_preds)
all_labels = np.array(all_labels)
all_probs = np.array(all_probs)

top1_acc = np.mean(all_preds == all_labels)
top5_acc = top_k_accuracy_score(all_labels, all_probs, k=5, labels=list(range(NUM_CLASSES)))

print(f"  Top-1 accuracy: {top1_acc:.4f} ({top1_acc*100:.2f}%)")
print(f"  Top-5 accuracy: {top5_acc:.4f} ({top5_acc*100:.2f}%)")

# Gate checks
GATE_TOP1 = 0.98
GATE_TOP5 = 0.99
print(f"\n  [{'PASS' if top1_acc >= GATE_TOP1 else 'FAIL'}] Top-1 >= {GATE_TOP1}: {top1_acc:.4f}")
print(f"  [{'PASS' if top5_acc >= GATE_TOP5 else 'FAIL'}] Top-5 >= {GATE_TOP5}: {top5_acc:.4f}")

# Worst 10 classes
report = classification_report(all_labels, all_preds, target_names=class_names,
                                output_dict=True, zero_division=0)
worst_classes = sorted(
    [(name, info["f1-score"]) for name, info in report.items()
     if name in class_names],
    key=lambda x: x[1]
)
print(f"\n  Worst 10 classes (by F1):")
for name, f1 in worst_classes[:10]:
    print(f"    {name:10s} F1={f1:.3f}")


# %% Cell 11: Stone-texture test (simulate real stone crops)
print("\n" + "=" * 60)
print("STONE-TEXTURE ROBUSTNESS TEST")
print("=" * 60)

# Apply stone-texture augmentation to test images and measure accuracy
stone_transform = AlbumentationsTransform(
    A.Compose([
        A.Resize(INPUT_SIZE, INPUT_SIZE),
        A.GaussNoise(std_range=(15.0 / 255.0, 50.0 / 255.0), p=0.8),
        A.GaussianBlur(blur_limit=(3, 7), p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.7),
        A.Normalize(mean=(0.0, 0.0, 0.0), std=(1.0, 1.0, 1.0), max_pixel_value=255.0),
        ToTensorV2(),
    ]),
    stone_blender=stone_blender,
    stone_prob=1.0,  # Apply stone texture to ALL test images
)

stone_test_ds = ImageFolder(TEST_DIR, transform=stone_transform)
# Remap
stone_test_ds.class_to_idx = train_ds.class_to_idx
stone_test_ds.classes = train_ds.classes
new_samples = []
for path, _old_idx in stone_test_ds.samples:
    class_name = os.path.basename(os.path.dirname(path))
    new_idx = train_ds.class_to_idx.get(class_name)
    if new_idx is not None:
        new_samples.append((path, new_idx))
stone_test_ds.samples = new_samples
stone_test_ds.targets = [s[1] for s in new_samples]
stone_test_ds.imgs = new_samples

stone_test_loader = DataLoader(stone_test_ds, batch_size=BATCH_SIZE, shuffle=False,
                                num_workers=NUM_WORKERS, pin_memory=True)

stone_preds, stone_labels = [], []
with torch.no_grad():
    for x, y in stone_test_loader:
        x = x.to(DEVICE)
        preds = model(x).argmax(dim=1).cpu().numpy()
        stone_preds.extend(preds)
        stone_labels.extend(y.numpy())

stone_acc = np.mean(np.array(stone_preds) == np.array(stone_labels))
print(f"  Stone-texture accuracy: {stone_acc:.4f} ({stone_acc*100:.2f}%)")
print(f"  [{'PASS' if stone_acc >= 0.50 else 'FAIL'}] Stone acc >= 50%: {stone_acc:.4f}")


# %% Cell 12: ONNX export (fp32)
print("\nExporting to ONNX...", flush=True)
model.eval()
model.to("cpu")

dummy = torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE)
onnx_fp32_path = os.path.join(OUT_DIR, "hieroglyph_classifier.onnx")

torch.onnx.export(
    model.model, dummy, onnx_fp32_path,
    opset_version=18,
    input_names=["input"], output_names=["output"],
    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    dynamo=False,
)

fp32_size = os.path.getsize(onnx_fp32_path) / 1024**2
print(f"  fp32 ONNX: {fp32_size:.1f} MB")

# Validate
sess = ort.InferenceSession(onnx_fp32_path, providers=["CPUExecutionProvider"])
dummy_np = np.random.rand(1, 3, INPUT_SIZE, INPUT_SIZE).astype(np.float32)
out = sess.run(None, {"input": dummy_np})
assert out[0].shape == (1, NUM_CLASSES), f"Expected (1, {NUM_CLASSES}), got {out[0].shape}"
print(f"  Output shape: {out[0].shape}")


# %% Cell 13: Quantize to uint8
from onnxruntime.quantization import quantize_dynamic, QuantType

uint8_path = os.path.join(OUT_DIR, "hieroglyph_classifier_uint8.onnx")
quantize_dynamic(onnx_fp32_path, uint8_path, weight_type=QuantType.QUInt8)

uint8_size = os.path.getsize(uint8_path) / 1024**2
print(f"  fp32:  {fp32_size:.1f} MB")
print(f"  uint8: {uint8_size:.1f} MB")

# Validate uint8
sess_q = ort.InferenceSession(uint8_path, providers=["CPUExecutionProvider"])
out_q = sess_q.run(None, {"input": dummy_np})
assert out_q[0].shape == (1, NUM_CLASSES)

if uint8_size > 8.0:
    print(f"  WARN: uint8 model {uint8_size:.1f} MB > 8 MB browser budget")
else:
    print(f"  PASS: uint8 {uint8_size:.1f} MB <= 8 MB")


# %% Cell 14: Save label_mapping.json + model_metadata.json
# Label mapping (Gardiner code to index)
gardiner_to_idx = {name: i for i, name in enumerate(class_names)}
idx_to_gardiner = {i: name for i, name in enumerate(class_names)}

label_mapping = {
    "num_classes": NUM_CLASSES,
    "gardiner_to_idx": gardiner_to_idx,
    "idx_to_gardiner": idx_to_gardiner,
}
label_path = os.path.join(OUT_DIR, "label_mapping.json")
with open(label_path, "w") as f:
    json.dump(label_mapping, f, indent=2)

metadata = {
    "model_name": "wadjet_hieroglyph_classifier_v2",
    "architecture": "MobileNetV3-Small (timm)",
    "task": "image_classification",
    "num_classes": NUM_CLASSES,
    "input_size": INPUT_SIZE,
    "input_shape": [1, 3, INPUT_SIZE, INPUT_SIZE],
    "normalization": "divide_by_255",
    "output_shape": [1, NUM_CLASSES],
    "quantized": True,
    "quantization": "uint8_dynamic",
    "fp32_size_mb": round(fp32_size, 1),
    "uint8_size_mb": round(uint8_size, 1),
    "training": {
        "p1_epochs": P1_EPOCHS,
        "p2_epochs": P2_EPOCHS,
        "p1_lr": P1_LR,
        "p2_lr": P2_LR,
        "stone_aug_prob": STONE_AUG_PROB,
        "focal_gamma": FOCAL_GAMMA,
        "label_smoothing": LABEL_SMOOTHING,
    },
    "metrics": {
        "test_top1_accuracy": round(float(top1_acc), 4),
        "test_top5_accuracy": round(float(top5_acc), 4),
        "stone_texture_accuracy": round(float(stone_acc), 4),
    },
    "improvements_over_v1": {
        "stone_texture_augmentation": True,
        "aggressive_domain_gap_augmentation": True,
        "more_finetune_epochs": True,
        "lower_finetune_lr": True,
    },
}
meta_path = os.path.join(OUT_DIR, "model_metadata.json")
with open(meta_path, "w") as f:
    json.dump(metadata, f, indent=2)

print(f"Saved: {label_path}")
print(f"Saved: {meta_path}")

# Copy all outputs
for src_name in ["hieroglyph_classifier.onnx", "hieroglyph_classifier_uint8.onnx",
                 "label_mapping.json", "model_metadata.json"]:
    src = os.path.join(OUT_DIR, src_name)
    if os.path.isfile(src):
        print(f"  {src_name}: {os.path.getsize(src)/1024:.0f} KB")


# %% Cell 15: Final summary
print("\n" + "=" * 60)
print("TRAINING SUMMARY — MobileNetV3 Hieroglyph Classifier v2")
print("=" * 60)
print(f"  Architecture:     MobileNetV3-Small")
print(f"  Input:            {INPUT_SIZE}x{INPUT_SIZE}")
print(f"  Classes:          {NUM_CLASSES}")
print(f"  Stone aug prob:   {STONE_AUG_PROB}")
print(f"  ONNX uint8:       {uint8_size:.1f} MB")
print()
print(f"  Test top-1:       {top1_acc*100:.2f}%")
print(f"  Test top-5:       {top5_acc*100:.2f}%")
print(f"  Stone-texture:    {stone_acc*100:.2f}%")
print()

all_pass = True
checks = [
    (f"Top-1 >= {GATE_TOP1*100:.0f}%", top1_acc >= GATE_TOP1),
    (f"Top-5 >= {GATE_TOP5*100:.0f}%", top5_acc >= GATE_TOP5),
    ("Stone acc >= 50%", stone_acc >= 0.50),
    (f"ONNX <= 8 MB", uint8_size <= 8.0),
]
for name, passed in checks:
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    print(f"  [{status}] {name}")

print()
if all_pass:
    print("  ALL GATES PASSED — Classifier ready for deployment!")
else:
    print("  SOME GATES FAILED — Review before deploying.")
    if stone_acc < 0.50:
        print("  Hint: Increase STONE_AUG_PROB, add more real stone crops to training data")

print("\nDone.", flush=True)
