> **Note**: This is a historical document. File paths may reference the old project location (Final_Horus/Wadjet-v2).

# Wadjet v2 — Master Plan (PyTorch + Gemini Vision Rebuild)

> **Status**: PLANNING — Implementation starts on "START" prompt
> **Written**: 2026-03-20
> **Author**: Self-documentation for continuity between sessions
> **Location**: `planning/rebuild/` — see also REBUILD_TASKS.md, PROGRESS.md, START_PROMPTS.md

---

## 0. Executive Summary

### What Was Done (Already Complete ✅)
The **frontend** for Wadjet v2 is **100% complete** (Phase P0–P6). All 9 pages
render, the Black & Gold design system is polished, animations work, mobile is
responsive, accessibility passes, the service worker caches assets — frontend
needs no changes.

**The only broken parts** are:
1. The ML models (Keras/TF.js → `_FusedConv2D` fused op errors at inference)
2. The backend integration files that call those models

### What This Plan Rebuilds
| Component | Old (Broken) | New (This Plan) |
|-----------|-------------|-----------------|
| Hieroglyph Detector | `glyph_detector.pt` → TF.js (broken) | **KEEP** `glyph_detector_uint8.onnx` (works fine) |
| Hieroglyph Classifier | `efficientnet_v2s.keras` → `_FusedConv2D` crash | **PyTorch MobileNetV3-Small → ONNX** |
| Landmark Classifier | `EfficientNetV2.keras` → TF.js crash | **PyTorch EfficientNet-B0 → ONNX** |
| Landmark Enrichment | N/A | **Gemini Vision** (describes + verifies low-confidence cases) |
| Backend pipeline | `hieroglyph_pipeline.py` calls broken Keras | **Fix ONNX Runtime integration** |
| Translation | Disabled at 2 levels | **Re-enable** with corrected threshold (0.25→0.15) |
| Gardiner mapping | Only 71/171 signs mapped | **Complete 171/171** |

### Decision Rationale

**Why PyTorch for both classifiers?**
- `torch.onnx.export()` is native — no `tf2onnx` dependency, no external conversion library
- Kaggle GPU kernels have `torch`, `torchvision`, `timm`, `onnx`, `onnxruntime`, `albumentations` **pre-installed** — no pip failures
- ONNX is directly compatible with existing `ort.InferenceSession()` browser code
- timm has both MobileNetV3-Small (hieroglyphs) AND EfficientNet-B0 (landmarks) with ImageNet weights
- `pytorch-lightning` removes all training boilerplate (checkpointing, multi-GPU auto)

**Why Kaggle for training?**
- Free T4/P100 GPU — no local CUDA setup needed
- Previously failed because `tf2onnx` required internet pip install → **no longer an issue** (PyTorch ONNX export is built-in)
- Dataset uploaded to Kaggle as a private dataset; notebook downloads outputs
- After training: download ONNX + `label_mapping.json` to local project

**Why a local landmark model (EfficientNet-B0)?**
- We have 52-class, well-balanced data (~30k images, min=176/class) — more than enough
- Local model = no API cost, offline-capable, fast, no rate limits
- EfficientNet-B0 chosen over MobileNet: landmark photos are complex real-world scenes
  that need more capacity than simple glyph patches
- Training data: merged dataset (v1 splits + eg-landmarks extra + augmentation, all prepared locally)

**Why Gemini Vision as complementary (not primary)?**
- After local model predicts, Gemini Vision enriches the result: description + interesting facts
- If local model confidence < 0.5 → Gemini also identifies (double-check)
- If Gemini API fails → graceful fallback to local model result only
- This hybrid approach: fast + offline + rich descriptions + low-confidence safety net

**Why keep existing YOLO detector?**
- `glyph_detector_uint8.onnx` already works in browser via ONNX Runtime Web
- It was trained correctly (PyTorch → ONNX natively), never had the Keras issue
- No rebuild needed — just keep it

---

## 1. Data Inventory & Training Platform

### 1.1 Hieroglyph Classification Data
```
Location: D:\Personal attachements\Projects\Final_Horus\Wadjet\
          hieroglyph_model\data\splits\classification\

Structure (ImageFolder-compatible):
  train\
    A1\   000001.png, 000002.png, ...
    A55\  ...
    G17\  ...
    ... (171 classes total)
  val\    (171 classes)
  test\   (171 classes)

Stats:
  - Train: 15,017 images
  - Classes: 171 Gardiner sign codes (A1, A55, Aa15, D1, G17, ...)
  - Format: PNG, variable size
  - NO horizontal flip augmentation (hieroglyphs are direction-sensitive!)
```

### 1.2 Landmark Classification Data (Prepared ✅)
```
Location (Kaggle upload source — PREPARED):
  data/landmark_classification/   ← clean train/val/test, merged + augmented, ready to upload

Structure (ImageFolder-compatible):
  train\
    abu_simbel\     image1.png, image2.jpg, ...
    karnak_temple\  ...
    ... (52 classes total)
  val\  (52 classes)
  test\ (52 classes)

Stats after preparation:
  - Train: 25,710 images | 52 classes | Min=300 | Max=1,573 | Avg=494.4
  - Val:    4,506 images | 52 classes
  - Test:   4,497 images | 52 classes
  - Classes: 52 Egyptian landmarks (abu_simbel, great_pyramids_of_giza, ... )
  - Format: mixed JPG/PNG
  - Data merged from: v1 splits (21,151 train) + eg-landmarks extra (+1,938 for 37 classes)
  - 33 weak classes augmented to 300 minimum (HorizontalFlip ✓, rotation, brightness/contrast)
  - Prep script: scripts/prepare_landmark_data.py (executed ✅)
```

### 1.3 Hieroglyph Classification Data (Prepared ✅)
```
Location (Kaggle upload source — PREPARED):
  data/hieroglyph_classification/   ← clean train/val/test, augmented, ready to upload

Stats after preparation:
  - Train: 16,638 images | 171 classes | Min=80 | Max=413 | Avg=97.3
  - Val:    1,152 images | 167 classes
  - Test:   1,154 images | 169 classes
  - 67 weak classes augmented to 80 minimum (NO horizontal flip!)
  - Augment script: scripts/prepare_hieroglyph_data.py
```

### 1.4 Other Resources
```
Existing ONNX Detector (KEEP — don't rebuild):
  D:\Personal attachements\Projects\Final_Horus\Wadjet\
  hieroglyph_model\models\detection\glyph_detector_uint8.onnx

RAG Embeddings (prepared ✅):
  data/embeddings/corpus.index      ← FAISS index (21.4 MB)
  data/embeddings/corpus_ids.json   ← ID mapping (2.3 MB)

Translation Corpus (prepared ✅):
  data/translation/corpus.jsonl      ← full RAG corpus (2.1 MB)
  data/translation/corpus_train.jsonl, corpus_val.jsonl, corpus_test.jsonl

Old Keras Classifiers (reference only — broken, do not use):
  D:\Personal attachements\Projects\Final_Horus\Wadjet\
  hieroglyph_model\models\classification\efficientnet_v2s.keras

eg-landmarks extra data (MERGED into landmark_classification ✅):
  Originally: data/downloads/eg-landmarks/ (279 classes, ~50MB)
  37 matching classes (+1938 images) merged into data/landmark_classification/train/
  Download folder deleted after merge.
```

**Previous failure (Keras)**: The old Kaggle approach failed because:
1. `tf2onnx` is not pre-installed on Kaggle, and `pip install` requires internet
2. Even if tf2onnx ran, Keras EfficientNetV2 produces `_FusedConv2D` ops that break ONNX Runtime

**Why Kaggle works now (PyTorch)**:
- `torch`, `torchvision`, `timm`, `albumentations`, `onnx`, `onnxruntime` are all **pre-installed** on Kaggle GPU kernels
- `torch.onnx.export()` is built-in — zero extra installs needed
- Only `pytorch-lightning` may need `!pip install lightning` (one line, fast)

**Kaggle account**: `nadermohamedcr7`
**Kaggle credentials**: `C:\Users\Nader\.kaggle\kaggle.json` ✅ (already in place, verified working)
**CLI path** (use full path — `kaggle` not in system PATH):
```
D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\.venv\Scripts\kaggle.exe
```
Or activate venv first (`.\venv\Scripts\Activate.ps1`) then just use `kaggle`.

**Kaggle workflow** (using `kaggle-api` — `D:\Personal attachements\Repos\kaggle-api\`):
```bash
# Credentials already at C:\Users\Nader\.kaggle\kaggle.json — no setup needed!

# ── HIEROGLYPH DATASET ──────────────────────────────────────────────────────
# Step 1a — Upload hieroglyph dataset (source: data/hieroglyph_classification/ — already prepared!)
kaggle datasets create -p "data\hieroglyph_classification" --dir-mode zip
# Dataset ID: nadermohamedcr7/wadjet-hieroglyph-classification

# Step 2a — Push hieroglyph training notebook to Kaggle GPU
kaggle kernels push -p planning/model-rebuild/pytorch/hieroglyph/

# Step 3a — Monitor hieroglyph training
kaggle kernels status nadermohamedcr7/hieroglyph-classifier

# Step 4a — Download hieroglyph outputs after training completes
kaggle kernels output nadermohamedcr7/hieroglyph-classifier -p models/hieroglyph/classifier/

# ── LANDMARK DATASET ─────────────────────────────────────────────────────────
# Step 1b — Upload merged landmark dataset (v1 splits + eg-landmarks + augmented, all-in-one)
kaggle datasets create -p "data\landmark_classification" --dir-mode zip
# Dataset ID: nadermohamedcr7/wadjet-landmark-classification
# Metadata title: "Wadjet Landmark Classification"

# Step 2b — Push landmark training notebook to Kaggle GPU
kaggle kernels push -p planning/model-rebuild/pytorch/landmark/

# Step 3b — Monitor landmark training
kaggle kernels status nadermohamedcr7/landmark-classifier

# Step 4b — Download landmark outputs after training completes
kaggle kernels output nadermohamedcr7/landmark-classifier -p models/landmark/classifier/
```
Hieroglyph outputs land in `models/hieroglyph/classifier/` — ready for Phase C.
Landmark outputs land in `models/landmark/classifier/` — ready for Phase C.

**Kaggle archive** (old TF/Keras notebooks — do not use for training):
- `planning/model-rebuild/kaggle-archive/` — kept for reference only

**Active training notebooks**:
- `planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier.ipynb` — hieroglyph MobileNetV3-Small
- `planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb` — landmark EfficientNet-B0
(write locally → push to Kaggle via `kaggle kernels push`)

---

## 2. Target Architecture

### 2.1 Hieroglyph Classifier (New)
```
Architecture:   torchvision.models.mobilenet_v3_small (ImageNet pretrained)
Input:          [1, 3, 128, 128] float32 NCHW (PyTorch native)
Output:         [1, 171] softmax probabilities
Export:         torch.onnx.export() → opset 17 → hieroglyph_classifier.onnx
Quantize:       onnxruntime.quantization.quantize_dynamic() → uint8
Final file:     hieroglyph_classifier_uint8.onnx (~3-5 MB)

Training strategy:
  Phase 1 — Head only (5 epochs, lr=1e-3, backbone frozen)
  Phase 2 — Fine-tune top 70% layers (30 epochs, lr=1e-4 cosine decay)
  Loss:     FocalLoss(gamma=2.0) + class weights (sqrt-inverse-frequency)
  Augment:  random brightness/contrast/saturation + rotation ±10° (NO h-flip!)
  Tracking: WandB (optional) or just print metrics
```

### 2.2 Landmark Classifier (New — PyTorch EfficientNet-B0)
```
Architecture:   timm.create_model('efficientnet_b0', pretrained=True, num_classes=52)
Input:          [1, 3, 224, 224] float32 NCHW (PyTorch native)
Output:         [1, 52] softmax probabilities
Export:         torch.onnx.export() → opset 17 → landmark_classifier.onnx
Quantize:       onnxruntime.quantization.quantize_dynamic() → uint8
Final file:     landmark_classifier_uint8.onnx (~15-20 MB)
Label mapping:  landmark_label_mapping.json → {0: "abu_simbel", ..., 51: "white_desert"}

Training strategy:
  Dataset:  52 Egyptian landmarks, 25,710 train images (min=300, max=1573, avg=494)
            Merged from: v1 splits + eg-landmarks extra + augmentation (all done locally ✅)
            Single Kaggle dataset: nadermohamedcr7/wadjet-landmark-classification
  Phase 1 — Head only (5 epochs, lr=1e-3, backbone frozen)
  Phase 2 — Fine-tune top 50% layers (30 epochs, lr=5e-5 cosine decay)
  Loss:     CrossEntropy + label smoothing 0.1 + class weights (sqrt-inverse-frequency)
  Augment:  HorizontalFlip ✓ + rotation + brightness/contrast/shadow (real-world photos)
  Tracking: print metrics per epoch

Why EfficientNet-B0 (not MobileNetV3-Small)?
  - Landmark photos are complex real-world scenes with backgrounds, crowds, lighting
  - 52 classes are diverse (mosques, pyramids, museums, oases, statues...)
  - EfficientNet-B0 has better capacity with acceptable model size (~15-20 MB uint8)
  - MobileNetV3-Small is good for glyph patches (simple, uniform background)
    but under-powered for diverse real-world landmark photos
```

### 2.3 Landmark Identification Endpoint (Hybrid: Local Model + Gemini)
```
Endpoint:   POST /api/explore/identify
Input:      multipart image upload

Flow:
  1. Run local landmark_classifier_uint8.onnx → get predicted class + confidence
  2. If confidence >= 0.5:
       Return: {name, slug, confidence, ai_description (from Gemini)}
       → Gemini call is optional enrichment (description + facts), not identification
  3. If confidence < 0.5:
       Also call Gemini Vision → gemini-2.5-flash identifies the landmark
       Return best answer from model + gemini with disclaimer
  4. If ONNX fails:
       Fall back to Gemini Vision only
  5. If both fail:
       Return error with user-friendly message

Output JSON:
  {
    "name": "Great Pyramids of Giza",
    "slug": "great_pyramids_of_giza",
    "confidence": 0.94,
    "source": "local_model",      ← or "gemini" or "hybrid"
    "description": "...",         ← Gemini-generated description
    "top3": [...]                 ← top-3 predictions from ONNX model
  }
```

### 2.4 Hieroglyph Detector (Keep Unchanged)
```
File:       models/hieroglyph/detection/glyph_detector_uint8.onnx
Input:      [1, 3, 640, 640] float32 NCHW
Output:     YOLOv8 outputs (bboxes + scores)
No changes needed!
```

---

## 2.5 Real-Time Camera Architecture (Already Implemented — Fix Only)

The Scan page has **two input modes** (both already built in the frontend):

### Mode 1 — Photo Upload
`scan.html` → drag-drop / `<input type="file">` → `pipeline.processImage(imgElement)`
→ detect → classify → transliterate → translate

### Mode 2 — Real-Time Live Camera ✅ Implemented in JS
`scan.html` → "Camera" tab → `navigator.mediaDevices.getUserMedia()` → `<video>` element
→ `pipeline.startCameraLoop(video, overlayCanvas)` → continuous detection at ~10 fps

**How the camera loop works** (`hieroglyph-pipeline.js`):
```javascript
// startCameraLoop() — continuous detection on live video
HieroglyphPipeline.prototype.startCameraLoop = function(video, overlayCanvas, opts) {
    // Draws gold bounding boxes (#D4AF37) in real-time on the overlay canvas
    // Calls detect(video) every frame — video is accepted as source just like an image
    // Draws confidence % above each box
    // Calls opts.onDetections(boxes) callback if provided
};

// captureAndClassify() — snap a frame from video and run full pipeline
HieroglyphPipeline.prototype.captureAndClassify = async function(video) {
    // Captures current video frame to a canvas
    // Then runs processImage(canvas) → detect → classify → translit → translate
};
```

**Camera data flow**:
```
getUserMedia({video: true})
  → <video x-ref="video" autoplay playsinline>
  → startCameraLoop(video, overlayCanvas)
    → detect(video)              ← NCHW ✅ (detector already correct)
    → draw gold boxes on canvas  ← purely canvas overlay, no DOM changes
  → user clicks "Capture"
  → captureAndClassify(video)
    → processImage(canvas snapshot)
      → detect(canvas) ✅
      → classify(canvas, boxes)  ← ⚠️ NHWC BUG → fixed in Phase D
```

**Status after Phase D fix**:
- Detection overlay: ✅ Works (NCHW)
- Capture + classify: ✅ Works (after NCHW fix to `classify()` + `_warmup()`)

**No backend needed for camera mode** — ONNX Runtime Web runs entirely in browser
(WASM execution provider). The camera tab in `scan.html` has a "Browser mode" toggle
that switches to client-side ONNX inference (no server call).

**Landmark Identify** (`explore.html`):
- Photo upload ONLY — no live camera mode for landmarks
- Uses HTMX → POST `/api/explore/identify` → Gemini Vision API
- The user uploads a photo from gallery/device storage

---

## 3. Implementation Phases

### Phase A: Kaggle Setup & Verification (1 session)
> **READ BEFORE STARTING**: `CLAUDE.md`, `planning/CONSTITUTION.md`
> **REPO**: `D:\Personal attachements\Repos\kaggle-api\` — Kaggle CLI for dataset upload + notebook push

**A.1** Install the Kaggle CLI and configure credentials:
```bash
pip install kaggle
# Download kaggle.json from kaggle.com → Account → Settings → API → Create New Token
# Place at: C:\Users\<you>\.kaggle\kaggle.json
kaggle --version   # should print version
```

**A.2** Zip and upload the hieroglyph dataset to Kaggle as a private dataset:
```bash
# dataset-metadata.json already created ✅ at data/hieroglyph_classification/dataset-metadata.json
# Upload:
kaggle datasets create -p "data\hieroglyph_classification" --dir-mode zip
```

**A.2b** Upload the merged landmark dataset:
```bash
# dataset-metadata.json already created ✅ at data/landmark_classification/dataset-metadata.json
# This dataset contains: v1 splits + eg-landmarks extra + augmentation (25,710 train, 52 classes, min=300)
# Upload:
kaggle datasets create -p "data\landmark_classification" --dir-mode zip
```

**A.3** Copy ONNX detector to project (local — needed for backend Phase C):
```bash
# From old project:
copy "D:\Personal attachements\Projects\Final_Horus\Wadjet\hieroglyph_model\models\detection\glyph_detector_uint8.onnx" "models\hieroglyph\detection\glyph_detector_uint8.onnx"
```

**A.4** Create skeleton notebooks + `kernel-metadata.json` for Kaggle push:
```
planning/model-rebuild/pytorch/
  hieroglyph/
    hieroglyph_classifier.ipynb   ← hieroglyph training notebook
    kernel-metadata.json           ← GPU, dataset slug, notebook title
  landmark/
    landmark_classifier.ipynb     ← landmark training notebook
    kernel-metadata.json           ← GPU, dataset slugs, notebook title
```

`kernel-metadata.json` for hieroglyph notebook:
```json
{
  "id": "nadermohamedcr7/hieroglyph-classifier",
  "title": "Wadjet Hieroglyph Classifier",
  "code_file": "hieroglyph_classifier.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": false,
  "dataset_sources": ["nadermohamedcr7/wadjet-hieroglyph-classification"],
  "competition_sources": [],
  "kernel_sources": []
}
```

`kernel-metadata.json` for landmark notebook:
```json
{
  "id": "nadermohamedcr7/landmark-classifier",
  "title": "Wadjet Landmark Classifier",
  "code_file": "landmark_classifier.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": false,
  "dataset_sources": [
    "nadermohamedcr7/wadjet-landmark-classification"
  ],
  "competition_sources": [],
  "kernel_sources": []
}
```

**Checkpoint**: `kaggle datasets list --mine` shows both `wadjet-hieroglyph-classification` AND `wadjet-landmark-classification`. Both `kernel-metadata.json` files are valid.

---

### Phase B: Hieroglyph Classifier Training (1-2 sessions)
> **SKILL**: Load `ml-engineer` skill from repos before starting
> **PLATFORM**: Kaggle GPU (T4 or P100) — push with `kaggle kernels push`, download with `kaggle kernels output`
> **REFERENCE**: `D:\Personal attachements\Repos\kaggle-api\` — CLI to push notebook + download outputs
> **REFERENCE**: `D:\Personal attachements\Repos\pytorch-image-models\` (timm — pretrained MobileNetV3, pre-installed on Kaggle)
> **REFERENCE**: `D:\Personal attachements\Repos\pytorch-lightning\` (training loop — `!pip install lightning` at top of notebook)
> **REFERENCE**: `D:\Personal attachements\Repos\albumentations\` (augmentation, pre-installed on Kaggle)
> **REFERENCE**: `D:\Personal attachements\Repos\kornia\` (GPU-native augmentation, pre-installed on Kaggle)
> **REFERENCE**: `D:\Personal attachements\Repos\mlflow\` (experiment tracking — pre-installed on Kaggle, OR use wandb)
> **REFERENCE**: `D:\Personal attachements\Repos\optuna\` (optional: hyperparameter tuning if accuracy < 70%)
> **IF STUCK**: See `04-Meta-PyTorch\02-PyTorch\` for patterns

**B.0 (Optional but recommended)** Inspect dataset with fiftyone before training:
```python
# D:\Personal attachements\Repos\fiftyone\
import fiftyone as fo
dataset = fo.Dataset.from_dir(
    dataset_dir=TRAIN_DIR,
    dataset_type=fo.types.ImageClassificationDirectoryTree,
)
session = fo.launch_app(dataset)  # Visual browser — spot bad labels / duplicates
```

**B.1** Create `planning/model-rebuild/pytorch/hieroglyph_classifier.ipynb`

Notebook structure:
```
Cell 1:  Configuration (paths, hyperparams)
Cell 2:  Dataset + DataLoader (torchvision.ImageFolder)
Cell 3:  Albumentations augmentation pipeline (NO h-flip!)
Cell 4:  Focal Loss + class weights
Cell 5:  Model (PyTorch Lightning LightningModule wrapping MobileNetV3-Small)
Cell 6:  pytorch-lightning Trainer — Phase 1 (backbone frozen)
Cell 7:  pytorch-lightning Trainer — Phase 2 (fine-tune top 70%)
Cell 8:  Evaluation (classification report, per-class F1)
Cell 9:  ONNX Export (torch.onnx.export)
Cell 10: ONNX Validation (onnxruntime inference check)
Cell 11: ONNX Quantization (uint8)
Cell 12: Save label_mapping.json + model_metadata.json
```

**B.2** Key code patterns to use:
```python
# Cell 0 — install only what's missing on Kaggle
!pip install -q lightning  # pytorch-lightning; everything else is pre-installed

# Data loading (no TFRecord reader needed — straight ImageFolder!)
from torchvision.datasets import ImageFolder
from torchvision import transforms
import pytorch_lightning as pl
import timm

# On Kaggle — dataset is mounted at /kaggle/input/<dataset-slug>/
TRAIN_DIR = "/kaggle/input/wadjet-hieroglyph-classification/train"
VAL_DIR   = "/kaggle/input/wadjet-hieroglyph-classification/val"
TEST_DIR  = "/kaggle/input/wadjet-hieroglyph-classification/test"
# Outputs go to /kaggle/working/ — downloaded after run
OUT_DIR   = "/kaggle/working"

# Model — use timm for cleaner pretrained loading
backbone = timm.create_model('mobilenetv3_small_100', pretrained=True, num_classes=171)
# OR torchvision:
import torchvision.models as models
backbone = models.mobilenet_v3_small(weights='IMAGENET1K_V1')
backbone.classifier[3] = torch.nn.Linear(1024, 171)

# ONNX Export (native — no tf2onnx!)
dummy = torch.randn(1, 3, 128, 128).to(device)
torch.onnx.export(
    model, dummy, "hieroglyph_classifier.onnx",
    opset_version=17,
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={'input': {0: 'batch'}, 'output': {0: 'batch'}}
)

# ONNX Quantization
from onnxruntime.quantization import quantize_dynamic, QuantType
quantize_dynamic("hieroglyph_classifier.onnx", 
                 "hieroglyph_classifier_uint8.onnx",
                 weight_type=QuantType.QUInt8)
```

**B.3** After training runs on Kaggle, download outputs:
```bash
# Download all outputs from the Kaggle notebook to local project
kaggle kernels output nadermohamedcr7/hieroglyph-classifier -p models/hieroglyph/classifier/
```

Expected outputs in `models/hieroglyph/classifier/`:
```
  hieroglyph_classifier.onnx          ← fp32 (backup)
  hieroglyph_classifier_uint8.onnx    ← production (use this)
  model_metadata.json                  ← {"input_size": 128, "num_classes": 171, "format": "NCHW"}
  label_mapping.json                   ← {0: "A1", 1: "A55", ..., 170: "Z11"}
```

**Checkpoint**: Run ONNX validation:
```python
import onnxruntime as ort, numpy as np
sess = ort.InferenceSession("hieroglyph_classifier_uint8.onnx")
dummy = np.random.rand(1, 3, 128, 128).astype(np.float32)
out = sess.run(None, {'input': dummy})
assert out[0].shape == (1, 171), "Wrong output shape!"
print(f"Max class prob: {out[0].max():.4f}")
```

---

### Phase B2: Landmark Classifier Training (1-2 sessions)
> **SKILL**: Load `ml-engineer`, `computer-vision-expert` skills before starting
> **PLATFORM**: Kaggle GPU (T4 or P100) — uses BOTH landmark datasets attached
> **REFERENCE**: `D:\Personal attachements\Repos\pytorch-image-models\` (timm — pretrained EfficientNet-B0)
> **REFERENCE**: `D:\Personal attachements\Repos\pytorch-lightning\` (training loop — `!pip install lightning`)
> **REFERENCE**: `D:\Personal attachements\Repos\albumentations\` (augmentation, pre-installed on Kaggle)
> **REFERENCE**: `D:\Personal attachements\Repos\kornia\` (GPU-native augmentation — optional)
> **REFERENCE**: `D:\Personal attachements\Repos\optuna\` (optional: hyperparameter tuning if accuracy < 75%)
> **IF STUCK**: See `04-Meta-PyTorch\02-PyTorch\` for patterns

**B2.1** Create `planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb`

Notebook structure:
```
Cell 1:  Configuration (paths, hyperparams, EG_TO_V1 class mapping)
Cell 2:  Dataset merge (v1 splits + eg-landmarks extra via EG_TO_V1 mapping)
Cell 3:  DataLoader (torchvision.ImageFolder after merged directory setup)
Cell 4:  Albumentations augmentation pipeline (HorizontalFlip ✓ allowed for real photos!)
Cell 5:  Class weights (sqrt-inverse-frequency) + on-the-fly augment to TARGET_MIN=300
Cell 6:  Model (timm EfficientNet-B0 + Lightning Module)
Cell 7:  Phase 1 training (head only, backbone frozen, 5 epochs)
Cell 8:  Phase 2 fine-tune (top 50% layers, 30 epochs, cosine lr)
Cell 9:  Evaluation (per-class F1, top-3 accuracy)
Cell 10: ONNX export (torch.onnx.export, opset=17, NCHW)
Cell 11: ONNX validation
Cell 12: ONNX quantization (uint8)
Cell 13: Save landmark_label_mapping.json (sorted class names)
```

**B2.2** EG_TO_V1 class mapping — paste this dict into Cell 1:
```python
# Maps eg-landmarks folder names → our v1 snake_case class names
EG_TO_V1 = {
    "Abu_Simbel":                         "abu_simbel",
    "Akhenaten":                          "akhenaten",
    "Al_Azhar_Mosque":                    "al_azhar_mosque",
    "Al_Azhar_Park":                      "al_azhar_park",
    "Muizz_Street":                       "al_muizz_street",
    "Amenhotep_III":                      "amenhotep_iii",
    "Aswan_High_Dam":                     "aswan_high_dam",
    "Bab_Zuweila":                        "bab_zuweila",
    "Baron_Empain_Palace":                "baron_empain_palace",
    "Bent_Pyramid":                       "bent_pyramid",
    "Great_Library_of_Alexandria":        "bibliotheca_alexandrina",
    "Cairo_Citadel":                      "cairo_citadel",
    "Cairo_Tower":                        "cairo_tower",
    "Catacombs_of_Kom_el_Shuqafa":        "catacombs_of_kom_el_shoqafa",
    "Qaitbay_Citadel":                    "citadel_of_qaitbay",
    "Colossi_of_Memnon":                  "colossi_of_memnon",
    "Deir_el_Medina":                     "deir_el_medina",
    "Dendera_Temple":                     "dendera_temple",
    "Temple_of_Edfu":                     "edfu_temple",
    "Egyptian_Museum":                    "egyptian_museum_cairo",
    "Grand_Egyptian_Museum":              "grand_egyptian_museum",
    "Pyramids_of_Giza":                   "great_pyramids_of_giza",
    "Great_Sphinx_of_Giza":               "great_sphinx_of_giza",
    "Hanging_Church":                     "hanging_church",
    "Great_Hypostyle_Hall_of_Karnak":     "karnak_temple",
    "Khan_El_Khalili":                    "khan_el_khalili",
    "Luxor_Temple":                       "luxor_temple",
    "Mask_Of_Tutankhamun":                "mask_of_tutankhamun",
    "Medinet_Habu":                       "medinet_habu",
    "Montaza_Palace":                     "montaza_palace",
    "Muhammad_Ali_Mosque":                "muhammad_ali_mosque",
    "Nefertiti_Bust":                     "nefertiti_bust",
    "Philae_Temple":                      "philae_temple",
    "Pyramid_of_Djoser":                  "pyramid_of_djoser",
    "Ramesses_II":                        "ramesses_ii",
    "Red_Pyramid":                        "red_pyramid",
    "Mortuary_Temple_of_Hatshepsut":      "temple_of_hatshepsut",
    "Tomb_of_Nefertari":                  "tomb_of_nefertari",
    "Valley_of_the_Kings":                "valley_of_the_kings",
    "White_Desert":                       "white_desert",
    "Pompeys_Pillar":                     "pompeys_pillar",
    "Siwa":                               "siwa_oasis",
}
```

**B2.3** Key training code patterns:
```python
# Cell 0 — install only what's missing
!pip install -q lightning

# On Kaggle — single merged dataset mounted at:
TRAIN = "/kaggle/input/wadjet-landmark-classification/train"
VAL   = "/kaggle/input/wadjet-landmark-classification/val"
TEST  = "/kaggle/input/wadjet-landmark-classification/test"
OUT_DIR  = "/kaggle/working"
# NOTE: Data is already merged + augmented. No eg-landmarks merge step needed!

# Model — EfficientNet-B0 with 52 classes
import timm
model = timm.create_model('efficientnet_b0', pretrained=True, num_classes=52)

# ONNX Export
dummy = torch.randn(1, 3, 224, 224).to(device)
torch.onnx.export(
    model, dummy, "landmark_classifier.onnx",
    opset_version=17,
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={'input': {0: 'batch'}, 'output': {0: 'batch'}}
)

# ONNX Quantization
from onnxruntime.quantization import quantize_dynamic, QuantType
quantize_dynamic("landmark_classifier.onnx",
                 "landmark_classifier_uint8.onnx",
                 weight_type=QuantType.QUInt8)
```

**B2.4** After training runs on Kaggle, download outputs:
```bash
kaggle kernels output nadermohamedcr7/landmark-classifier -p models/landmark/classifier/
```

Expected outputs in `models/landmark/classifier/`:
```
  landmark_classifier.onnx          ← fp32 (backup)
  landmark_classifier_uint8.onnx    ← production (use this, ~15-20MB)
  model_metadata.json                ← {"input_size": 224, "num_classes": 52, "format": "NCHW"}
  landmark_label_mapping.json        ← {0: "abu_simbel", 1: "akhenaten", ..., 51: "white_desert"}
```

**Checkpoint**: Run ONNX validation:
```python
import onnxruntime as ort, numpy as np
sess = ort.InferenceSession("landmark_classifier_uint8.onnx")
dummy = np.random.rand(1, 3, 224, 224).astype(np.float32)
out = sess.run(None, {'input': dummy})
assert out[0].shape == (1, 52), "Wrong output shape!"
print(f"Max class prob: {out[0].max():.4f}")
```

**Gate**: val accuracy > 75%, ONNX output shape [1, 52] confirmed.

---

### Phase C: Backend Integration (1 session)
> **SKILL**: Load `fastapi-pro` skill from repos
> **READ**: `app/core/hieroglyph_pipeline.py`, `app/core/gardiner.py`
> **READ**: `app/api/scan.py`, `app/api/explore.py`
> **REFERENCE**: `D:\Personal attachements\Repos\sentence-transformers\` — bge-m3 embeddings used in `rag_translator.py`
> **REFERENCE**: `D:\Personal attachements\Repos\faiss\` — FAISS index used in `rag_translator.py` (debug if search fails)
> **REFERENCE**: `D:\Personal attachements\Repos\05-LangChain\langchain\` — LangChain patterns if `rag_translator.py` uses chains
> **REFERENCE**: `D:\Personal attachements\Repos\01-Google-AI\` — Gemini Vision multimodal API examples (for `identify_landmark`)
> **REFERENCE**: `D:\Personal attachements\Repos\Prompt-Engineering-Guide\` — prompt engineering patterns for identify_landmark prompt design

**C.1 Fix `app/core/hieroglyph_pipeline.py`**

The pipeline currently loads the ONNX classifier but may have path/format issues.
Key changes needed:
- Input preprocessing: PIL → numpy → `[1, 3, 128, 128]` float32 NCHW (NOT NHWC!)
- Model path: `models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx`
- Output: argmax → class index → gardiner code via `label_mapping.json`
- Threshold: drop from 0.25 → 0.15 (more detections)

```python
# IMPORTANT: PyTorch-trained ONNX needs NCHW input!
# (Keras was NHWC — this is the critical format change)

def preprocess_for_classifier(image_pil: Image.Image) -> np.ndarray:
    """Resize + normalize → NCHW float32 for PyTorch ONNX classifier."""
    img = image_pil.resize((128, 128)).convert('RGB')
    arr = np.array(img, dtype=np.float32) / 255.0      # HWC [128, 128, 3]
    arr = arr.transpose(2, 0, 1)                        # CHW [3, 128, 128]
    arr = arr[np.newaxis, ...]                          # NCHW [1, 3, 128, 128]
    return arr
```

**C.2 Fix `app/core/gardiner.py`**

Currently only 71/171 signs are mapped. Need to complete all 171.
Reference file: `D:\Personal attachements\Projects\Final_Horus\Wadjet\hieroglyph_model\data\reference\`
or check the label_mapping.json generated during training.

**C.3 Re-enable translation pipeline**

Translation is disabled at 2 levels. Check:
- `app/core/rag_translator.py` — remove the "disabled" flag
- `app/api/scan.py` — the CONFIDENCE_THRESHOLD may be too high (set to 0.15)
- `app/core/transliteration.py` — verify it handles 171-class output

**C.4 Add hybrid landmark identification endpoint**

New endpoint in `app/api/explore.py` (local ONNX model first, then Gemini):
```python
@router.post("/api/explore/identify")
async def identify_landmark(
    file: UploadFile,
    settings = Depends(get_settings)
):
    image_bytes = await file.read()

    # Step 1: Run local ONNX model
    from app.core.landmark_pipeline import LandmarkClassifier
    classifier = get_landmark_classifier()    # singleton, loaded at startup
    onnx_result = classifier.predict(image_bytes)
    # Returns: {"slug": "abu_simbel", "name": "Abu Simbel", "confidence": 0.94, "top3": [...]}

    # Step 2: Decide output source
    if onnx_result["confidence"] >= 0.5:
        # High confidence → local model result + Gemini description (enrichment only)
        source = "local_model"
        from app.core.gemini_service import GeminiService
        gemini = GeminiService(settings)
        description = await gemini.describe_landmark(onnx_result["slug"])
    else:
        # Low confidence → also ask Gemini Vision to identify
        from app.core.gemini_service import GeminiService
        gemini = GeminiService(settings)
        gemini_result = await gemini.identify_landmark(image_bytes)
        source = "hybrid"
        description = gemini_result.get("description", "")
        if gemini_result.get("confidence", 0) > onnx_result["confidence"]:
            onnx_result.update(gemini_result)  # Gemini wins if more confident

    return {
        "name": onnx_result["name"],
        "slug": onnx_result["slug"],
        "confidence": onnx_result["confidence"],
        "source": source,
        "description": description,
        "top3": onnx_result.get("top3", [])
    }
```

Add to `app/core/gemini_service.py`:
```python
async def identify_landmark(self, image_bytes: bytes) -> dict:
    """Gemini Vision fallback — used only when ONNX confidence < 0.5."""
    prompt = """Identify which Egyptian landmark or artifact this photo shows.
Respond ONLY with valid JSON (no markdown or explanation):
{
  "name": "Great Pyramids of Giza",
  "slug": "great_pyramids_of_giza",
  "confidence": 0.95,
  "description": "Built by pharaohs of the 4th dynasty...",
  "top3": [{"name": "...", "slug": "...", "confidence": 0.95}]
}
If not an Egyptian landmark, return confidence: 0.0."""
    # ... Gemini multimodal API call ...

async def describe_landmark(self, slug: str) -> str:
    """Get enrichment description for a confirmed landmark (high-confidence case)."""
    # ... lightweight Gemini text call ...
```

Add `app/core/landmark_pipeline.py` (new file):
```python
import onnxruntime as ort
import numpy as np
import json
from PIL import Image
import io

class LandmarkClassifier:
    """Local ONNX EfficientNet-B0 classifier for 52 Egyptian landmarks."""
    def __init__(self, model_path: str, label_mapping_path: str):
        self.session = ort.InferenceSession(model_path)
        with open(label_mapping_path) as f:
            self.labels = json.load(f)   # {0: "abu_simbel", ...}

    def predict(self, image_bytes: bytes) -> dict:
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB').resize((224, 224))
        arr = np.array(img, dtype=np.float32) / 255.0
        arr = arr.transpose(2, 0, 1)[np.newaxis, ...]   # NCHW [1, 3, 224, 224]
        logits = self.session.run(None, {'input': arr})[0][0]
        probs = np.exp(logits) / np.exp(logits).sum()   # softmax
        top3_idx = probs.argsort()[-3:][::-1]
        slug = self.labels[str(top3_idx[0])]
        return {
            "slug": slug,
            "name": slug.replace('_', ' ').title(),
            "confidence": float(probs[top3_idx[0]]),
            "top3": [{"slug": self.labels[str(i)], "confidence": float(probs[i])} for i in top3_idx]
        }
```

**C.5 Update `app/api/explore.py`**

Remove the old TF.js-based identification endpoint and all references.
Wire in the new hybrid endpoint defined above.
Update the response schema to match `{name, slug, confidence, source, description, top3}`.

**Checkpoint**: 
```bash
curl -X POST http://localhost:8000/api/scan -F "file=@test_glyph.jpg"
# Should return: glyphs detected → classified → transliterated → translated
curl -X POST http://localhost:8000/api/explore/identify -F "file=@pyramids.jpg"
# Should return: {"name": "Pyramids of Giza", "confidence": 0.97, ...}
```

---

### Phase D: Frontend Updates (1 session)
> **SKILL**: Load `tailwind-patterns` skill from repos
> **READ**: `app/templates/scan.html`, `app/templates/explore.html`
> **READ**: `app/static/js/hieroglyph-pipeline.js`

**D.1 Update `app/static/js/hieroglyph-pipeline.js`**

CRITICAL CHANGE: PyTorch → ONNX models use NCHW, not NHWC. Two places must change:

**Place 1 — `_warmup()` dummy tensor (runs at model load):**
```javascript
// OLD (NHWC — causes warmup crash or wrong shape with PyTorch model):
var dummyCls = new ort.Tensor('float32', new Float32Array(1 * s * s * 3), [1, s, s, 3]);
// NEW (NCHW):
var dummyCls = new ort.Tensor('float32', new Float32Array(1 * 3 * s * s), [1, 3, s, s]);
```

**Place 2 — `classify()` pixel loop + tensor shape:**
```javascript
// OLD (NHWC interleaved loop):
floats[p * 3]     = imgData[p * 4]     / 255.0;
floats[p * 3 + 1] = imgData[p * 4 + 1] / 255.0;
floats[p * 3 + 2] = imgData[p * 4 + 2] / 255.0;
var inputTensor = new ort.Tensor('float32', floats, [1, size, size, 3]);

// NEW (NCHW planar — matches the detector's existing loop):
floats[p]                  = imgData[p * 4]     / 255.0;  // R plane
floats[pixelCount + p]     = imgData[p * 4 + 1] / 255.0;  // G plane
floats[2 * pixelCount + p] = imgData[p * 4 + 2] / 255.0;  // B plane
var inputTensor = new ort.Tensor('float32', floats, [1, 3, size, size]);
```

Model path update:
```javascript
// OLD: /models/hieroglyph/classifier/mobilenet_v3_small_uint8.onnx
// NEW: /models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx
```

> Note: `startCameraLoop()` only calls `detect()` — detection is already NCHW ✅.
> `captureAndClassify()` calls `processImage()` which calls `classify()` — inherits the fix.

**D.2 Update `app/templates/explore.html`**

Remove the TF.js landmark identification code entirely.
Add HTMX call to the new Gemini Vision endpoint:
```html
<!-- Remove all tf.loadLayersModel() and TF.js code -->
<!-- Add: -->
<form hx-post="/api/explore/identify" 
      hx-encoding="multipart/form-data"
      hx-target="#identify-result"
      hx-indicator="#identify-spinner">
  <input type="file" name="file" accept="image/*">
  <button class="btn-gold">Identify Landmark</button>
</form>
<div id="identify-result"></div>
```

**D.3 Update service worker cache version**

In `app/static/sw.js`:
```javascript
const CACHE_VERSION = 'v15';  // Bump from v14
const MODEL_CACHE = 'wadjet-models-v15';
```

In `app/templates/base.html`:
```html
<!-- Bump ?v= cache busters -->
<link rel="stylesheet" href="/static/dist/styles.css?v=15">
<script src="/static/js/app.js?v=15"></script>
```

**Checkpoint**: Open browser → scan a hieroglyph image → see classification with
Gardiner code → transliteration → translation. Upload landmark photo → Gemini
identifies it → redirect to detail page.

---

### Phase E: Integration Testing & Deploy (1 session)
> **SKILL**: Load `deployment-engineer`, `docker-expert` skills
> **READ**: `Dockerfile`, `render.yaml`, `docker-compose.yml`
> **REFERENCE**: `D:\Personal attachements\Repos\BentoML\` — model packaging into Docker container (alternative if raw Dockerfile is complex)
> **REFERENCE**: `D:\Personal attachements\Repos\18-Security\gitleaks\` — scan codebase for accidentally committed API keys before deploy
> **REFERENCE**: `D:\Personal attachements\Repos\18-Security\Top10\` — OWASP security review: file upload, injection, access control

**E.1 Run full E2E test locally**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Test every feature manually:
# [ ] Landing page loads
# [ ] Scan: upload hieroglyph → full pipeline works
# [ ] Dictionary: 171 signs visible
# [ ] Write: text → hieroglyphs
# [ ] Explore: browse landmarks, identify photo via Gemini
# [ ] Chat: Thoth chatbot responds
# [ ] Quiz: generates questions
```

**E.2 Build production CSS**:
```bash
npm run build   # Minified TailwindCSS
```

**E.3 Fix Dockerfile**:
```dockerfile
# Multi-stage build
FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY . .
# NOTE: models/ are git-ignored — must be copied/mounted separately in prod
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**E.4 Deploy to Render**:
- Render free tier: 512MB RAM — the ONNX classifier (~5MB) loads fine
- Set environment variables: `GEMINI_API_KEYS`, `SECRET_KEY`
- Models must be committed or mounted (not git-ignored on Render)

---

## 4. File Map (Quick Reference)

### Files to KEEP (no changes)
| File | Reason |
|------|--------|
| `app/templates/*.html` | Frontend is complete |
| `app/static/css/input.css` | CSS is complete |
| `app/static/js/app.js` | Alpine.js globals are fine |
| `app/core/gemini_service.py` | Just add `identify_landmark()` |
| `app/core/thoth_chat.py` | Chat works fine |
| `app/core/quiz_engine.py` | Quiz works fine |
| `app/core/recommendation_engine.py` | Works fine |
| `models/hieroglyph/detection/` | ONNX detector WORKS |
| `data/` | All JSON landmark data intact |

### Files to CREATE
| File | What |
|------|------|
| `planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier.ipynb` | PyTorch hieroglyph training notebook |
| `planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb` | PyTorch landmark training notebook |
| `models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx` | Output of hieroglyph training |
| `models/hieroglyph/classifier/label_mapping.json` | `{0: "A1", 1: "A55", ...}` |
| `models/hieroglyph/classifier/model_metadata.json` | Input size, classes, format |
| `models/landmark/classifier/landmark_classifier_uint8.onnx` | Output of landmark training |
| `models/landmark/classifier/landmark_label_mapping.json` | `{0: "abu_simbel", ..., 51: "white_desert"}` |
| `models/landmark/classifier/model_metadata.json` | Input size (224), classes (52), format |
| `app/core/landmark_pipeline.py` | ONNX inference wrapper for landmark classifier |
| `app/templates/partials/identify_result.html` | HTMX partial for identify response |

### Files to FIX
| File | What to Fix |
|------|------------|
| `app/core/hieroglyph_pipeline.py` | NCHW input, correct ONNX path, lower threshold |
| `app/core/gardiner.py` | Complete 71→171 sign mapping |
| `app/core/rag_translator.py` | Remove disabled flag |
| `app/core/gemini_service.py` | Add `identify_landmark()` (low-conf fallback) + `describe_landmark()` (enrichment) |
| `app/api/scan.py` | Lower confidence threshold (0.25→0.15) |
| `app/api/explore.py` | Replace TF.js endpoint with hybrid ONNX+Gemini identify endpoint |
| `app/static/js/hieroglyph-pipeline.js` | NHWC→NCHW, new model path |
| `app/templates/explore.html` | Remove TF.js, add HTMX identify form |
| `app/static/sw.js` | Bump cache version to v15 |
| `app/templates/base.html` | Bump ?v= cache busters |

---

## 4.5 AGENTS.md — Key Resources from Repos

The file `D:\Personal attachements\Repos\AGENTS.md` documents all available repos.
Here are the ones directly relevant to this rebuild:

| Repo | Path | Why It Matters |
|------|------|----------------|
| `pytorch-lightning` | `Repos\pytorch-lightning\` | Remove all training boilerplate |
| `pytorch-image-models` (timm) | `Repos\pytorch-image-models\` | Pretrained MobileNetV3, EfficientNet |
| `albumentations` | `Repos\albumentations\` | Best augmentation library |
| `kornia` | `Repos\kornia\` | GPU-native augmentation on tensors |
| `fiftyone` | `Repos\fiftyone\` | Inspect hieroglyph dataset visually |
| `wandb` | `Repos\wandb\` | Track training experiments |
| `hydra` | `Repos\hydra\` | Config management for training experiments |
| `onnx` | `Repos\onnx\` | Debug/fix ONNX conversion issues |
| `Hierarchical-Localization` | `Repos\Hierarchical-Localization\` | **Place recognition** — offline landmark identification fallback |
| `optuna` | `Repos\optuna\` | Hyperparameter optimization if needed |
| `LitServe` | `Repos\LitServe\` | 2x faster than FastAPI for ML endpoints |
| `vision` (torchvision) | `Repos\vision\` | DataLoader, transforms, detection models |
| `faiss` | `Repos\faiss\` | Vector search for hloc + existing RAG translation |
| `sentence-transformers` | `Repos\sentence-transformers\` | Used in existing RAG translation (bge-m3 embeddings) |
| `supervision` | `Repos\supervision\` | Bounding box drawing + stream annotation (dev/debug) |
| `celery` + `redis-py` | `Repos\celery\` + `Repos\redis-py\` | (Optional) async task queue if ML inference needs queuing |
| `RecBole` | `Repos\RecBole\` | 90+ recommendation algorithms — directly powers `recommendation_engine.py` |
| `langchain` | `Repos\05-LangChain\langchain\` | LangChain patterns — for fixing/debugging `rag_translator.py` |
| `ultralytics` | `Repos\ultralytics\` | YOLO reference — understand existing `glyph_detector_uint8.onnx` model format |
| `BentoML` | `Repos\BentoML\` | Model packaging → Docker container (Phase E deploy alternative to raw Dockerfile) |
| `dinov2` | `Repos\dinov2\` | Visual feature embeddings — optional for hloc offline landmark fallback (Section 6.5) |
| `gitleaks` | `Repos\18-Security\gitleaks\` | Pre-deploy secret scanner — ensure no API keys committed to repo |
| `OWASP Top10` | `Repos\18-Security\Top10\` | Web security review checklist — file upload, injection, access control |

**Computer Vision Tourism Stack** (from AGENTS.md):
```
Place Recognition  → Hierarchical-Localization + faiss
Training Loop      → pytorch-lightning + albumentations + pytorch-image-models (timm)
Config Mgmt        → hydra (experiment configs, sweep params)
HPO                → optuna (hyperparameter optimization)
MLOps tracking    → wandb + mlflow
Serving API        → LitServe + onnx
Debug/Inspect      → fiftyone
Dev/Annotation     → supervision (bboxes), label-studio (re-labeling)
Existing RAG       → faiss + sentence-transformers (bge-m3) — already in app
```

---

## 5. Skills & Resources to Load Per Phase

| Phase | Skills to Load | Repos to Reference |
|-------|---------------|-------------------|
| **A** (Setup) | `ml-engineer`, `mlops-engineer` | `04-Meta-PyTorch\02-PyTorch\`, `vision\`, `kaggle-api\` |
| **B** (Hieroglyph Training) | `ml-engineer`, `computer-vision-expert` | `pytorch-image-models\`, `pytorch-lightning\`, `albumentations\`, `kornia\`, `fiftyone\`, `wandb\`, `hydra\` |
| **B2** (Landmark Training) | `ml-engineer`, `computer-vision-expert` | `pytorch-image-models\`, `pytorch-lightning\`, `albumentations\`, `kornia\`, `wandb\` |
| **C** (Backend) | `fastapi-pro`, `fastapi-router-py` | `antigravity-awesome-skills\skills\fastapi-pro\` |
| **C** (Gemini hybrid) | `gemini-api-dev`, `llm-app-patterns`, `prompt-engineering-patterns` | `01-Google-AI\`, `Prompt-Engineering-Guide\` |
| **D** (Frontend) | `tailwind-patterns` | `21-Frontend-UI\` |
| **E** (Deploy) | `deployment-engineer`, `docker-expert` | `16-DevOps-Infrastructure\`, `LitServe\` |

**Full skill paths** (`D:\Personal attachements\Repos\antigravity-awesome-skills\skills\`):
```
ml-engineer\SKILL.md               ← PyTorch training, ONNX export, quantization
computer-vision-expert\SKILL.md    ← Model architecture, augmentation, classification
mlops-engineer\SKILL.md            ← Kaggle workflow, experiment tracking, model versioning
ml-pipeline-workflow\SKILL.md      ← End-to-end ML pipeline patterns
fastapi-pro\SKILL.md               ← FastAPI best practices, file upload, async endpoints
fastapi-router-py\SKILL.md         ← Router patterns
gemini-api-dev\SKILL.md            ← google-genai SDK, multimodal, key rotation
llm-app-patterns\SKILL.md          ← LLM integration patterns
prompt-engineering-patterns\SKILL.md ← Gemini prompt templates for JSON output
deployment-engineer\SKILL.md       ← Render.com, env vars, health checks
docker-expert\SKILL.md             ← Multi-stage Dockerfile, model mounting
tailwind-patterns\SKILL.md         ← TailwindCSS v4 (frontend only)
```

> **Gemini SDK Note**: The project uses `google-genai >= 1.0.0` (new unified SDK).
> Current model in production: `gemini-2.5-flash` (verified working in `gemini_service.py`).
> The `gemini-api-dev` skill may reference newer model names — use `gemini-2.5-flash`
> unless a newer model is confirmed available in your API dashboard.

**If stuck on a problem — check these first:**
```
D:\Personal attachements\Repos\pytorch-image-models\     ← timm (MobileNetV3 etc.)
D:\Personal attachements\Repos\pytorch-lightning\        ← training loop patterns
D:\Personal attachements\Repos\albumentations\           ← augmentation
D:\Personal attachements\Repos\kornia\                   ← GPU-native augmentation
D:\Personal attachements\Repos\fiftyone\                 ← dataset inspection/debug
D:\Personal attachements\Repos\wandb\                    ← experiment tracking
D:\Personal attachements\Repos\hydra\                    ← experiment config (yaml-based)
D:\Personal attachements\Repos\onnx\                     ← ONNX debugging
D:\Personal attachements\Repos\04-Meta-PyTorch\02-PyTorch\ ← PyTorch core patterns
D:\Personal attachements\Repos\07-HuggingFace\           ← transformers/models
D:\Personal attachements\Repos\Hierarchical-Localization\ ← landmark place recognition (offline)
D:\Personal attachements\Repos\LitServe\                 ← fast ML API serving
D:\Personal attachements\Repos\optuna\                   ← hyperparameter optimization
D:\Personal attachements\Repos\sentence-transformers\    ← bge-m3 embeddings (existing RAG)
D:\Personal attachements\Repos\supervision\              ← bounding box drawing (dev)
D:\Personal attachements\Repos\Prompt-Engineering-Guide\ ← prompt engineering ref
```

---

## 6. Critical Rules & Gotchas

### ML Critical Rules
- `NO horizontal flip for hieroglyphs` — direction is semantically meaningful
- `PyTorch → ONNX = NCHW [1,3,H,W]` — DIFFERENT from old Keras NHWC [1,H,W,3]
- `float32 ONLY` — no mixed precision (causes fused ops that break ONNX)
- `opset_version=17` in torch.onnx.export (matches existing pipeline)
- `dynamic_axes` must include batch dimension for browser inference

### Backend Critical Rules
- `--color-bg` is forbidden in TailwindCSS v4 (conflicts with `bg-*` utilities)
- Gemini API keys: comma-separated in `GEMINI_API_KEYS` env var  
- ONNX Runtime session: create ONCE at startup, not per-request (expensive!)
- Translation threshold: `CONFIDENCE_THRESHOLD = 0.15` (was 0.25, too strict)

### Deploy Critical Rules
- `models/` folder is git-ignored → must be mounted/committed for Render
- CSS must be built (`npm run build`) before deploy
- Service worker cache version must be bumped after any model/JS/CSS change

---

## 6.5 Landmark Identification — Two-Tier Strategy

### Tier 1 (Primary): Gemini Vision API
- Fast, zero-training, works for any photo
- Requires internet + API key
- `gemini-2.5-flash` (fast + cheap)

### Tier 2 (Optional Offline Fallback): Hierarchical-Localization (hloc)
- Repo: `D:\Personal attachements\Repos\Hierarchical-Localization\`
- How: Index reference photos of all 52 landmarks → query photo → nearest match
- Works 100% offline, no API key
- Tradeoff: needs reference images indexed, less flexible than VLM
- Only implement if user needs offline mode or API budget is a concern
- See `Repos\AGENTS.md` → priority: CRITICAL for place recognition

**Decision**: Implement Tier 1 first (Gemini — simpler, better accuracy for novel angles).
Add Tier 2 as optional enhancement in Phase E or future phase.

---

## 7. Gemini Vision Landmark Identification — Design

### Prompt Template (final)
```python
LANDMARK_IDENTIFICATION_PROMPT = """You are an expert on Egyptian heritage.

Analyze this photo and identify the Egyptian landmark shown.

Rules:
- ONLY respond with valid JSON, no markdown code blocks, no extra text
- Set confidence between 0.0 and 1.0
- If you cannot identify it as an Egyptian landmark, set confidence to 0.0
- The slug must use underscores and lowercase

Known landmarks (use these slugs exactly if applicable):
abu_simbel, pyramids_of_giza, karnak_temple, luxor_temple, valley_of_kings,
cairo_citadel, al_azhar_mosque, bibliotheca_alexandrina, abu_mena, philae_temple,
kom_ombo_temple, edfu_temple, medinet_habu, deir_el_bahari, colossi_of_memnon,
aswan_high_dam, citadel_of_qaitbay, ben_ezra_synagogue, cairo_tower, ...

Response format (JSON only):
{
  "name": "Abu Simbel Temples",
  "confidence": 0.95,
  "slug": "abu_simbel",
  "description": "Twin rock temples built by Ramesses II circa 1264 BC",
  "alternatives": [
    {"name": "Nefertari Temple", "confidence": 0.03, "slug": "abu_simbel"}
  ]
}"""
```

### API Design
```
POST /api/explore/identify
  - Content-Type: multipart/form-data
  - file: UploadFile (jpg/png, max 10MB)
  - Returns: IdentifyLandmarkResponse
    - name: str
    - confidence: float (0-1)
    - slug: str | null
    - description: str
    - alternatives: list[{name, confidence, slug}]
    
Error handling:
  - File too large: 413
  - Not an image: 422
  - Gemini API failure: return {"name": null, "confidence": 0, "error": "..."}
  - Rate limit: retry with next key (17 keys available!)
```

---

## 8. START PROMPT Template

When ready to begin implementation, send this prompt:

```
START Phase [A/B/C/D/E]: [phase name]

Context:
- Plan: planning/rebuild/MASTER_PLAN.md
- Tasks: planning/rebuild/REBUILD_TASKS.md
- Current state: [what was just completed]
- Starting point: [exact first task, e.g., "B.1 — create training notebook"]

Skills to load first:
- Read: D:\Personal attachements\Repos\antigravity-awesome-skills\skills\ml-engineer\SKILL.md
- Read: D:\Personal attachements\Repos\AGENTS.md (for repo references)

Notes:
- [any specific observations or constraints]
```

### Recommended Session Order:
1. **START Phase A: Environment Setup** — verify PyTorch GPU, install deps, check data
2. **START Phase B: Hieroglyph Training** — inspect with fiftyone, create notebook, train, export ONNX
3. **START Phase C: Backend Integration** — fix pipeline (NCHW), gardiner 171 signs, Gemini Vision endpoint
4. **START Phase D: Frontend Updates** — fix JS preprocessing (NCHW), explore.html Gemini form
5. **START Phase E: Deploy** — E2E test, Docker, Render

> **Order is fixed**: E (Deploy) must come LAST. Never deploy before model + backend work.

---

## 9. Expected Outcomes

After completing all phases:

| Feature | Before | After |
|---------|--------|-------|
| Scan hieroglyphs | ❌ Crashes (`_FusedConv2D`) | ✅ Full pipeline: detect→classify→translit→translate |
| Dictionary | ✅ 171 signs displayed | ✅ Unchanged |
| Write | ✅ Already works | ✅ Unchanged |
| Explore/Browse | ✅ 52 landmarks displayed | ✅ Unchanged |
| Identify landmark | ❌ TF.js crash | ✅ Gemini Vision (accurate, fast) |
| Chat with Thoth | ✅ Works | ✅ Unchanged |
| Quiz | ✅ Works | ✅ Unchanged |
| Offline mode | ⚠️ Models cached but broken | ✅ ONNX models cached and working |

---

## 10. What NOT To Do

- ❌ DO NOT use `mixed_float16` (breaks ONNX export)
- ❌ DO NOT add horizontal flip augmentation to hieroglyph training
- ❌ DO NOT use `tf2onnx` (we're using native `torch.onnx.export`)
- ❌ DO NOT touch the frontend design/layout — it's complete
- ❌ DO NOT rebuild the YOLO detector — it works fine
- ❌ DO NOT train a PyTorch landmark model (Gemini Vision is better)
- ❌ DO NOT use `--color-bg` CSS variable (TailwindCSS v4 conflict)
- ❌ DO NOT create NHWC inputs for the new PyTorch ONNX classifier (use NCHW)
- ❌ DO NOT forget to bump cache busters after model changes
