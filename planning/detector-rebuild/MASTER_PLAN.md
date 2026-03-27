> **Note**: This is a historical document. File paths may reference the old project location (Final_Horus/Wadjet-v2).

# Wadjet v2 — Detector Rebuild Master Plan (YOLO26s)

> **Status**: PLANNING — Implementation starts on "START" prompt
> **Written**: 2026-03-24
> **Author**: Self-documentation for continuity between sessions
> **Location**: `planning/detector-rebuild/` — see also REBUILD_TASKS.md, PROGRESS.md, START_PROMPTS.md
> **Detailed Plan**: `DETECTOR_REBUILD_PLAN.md` (architecture decisions, data strategy, code changes)

---

## 0. Executive Summary

### What Was Done (Already Complete ✅)
The **full Wadjet v2 app** is deployed and working (HF Spaces, 9 pages, 86/86 tasks).
Both classifiers are rebuilt (PyTorch → ONNX):
- Hieroglyph Classifier: MobileNetV3-Small, 98.18% top-1, 171 Gardiner classes
- Landmark Classifier: EfficientNet-B0, 93.80% top-1, 52 classes
- Ensemble system: ONNX + Gemini + Grok tiebreaker
- AI fallback: Gemini reads inscriptions when ONNX detector fails

### What Is Broken
The **hieroglyph detector** (`glyph_detector_uint8.onnx`) is essentially useless on real stone photos.
It was trained on 261 images with auto-generated labels (OpenCV contour detection).
Gemini AI is doing 90%+ of the actual detection work via the fallback system.

### What This Plan Rebuilds

| Component | Old (Broken) | New (This Plan) |
|-----------|-------------|-----------------|
| Detector Model | YOLOv8s, 261 auto-labeled imgs | **YOLO26s**, 5000+ hand-verified imgs |
| Annotations | OpenCV contour auto-labels | **GroundingDINO (via `transformers`) + Label Studio manual verification** |
| Output Format | `[1, 5, 8400]` + NMS | **`[1, 300, 6]` NMS-free (end-to-end)** |
| Post-processing | Manual NMS in postprocess.py | **Confidence filter only** (model handles NMS) |
| Training Data | 261 images, 1 source | **5000+** from 7+ sources, 10+ museums |
| Data Collection | Manual download | **Scrapling spiders + browser-use AI agent + museum APIs** |
| Test Protocol | Synthetic val only | **Real stone inscription test set** |

### Decision Rationale

**Why YOLO26s?**
- NMS-free end-to-end output → simpler ONNX, faster inference, no NMS post-processing
- ProgLoss + STAL → improved small object detection (tiny glyphs on walls)
- MuSGD optimizer → better convergence
- 43% faster CPU inference → web-friendly
- Same `ultralytics` API → familiar training pipeline
- Built-in ONNX export with end-to-end option

**Why single-class detection (not multi-class 171)?**
- Detection = WHERE glyphs are; Classification = WHICH glyph it is
- Multi-class with 171 classes would need 10x more data per class
- Existing MobileNetV3 classifier already achieves 98.18% — keep the two-stage pipeline
- Easier to improve each component independently

**Why 5000+ images?**
- V1 had 261 with auto-labels → catastrophic failure on real stone
- Academic reference (HLA dataset): 897 museum-quality images, professionally annotated
- Industry best practice: 3000-5000+ images for robust single-class detection
- Mixed sources (10+ museums, synthetic, stone, papyrus, ostraca) ensure maximum domain diversity
- We have the tools to do it (Scrapling spiders, museum APIs, GroundingDINO auto-annotation)
- More data = less reliance on AI fallback = lower Gemini API costs

---

## 1. Data Sources & Preparation

### 1.0 Available Tools (Local Repos)

> All tools are already cloned at `D:\Personal attachements\Repos\`. No additional installs needed for most.

| Tool | Repo Path | Purpose |
|------|-----------|---------|
| **Scrapling** | `Repos/22-Web-Scraping/Scrapling/` | Primary scraping framework — Spider class, StealthyFetcher (Cloudflare bypass), DynamicFetcher (Playwright), async, rate limiting, proxy rotation, pause/resume, per-domain throttling |
| **browser-use** | `Repos/06-AI-Agents/browser-use/` | AI-powered browser automation — Playwright + LLM for JS-heavy museum sites (JSTOR, Europeana, interactive galleries) |
| **GroundingDINO** | `transformers` library (already installed) | **PRIMARY annotation tool**. Zero-shot object detection via `AutoModelForZeroShotObjectDetection`. Text prompt → bounding boxes. Runs on CPU. No separate repo install needed. |
| ~~LangSAM~~ | ~~`Repos/lang-segment-anything/`~~ | ~~REPLACED by GroundingDINO via transformers. LangSAM adds SAM2 masks we don't need (we only need bboxes). Also avoids heavy install + GPU VRAM requirements.~~ |
| **supervision** | `Repos/supervision/` | Dataset format conversion (COCO↔YOLO↔VOC), merging, splitting, annotation visualization |
| **label-studio** | `Repos/label-studio/` | Web UI annotation platform — import auto-proposals, human verify/correct, export YOLO/COCO, ML backend for active learning |
| **CLIP / open_clip** | `Repos/CLIP/`, `Repos/open_clip/` | Text-based image retrieval — filter scraped images by relevance ("hieroglyph inscription" vs noise). Smart dedup |
| **albumentations** | `Repos/albumentations/` | Advanced augmentation — CLAHE, perspective, shadow, noise, compression artifacts |
| **kaggle-api** | `Repos/kaggle-api/` | Kaggle CLI — search/download existing hieroglyph datasets |
| **HF datasets** | `Repos/07-HuggingFace/datasets/` | `load_dataset()` — stream HuggingFace datasets without full download |
| **celery** | `Repos/celery/` | Distributed task queue — parallel scraping jobs with retry, monitoring, concurrency control |
| **PaddleOCR** | `Repos/PaddleOCR/` | Extract text captions from museum catalogue pages (80+ languages) |
| ~~SAM2~~ | ~~`Repos/segment-anything-2/`~~ | ~~Not needed — we only need bounding boxes, not segmentation masks~~ |
| **ByteTrack** | `Repos/ByteTrack/` | Multi-object tracking — potentially useful for video frame detection |

### 1.1 Source Inventory

| # | Source | Target Images | Format | License | Tool / Action |
|---|--------|--------------|--------|---------|---------------|
| D1 | V1 raw detection images | 496 | JPG | Own | Re-annotate with GroundingDINO + Label Studio manual verify |
| D2 | HLA Dataset (HuggingFace) | 897 | JPG + COCO JSON | CC BY-NC 4.0 | Convert polygons → YOLO bboxes (script) |
| D3 | Signs Segmentation (HF) | 300 | JPG + COCO JSON | CC BY-NC 4.0 | Convert individual sign masks → bboxes (script) |
| D4 | **Museum scraping (10+ museums)** | **~2,500** | JPG | CC0/Public Domain | **Scrapling spiders + browser-use + Met API** |
| D5 | **Synthetic composites** | **~1,000** | PNG | Own (generated) | Paste classification crops onto stone textures |
| D6 | Roboflow Hieroglyph | 40 | YOLO format | CC BY 4.0 | Download and merge |
| D7 | **Kaggle dataset search** | **~200-500** | Various | Various | `kaggle datasets list --search hieroglyph` |
| D8 | **CLIP-filtered web images** | **~300-500** | JPG | Various | Google Images / Flickr → CLIP filter for relevance |
| | **TOTAL TARGET** | **~5,500-6,200** | | | |

### 1.1.1 Museum Scraping Breakdown (D4)

> Using **Scrapling** Spider framework with per-museum rate limiting, pause/resume, and StealthyFetcher where needed.
> For JS-heavy galleries, fall back to **browser-use** AI agent.

| # | Museum / Source | API Type | License | Target | Notes |
|---|----------------|----------|---------|--------|-------|
| M1 | **Metropolitan Museum Open Access** | REST API (`collectionapi.metmuseum.org`) | CC0 | 800-1000 | Largest: 30K+ Egyptian pieces, departmentId=10, hasImages=true, q="hieroglyph" |
| M2 | **British Museum** | IIIF API + SPARQL | CC BY-NC-SA 4.0 | 400-500 | Huge Egyptian collection, search "hieroglyph", filter by culture |
| M3 | **Wikimedia Commons** | MediaWiki API | CC BY-SA / Public Domain | 400-500 | Categories: "Egyptian hieroglyphs", "Ancient Egyptian inscriptions" |
| M4 | **Museo Egizio (Turin)** | Web scraping (Scrapling) | Research use | 150-200 | World's oldest Egyptian museum, digital collection |
| M5 | **Louvre Collections** | Open Data / IIIF | Etalab 2.0 (open) | 150-200 | `collections.louvre.fr`, département des Antiquités égyptiennes |
| M6 | **Brooklyn Museum** | REST API (public) | CC0 / Public Domain | 100-150 | `api.brooklynmuseum.org`, Egyptian collection |
| M7 | **Penn Museum** | Web scraping (Scrapling + StealthyFetcher) | Research use | 100-150 | University of Pennsylvania, strong Egyptology collection |
| M8 | **Oriental Institute (Chicago)** | Web scraping | Research use | 80-100 | Epigraphic Survey, Medinet Habu, Luxor Temple |
| M9 | **Petrie Museum (UCL)** | IIIF / web | CC BY-NC-SA | 80-100 | Specialized hieroglyphic collection |
| M10 | **IFAO (French Institute Cairo)** | Research archive | Academic | 50-100 | Specialized inscriptions, limited access |
| M11 | **Flickr** | Flickr API | CC licensed | 100-200 | Search: "Egyptian hieroglyphs", filter CC, CLIP-verify |
| M12 | **Europeana** | Search API | Varies (mostly PD/CC) | 100-150 | Aggregator: cross-museum Egyptian artifacts |
| | **SUBTOTAL** | | | **~2,500-3,350** | After dedup and CLIP filtering for relevance |

### 1.2 Annotation Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Raw Image      │────▶│  CLIP Filter      │────▶│  GroundingDINO   │────▶│  Label Studio    │
│  (scraped)      │     │  (relevance score │     │  (via transformers│     │  (human verify)  │
└─────────────────┘     │   ≥ 0.25 keep)    │     │   zero-shot det) │     └──────────────────┘
                        └──────────────────┘     └──────────────────┘            │
                              │                         │                        ▼
                        Remove non-hieroglyph     Proposed bounding       Final YOLO labels
                        images (ads, maps,        boxes (auto, ~75-80%)   (verified, clean)
                        modern buildings)
```

**Pipeline tools:**
1. **CLIP** (`Repos/CLIP/`): Score each image against "ancient Egyptian hieroglyph inscription on stone". Drop images < 0.25 similarity (removes noise)
2. **GroundingDINO** (via `transformers`): `AutoModelForZeroShotObjectDetection` with text prompt "hieroglyph sign" → bounding boxes. Runs on CPU. No SAM masks needed — we only need bbox coordinates.
3. **supervision** (`Repos/supervision/`): Convert GroundingDINO output → YOLO format, merge datasets, visualize annotations for QA
4. **Label Studio** (`Repos/label-studio/`): Import auto-proposals (pre-labeled), human annotator verifies/corrects. ML backend can use our classifier for active learning

For HLA/Signs datasets: convert their COCO polygon annotations → YOLO bbox format (automated script via supervision).

### 1.3 Synthetic Composite Generation

```python
# Pseudocode for synthetic data generation
1. Pick random stone/wall texture as background (from museum photo crops)
2. Select 5-20 random glyph crops from classification dataset (16,638 images)
3. Apply to each glyph:
   - Random scale (0.5x-2x relative to background)
   - Perspective warp (slight)
   - Color matching (histogram matching to background)
   - Edge blending (alpha blend at borders)
4. Place glyphs in reading-order grid (columns, right-to-left typical)
5. Apply overall effects: noise, brightness jitter, shadow overlay
6. Export image + YOLO labels (known bbox positions)
```

### 1.4 Dataset Structure (Kaggle Upload)

```
wadjet-hieroglyph-detection/
├── dataset-metadata.json
├── images/
│   ├── train/     # 80% (~4,000-4,500 images)
│   ├── val/       # 15% (~750-800 images)
│   └── test/      # 5% (~250-300 images)
├── labels/
│   ├── train/     # matching .txt files (YOLO format)
│   ├── val/
│   └── test/
└── hieroglyph_det.yaml    # YOLO dataset config
```

YOLO label format (each .txt line): `class_id cx cy w h` (normalized 0-1)
Single class: all lines are `0 cx cy w h`

---

## 2. Training Configuration

### 2.1 Environment: Kaggle (T4 GPU)

Proven pipeline from classifier training (2 successful runs: hieroglyph + landmark).

**CRITICAL FIXES — Apply ALL (learned from 36 bugs across v1-v7):**

| # | Fix | Why | Applies to Detector? |
|---|-----|-----|----------------------|
| 1 | `"machine_shape": "NvidiaTeslaT4"` in kernel-metadata.json | P100/sm_60 dropped in PyTorch 2.10+cu128 | ✅ Yes |
| 2 | `"id": "nadermohamedcr7/<slug>"` in kernel-metadata.json | Wrong format = push failure | ✅ Yes |
| 3 | `dataset_sources: ["nadermohamedcr7/<dataset-slug>"]` | Wrong username = dataset not found | ✅ Yes |
| 4 | Cell IDs on every notebook cell (`#VSC-XXXXXXXX`) | Missing IDs = future nbformat hard error | ✅ Yes |
| 5 | `pip install -q onnxscript onnxruntime` in first cell | `onnxscript` NOT pre-installed, needed by `torch.onnx.export` (PyTorch 2.10+) | ❓ Maybe (ultralytics may handle ONNX differently) |
| 6 | `pip install -U ultralytics` in first cell | Kaggle may have old version without YOLO26 | ✅ Yes |
| 7 | 3-level DATA_ROOT auto-discovery code | Kaggle mount paths are unpredictable | ✅ Yes |
| 8 | `enable_progress_bar=False` in trainer | tqdm breaks papermill stdout | ❓ Maybe (ultralytics has its own progress handling) |
| 9 | KeepAlive prints (flush=True) every N batches | Papermill kills cells with >4s silence (IOPub timeout) | ✅ Yes — print progress during YOLO training |
| 10 | NO horizontal flip (`fliplr=0.0, flipud=0.0`) | Hieroglyph orientation = meaning | ✅ Yes |
| 11 | `dynamo=False` in `torch.onnx.export()` | `dynamo=True` creates separate `.onnx.data` sidecar file | ❓ Maybe (ultralytics export may differ) |
| 12 | `dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}}` | Without this, batch dimension locked at 1 | ❓ Maybe |
| 13 | `precision="32-true"` (no mixed precision) | Mixed precision creates fused ops that may break ONNX | ✅ Yes — verify ultralytics not using AMP |
| 14 | ONNX output shape assertion post-export | Prevents deploying wrong shape model | ✅ Yes: assert `[1, 300, 6]` |
| 15 | uint8 model size assertion (< 20MB) | Budget for web serving | ✅ Yes |
| 16 | No apostrophes/special chars in filenames | Kaggle zip upload breaks on special chars | ✅ Yes — check dataset before upload |
| 17 | `import pytorch_lightning as L` (NOT `lightning`) | Kaggle pre-installs old package name | ❓ Maybe (ultralytics uses its own training loop) |

**Pre-installed on Kaggle (no pip):** `torch`, `torchvision`, `timm`, `onnx`, `onnxruntime`, `albumentations`, `pytorch_lightning`, `sklearn`
**Must install:** `ultralytics` (latest with YOLO26), `onnxscript` (if doing manual ONNX export)

**Reference notebooks** (working, both successful):
- `planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier.ipynb` — MobileNetV3-Small, 98.18%
- `planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb` — EfficientNet-B0, 93.80%

### 2.2 YOLO26s Configuration

```yaml
model: yolo26s.pt            # COCO pretrained (transfer learning)
data: hieroglyph_det.yaml    # custom dataset
epochs: 150                  # plenty with early stopping
batch: 16                    # T4-friendly at 640px
imgsz: 640                   # standard YOLO size
patience: 30                 # early stopping window
optimizer: auto              # MuSGD (YOLO26 default)
lr0: 0.01
lrf: 0.01
warmup_epochs: 5

# Augmentation
mosaic: 1.0
mixup: 0.1
close_mosaic: 15
fliplr: 0.0                  # NO horizontal flip (glyph orientation = meaning)
flipud: 0.0                  # NO vertical flip
degrees: 15.0
translate: 0.1
scale: 0.5
perspective: 0.001
hsv_h: 0.015
hsv_s: 0.7
hsv_v: 0.4
```

### 2.3 Transfer Learning Strategy

| Phase | Epochs | Backbone | LR | Purpose |
|-------|--------|----------|-----|---------|
| Phase 1 | 20 | Frozen | 0.01 | Learn detection head |
| Phase 2 | 130 | Unfrozen | 0.001 | Fine-tune full network |

### 2.4 Quality Gates

| Metric | Minimum | Target |
|--------|---------|--------|
| mAP50 | 0.85 | 0.92+ |
| Precision | 0.80 | 0.88+ |
| Recall | 0.80 | 0.88+ |
| Real stone test (20 photos) | 12/20 | 16/20+ |
| ONNX model size (uint8) | < 20MB | < 15MB |
| Inference time (CPU) | < 500ms | < 200ms |
| AI fallback rate | < 50% | < 25% |

---

## 3. ONNX Export & Deployment

### 3.1 Export Pipeline

```python
from ultralytics import YOLO

model = YOLO("best.pt")

# End-to-end export (NMS-free)
model.export(format="onnx", imgsz=640, simplify=True, opset=17, end2end=True)

# Quantize
from onnxruntime.quantization import quantize_dynamic, QuantType
quantize_dynamic("best.onnx", "best_uint8.onnx", weight_type=QuantType.QUInt8)
```

### 3.2 Output Shape Change

| Model | Output Shape | Post-Processing |
|-------|-------------|-----------------|
| Old (YOLOv8s) | `[1, 5, 8400]` | NMS required |
| New (YOLO26s e2e) | `[1, 300, 6]` | Confidence filter only |

New output columns: `[x1, y1, x2, y2, confidence, class_id]`
Max 300 detections per image.

### 3.3 Model Deployment Path

```
models/hieroglyph/
├── classifier/
│   ├── hieroglyph_classifier_uint8.onnx  (existing — KEEP)
│   └── label_mapping.json                (existing — KEEP)
└── detector/
    ├── glyph_detector_uint8.onnx         (REPLACE with new YOLO26s)
    └── model_metadata.json               (NEW — document shapes)
```

---

## 4. Backend Integration

### 4.1 Files to Update

| File | Change | Impact |
|------|--------|--------|
| `app/core/postprocess.py` | Rewrite `postprocess()` for `[1, 300, 6]` output | **MAJOR** — no NMS, just filter |
| `app/core/postprocess.py` | Keep `preprocess()` mostly unchanged (letterbox 640) | Minor tweaks |
| `app/core/hieroglyph_pipeline.py` | Update detector model path if needed | Minimal |
| `app/api/scan.py` | Keep AI fallback as-is | No change |
| `app/static/js/hieroglyph-pipeline.js` | **Rewrite `detect()` for `[1,300,6]`, remove `_nms()`/`_iou()`** | **MAJOR** — actively used in scan page client-side mode |

### 4.2 New postprocess.py Flow (Simplified)

```python
# OLD flow (YOLOv8s):
# output [1, 5, 8400] → transpose → conf filter → NMS → size filter → merge

# NEW flow (YOLO26s e2e):
# output [1, 300, 6] → conf filter → size filter → sort by confidence
# NO NMS NEEDED — model outputs final detections directly
```

---

## 5. Risk Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Insufficient data quality | Medium | High | Phase D5 synthetic bridges domain gap; CLIP filters noise; 10+ museum sources = diversity |
| YOLO26 too new on Kaggle | Low | Medium | `pip install -U ultralytics` at start; fallback to YOLO11s |
| GroundingDINO annotation noise | Medium | Medium | Human verification of ALL boxes in Label Studio; supervision for visual QA |
| Museum rate limiting / blocking | Medium | Low | Scrapling with per-domain throttling, StealthyFetcher, proxy rotation, pause/resume |
| JS-heavy museum sites | Medium | Low | browser-use AI agent handles interactive galleries |
| T4 OOM with YOLO26s@640 | Low | Low | batch=8 or use yolo26n |
| ONNX export shape mismatch | Low | High | Validate shape before deploying |
| HLA dataset gated access | Medium | Low | Apply for access; if rejected, 6+ other sources compensate |
| Image licensing issues | Low | Medium | Prioritize CC0/Public Domain (Met, Brooklyn); track license per source |
| CLIP filtering too aggressive | Low | Low | Tune threshold; visually inspect borderline images |

---

## 6. Skills to Load

| Task | Skills |
|------|--------|
| Data prep | `computer-vision-expert`, `ml-engineer` |
| Training | `computer-vision-expert`, `mlops-engineer` |
| Integration | `fastapi-pro`, `fastapi-router-py` |
| Export/Deploy | `docker-expert`, `deployment-engineer` |

---

## 7. External References

- YOLO26 Docs: https://docs.ultralytics.com/models/yolo26/
- YOLO Training: https://docs.ultralytics.com/modes/train/
- ONNX Export: https://docs.ultralytics.com/modes/export/
- HLA Dataset: https://huggingface.co/datasets/AhmedElTaher/Egyptian_Hieroglyphic_Layout_Analysis_HLA
- Signs Segmentation: https://huggingface.co/datasets/AhmedElTaher/Egyptian_Hieroglyphic_Signs_Segmentation_with_Orientation
- Roboflow Hieroglyph: https://universe.roboflow.com/project-jsqal/hieroglyph-dataset-gzd5g
- GroundingDINO: https://github.com/IDEA-Research/GroundingDINO
- Existing detector: `models/hieroglyph/detector/glyph_detector_uint8.onnx` (11MB, YOLOv8s)
