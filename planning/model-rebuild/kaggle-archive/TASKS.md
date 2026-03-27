# Model Rebuild — Task List

**Input**: `planning/model-rebuild/PLAN.md`
**Format**: `[ID] [P?] [Phase] Description`
- **[P]**: Can run in parallel (no dependencies)
- **[Phase]**: Which phase this belongs to

**Updated**: 2026-03-20 Session 5 — **ONNX-Unified Architecture**

---

## Phase 0: Data Preparation ✅ COMPLETE

**Purpose**: Maximize training data quality before model training

### Explore Additional Data Sources
- T001 [P] [Phase0] ⏭️ DEFERRED — Download external datasets (only if accuracy insufficient)
- T002 [P] [Phase0] ⏭️ DEFERRED
- T003 [Phase0] ✅ Map overlapping Gardiner codes — all 171 in external 767-class dataset
- T004-T006 [Phase0] ⏭️ DEFERRED — merge external data only if needed

### Data Quality Checks
- T007 [P] [Phase0] ✅ Audit 7 classes with <30 images
- T008 [Phase0] ✅ Decision: KEEP all 171 — Focal Loss + class weights compensate
- T009 [Phase0] ✅ Validate label_mapping.json — fixed 5 descriptions + 2 unicode entries

---

## Phase 1: Hieroglyph Classifier (ONNX)

**Purpose**: Train hieroglyph classifier and export as ONNX for browser + server

### CRITICAL RULES
1. Train with **float32 ONLY** (no mixed_float16 — this caused _FusedConv2D crashes in v1)
2. Export via **`tf2onnx.convert.from_keras(model, input_signature=spec)`** → `.onnx` file
3. Quantize via **`onnxruntime.quantization.quantize_dynamic()`** → uint8
4. Load in browser with **`ort.InferenceSession.create(url)`** (NOT any TF.js API)
5. Use **MobileNetV3-Small** at **128×128** input
6. **No horizontal flip** augmentation for hieroglyphs (Rule #31 — orientation matters)

### Setup (Kaggle Notebook)
- T010 [Phase1] Create Kaggle training notebook at `planning/model-rebuild/notebooks/hieroglyph_classifier.ipynb`
- T011 [Phase1] Notebook: `pip install tf2onnx onnxruntime` in first cell
- T012 [Phase1] Notebook: load existing TFRecords (10 train shards from `naderelakany/wadjet-tfrecords/classification/`)
- T013 [Phase1] Notebook: decode TFRecords → resize to 128×128 (from 384 stored size) → float32 /255.0
- T014 [Phase1] Notebook: build MobileNetV3-Small with ImageNet weights
- T015 [Phase1] Notebook: replace top layer → GlobalAveragePooling2D → Dropout(0.3) → Dense(171, softmax)
- T016 [Phase1] Notebook: train with Focal Loss (γ=2.0), sqrt-inverse-frequency class weights, **float32 only**
- T017 [Phase1] Notebook: online augmentation (brightness ±20%, contrast 0.8-1.2, rotation ±10° — NO flip)
- T018 [Phase1] Notebook: head phase (5 epochs, backbone frozen) → fine-tune phase (30 epochs, 70% unfrozen)

### ONNX Export
- T019 [Phase1] Notebook: export via `tf2onnx.convert.from_keras(model, input_signature=[(tf.TensorSpec((None,128,128,3), tf.float32),)])`
- T020 [Phase1] Notebook: save full-precision ONNX: `hieroglyph_classifier.onnx`
- T021 [Phase1] Notebook: quantize → `hieroglyph_classifier_uint8.onnx` via `quantize_dynamic()`
- T022 [Phase1] Notebook: validate ONNX output matches Keras output (max diff < 1e-5 for float, < 0.02 for uint8)
- T023 [Phase1] Notebook: save label_mapping.json alongside model

### Metrics & Logging
- T024 [Phase1] Notebook: log metrics to W&B and print per-class F1
- T025 [Phase1] Notebook: save best .keras model + both ONNX files as outputs

### Execution
- T026 [Phase1] Upload notebook + dataset to Kaggle
- T027 [Phase1] Run training on Kaggle GPU (T4/P100)
- T028 [Phase1] Download: `hieroglyph_classifier_uint8.onnx`, `label_mapping.json`
- T029 [Phase1] Copy to `models/hieroglyph/classifier/` (replace current broken TF.js files)

### Validation
- T030 [Phase1] Test ONNX model loads in Python with `onnxruntime`
- T031 [Phase1] Test ONNX model loads in browser with `ort.InferenceSession.create()`
- T032 [Phase1] Test classification: upload hieroglyph image → verify Gardiner codes returned

---

## Phase 2: Landmark Classifier (ONNX)

**Purpose**: Train landmark classifier and export as ONNX (SAME rules as Phase 1)

### Setup (Kaggle Notebook)
- T035 [Phase2] Create Kaggle training notebook at `planning/model-rebuild/notebooks/landmark_classifier.ipynb`
- T036 [Phase2] Notebook: `pip install tf2onnx onnxruntime` in first cell
- T037 [Phase2] Notebook: load TFRecords from `naderelakany/wadjet-tfrecords` (52-class landmark, `train/`/`val/`/`test/` dirs)
- T038 [Phase2] Notebook: decode → resize to 224×224 → float32 /255.0
- T039 [Phase2] Notebook: build EfficientNetV2-B0 with ImageNet, replace top → Dense(52)
- T040 [Phase2] Notebook: train with CategoricalFocalLoss, class weights, MixUp/CutMix, **float32 only**

### ONNX Export
- T041 [Phase2] Notebook: export via `tf2onnx.convert.from_keras(model, input_signature=[(tf.TensorSpec((None,224,224,3), tf.float32),)])`
- T042 [Phase2] Notebook: quantize → `landmark_classifier_uint8.onnx`
- T043 [Phase2] Notebook: validate ONNX output matches Keras
- T044 [Phase2] Notebook: save model_metadata.json (52 class names + display names)

### Execution
- T045 [Phase2] Upload and run on Kaggle GPU
- T046 [Phase2] Download outputs
- T047 [Phase2] Copy to `models/landmark/onnx/` (new directory, keep old tfjs/ for reference)

### Validation
- T048 [Phase2] Test ONNX model loads in Python
- T049 [Phase2] Test ONNX model loads in browser
- T050 [Phase2] Test identification: upload landmark photo → verify correct class

---

## Phase 3: Backend Python Fixes

**Purpose**: Fix all server-side issues that don't require new models

### Server-Side ONNX Migration
- T050a [P] [Phase3] Update `hieroglyph_pipeline.py` to use `onnxruntime` for classification (replace Keras model loading)
- T050b [P] [Phase3] Update server-side landmark identification to use ONNX model
- T050c [Phase3] Update `config.py` defaults: `classifier_input_size=128`, model paths to `.onnx` files

### Gardiner Mapping (CRITICAL)
- T050 [P] [Phase3] Read `label_mapping.json` to get all 171 Gardiner codes with descriptions
- T051 [P] [Phase3] Update `app/core/gardiner.py` to include ALL 171 signs (currently only 71 — missing 100 signs)
- T052 [Phase3] Verify all 171 signs are also served by the dictionary page

### Result Format Fix
- T053 [P] [Phase3] Fix `scan.html` client scan result mapping — ensure camelCase→snake_case is correct
- T054 [Phase3] Verify: client scan results display correctly in the template

### Translation Pipeline
- T055 [P] [Phase3] Change `enable_translation=False` → `True` in `app/dependencies.py`
- T056 [P] [Phase3] Change `?translate=false` → `?translate=true` in `scan.html` (both server & client modes)
- T057 [Phase3] Unify Gemini key loading: `rag_translator.py` should use same pattern as `gemini_service.py`
- T058 [Phase3] Test: scan with translation returns English + Arabic text

### Detection Tuning
- T059 [P] [Phase3] Lower `CONF_THRESHOLD` from 0.25 to 0.15 in `app/core/postprocess.py`
- T060 [P] [Phase3] Make threshold configurable via `app/config.py` settings
- T061 [Phase3] Test: server scan on real hieroglyph photos returns detections

### Misc Fixes
- T062 [P] [Phase3] Fix `classifier_input_size=384` default → `224` in `hieroglyph_pipeline.py`
- T063 [P] [Phase3] Fix `preprocess()` return type hint in `postprocess.py` (4 vs 5 items)
- T064 [P] [Phase3] Wire `recommendation_engine.recommend()` into landmark detail API

---

## Phase 4: Browser Integration — ONNX-Unified + Real-Time Camera

**Purpose**: Replace all TF.js code with ONNX, add continuous camera scanning

### ONNX Migration in Browser
- T070 [Phase4] Rewrite `hieroglyph-pipeline.js` classifier section: replace `tf.loadGraphModel()` with `ort.InferenceSession.create()`
- T071 [Phase4] Update classifier preprocessing: canvas resize → getImageData → normalize /255.0 → NHWC format → `new ort.Tensor('float32', data, [1,128,128,3])`
- T072 [Phase4] Rewrite `explore.html` landmark identification: replace `tf.loadLayersModel()` with `ort.InferenceSession.create()`
- T073 [Phase4] Update landmark preprocessing: resize to 224×224 → /255.0 → NHWC → `new ort.Tensor('float32', data, [1,224,224,3])`
- T074 [Phase4] Remove TF.js CDN import from `scan.html` (`@tensorflow/tfjs@4.22.0`)
- T075 [Phase4] Remove TF.js lazy-load from `explore.html`
- T076 [Phase4] Add ONNX Runtime Web CDN to `explore.html` (already in scan.html)
- T077 [Phase4] Update `HieroglyphPipeline.isAvailable()` — check `typeof ort !== 'undefined'` only (remove `tf` check)

### Real-Time Camera (using face-api.js patterns)

### PATTERN
Use `setTimeout(() => onPlay())` recursive loop (NOT requestAnimationFrame):
```javascript
async function onPlay() {
  if (video.paused || video.ended || !modelLoaded) return setTimeout(onPlay);
  // Draw video frame to canvas, get image data
  ctx.drawImage(video, 0, 0, width, height);
  const imageData = ctx.getImageData(0, 0, width, height);
  // Run ONNX detection
  const result = await detectOnnx(imageData);
  drawBoxes(result);
  setTimeout(onPlay);  // schedule next frame
}
```

### Tasks
- T078 [Phase4] Design camera scanning architecture (detection loop + classify-on-tap)
- T079 [Phase4] Add canvas overlay on video element for bounding box drawing
- T080 [Phase4] Implement `setTimeout(() => onPlay())` loop with paused/ended guards
- T081 [Phase4] Run ONNX detection on each frame: canvas → getImageData → ONNX tensor → detect
- T082 [Phase4] Draw detected boxes in real-time on overlay canvas
- T083 [Phase4] Add "Capture & Classify" button that freezes frame and runs full ONNX pipeline
- T084 [Phase4] Support front/back camera switching via `facingMode` constraint
- T085 [Phase4] Test on mobile browsers (Chrome Android, Safari iOS)

---

## Phase 5: Integration & Final Testing

- T090 [Phase5] Deploy all new ONNX models to correct directories
- T091 [Phase5] Bump service worker cache version (wadjet-v14+)
- T092 [Phase5] Update all model URL version params (?v=14)
- T093 [Phase5] End-to-end test: Server scan (upload → ONNX detect → ONNX classify → transliterate → translate)
- T094 [Phase5] End-to-end test: Client scan (browser upload → ONNX detect → ONNX classify → display)
- T095 [Phase5] End-to-end test: Camera real-time scan
- T096 [Phase5] End-to-end test: Landmark identification via ONNX
- T097 [Phase5] End-to-end test: Dictionary browsing (all 171 signs)
- T098 [Phase5] Verify: ZERO TF.js references remain in codebase (`grep -r "tensorflow\|tfjs\|tf\." --include="*.html" --include="*.js"`)
- T099 [Phase5] Performance test: First scan < 5s, subsequent < 2s
- T100 [Phase5] Test on different browsers (Chrome, Firefox, Safari, Edge)
- T101 [Phase5] Update progress tracking files
