# Wadjet v2 — Detector Rebuild Known Issues

> This file explains WHY the current detector is broken and what the rebuild fixes.
> Ground truth for understanding the problem before starting work.

---

## ISSUE 1: Detector Fails on Real Stone Inscriptions

**Symptom**: The ONNX hieroglyph detector (`glyph_detector_uint8.onnx`, YOLOv8s) finds ≤2 glyphs or returns very low confidence (avg <0.30) on real stone inscription photos. Clean composite images work fine (9/10 glyphs at >64% confidence).

**Root Cause**:
The detector was trained on only **261 images** with **auto-generated labels**. Labels were created by running OpenCV algorithms (CLAHE → threshold → contour detection → NMS) on the images — NOT by a human annotating actual glyph locations. The model learned to detect "things that look like contours in processed images" rather than actual hieroglyphs on stone.

**Why it wasn't caught earlier**:
- The V1 validation set was a subset of the same auto-labeled data → artificially high metrics (mAP50=0.8753)
- Never tested on real museum stone photos during development
- The AI fallback system (Gemini reads inscriptions) masked the detector's failure in production

**Evidence**:
- Clean composite: 9/10 glyphs detected at avg 64% confidence
- Real stone wall: 1/20 glyphs detected at 18% confidence
- Current AI fallback rate: >90% (Gemini doing almost all detection work)

**Fix**: Rebuild detector from scratch with:
1. **YOLO26s** architecture (NMS-free, better small object detection)
2. **5,000+ properly annotated images** (GroundingDINO via `transformers` + Label Studio human verification)
3. **Multi-source data** (10+ museums via Scrapling, HLA dataset, synthetics, CLIP-filtered web images)
4. **Real stone test set** (20 photos) in quality gates
5. **CLIP filtering** to ensure image relevance
6. **Ethical scraping** via Scrapling with rate limiting, proxy rotation, and pause/resume

**Status**: Planning complete. Data preparation not started.

---

## ISSUE 2: Auto-Generated Labels Are Unreliable

**Symptom**: V1 training labels (YOLO format .txt files) have bounding boxes that don't accurately capture individual hieroglyphs.

**Root Cause**:
The V1 annotation pipeline used:
```
Image → CLAHE enhancement → Adaptive threshold → Find contours → Filter by area → NMS → YOLO labels
```
This is a fragile heuristic that:
- Merges adjacent glyphs into one box (under-segmentation)
- Splits complex glyphs into multiple boxes (over-segmentation)
- Labels stone texture as glyphs (false positives)
- Misses worn/faded glyphs entirely (false negatives)

**Fix**: Re-annotate ALL V1 images using **GroundingDINO** (via `transformers` — `AutoModelForZeroShotObjectDetection`) for zero-shot detection, followed by human verification in **Label Studio** (`Repos/label-studio/`). Use **supervision** (`Repos/supervision/`) for format conversion and visual QA. Discard all old auto-generated labels.

**Status**: Not started.

---

## ISSUE 3: Output Format Incompatibility (Future)

**Symptom**: Will occur when new YOLO26s model replaces old YOLOv8s.

**Root Cause**:
- Old model: output `[1, 5, 8400]` (transposed: xy, wh, conf per anchor)
- New model: output `[1, 300, 6]` (direct: x1, y1, x2, y2, conf, class_id)

The current `postprocess.py` expects `[1, 5, 8400]` and applies manual NMS. The new model's NMS-free end-to-end output requires a different parsing approach.

**Fix**: Rewrite `GlyphDetector.postprocess()` in `app/core/postprocess.py` to:
1. Parse `[1, 300, 6]` directly
2. Remove NMS step
3. Keep confidence filter, size filter, coordinate rescaling

**Status**: Will be addressed in Phase D-INTEGRATE after model is trained.

---

## ISSUE 4: Domain Gap Between Training and Inference

**Symptom**: Detector works on clean digital images but fails on worn stone, low contrast, shadow, and 3D relief carvings.

**Root Cause**: V1 training data was mostly clean photos. Real-world hieroglyphs appear on:
- Weathered limestone with erosion damage
- Granite with complex texture
- Painted surfaces (Valley of the Kings) with color fading
- 3D relief with shadow depending on lighting angle
- Papyrus with stains and tears

**Fix**: Multi-source training data strategy:
1. **Real museum photos** from 10+ museums (HLA dataset: Cairo Museum, Met, Louvre, British Museum; + scraped via **Scrapling** spiders)
2. **CLIP filtering** (`Repos/CLIP/`) to ensure all images contain actual hieroglyph inscriptions
3. **Synthetic composites** (~1,000) with simulated wear, lighting, texture
4. **Heavy augmentation** (HSV jitter, perspective warp, noise, CLAHE via albumentations)
5. **Source-stratified splits** ensuring val/test have real stone photos from diverse museums

**Status**: Will be addressed during data preparation (Phase D-PREP).

---

## ISSUE 5: Kaggle Training Bug Registry (36 Bugs from Classifier Training)

> These bugs were discovered across v1-v7 of the hieroglyph and landmark classifier training.
> The detector notebook MUST account for ALL of them. See MASTER_PLAN.md §2.1 for the full table.

### Critical (will silently break training or export):

| Bug | Symptom | Fix |
|-----|---------|-----|
| P100 GPU incompatible | CUDA error (sm_60 dropped in PyTorch 2.10+cu128) | `"machine_shape": "NvidiaTeslaT4"` in kernel-metadata.json |
| Dataset not found | `FileNotFoundError` at training start | Auto-discovery DATA_ROOT code (3-level fallback) |
| Wrong dataset slug | Dataset mounts empty | `dataset_sources: ["nadermohamedcr7/<exact-slug>"]` |
| IOPub timeout (papermill) | Kernel silently killed during training | Print progress with `flush=True` every N batches (KeepAlive pattern) |
| tqdm breaks papermill | Garbled output, possible freeze | `enable_progress_bar=False` (for Lightning); check ultralytics behavior |
| Mixed precision fused ops | ONNX Runtime crash with unsupported ops | `precision="32-true"` / verify ultralytics not using AMP |
| `dynamo=True` sidecar file | Two-file ONNX output breaks deployment | `dynamo=False` in `torch.onnx.export()` |
| Missing `dynamic_axes` | Batch dimension locked at 1 | Add `dynamic_axes` to ONNX export call |
| H-flip on hieroglyphs | Model learns mirrored glyphs (don't exist) | `fliplr=0.0, flipud=0.0` |

### Medium (will cause push/download failures):

| Bug | Symptom | Fix |
|-----|---------|-----|
| Wrong kernel-metadata.json ID | Push rejected | `"id": "nadermohamedcr7/<slug>"` exact format |
| Missing cell IDs | nbformat warning → future hard error | Add `#VSC-XXXXXXXX` IDs to all cells |
| `onnxscript` not installed | `torch.onnx.export()` fails | `pip install -q onnxscript` in first cell |
| `lightning` → `pytorch_lightning` | Import error | Use `import pytorch_lightning as L` |
| Apostrophes in filenames | Kaggle zip upload corrupted | Remove special chars before upload |
| No output size assertion | Oversized model deployed | Assert uint8 < 20MB |

### Important Notes for YOLO26s (differences from classifier notebooks):

1. **ultralytics has its own training loop** — it handles progress bars, data loading, augmentation, ONNX export. Many fixes (KeepAlive, enable_progress_bar, precision) may need adaptation.
2. **YOLO export uses `model.export(format="onnx", end2end=True)`** — different from manual `torch.onnx.export()`. dynamic_axes and dynamo flags may not apply directly.
3. **Always verify**: After export, load the ONNX in `ort.InferenceSession` and assert output shape `[1, 300, 6]`.
4. **Reference notebooks**: `planning/model-rebuild/pytorch/hieroglyph/` and `landmark/` — use as structural templates.

**Status**: All fixes documented. Will be applied when creating detector training notebook (Phase D-TRAIN, task T1.3).

---

## NON-ISSUES (Things That Work Fine)

| Component | Status | Notes |
|-----------|--------|-------|
| Hieroglyph Classifier | ✅ Working | MobileNetV3-Small, 98.18% top-1, 171 classes |
| Landmark Classifier | ✅ Working | EfficientNet-B0, 93.80% top-1, 52 classes |
| AI Fallback (Gemini) | ✅ Working | Reads inscriptions when detector fails |
| Ensemble System | ✅ Working | ONNX + Gemini + Grok tiebreaker |
| Full Sequence Verification | ✅ Working | AI verifies all glyph classifications |
| Frontend (all 9 pages) | ✅ Working | Do not change |
| Backend APIs | ✅ Working | Only postprocess.py needs update |
| HF Spaces Deployment | ✅ Working | Docker build, port 7860 |
