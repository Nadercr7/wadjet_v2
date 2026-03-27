# Wadjet v2 — Detector Rebuild Start Prompts

> Ready-to-paste prompts for each detector rebuild phase.
> **Order**: Phase D-PREP → D-TRAIN → D-INTEGRATE
> **Tasks reference**: `planning/detector-rebuild/REBUILD_TASKS.md`
> **Full plan**: `planning/detector-rebuild/MASTER_PLAN.md`
> **Detailed plan**: `planning/detector-rebuild/DETECTOR_REBUILD_PLAN.md`
> **Known issues**: `planning/detector-rebuild/KNOWN_ISSUES.md`
> **Pre-launch gate**: `planning/detector-rebuild/CHECKLIST.md`

---

## PHASE D-PREP — Data Preparation

> Send this prompt to start data preparation.

```
We're working on Wadjet v2 — an AI-powered Egyptian heritage web app.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST (in order):
1. CLAUDE.md
2. planning/detector-rebuild/MASTER_PLAN.md     ← full rebuild plan
3. planning/detector-rebuild/REBUILD_TASKS.md    ← task tracker, start at Phase D-PREP
4. planning/detector-rebuild/KNOWN_ISSUES.md     ← WHY the detector is broken
5. planning/detector-rebuild/DETECTOR_REBUILD_PLAN.md  ← detailed architecture & data strategy

CONTEXT:
- The app is fully deployed and working. Do NOT touch templates, CSS, or existing backend.
- The hieroglyph DETECTOR (glyph_detector_uint8.onnx) is broken on real stone photos.
- We are rebuilding it from scratch using YOLO26s (single-class, NMS-free).
- The CLASSIFIER is fine (MobileNetV3-Small, 98.18% top-1) — don't touch it.
- AI fallback (Gemini reads inscriptions) stays as backup — don't remove it.

ENVIRONMENT:
- Data-prep venv: `scripts/dataprep-env/` (PyTorch 2.11 CPU, transformers 5.3, supervision 0.27, opencv)
- Activate: `& scripts\dataprep-env\Scripts\Activate.ps1`
- Local GPU NOT available (Quadro T1000 permissions issue). All annotation runs on CPU.
- C: drive has 0.2GB free. D: drive has 36GB. Use D: for all temp/cache (`$env:TEMP = "D:\tmp"`).
- **DO NOT upload dataset to Kaggle (D8.8) until user explicitly says so.**

PHASE D-PREP GOAL: Prepare a high-quality detection dataset with **5,000+ properly annotated images** from 7+ sources.

DATA SOURCES:
1. V1 raw detection images: 496 JPGs at D:\Personal attachements\Projects\Final_Horus\Wadjet\hieroglyph_model\data\raw\detection_images\
2. HLA Dataset: https://huggingface.co/datasets/AhmedElTaher/Egyptian_Hieroglyphic_Layout_Analysis_HLA (897 images, COCO format)
3. Signs Segmentation: https://huggingface.co/datasets/AhmedElTaher/Egyptian_Hieroglyphic_Signs_Segmentation_with_Orientation (300 images)
4. Museum scraping (10+ museums): Met API, British Museum IIIF, Wikimedia, Museo Egizio, Louvre, Brooklyn, Penn, Oriental Institute, Petrie, IFAO, Flickr, Europeana — target: 2,500-3,000 images
5. Existing Kaggle/HF datasets: search and download any other hieroglyph detection datasets (target: 200-500)
6. Synthetic composites: Paste classification glyphs onto stone textures (target: 1,000)
7. Roboflow: https://universe.roboflow.com/project-jsqal/hieroglyph-dataset-gzd5g (40 images, CC BY 4.0)
8. CLIP-filtered web images: Google/Bing/Flickr → CLIP filter for relevance (target: 300-500)

TOOLS (all cloned at D:\Personal attachements\Repos\):
- **GroundingDINO** via `transformers` (already installed in dataprep-env) — PRIMARY annotation tool. `AutoModelForZeroShotObjectDetection` + `AutoProcessor`. Zero-shot: text prompt → bounding boxes. Runs on CPU.
- **Scrapling** at `Repos/22-Web-Scraping/Scrapling/` — PRIMARY scraping tool. Spider framework, StealthyFetcher (Cloudflare bypass), DynamicFetcher (Playwright), async, rate limiting, proxy rotation, pause/resume, per-domain throttling
- **browser-use** at `Repos/06-AI-Agents/browser-use/` — AI browser agent for JS-heavy museum sites (Playwright + LLM)
- **CLIP / open_clip** at `Repos/CLIP/`, `Repos/open_clip/` — Text-image similarity for filtering: score images against "ancient Egyptian hieroglyph inscription", drop < 0.25
- **supervision** at `Repos/supervision/` — Dataset format conversion (COCO↔YOLO↔VOC), merging, splitting, annotation visualization
- **label-studio** at `Repos/label-studio/` — Web annotation UI: import auto-proposals, human verify/correct, export YOLO
- **albumentations** at `Repos/albumentations/` — Augmentation: CLAHE, perspective, shadow, noise
- **kaggle-api** at `Repos/kaggle-api/` — Search/download Kaggle datasets
- **HF datasets** at `Repos/07-HuggingFace/datasets/` — Stream HuggingFace datasets
- Classification dataset (for synthetic): data/hieroglyph_classification/ (16,638 images, 171 classes)

SCRAPING STRATEGY:
The primary tool is Scrapling's Spider framework — NOT basic requests. For each museum:
1. Create a Scrapling Spider class with start_urls and parse() method
2. Configure per-domain rate limiting (2-5 second delays)
3. Use StealthyFetcher for sites with anti-bot protection
4. Use browser-use AI agent for JS-heavy interactive galleries
5. Save all images with metadata (source, URL, license, download date)
6. Deduplicate with perceptual hash (pHash) across all museums
7. Filter with CLIP for relevance (remove non-hieroglyph images)

ANNOTATION PIPELINE:
1. CLIP filter → 2. GroundingDINO auto-annotate (via transformers, CPU) → 3. supervision format → 4. Label Studio verify

SCRIPTS TO CREATE:
1. scripts/scrape_museums.py              — Scrapling spiders for 10+ museums (modular, one class per museum)
2. scripts/clip_filter_images.py          — CLIP-based relevance filtering
3. scripts/annotate_with_gdino.py         — GroundingDINO auto-annotation → YOLO format
4. scripts/convert_hla_to_yolo.py         — HLA/Signs COCO → YOLO via supervision
5. scripts/generate_synthetic_composites.py — synthetic training images
6. scripts/merge_detection_datasets.py    — merge all 7+ sources, deduplicate, split
7. scripts/validate_dataset.py            — dataset QA (stats, visualization, consistency)

CONSTRAINTS:
- Output: YOLO format (class_id cx cy w h, normalized 0-1)
- Single class: all labels use class_id = 0 (hieroglyph)
- No horizontal flip in data augmentation (glyph orientation = meaning)
- Stratify splits by source for diversity
- Track license per image source
- Use ethical scraping: rate limiting, respect robots.txt, prioritize CC0/Public Domain

Start with D1.1: Set up GroundingDINO via transformers (already installed in dataprep-env). Then write the annotation script.
```

---

## PHASE D-TRAIN — Model Training

> Send this prompt after data preparation is complete.

```
We're working on Wadjet v2 — an AI-powered Egyptian heritage web app.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST:
1. CLAUDE.md
2. planning/detector-rebuild/MASTER_PLAN.md
3. planning/detector-rebuild/REBUILD_TASKS.md  ← start at Phase D-TRAIN
4. planning/detector-rebuild/DETECTOR_REBUILD_PLAN.md

CONTEXT:
- Phase D-PREP is COMPLETE. Detection dataset is uploaded to Kaggle.
- Dataset: 5,000+ images with YOLO format labels, train/val/test splits.
- 20 real stone inscription photos in test set.
- Kaggle account: nadermohamedcr7
- Kaggle CLI: .venv\Scripts\kaggle.exe

PHASE D-TRAIN GOAL: Train YOLO26s on our dataset and export to ONNX uint8.

KAGGLE LESSONS (from 36 bugs across v1-v7 classifier training — ALL VERIFIED):

ENVIRONMENT:
- kernel-metadata.json: `"machine_shape": "NvidiaTeslaT4"` (P100 dropped in PyTorch 2.10+cu128)
- kernel-metadata.json: `"id": "nadermohamedcr7/<kernel-slug>"` (exact format required)
- kernel-metadata.json: `dataset_sources: ["nadermohamedcr7/<dataset-slug>"]` (must match upload)
- First cell: `pip install -U ultralytics` (Kaggle may have old version without YOLO26)
- First cell: `pip install -q onnxscript` (NOT pre-installed, needed for ONNX export)
- `import pytorch_lightning as L` NOT `import lightning` (old package name on Kaggle)
- Pre-installed (no pip): torch, torchvision, timm, onnx, onnxruntime, albumentations, sklearn

DATA HANDLING:
- 3-level DATA_ROOT auto-discovery code (Kaggle mount paths are unpredictable)
- NO apostrophes/special chars in dataset filenames (breaks zip upload)
- dataset_sources format: `"owner/slug"` must be exact

TRAINING:
- NO horizontal flip (`fliplr=0.0, flipud=0.0`) — hieroglyph orientation = meaning!
- KeepAlive prints with flush=True every N batches (papermill kills cells with >4s silence — IOPub timeout)
- `enable_progress_bar=False` if using PyTorch Lightning (tqdm breaks papermill)
- `precision="32-true"` (mixed precision creates fused ops that break ONNX)
- Cell IDs on EVERY notebook cell (missing IDs = future nbformat hard error)

ONNX EXPORT:
- `dynamo=False` in torch.onnx.export (dynamo=True creates separate .onnx.data sidecar file)
- `dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}}` (without = batch locked at 1)
- Assert output shape `[1, 300, 6]` after export (prevents deploying wrong model)
- Assert uint8 model size < 20MB (web serving budget)
- For YOLO26: ultralytics handles most export internally — but VERIFY output shape and size

NOTE: Some fixes (IOPub, progress bar, precision) may need adaptation for YOLO26 since ultralytics
has its own training loop. Check ultralytics source + test locally before pushing to Kaggle.

REFERENCE NOTEBOOKS (both successful, use as template for structure):
- planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier.ipynb (98.18% top-1)
- planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb (93.80% top-1)

TRAINING CONFIG:
- Model: yolo26s.pt (COCO pretrained, pip install -U ultralytics)
- Input: 640×640, single class ("hieroglyph")
- Epochs: 150, patience: 30, batch: 16
- NO horizontal flip (fliplr=0.0), NO vertical flip (flipud=0.0)
- End-to-end export (NMS-free, output [1, 300, 6])
- Quantize to uint8 with onnxruntime.quantization

QUALITY GATES:
- mAP50 ≥ 0.85
- Precision ≥ 0.80, Recall ≥ 0.80
- Real stone inscription test: detect ≥ 12/20 visible glyphs
- AI fallback rate < 50% on test set
- ONNX uint8 < 20MB
- Output shape: [1, 300, 6]

FILES TO CREATE:
- planning/model-rebuild/pytorch/detector/hieroglyph_detector.ipynb
- planning/model-rebuild/pytorch/detector/kernel-metadata.json

Start with T1.1: Create the Kaggle training notebook.
```

---

## PHASE D-INTEGRATE — Backend Integration

> Send this prompt after model is trained and ONNX exported.

```
We're working on Wadjet v2 — an AI-powered Egyptian heritage web app.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST:
1. CLAUDE.md
2. planning/detector-rebuild/MASTER_PLAN.md
3. planning/detector-rebuild/REBUILD_TASKS.md  ← start at Phase D-INTEGRATE
4. app/core/postprocess.py  ← MUST READ — this is the file to update
5. app/core/hieroglyph_pipeline.py  ← pipeline that uses the detector
6. app/api/scan.py  ← has AI fallback code (keep it)

CONTEXT:
- Phase D-TRAIN is COMPLETE. New YOLO26s model is trained and exported.
- Model files are at: models/hieroglyph/detector/
  - glyph_detector_uint8.onnx (new YOLO26s, NMS-free)
  - model_metadata.json (documents input/output shapes)

CRITICAL CHANGE — OUTPUT FORMAT:
- OLD (YOLOv8s): output [1, 5, 8400] → needed NMS post-processing
- NEW (YOLO26s): output [1, 300, 6] → NMS-free, direct detections
  - Columns: [x1, y1, x2, y2, confidence, class_id]
  - Max 300 detections per image

PHASE D-INTEGRATE GOAL: Update postprocess.py for new output format and deploy.

CHANGES NEEDED:
1. postprocess.py — Rewrite postprocess() method:
   - Parse [1, 300, 6] output (not [1, 5, 8400])
   - Remove NMS step (model handles it internally)
   - Keep: confidence filter, size filter, rescale to original coords
   - Keep: preprocess() mostly unchanged (letterbox 640)
2. models/hieroglyph/detector/ — Replace old ONNX with new one
3. Test end-to-end: POST /api/scan with real photos
4. Verify AI fallback still works
5. Push to GitHub + HF Spaces

DO NOT CHANGE:
- app/core/hieroglyph_pipeline.py (unless model path changed)
- app/api/scan.py (AI fallback stays)
- Any frontend templates or CSS
- The classifier (MobileNetV3-Small works fine)

Start with I1.1: Update postprocess.py for the new YOLO26s output format.
```

---

## QUICK RESUME PROMPT (Any Phase)

> Use this to resume work mid-session.

```
We're continuing the Wadjet v2 detector rebuild.
Project: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

Read planning/detector-rebuild/PROGRESS.md to see current status.
Read planning/detector-rebuild/REBUILD_TASKS.md for task tracker.

Continue from where we left off. Check PROGRESS.md for the last completed task.
```
