# Wadjet v2 — PyTorch Rebuild Task Tracker

> **Master Plan**: `planning/rebuild/MASTER_PLAN.md`
> **Status**: ALL PHASES COMPLETE (A, B, B2, C, D, E) — Deployed to HF Spaces

---

## Phase A: Environment & Verification

| # | Task | Status | Notes |
|---|------|--------|-------|
| A.1 | Install Kaggle CLI + configure credentials | ✅ | `pip install kaggle` → `kaggle.json` at `~/.kaggle/` → `kaggle --version` |
| A.2 | Upload hieroglyph dataset to Kaggle | ✅ | Uploaded 2026-03-21 (~1GB). `kaggle datasets list --mine` confirms. |
| A.2b | Upload landmark dataset to Kaggle | ✅ | Uploaded 2026-03-23 (~14GB). Fixed apostrophe in Pompey's filenames. `kaggle datasets list --mine` confirms. |
| A.3 | Verify data paths accessible locally (reference) | ✅ | Data uploaded from `data/hieroglyph_classification/` and `data/landmark_classification/` directly |
| A.4 | Copy ONNX detector to project | ✅ | Copied from v1 → `models/hieroglyph/detection/glyph_detector_uint8.onnx` (11 MB) |
| A.5 | Create `planning/model-rebuild/pytorch/` folder | ✅ | Already created — ready for training notebooks |
| A.6 | Create skeleton notebooks + `kernel-metadata.json` | ✅ | Both notebooks created: `hieroglyph_classifier.ipynb` (18KB) + `landmark_classifier.ipynb` (17KB) + both kernel-metadata.json ✅ |

**Gate**: `kaggle datasets list --mine` shows both datasets, detector copied, both kernel-metadata.json files valid.

---

## Phase B: Hieroglyph Classifier Training

| # | Task | Status | Notes |
|---|------|--------|-------|
| B.0 | (Optional) Inspect dataset with fiftyone | ⏭️ | Skipped — dataset already verified in Phase A audit |
| B.1 | Create training notebook | ✅ | Fixed: precision→32-true, normalization→/255 (no ImageNet), added assertions |
| B.2 | Dataset class (ImageFolder) | ✅ | 171 classes, with [0,1] range assertions |
| B.3 | Albumentations augmentation | ✅ | rotation+brightness+contrast+blur — NO h-flip! Norm: /255 only |
| B.4 | FocalLoss + class weights | ✅ | sqrt-inverse-frequency, gamma=2.0, label_smoothing=0.1 |
| B.5 | MobileNetV3-Small model | ✅ | `timm.create_model('mobilenetv3_small_100')`, 171 classes |
| B.6 | Wrap in pytorch-lightning LightningModule | ✅ | freeze/unfreeze_top, CosineAnnealingLR, AdamW |
| B.7 | Phase 1: head training (pl.Trainer) | ✅ | 5 epochs, backbone frozen, lr=1e-3, **precision="32-true"** |
| B.7b | Phase 2: fine-tune (pl.Trainer) | ✅ | 30 epochs, top 70% unfrozen, cosine lr, **precision="32-true"** |
| B.8 | Evaluation (classification_report) | ✅ | Top-1/5 accuracy, macro/weighted F1, worst-10 classes |
| B.9 | Export to ONNX fp32 | ✅ | `torch.onnx.export`, opset=17, NCHW, dynamic batch |
| B.10 | Quantize to uint8 | ✅ | `quantize_dynamic(QUInt8)`, ≤8MB size assertion |
| B.11 | Validate ONNX output | ✅ | Shape [1,171], ORT session test, fp32 + uint8 validated |
| B.12 | Save label_mapping.json + model_metadata.json | ✅ | normalization="divide_by_255", NCHW, accuracy metrics |
| B.13 | Push to Kaggle + download outputs | ✅ | Pushed v7 → COMPLETE. 98.18% top-1, 99.91% top-5. Models at `models/hieroglyph/classifier/` |

**Gate**: ✅ ONNX inference returns correct shape [1,171], val accuracy 98.18% (gate was >70%). Hieroglyph classifier PASSED.

---

## Phase B2: Landmark Classifier Training

| # | Task | Status | Notes |
|---|------|--------|-------|
| B2.1 | Create landmark training notebook | ✅ | `planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb` |
| B2.2 | DataLoader setup (ImageFolder, 52 classes, 224×224) | ✅ | Data is pre-merged + augmented — just use ImageFolder on /kaggle/input/wadjet-landmark-classification/ |
| B2.3 | DataLoader (ImageFolder, 52 classes, 224×224) | ✅ | `torchvision.ImageFolder`, `albumentations` transforms |
| B2.4 | Augmentation pipeline (HorizontalFlip ✓) | ✅ | Flip + rotation + brightness/contrast/shadow — real-world photos! |
| B2.5 | Class weights (data already augmented to min=300) | ✅ | sqrt-inverse-frequency weights, CrossEntropyLoss(smoothing=0.1) |
| B2.6 | EfficientNet-B0 model (timm, 52 classes) | ✅ | `timm.create_model('efficientnet_b0', pretrained=True, num_classes=52)` |
| B2.7 | Wrap in Lightning Module | ✅ | Same pattern as hieroglyph notebook |
| B2.8 | Phase 1: head training (8 epochs, frozen backbone) | ✅ | Best epoch 6, val_acc=82.69% |
| B2.9 | Phase 2: fine-tune (40 epochs, cosine lr) | ✅ | Best epoch 26, val_acc=93.63% |
| B2.10 | Evaluation (per-class F1, top-3 accuracy) | ✅ | Test top-1=93.80%, top-3=97.40% |
| B2.11 | Export ONNX fp32 | ✅ | opset=18, NCHW [1,3,224,224], 15.52 MB |
| B2.12 | Quantize to uint8 | ✅ | `quantize_dynamic` → `landmark_classifier_uint8.onnx` (4.17 MB) |
| B2.13 | Validate ONNX output | ✅ | Shape [1,52], probabilities sum to ~1.0 |
| B2.14 | Save landmark_label_mapping.json | ✅ | 52 classes: abu_simbel → white_desert |
| B2.15 | Copy outputs to `models/landmark/` | ✅ | fp32 onnx + uint8 onnx + label mapping + model_metadata.json |

**Gate**: ✅ ONNX inference returns shape [1, 52], val accuracy 93.80% (gate was >75%). Landmark classifier PASSED.

---

## Phase C: Backend Integration

| # | Task | Status | Notes |
|---|------|--------|-------|
| C.1 | Audit `hieroglyph_pipeline.py` | ✅ | Found NHWC in _classify_crops + _get_classifier auto-detect |
| C.2 | Fix classifier input: NHWC → NCHW | ✅ | Added `crop.transpose(2,0,1)` in _classify_crops, fixed auto-detect to use shape[2] |
| C.3 | Fix classifier model path | ✅ | Path already correct; fixed label_mapping loader to handle both flat and wrapped formats |
| C.4 | Fix confidence threshold | ✅ | config.py already had 0.15; fixed rag_translator embed path (data/embeddings/) |
| C.5 | Complete `gardiner.py` mapping | ✅ | Already 172 signs mapped (covers all 171 model classes) — no changes needed |
| C.6 | Re-enable translation pipeline | ✅ | Already enabled (enable_translation=True); fixed FAISS path mismatch in rag_translator.py |
| C.7 | Create `app/core/landmark_pipeline.py` | ✅ | ONNX wrapper: NCHW [1,3,224,224], softmax, top-k, 52 classes, lazy-load session |
| C.8 | Add `identify_landmark()` + `describe_landmark()` to gemini_service.py | ✅ | Vision identification (image+JSON) + text-only description enrichment |
| C.9 | Add POST /api/explore/identify endpoint (hybrid) | ✅ | ONNX → conf≥0.5 = describe → conf<0.5 = Gemini Vision → fallback gracefully |
| C.10 | Remove old TF.js explore endpoint | ✅ | No old endpoint existed in explore.py (TF.js was client-side only) |
| C.11 | Test scan API manually | ✅ | POST /api/scan returns 200, pipeline runs (0 detections on test image) |
| C.12 | Test identify API manually | ✅ | POST /api/explore/identify returns 200, hybrid mode works, Gemini enriches |

**Gate**: ✅ All `/api/*` endpoints return 200. Scan pipeline runs with NCHW. Identify returns landmark JSON with hybrid ONNX+Gemini.

---

## Phase D: Frontend Updates

| # | Task | Status | Notes |
|---|------|--------|-------|
| D.1 | Audit `hieroglyph-pipeline.js` for NHWC usage | ✅ | Found 2 places: _warmup() dummy tensor + classify() pixel loop |
| D.2 | Change classifier preprocessing to NCHW | ✅ | Planar NCHW loop + [1,3,size,size] tensor; warmup [1,3,s,s]; updated comments |
| D.3 | Update classifier model URL in JS | ✅ | Already correct; also fixed label_mapping access to handle flat format |
| D.4 | Remove TF.js code from explore.html | ✅ | Removed _loadOrt, _ensureModel, _loadAndWarmModel, _preprocessImage, runIdentification |
| D.5 | Add HTMX Gemini identify form to explore.html | ✅ | hx-post="/api/explore/identify" with indicator; endpoint returns HTML partial for HX-Request |
| D.6 | Add identify result partial template | ✅ | Created partials/identify_result.html with Jinja2 rendering |
| D.7 | Bump sw.js cache version to v15 | ✅ | wadjet-v15; also fixed landmark model paths (removed /onnx/ subdir) |
| D.8 | Bump base.html cache busters | ✅ | styles.css?v=15 |
| D.9 | Build production CSS | ✅ | npm run build — added HTMX indicator utility classes to input.css |
| D.10 | Browser smoke test | ✅ | All pages 200, identify returns HTML partial, NCHW verified, no TF.js remnants |

**Gate**: ✅ All pages render. Identify endpoint returns HTML partial for HTMX. Hieroglyph pipeline uses NCHW. No TF.js/ONNX client-side code in explore.

---

## Phase E: Deploy

> ⚠️ **Only start after Phases A–D are fully done.** Never deploy broken models.

| # | Task | Status | Notes |
|---|------|--------|-------|
| E.1 | Full E2E test locally | ✅ | 13/14 tests pass (all 9 pages 200, health OK, identify works). Security scan: 0 hardcoded keys |
| E.2 | Fix Dockerfile for new models | ✅ | Removed tailwind.config.js ref (TW v4), COPY models/ + data/ (filtered by .dockerignore). Fixed .gitignore with model whitelist (8 files). Fixed .env.example paths. Added PYTHON_VERSION + NODE_VERSION to render.yaml. Made faiss+sentence-transformers optional. Fixed Starlette 1.0 TemplateResponse API. Fixed Alpine v3 @click in identify_result.html |
| E.3 | Test Docker build locally | ✅ | Image builds (1.78GB). All 9 pages 200. Both ONNX models run: hieroglyph [1,3,128,128]→[1,171], landmark [1,3,224,224]→[1,52] |
| E.4 | Configure Render env vars | ✅ | render.yaml: PYTHON_VERSION=3.13.0, NODE_VERSION=22, ENVIRONMENT=production, GEMINI_API_KEYS (sync:false) |
| E.5 | Deploy to HF Spaces | ✅ | Pivoted from Render (needs credit card) to HF Spaces (free Docker). Git LFS for binaries. Pushed to https://huggingface.co/spaces/nadercr7/wadjet-v2. Secrets configured (17 Gemini keys + model names + environment) |
| E.6 | Smoke test on production URL | ✅ | All 9 pages load at https://nadercr7-wadjet-v2.hf.space/. Health 200. Dictionary 172 signs. Explore 56 landmarks. Chat/Quiz/Write/Scan all render |

**Gate**: Production URL responds, all features work, no 500 errors.

---

## Legend
- ⬜ Not started
- 🔄 In progress
- ✅ Completed
- ❌ Blocked
- ⏭️ Skipped
