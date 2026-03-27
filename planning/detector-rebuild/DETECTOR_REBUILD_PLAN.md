# Hieroglyph Detector Rebuild — Comprehensive Plan

> **Created:** 2026-03-24
> **Goal:** Build a hieroglyph detector that actually works on real stone inscription photos

---

## 1. Problem Statement

### Why the Current Detector Fails

The current glyph detector (YOLOv8s uint8 ONNX, 11MB) was trained on only **261 images** with **algorithmically-generated labels** (OpenCV CLAHE → threshold → contour → NMS). It achieves mAP50=0.8753 on its own synthetic-labeled val set, but **fails catastrophically on real stone inscription photos**.

**Root causes:**
1. **Insufficient data**: 261 images is far too few for robust detection
2. **Fake labels**: Auto-generated via OpenCV contour detection, NOT hand-annotated. The model learned to detect "things that look like contours" rather than actual hieroglyphs
3. **Domain gap**: Trained on relatively clean images; fails on worn stone, variable lighting, weathered surfaces, and 3D relief carving
4. **Single-class only**: Detects "hieroglyph" as a blob, no Gardiner class information at detection time

**Current workaround**: AI fallback — when ONNX finds ≤2 glyphs or avg_conf < 0.30, Gemini Vision reads the entire inscription. This means Gemini is doing 90%+ of the real work.

---

## 2. Architecture Decision

### Model: YOLO26s (January 2026) — Single-Class Detection

**Why YOLO26s over alternatives:**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **YOLO26s** | NMS-free (end-to-end), ProgLoss for small objects, MuSGD optimizer, built-in ONNX export, 9.5M params, 43% faster CPU | Newest, less community examples | **CHOSEN** |
| YOLO11s | Solid, well-tested, community examples | Needs NMS post-processing, older arch | Runner-up |
| YOLOv8s (current) | Same as v1, known pipeline | Already proven inadequate architecture isn't the issue | No |
| RTMDet (mmdetection) | Academic quality | Heavy framework, complex ONNX export | No |
| GroundingDINO | Zero-shot, great for annotation | Too heavy for inference (900M params) | Use for data only |
| YOLOE-26 | Open-vocab, text prompts | Heavier, less precise for known domain | Potential Phase 2 |

**Why single-class detection (not multi-class):**
- Detection task: find WHERE glyphs are (bounding boxes)
- Classification task: identify WHICH glyph it is (Gardiner code)
- Keeping them separate allows: different model sizes, independent improvement, proven classifier already at 98.18%
- Multi-class detection with 171 classes would need 10x more data per class

### Architecture Summary

```
Photo → YOLO26s Detector → Crop glyphs → MobileNetV3 Classifier → Gardiner codes
         (single-class)     (existing)      (98.18% top-1)

Fallback: if ≤2 detections or avg_conf < threshold → Gemini AI reads inscription
```

### Model Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base model | `yolo26s.pt` (COCO pretrained) | Transfer learning, small enough for web |
| Input size | 640×640 | Standard YOLO, matches current pipeline |
| Classes | 1 ("hieroglyph") | Single-class detection |
| End-to-end | Yes (NMS-free) | Simpler ONNX, faster inference |
| Export | ONNX uint8 quantized | Matches existing deployment |
| Target size | < 15MB (uint8) | Web-friendly |

### Output Format (CRITICAL CHANGE)

**Current** (YOLOv8s): `[1, 5, 8400]` → requires NMS post-processing
**New** (YOLO26s end-to-end): `[1, 300, 6]` → (batch, max_detections, [x1,y1,x2,y2,conf,class])

This means `postprocess.py` will need updating — the new model outputs final detections directly, no NMS needed.

---

## 3. Data Strategy — The Critical Part

### 3.1 Available Tools (Local Repos — `D:\Personal attachements\Repos\`)

| Tool | Path | Purpose |
|------|------|---------|
| **Scrapling** | `22-Web-Scraping/Scrapling/` | Primary scraping — Spider class, StealthyFetcher, DynamicFetcher, async, rate limiting, proxy rotation, pause/resume |
| **browser-use** | `06-AI-Agents/browser-use/` | AI browser agent — Playwright + LLM for JS-heavy museum sites |
| **GroundingDINO** | `transformers` library | **PRIMARY annotation tool.** Zero-shot detection via `AutoModelForZeroShotObjectDetection`. Text prompt → bboxes. CPU-compatible. |
| ~~LangSAM~~ | ~~`lang-segment-anything/`~~ | ~~REPLACED. We only need bboxes, not SAM masks. GroundingDINO via transformers is lighter and CPU-friendly.~~ |
| **CLIP / open_clip** | `CLIP/`, `open_clip/` | Text-image similarity — filter scraped images for relevance |
| **supervision** | `supervision/` | Dataset conversion (COCO↔YOLO), merging, splitting, visualization |
| **label-studio** | `label-studio/` | Web annotation UI — import proposals, human verify, export YOLO/COCO |
| **albumentations** | `albumentations/` | Advanced augmentation — CLAHE, perspective, shadow, noise |
| **celery** | `celery/` | Distributed task queue — parallel scraping with retry |
| **kaggle-api** | `kaggle-api/` | Search/download existing Kaggle hieroglyph datasets |
| **HF datasets** | `07-HuggingFace/datasets/` | Stream HuggingFace datasets |
| **PaddleOCR** | `PaddleOCR/` | Extract metadata captions from museum pages |
| **SAM2** | `segment-anything-2/` | Precise segmentation masks |

### 3.2 Available Data Sources

| Source | Type | Count | Quality | Notes |
|--------|------|-------|---------|-------|
| V1 raw images | Inscription photos | 496 JPGs | Mixed (clean to worn) | Need RE-ANNOTATION (old labels = auto-generated garbage) |
| Roboflow Hieroglyph | Annotated det. | 40 imgs, 86 classes | Good annotations | Tiny but multi-class, CC BY 4.0 |
| HLA Dataset (HuggingFace) | Layout analysis | 897 imgs | Professional (CVAT) | Line + Cartouche segmentation, real museum photos |
| Signs Segmentation (HF) | Individual signs | 300 line crops | Professional | Sign-level polygon masks with orientation |
| HuggingFace Egyptian_hieroglyphs | Classification | 4,000+ | Mixed | Isolated glyphs, good for synthetic composites |
| V1 GlyphNet | Classification | ~4,000+ | Clean renders | Isolated glyphs for synthetic data |
| V1 GlyphReader | Mixed | varies | Academic | Mixed quality |
| Our classification dataset | Isolated glyphs | 16,638+ | Good | 171 classes, clean crops |

### 3.3 Data Pipeline Strategy (Multi-Source Fusion)

**Target: 5,000+ annotated images** (20x improvement over V1's 261)

#### Phase D1: Re-annotate V1 Raw Images (~496 images)
- **Tool**: GroundingDINO (via `transformers`) zero-shot → manual correction in Label Studio
- GroundingDINO prompt: "hieroglyph", "Egyptian hieroglyphic sign", "carved symbol"
- Semi-automatic: GroundingDINO proposes boxes → human verifies/corrects in Label Studio
- Estimated yield: ~400-450 usable images

#### Phase D2: Convert HLA Dataset (~897 images)
- HLA has "Line" polygons → convert polygon to bounding boxes
- Each "Line" polygon can potentially be split into individual signs
- Use Signs Segmentation dataset (300 images) for individual sign boxes
- Convert COCO polygon format → YOLO bbox format using **supervision** library

#### Phase D3: Scrape Museum Collections (~2,500-3,000 images)
- **Primary tool**: Scrapling Spider framework with per-museum rate limiting
- **JS-heavy sites**: browser-use AI agent for interactive galleries
- **CLIP filtering**: Score every scraped image against "ancient Egyptian hieroglyph inscription" — drop < 0.25 similarity
- **Dedup**: Perceptual hash (pHash) to remove duplicates across museums

| # | Museum / Source | API/Method | License | Target |
|---|----------------|------------|---------|--------|
| M1 | **Metropolitan Museum Open Access** | REST API (`collectionapi.metmuseum.org`) | CC0 | 800-1000 |
| M2 | **British Museum** | IIIF API + SPARQL | CC BY-NC-SA 4.0 | 400-500 |
| M3 | **Wikimedia Commons** | MediaWiki API | CC BY-SA / PD | 400-500 |
| M4 | **Museo Egizio (Turin)** | Scrapling (StealthyFetcher) | Research use | 150-200 |
| M5 | **Louvre Collections** | Open Data / IIIF | Etalab 2.0 | 150-200 |
| M6 | **Brooklyn Museum** | REST API (public) | CC0 / PD | 100-150 |
| M7 | **Penn Museum** | Scrapling (StealthyFetcher) | Research use | 100-150 |
| M8 | **Oriental Institute (Chicago)** | Scrapling | Research use | 80-100 |
| M9 | **Petrie Museum (UCL)** | IIIF / Scrapling | CC BY-NC-SA | 80-100 |
| M10 | **IFAO (French Institute Cairo)** | Research archive | Academic | 50-100 |
| M11 | **Flickr** | Flickr API | CC licensed | 100-200 |
| M12 | **Europeana** | Search API | Varies (mostly PD/CC) | 100-150 |

- Annotate all scraped images with GroundingDINO → Label Studio verification (same pipeline as D1)

#### Phase D4: Search Existing Datasets (~200-500 images)
- `kaggle datasets list --search "hieroglyph"` → download relevant datasets
- `load_dataset()` from HuggingFace Hub → filter for hieroglyph-related image sets
- Convert all to unified YOLO format

#### Phase D5: Generate Synthetic Composites (~1,000 images)
- Take isolated glyphs from our classification dataset (16,638 images)
- Paste onto stone/wall texture backgrounds
- Apply: perspective warp, noise, wear damage, lighting gradients
- Each composite = 5-20 glyphs with known bounding boxes
- This bridges the domain gap between clean crops and stone surfaces
- Target: **1,000 composites** with diverse stone textures, lighting, and wear levels

#### Phase D6: Roboflow Hieroglyph Dataset (+40)
- Download CC BY 4.0 Roboflow dataset
- Convert to YOLO format
- Small but has quality multi-class annotations

#### Phase D7: CLIP-Filtered Web Images (~300-500)
- Google Images / Flickr search: "Egyptian hieroglyphs", "temple inscription", "cartouche"
- Download high-res candidates
- CLIP filter: keep only images with hieroglyph content (similarity ≥ 0.25)
- Annotate with GroundingDINO + Label Studio

### 3.4 Data Augmentation (During Training)

**YOLO26 built-in augmentations:**
- Mosaic: 1.0 (combine 4 images)
- MixUp: 0.1
- Random perspective: 0.001
- HSV hue: 0.015, saturation: 0.7, value: 0.4
- Rotation: ±15°
- Scale: ±0.5
- Translation: ±0.1
- **NO horizontal flip** (hieroglyph orientation = meaning)
- Vertical flip: 0.0

**Additional via Albumentations (in data prep):**
- CLAHE (simulate different stone lighting)
- Random brightness/contrast
- Gaussian noise
- JPEG compression artifacts
- Random shadow
- Perspective transform (slight)

### 3.5 Dataset Split

| Split | Ratio | Purpose |
|-------|-------|---------|
| Train | 80% | Model training (~4,000-4,500 images) |
| Val | 15% | Hyperparameter tuning & early stopping (~750-800 images) |
| Test | 5% | Final evaluation on unseen data (~250-300 images) |

**Critical**: Stratify by source (V1 raw, HLA, museum-scraped, synthetic, CLIP-filtered) so each split has realistic diversity.
**Real stone test set**: 20 hand-picked photos of actual temple walls / museum artifacts in test split.

---

## 4. Training Plan

### 4.1 Environment: Kaggle (T4 GPU)

Same proven pipeline from classifier training:
- GPU: Tesla T4 (NvidiaTeslaT4)
- Framework: `ultralytics` (pip-installable, works on Kaggle)
- Export: ONNX → quantize to uint8

### 4.2 Training Configuration

```yaml
# YOLO26s Hieroglyph Detection Config
model: yolo26s.pt           # COCO pretrained
data: hieroglyph_det.yaml   # custom dataset

# Training
epochs: 150
batch: 16                   # T4 with 640 input
imgsz: 640
patience: 30                # early stopping
optimizer: auto             # MuSGD (YOLO26 default)
lr0: 0.01
lrf: 0.01
momentum: 0.937
weight_decay: 0.0005
warmup_epochs: 5

# Augmentation
mosaic: 1.0
mixup: 0.1
close_mosaic: 15
fliplr: 0.0                 # NO horizontal flip!
flipud: 0.0                 # NO vertical flip
degrees: 15.0
translate: 0.1
scale: 0.5
perspective: 0.001
hsv_h: 0.015
hsv_s: 0.7
hsv_v: 0.4

# Loss (YOLO26 specific)
# ProgLoss + STAL automatically enabled for small object accuracy
```

### 4.3 Transfer Learning Strategy

1. **Phase 1 (Freeze backbone, 20 epochs)**: Learn detection head on our data with frozen COCO backbone features
2. **Phase 2 (Unfreeze all, 130 epochs)**: Fine-tune entire network, lower LR by 10x

### 4.4 Quality Gates

| Metric | Minimum | Target |
|--------|---------|--------|
| mAP50 | 0.85 | 0.92+ |
| Precision | 0.80 | 0.88+ |
| Recall | 0.80 | 0.88+ |
| Real stone test (20 photos) | 12/20 | 16/20+ |
| AI fallback rate | < 50% | < 25% |

**Real stone test**: 20 hand-picked photos of actual temple walls / museum artifacts. Must detect majority of visible hieroglyphs.

### 4.5 ONNX Export

```python
from ultralytics import YOLO

model = YOLO("best.pt")

# End-to-end export (NMS-free, output [1, 300, 6])
model.export(
    format="onnx",
    imgsz=640,
    simplify=True,
    opset=17,
    end2end=True,     # NMS-free!
    # int8=True,      # OR quantize separately
)
```

Then quantize with onnxruntime:
```python
from onnxruntime.quantization import quantize_dynamic, QuantType
quantize_dynamic("best.onnx", "best_uint8.onnx", weight_type=QuantType.QUInt8)
```

---

## 5. Backend Integration Plan

### 5.1 Update `postprocess.py`

The biggest code change: YOLO26 end-to-end outputs `[1, 300, 6]` instead of `[1, 5, 8400]`.

**New postprocess flow:**
```
input: [1, 300, 6] = [batch, max_dets, (x1, y1, x2, y2, conf, class_id)]
1. Filter by confidence threshold
2. Filter by box size/aspect ratio  
3. Rescale from 640 to original coords
4. Sort by confidence
5. Return detections
NO NMS NEEDED — model does it internally
```

### 5.2 Update `hieroglyph_pipeline.py`

- Update `_get_detector()` to use new model path
- Pipeline logic stays the same: detect → classify → transliterate → translate

### 5.3 Keep AI Fallback

The Gemini fallback in `scan.py` should remain as a safety net:
- ONNX detector: primary detection
- If ≤2 detections or avg_conf < threshold: Gemini reads full inscription
- Full-sequence verification: AI verifies all glyph classifications

### 5.4 Model Path

```
models/hieroglyph/
├── classifier/
│   ├── hieroglyph_classifier_uint8.onnx  (existing, 1.8MB)
│   └── label_mapping.json                (existing)
└── detector/
    ├── glyph_detector_uint8.onnx         (REPLACE — new YOLO26s)
    └── model_metadata.json               (new — document input/output shapes)
```

---

## 6. Phase Plan (Execution Order)

### Phase D-PREP: Data Preparation (Most Critical)

| Step | Task | Est. Images | Tool |
|------|------|-------------|------|
| D1 | Re-annotate V1 raw images with GroundingDINO + manual | ~400-496 | GroundingDINO + Label Studio |
| D2 | Convert HLA + Signs Segmentation to YOLO format | ~500-800 | supervision + Python script |
| D3 | Scrape 10+ museum collections + annotate | ~2,500-3,000 | Scrapling + browser-use + GroundingDINO |
| D4 | Search/download existing Kaggle/HF datasets | ~200-500 | kaggle-api + HF datasets |
| D5 | Generate synthetic composites | ~1,000 | Python (PIL/OpenCV) |
| D6 | Merge Roboflow dataset | +40 | Download + convert |
| D7 | CLIP-filtered web images | ~300-500 | CLIP + Scrapling + GroundingDINO |
| D8 | Merge all, split train/val/test, upload to Kaggle | 5,000+ | supervision + Python script |
| D4 | Generate synthetic composites | ~1,000 | Python (PIL/OpenCV) |
| D5 | Merge Roboflow dataset | +40 | Download + convert |
| D6 | Merge all, split train/val/test, upload to Kaggle | 5,000+ | supervision + Python script |

### Phase D-TRAIN: Training on Kaggle

| Step | Task | Notes |
|------|------|-------|
| T1 | Create Kaggle notebook with YOLO26s training | Auto-discovery, T4, all fixes from v1-v7 |
| T2 | Push to Kaggle, train | ~2-4 hours on T4 |
| T3 | Download & evaluate results | mAP50, real stone test |
| T4 | If fail gates → adjust data/config → retrain | Iterate |
| T5 | Export ONNX uint8, validate | Verify output shape [1, 300, 6] |

### Phase D-INTEGRATE: Backend Integration

| Step | Task | Notes |
|------|------|-------|
| I1 | Update `postprocess.py` for YOLO26 output format | [1,300,6] not [1,5,8400] |
| I2 | Deploy new model to `models/hieroglyph/detector/` | Replace old model |
| I3 | Test end-to-end pipeline locally | scan API with real photos |
| I4 | Push to GitHub + HF Spaces | Deploy |

---

## 7. Risk Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Insufficient data quality | Model still fails on stone | Focus Phase D5 synthetic + D7 CLIP-filtered to bridge domain gap; 10+ museum sources = diversity |
| YOLO26 too new, bugs | Training issues | Fallback to YOLO11s (same training API) |
| Kaggle ultralytics version | Old version without YOLO26 | `pip install -U ultralytics` at notebook start |
| ONNX export differences | Backend breaks | Validate output shape before deploying |
| T4 OOM with YOLO26s | Can't train | Reduce batch to 8, or use yolo26n instead |
| GroundingDINO annotation quality | Bad labels | Manual verification of ALL annotations in Label Studio |
| Museum rate limiting / blocking | Scraping stops | Scrapling StealthyFetcher + per-domain throttling + proxy rotation + pause/resume |
| JS-heavy museum sites | Can't scrape | browser-use AI agent handles interactive galleries |
| Image licensing issues | Legal risk | Prioritize CC0/PD museums (Met, Brooklyn); track license per source |
| CLIP filtering too aggressive/lenient | Wrong images | Tune threshold (0.25); visually inspect borderline images |

---

## 8. Files to Create

| File | Purpose |
|------|---------|
| `planning/model-rebuild/pytorch/detector/hieroglyph_detector.ipynb` | Kaggle training notebook |
| `planning/model-rebuild/pytorch/detector/kernel-metadata.json` | Kaggle push metadata |
| `scripts/scrape_museums.py` | Scrapling spider for 10+ museum collections |
| `scripts/clip_filter_images.py` | CLIP-based relevance filtering |
| `scripts/annotate_with_gdino.py` | GroundingDINO auto-annotation (bboxes via transformers, CPU) |
| `scripts/convert_hla_to_yolo.py` | HLA → YOLO format converter (via supervision) |
| `scripts/generate_synthetic_composites.py` | Synthetic data generation |
| `scripts/merge_detection_datasets.py` | Merge all sources, deduplicate, split |
| `scripts/validate_dataset.py` | Dataset quality checks, stats, visualization |

---

## 9. Success Criteria

1. **mAP50 ≥ 0.88** on validation set
2. **Real stone test**: Detect ≥ 14/20 glyphs on 20 real temple wall photos
3. **ONNX model < 15MB** (uint8 quantized)
4. **Inference < 200ms** on CPU (single image)
5. **Seamless backend integration**: Drop-in replacement with updated postprocess.py
6. **AI fallback still works**: Gemini catches what detector misses
7. **AI fallback rate < 50%**: Detector handles majority of real stone photos independently
8. **Source diversity**: Test set includes images from ≥ 5 different sources

---

## 10. Key Lessons from V1 (Don't Repeat)

1. ❌ Auto-generating labels via OpenCV → ✅ Use GroundingDINO + human verification
2. ❌ Training on 261 images → ✅ Target **5,000+** properly annotated images from 7+ sources, 10+ museums
3. ❌ Not testing on real stone photos → ✅ Include real museum photos in test set
4. ❌ No data diversity (all from one source) → ✅ Mix 5 data sources
5. ❌ No horizontal flip rule undocumented → ✅ Explicitly set `fliplr=0.0` in config
6. ❌ Model output format undocumented → ✅ Create model_metadata.json with shapes
7. ❌ Kaggle push issues (v1-v7) → ✅ Apply ALL known fixes from day 1
8. ❌ Using basic requests for scraping → ✅ Scrapling with rate limiting, proxy rotation, StealthyFetcher
9. ❌ No smart image filtering → ✅ CLIP-based relevance scoring to remove noise
10. ✅ GroundingDINO via `transformers` for annotation — lighter than LangSAM, CPU-friendly, no SAM masks needed (bboxes only)

---

## Appendix A: YOLO26 Quick Reference

```python
from ultralytics import YOLO

# Load pretrained
model = YOLO("yolo26s.pt")

# Train
results = model.train(
    data="hieroglyph_det.yaml",
    epochs=150,
    imgsz=640,
    batch=16,
    fliplr=0.0,
    flipud=0.0,
    patience=30,
)

# Validate
metrics = model.val()

# Export ONNX (end-to-end, no NMS needed)
model.export(format="onnx", imgsz=640, simplify=True, end2end=True)
```

## Appendix B: Dataset YAML Format

```yaml
# hieroglyph_det.yaml
path: /kaggle/input/datasets/nadermohamedcr7/wadjet-hieroglyph-detection
train: images/train
val: images/val
test: images/test

# Classes
names:
  0: hieroglyph

# Number of classes
nc: 1
```

## Appendix C: Expected Output Shapes

| Model | Head | Output Shape | Post-processing |
|-------|------|-------------|-----------------|
| YOLO26s (e2e) | one-to-one | `[1, 300, 6]` | Filter by conf only |
| YOLO26s (legacy) | one-to-many | `[1, 5, 8400]` | NMS required |
| YOLOv8s (current) | standard | `[1, 5, 8400]` | NMS required |

We use the **one-to-one head** (end-to-end) for simplicity and speed.
