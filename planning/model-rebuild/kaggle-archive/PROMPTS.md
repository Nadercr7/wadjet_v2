# Model Rebuild — Prompts

> **Last Updated**: 2026-03-20 Session 6 — **Deep Research Complete**

---

## Prompt 1: START (New Phase)

Use this prompt to start working on any phase of the model rebuild.
Replace `[PHASE NUMBER]` and `[PHASE NAME]` with the correct values.

```
## Context
I'm working on the Wadjet v2 project — an AI-powered Egyptian heritage web app.
Workspace: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2

## Planning Files (READ THESE FIRST — IN ORDER)
Before doing ANYTHING, read these files:
1. `CLAUDE.md` at project root — tech stack, design system, coding conventions
2. `planning/model-rebuild/PLAN.md` — Master plan, ONNX architecture, root cause analysis, deep research findings
3. `planning/model-rebuild/PROGRESS.md` — Current status of all tasks
4. `planning/model-rebuild/TASKS.md` — Detailed task breakdown (Phase 0-5)
5. `planning/model-rebuild/SESSION_LOG.md` — Previous session decisions and learnings (6 sessions)
6. `planning/model-rebuild/CHECKLIST.md` — Pre-launch validation checklist

## CRITICAL RULES (MUST FOLLOW — NON-NEGOTIABLE)
These are learned from 17+ iterations of debugging. Violating any of these WILL break the project.

### Model Training
- Train with **float32 ONLY** — NO mixed_float16 (causes fused ops that crash in any runtime)
- Use **MobileNetV3-Small** (hieroglyph, 128×128) or **EfficientNetV2-B0** (landmark, 224×224)
- **NO horizontal flip** for hieroglyph augmentation (orientation matters — Rule #31)

### Model Export — ONNX ONLY
- Export via **`tf2onnx.convert.from_keras(model, input_signature=spec)`** → `.onnx` file
- Quantize to uint8 via **`onnxruntime.quantization.quantize_dynamic()`**
- **NEVER** use `save_keras_model()`, `convert_tf_saved_model()`, or any TF.js converter
- **NEVER** use `tensorflowjs_converter` in any form
- Validate ONNX output matches Keras output before deploying

### Browser Loading — ONNX Runtime Web ONLY
- Load with **`ort.InferenceSession.create(url, {executionProviders: ['wasm']})`**
- **NEVER** use `tf.loadLayersModel()` or `tf.loadGraphModel()` — TF.js is REMOVED
- Classifiers (Keras origin): **NHWC** input — `new ort.Tensor('float32', data, [1,H,W,3])`
- Detector (YOLOv8): **NCHW** input — `new ort.Tensor('float32', data, [1,3,H,W])`
- Preprocessing: resize → /255.0 → flatten pixel data into Float32Array → create ort.Tensor
- Webcam: **`setTimeout(() => onPlay())`** pattern (from face-api.js), NOT requestAnimationFrame
- Video: draw frame to canvas → `getImageData()` → Float32Array → ort.Tensor

### Architecture Rule
- **ZERO TF.js in the project** — no CDN imports, no `tf.*` calls, no tfjs packages
- ONNX Runtime Web is the ONLY browser ML runtime (already loaded for YOLOv8 detector)

## Available Resources
- **Skills**: `D:\Personal attachements\Repos\antigravity-awesome-skills\skills\` (883 skills)
  - Phase 1-2 (Models): Load `computer-vision-expert`, `ml-engineer`, `data-scientist`
  - Phase 3 (Backend): Load `fastapi-pro`, `fastapi-router-py`
  - Phase 4 (Browser): reference `D:\Personal attachements\Repos\face-api.js\` for webcam patterns
  - Phase 5 (Testing): Load `web-performance-optimization`
- **V1 Reference**: `D:\Personal attachements\Projects\Final_Horus\Wadjet\` — training notebooks, data, working pipeline
- **Templates**: `D:\Personal attachements\Repos\spec-kit\templates\`

## Kaggle Datasets
- Own dataset: `naderelakany/wadjet-tfrecords` (171 classes hieroglyph + 52 classes landmark, TFRecords)
- Additional (if needed): `mohieymohamed/heroglyphics-signs` (767 classes, 33K images, Apache 2.0)

## Current Phase: [PHASE NUMBER]
I want to work on **Phase [X]: [PHASE NAME]** from the PLAN.

## Instructions
1. Read all planning files first (the order matters)
2. Check PROGRESS.md for what's already done
3. Load relevant skills for this phase from the Repos folder
4. Work through TASKS.md items for this phase systematically
5. Update PROGRESS.md after completing each task
6. Log decisions and learnings in SESSION_LOG.md
7. If something is unclear, research before guessing — check V1 code, skills, or online
8. Test everything after making changes
9. DON'T break what's already working
10. Remember: ALL browser ML goes through ONNX Runtime Web — no TF.js anywhere
```

---

## Prompt 2: CONTINUE (Resume Mid-Phase)

```
## Context
I'm continuing work on the Wadjet v2 model rebuild project.
Workspace: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2

## What to do FIRST
1. Read `planning/model-rebuild/PROGRESS.md` — check what was completed last session
2. Read `planning/model-rebuild/SESSION_LOG.md` — understand previous decisions and blockers
3. Read `planning/model-rebuild/TASKS.md` — find the next uncompleted tasks
4. Read `planning/model-rebuild/PLAN.md` — for overall context and the ONNX architecture

## REMINDER: Critical Rules (ONNX-Unified)
- **float32 ONLY** (no mixed_float16)
- **`tf2onnx.convert.from_keras()`** for export (never any TF.js converter)
- **`ort.InferenceSession.create()`** in browser (never any `tf.*` API)
- **`setTimeout(() => onPlay())`** for webcam (not requestAnimationFrame)
- **No horizontal flip** for hieroglyph augmentation
- **ZERO TF.js** in the entire project — fully removed

## Continue Workflow
1. Pick up from the next incomplete task in TASKS.md
2. Complete one task at a time
3. Test after each task
4. Update PROGRESS.md immediately after each task
5. Log in SESSION_LOG.md any decisions, issues, or learnings

## Important Rules
- Read existing code before modifying it
- Don't break working features
- If a model training step needs Kaggle, prepare the notebook locally but note it needs manual upload
- Always bump service worker cache version after model changes
- Test in browser after any model/pipeline change

## Resources
Same as START prompt — skills, V1 ref, face-api.js patterns, Kaggle datasets (see PLAN.md)
```

---

## Quick Reference: Phase-Specific Notes

### Phase 0 (Data Preparation) — ✅ COMPLETE
All data prep done. 15K hieroglyph images (171 classes), 46K landmark images (52 classes).
label_mapping.json fixed. Rare class strategy: keep all 171, Focal Loss handles imbalance.

### Phase 1 (Hieroglyph Classifier — ONNX)
- Training data: `naderelakany/wadjet-tfrecords` → `classification/` subdirectory
- Label mapping: `models/hieroglyph/label_mapping.json` (171 classes, idx_to_gardiner, fixed Session 3)
- Architecture: MobileNetV3-Small, 128×128
- Export: `tf2onnx.convert.from_keras()` → `hieroglyph_classifier.onnx` → `quantize_dynamic()` → `hieroglyph_classifier_uint8.onnx`
- Deploy to: `models/hieroglyph/classifier/`
- Notebook ready at: `planning/model-rebuild/notebooks/hieroglyph_classifier.ipynb`

### Phase 2 (Landmark Classifier — ONNX)
- Training data: `naderelakany/wadjet-tfrecords` → `train/`/`val/`/`test/` directories
- Metadata: `models/landmark/tfjs/model_metadata.json` (52 class names + display names)
- Architecture: EfficientNetV2-B0, 224×224
- Export: same ONNX pipeline as Phase 1
- Deploy to: `models/landmark/onnx/`
- Notebook ready at: `planning/model-rebuild/notebooks/landmark_classifier.ipynb`

### Phase 3 (Backend Fixes)
- All fixes in `app/core/` and `app/templates/`
- `gardiner.py` needs 100+ additional sign entries from `label_mapping.json` (currently only 71/171)
- Update `hieroglyph_pipeline.py` to use `onnxruntime` instead of Keras for classification
- Translation: flip two flags (`enable_translation=True` in dependencies.py, `translate=true` in scan.html)
- Detection threshold: lower from 0.25 to 0.15 in `postprocess.py`
- Can run **IN PARALLEL** with Phase 1-2 — no model dependency (except ONNX migration task)

### Phase 4 (Browser Integration — ONNX-Unified)
- **Key change**: Replace ALL `tf.*` code with `ort.*` equivalents
- `hieroglyph-pipeline.js`: Replace `tf.loadGraphModel()` classifier with `ort.InferenceSession.create()`
- `explore.html`: Replace `tf.loadLayersModel()` landmark with `ort.InferenceSession.create()`
- `scan.html`: Remove `@tensorflow/tfjs@4.22.0` CDN import
- `explore.html`: Remove lazy-loaded TF.js + WASM backend
- Add ONNX Runtime Web CDN to `explore.html` (already in scan.html)
- Webcam: `setTimeout(() => onPlay())`, draw video to canvas, getImageData → ONNX tensor
- Classifiers use **NHWC** format `[1,H,W,3]`, detector uses **NCHW** format `[1,3,H,W]`
- Reference: `D:\Personal attachements\Repos\face-api.js\examples\webcamFaceDetection.html`
- Front/back camera via `navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })`

### Phase 5 (Integration & Testing)
- Use `planning/model-rebuild/CHECKLIST.md` to validate everything
- **CRITICAL**: Verify zero TF.js references remain (`grep -r "tensorflow\|tfjs" --include="*.html" --include="*.js"`)
- Bump SW to wadjet-v14+
- Bump all model URLs `?v=14`
- Test all browsers (Chrome, Firefox, Safari, Edge)
- Test on mobile
