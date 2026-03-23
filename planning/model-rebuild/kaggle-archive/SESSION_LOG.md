# Model Rebuild — Session Log

## Session 6: 2026-03-20 (Deep Research & Readiness Validation)

### Context
User wanted exhaustive deep research before starting execution in a new chat. Requested: data sources, approaches, problem avoidance, online resources, full Repos folder utilization, clone anything useful, update everything for a clean START prompt.

### Research Completed

**Repos Folder (60+ folders explored)**:
- `01-Google-AI/03-ML-Frameworks/keras/` — has Keras source but NO ONNX examples
- `14-AI-Learning/` — fast.ai, GenAI agents, course22 — general ML, not directly useful
- `notebooks/` (180+ notebooks) — ALL are LLM fine-tuning (GRPO, LoRA, etc.) — NONE relevant
- `face-api.js/` — webcam patterns already documented in Session 2 ✅
- ONNX-related repos: **ZERO** exist in Repos folder → not needed, tf2onnx is a pip package

**Skills Read in Detail**:
- `computer-vision-expert` — YOLO26, SAM 3, ONNX/TensorRT deployment strategy
- `ml-engineer` — TF 2.x, ONNX cross-framework interop, quantization, edge deployment
- `data-scientist` — general ML/statistics, CNNs, image classification evaluation

**tf2onnx Official Docs (github.com/onnx/tensorflow-onnx)**:
- Supports TF 2.13+, Python 3.10-3.12, ONNX opset 14-18 (default 15)
- `from_keras()` **preserves NHWC by default** — this was our key discovery
- `inputs_as_nchw` parameter exists but adds a Transpose op; safer to keep native NHWC
- Our notebooks already use `opset=17` ✅
- Project seeking maintainer but tool is mature/stable

**ONNX Runtime Web (onnxruntime.ai)**:
- Supports `wasm`, `webgl`, `webgpu` providers
- Models can convert to `.ort` format for smaller binary + faster init (optional optimization)
- Session options `graphOptimizationLevel: 'all'` for maximum optimization
- Standard image classification tutorial confirms our approach

### Critical Bug Found & Fixed

**PLAN.md said classifiers use NCHW [1,3,H,W] but notebooks export NHWC**:
- tf2onnx `from_keras()` preserves Keras native NHWC format by default
- YOLOv8 detector uses NCHW (PyTorch origin)
- **Fix**: Updated PLAN, TASKS, PROMPTS to correctly say classifiers=NHWC, detector=NCHW
- Browser will have two preprocessing functions: `preprocessNCHW()` for detector, `preprocessNHWC()` for classifiers

### Decisions Made
1. **Keep NHWC for classifiers** — Keras native, no extra Transpose op, safer
2. **Keep NCHW for detector** — YOLOv8 native, already working
3. **No repos need cloning** — all resources are local or pip-installable
4. **No additional data needed before training** — existing 15K hieroglyph + 46K landmark is sufficient
5. **Static quantization as backup** — if `quantize_dynamic()` accuracy is poor, use `quantize_static()` with calibration data
6. **Notebooks are ready** — both export NHWC ONNX models correctly

### Files Modified
- `planning/model-rebuild/PLAN.md` — Fixed NHWC/NCHW references, added Session 6 findings, updated browser code pattern
- `planning/model-rebuild/TASKS.md` — Fixed T071 and T073 to use NHWC
- `planning/model-rebuild/PROMPTS.md` — Updated preprocessing instructions, session count
- `planning/model-rebuild/SESSION_LOG.md` — Added Session 6 entry
- `planning/model-rebuild/PROGRESS.md` — Updated with Phase 0 completion

### Gap Analysis Summary
| Gap | Resolution |
|-----|-----------|
| PLAN said NCHW for classifiers | **Fixed** → NHWC |
| No ONNX repos locally | Not needed (pip packages) |
| No useful CV notebooks in 180+ collection | Our own notebooks are purpose-built |
| tf2onnx seeking maintainer | Tool is mature, `from_keras()` stable |
| No static quantization fallback | Documented as backup strategy |

### Conclusion
All research complete. All docs updated and consistent. Notebooks ready for Kaggle upload. No blockers remain. User can open a new chat in the `planning/model-rebuild/` directory and send the START prompt for Phase 1.

---

## Session 4: 2026-03-20 (Training Notebooks Created)

### Context
Created both Kaggle training notebooks for Phase 1 (hieroglyph) and Phase 2 (landmark). User asked about landmarks, so Phase 2 notebook was also created (no longer deferred).

### Work Completed

**Hieroglyph Classifier Notebook** (`notebooks/hieroglyph_classifier.ipynb`):
- Covers T010-T022 (all Phase 1 setup tasks)
- MobileNetV3-Small, 128×128 input, 171 classes
- float32 only (explicit assertion, no mixed precision)
- Focal Loss (γ=2.0) + sqrt-inverse-frequency class weights
- Augmentation: brightness, contrast, saturation, rotation ±10° — NO horizontal flip
- Two-phase: head (5 epochs, Adam 1e-3) → finetune (30 epochs, AdamW + cosine decay 1e-4→5e-6)
- Export: `save_keras_model()` → layers-model + uint8 quantization
- Validation: model.json format assertion (must be "layers-model")
- Metadata output for deployment

**Landmark Classifier Notebook** (`notebooks/landmark_classifier.ipynb`):
- Covers T035-T041 (all Phase 2 setup tasks)
- EfficientNetV2-B0, 224×224 input, 52 classes
- float32 only (same assertion)
- CategoricalFocalLoss (for MixUp/CutMix soft labels) + clipped inverse-frequency weights [0.5, 3.0]
- Augmentation: flip (OK for landmarks), rotation ±18°, brightness, contrast, saturation, hue, random erasing
- MixUp (α=0.2) + CutMix (α=1.0), 50% probability each per batch
- WarmupCosineDecay LR schedule (warmup 1→3 epochs)
- Two-phase: head (5 epochs) → finetune (50 epochs, patience=15)
- Same export pipeline as hieroglyph

### Key Differences Between the Two Notebooks
| Aspect | Hieroglyph | Landmark |
|--------|-----------|----------|
| Architecture | MobileNetV3-Small | EfficientNetV2-B0 |
| Input size | 128×128 | 224×224 |
| Classes | 171 | 52 |
| Loss | FocalLoss (sparse) | CategoricalFocalLoss (one-hot) |
| Augment | No flip, no MixUp | Flip + MixUp + CutMix |
| Class weights | sqrt-inv-freq | inv-freq clipped [0.5, 3.0] |
| Finetune epochs | 30 | 50 |
| Batch size | 32 | 16 |

### V1 Reference Used
- Read V1 `wadjet-training.ipynb` (hieroglyph) and `03_model_training.ipynb` (landmark) 
- Extracted: TFRecord schema, loss functions, augmentation, LR schedules, class weights
- Applied all V1 patterns that worked (Focal Loss, class weights, two-phase training)
- Changed what caused failures (mixed_float16 → float32, convert_tf_saved_model → save_keras_model)

### Decisions Made
1. **Phase 2 no longer deferred** — notebook created alongside Phase 1
2. **Landmark data format confirmed**: `train-NNNNN-of-NNNNN.tfrecord` in `train/` subdirectory
3. **Both notebooks target same Kaggle dataset**: `naderelakany/wadjet-tfrecords`
4. **Hieroglyph data under `classification/` subdirectory**, landmark at root level

### Next Steps
- Upload notebooks to Kaggle & run on GPU (T023-T024, T042)
- After training: download models, deploy to `models/` directories
- Phase 3 backend fixes can proceed in parallel (no model dependency)

### Files Created
- `planning/model-rebuild/notebooks/hieroglyph_classifier.ipynb`
- `planning/model-rebuild/notebooks/landmark_classifier.ipynb`

---

## Session 3: 2026-03-20 (Phase 0 Completion + Phase 1 Notebook)

### Context
Phase 0 data preparation tasks T001-T009. Phase 1 training notebook creation.

### Phase 0 Findings

**Data Audit Results:**
- 171 classes, 15,017 augmented train images, 1,152 val, 1,154 test
- TFRecords: 10 train shards (520MB), 1 val (30MB), 1 test (26MB) — images at 384×384 JPEG
- TFRecord features: `image_raw` (JPEG bytes), `label` (int64), `gardiner_code` (string)
- 7 rare classes <30 augmented images: D156(6), P13(6), O11(11), V25(11), S24(16), T21(16), N18(28)
- D156 and P13 have 0 val/test images — can't evaluate individually
- 119/171 classes have <30 RAW images (before augmentation)
- Class size distribution (augmented): <30=7, 30-49=9, 50-99=100, 100-199=49, 200+=6

**label_mapping.json Validation:**
- idx↔gardiner bidirectional mapping: CORRECT (0-170, all 171)
- Matches V1 training directories perfectly
- Fixed 5 missing descriptions: D156, M195, O11, P13, P98
- Fixed 2 corrupted unicode entries: D21 (was "D22" text), M40 (was "Aa28" text)
- 3 extended Gardiner signs (D156, M195, P98) have no standard Unicode — correct

**V1 Training Config (from notebooks/scripts):**
- TFRecords written at 384×384 JPEG quality=95
- Parse: decode_jpeg → float32 /255.0 → ensure_shape
- V1 used EfficientNetV2-S + mixed_float16 (the root cause of TF.js crash)
- Focal Loss γ=2.0 + sqrt-inverse-frequency weights (KEEP)
- AdamW, CosineDecay 1e-4→5e-6, weight_decay=1e-4
- Head phase: 5 epochs frozen → Fine-tune: 50 epochs 70% unfrozen
- Augmentation: brightness ±0.2, contrast [0.8,1.2], rotation ±10°, NO FLIP

### Decisions Made
1. **Keep all 171 classes** — Focal Loss + class weights handle imbalance; rare classes acceptable risk
2. **External dataset merge DEFERRED** — start with existing 15K images, merge only if accuracy insufficient
3. **Use existing TFRecords** — already at 384×384, will resize to 128×128 during training
4. **Architecture: MobileNetV3-Small 128×128** — per PLAN.md decision
5. **label_mapping.json metadata fixed** — ready for dictionary page use

### Files Modified
- `models/hieroglyph/label_mapping.json` — fixed 5 descriptions + 2 unicode chars

---

## Session 1: 2026-03-20

### Context
After 17+ iterations trying to fix Keras 3 / TF.js compatibility issues with both the hieroglyph classifier and landmark model, we decided to take a clean approach: retrain models from scratch targeting TF.js from day 1.

### Research Completed
1. **Repos folder deep dive**: Found 30+ relevant skills (FastAPI, ML, CV, frontend, security, SEO), spec-kit templates, animation libraries, chatbot resources
2. **Backend analysis**: Identified 10 issues across 4 severity levels:
   - CRITICAL: TF.js `_FusedConv2D` crash (both models), incomplete Gardiner mapping
   - HIGH: Camera capture-only, client result format mismatch, detection threshold
   - MEDIUM: Config mismatches, disabled features, unwired endpoints
3. **Data inventory**: 
   - Hieroglyph: 15,017 train / 1,152 val / 1,154 test images, 171 classes, TFRecords ready
   - Landmark: ~46,306 images, 52 classes, TFRecords ready
   - Existing Kaggle notebooks for both tasks
4. **Architecture decisions**: 
   - Use EfficientNetV2-B0 / MobileNetV3 (smaller, TF.js friendly)
   - Train with float32 only (no mixed precision)
   - Export via `tfjs.converters.save_keras_model()` → layers-model format
   - Quantize to uint8 post-training

### Key Learnings
- `_FusedConv2D` is caused by TF graph optimization during SavedModel→GraphModel conversion
- `tfjs.converters.save_keras_model()` (Python API) produces clean layers-model without fused ops
- The Keras 3 `.keras` format uses different topology structure than TF.js expects
- Training with float32 (not mixed_float16) avoids Cast/DT_HALF issues entirely
- MobileNetV3-Small at 128×128 is sufficient for hieroglyph classification (small crops)

### Decisions Made
- Retrain both classifier models from scratch on Kaggle
- Keep ONNX detector as-is (works fine)
- Fix all backend Python issues in parallel (Phase 3)
- Add real-time camera scanning (Phase 4)

### Files Created
- `planning/model-rebuild/PLAN.md` — Master plan with phases
- `planning/model-rebuild/PROGRESS.md` — Progress tracker
- `planning/model-rebuild/SESSION_LOG.md` — This file
- `planning/model-rebuild/TASKS.md` — Detailed task list
- `planning/model-rebuild/PROMPTS.md` — Start/continue prompts

---

## Session 2: 2026-03-20 (Deep Research)

### Context
User requested comprehensive deep research before starting implementation. Goals:
1. Explore ALL resources in `D:\Personal attachements\Repos\` (57 top-level folders, 883 skills)
2. Research online: TF.js conversion best practices, Kaggle datasets, model approaches
3. Learn from face-api.js (browser-based ML reference implementation)
4. Check what's underutilized, what's missing
5. Update all planning docs with findings

### Research: `D:\Personal attachements\Repos\` Complete Inventory

**57 top-level folders**, including:
- `01-Google-AI/03-ML-Frameworks/keras/` — Full Keras 3 source (multi-backend)
- `01-Google-AI/03-ML-Frameworks/tensorflow/` — Full TF source
- `04-Meta-PyTorch/02-PyTorch/torchtune/` — Fine-tuning recipes
- `07-HuggingFace/` — transformers, peft (LoRA), accelerate, datasets, TRL
- `14-AI-Learning/course22/` — fast.ai with `03-which-image-models-are-best.ipynb`
- `16-DevOps/label-studio/` — Data annotation tool (hieroglyph annotation)
- `20-Prompts-GPT/` — 170+ persona prompts (for Thoth chatbot)
- `21-Frontend-UI/` — magicui, react-bits, Hover.css, atropos (already integrated)
- `face-api.js/` — **KEY**: Browser-based ML inference reference
- `notebooks/` — 180+ Unsloth fine-tuning notebooks (DeepSeek OCR, PaddleOCR)
- `antigravity-awesome-skills/` — 883 skills across all domains

**Not relevant/not needed**: PyTorch (we use TF/Keras), Llama/vLLM (not applicable), SaaS boilerplates, security tools

### Research: face-api.js Patterns (CRITICAL for Phase 4)

How face-api.js runs ML in the browser — directly applicable to our webcam feature:

1. **Model loading**: Custom `tf.io.loadWeights()` (we'll use simpler `tf.loadLayersModel()`)
2. **Weight format**: **uint8 quantized** at rest, dequantized by TF.js at load time
3. **Webcam loop**: `setTimeout(() => onPlay())` recursive pattern — NOT requestAnimationFrame
   - Naturally throttles to inference speed
   - Guards for `video.paused || video.ended`
4. **Preprocessing**: `tf.browser.fromPixels(videoElement)` → pad to square → resize bilinear → normalize
5. **Video input**: Pass `<video>` element directly (TF.js handles frames natively)
6. **Architecture**: SSD MobileNetV1 (face detection), Tiny YOLO v2 (tiny face detector)
7. **Backend**: No explicit backend selection — consumer provides (defaults to WebGL)
8. **Caching**: None built-in (relies on browser HTTP cache)
9. **TF.js version**: Pinned to `@tensorflow/tfjs-core@1.7.0` only (not full bundle)

### Research: Kaggle Hieroglyph Datasets

Discovered 4 datasets beyond our own:

| Dataset | Classes | Images | Key Notes |
|---------|---------|--------|-----------|
| `mohieymohamed/heroglyphics-signs` | **767** | **33,132** | Huge! Apache 2.0. Roboflow annotated. Could merge overlapping classes for data boost. |
| `alexandrepetit881234/egyptian-hieroglyphs` | **95** | 3,895 | Roboflow origin. CC BY 4.0. 60 notebooks written against this. |
| `ayatollahelkolally/hieroglyphs-dataset` | **171** | 4,031 | Same GlyphNet source we already use. MIT. |
| `ahmedelkelany/egyptian-hieroglyphic-layout-analysis` | Layout | 900 | Object detection bboxes for hieroglyphic layout analysis. |

Top Kaggle notebooks:
- "Hieroglyphs|Image Cropping+CNN, DenseNet (97% Acc)" by Ahmed Elsayed — 27 upvotes
- "Hieroglyph Classification DenseNet (0.85 F1)" by arturo-bandini-jr — 20 upvotes
- "Egyptian-hieroglyphs using EfficientNetV2B3" by Radwa — architecture validation

### Research: V1 Conversion Script Analysis (Root Cause)

Read both V1 conversion scripts in detail:

**Landmark** (`scripts/convert_tfjs.py`):
```python
model.export(str(saved_model_dir))            # ← SavedModel intermediary
tfjs.converters.convert_tf_saved_model(...)   # ← graph-model with _FusedConv2D
```

**Hieroglyph** (`hieroglyph_model/scripts/h2_12_13_export_tfjs.py`):
```python
model.export(str(saved_model_dir))            # ← same pattern
tfjs.converters.convert_tf_saved_model(...)   # ← same bug
```

Both scripts create an intermediate SavedModel (required because Keras 3 `.keras` format can't be directly deepcopied), then convert the SavedModel to a graph-model. The graph-model conversion applies Grappler optimization which fuses `Conv2D + BatchNorm + Activation` into `_FusedConv2D` — an op TF.js doesn't support.

The fix is simple: `tfjs.converters.save_keras_model(model, output_dir)` exports directly from the in-memory Keras model to layers-model format, no SavedModel intermediary needed, no Grappler optimization, no fused ops.

### Research: V1 Training Details (What to Carry Forward)

| Setting | V1 Hieroglyph | V1 Landmark | Keep/Change |
|---------|---------------|-------------|-------------|
| Architecture | EfficientNetV2-S | EfficientNetV2-S | **CHANGE** → MobileNetV3/B0 |
| Input size | 224×224 (from 384 TFRecords) | 384×384 | **CHANGE** → 128/224 |
| Precision | mixed_float16 | mixed_float16 | **CHANGE** → float32 |
| Loss | Focal Loss γ=2.0 | Focal Loss γ=2.0 | **KEEP** |
| Class weights | sqrt-inverse-frequency | Per-class alpha | **KEEP** |
| Augmentation (offline) | Albumentations (rotate, affine, blur, brightness) | Albumentations similar | **KEEP** |
| Augmentation (online) | Brightness, contrast, rotation (NO flip) | MixUp α=0.2, CutMix α=1.0 | **KEEP** |
| Rare class handling | Tiered multipliers (5×/3×/2×/1×) | Tiered multipliers | **KEEP** |
| Synthetic data | Noto Sans font-rendered glyphs | N/A | **KEEP** (nice boost) |
| Training phases | Head (5ep frozen) → Fine-tune (50ep) | Same | **KEEP** |
| GPU | Kaggle P100 16GB | Same | Same |
| Tracking | W&B | W&B | **KEEP** |

### Research: TF.js Official Docs Confirmation

From tensorflow.org/js:
- `tf.loadGraphModel()` → for SavedModel conversions → returns `tf.FrozenModel` (NOT trainable)
- `tf.loadLayersModel()` → for Keras conversions → returns `tf.Model` (can be retrained)
- Official recommendation: "Build with resource-constrained environments in mind"
- Supported ops for layers-model: standard Keras layers only (Dense, Conv2D, BatchNorm, etc.)
- graph-model warning: "If we encounter an unsupported operation during conversion, the process fails"

### Decisions Made
1. **No repos need cloning** — everything needed is already in Repos folder
2. **Data strategy**: Start with existing 17K hieroglyph images (171 classes). If accuracy insufficient, merge from `heroglyphics-signs` dataset (767 classes, 33K images) in a follow-up
3. **Architecture choice**: MobileNetV3-Small for hieroglyph (128×128), EfficientNetV2-B0 for landmark (224×224)
4. **Export strategy**: `save_keras_model()` directly — no SavedModel intermediary
5. **Webcam pattern**: `setTimeout(() => onPlay())` from face-api.js — not requestAnimationFrame
6. **Phase 3 can start immediately** — backend fixes have no model dependency
7. **Phase 2 deferred** — user said "skip landmark for now", focus on hieroglyph first

### Files Updated
- `planning/model-rebuild/PLAN.md` — Added deep research findings section (root cause, datasets, face-api.js patterns, skills inventory, repos structure)
- `planning/model-rebuild/TASKS.md` — Added Phase 0 (data prep), updated Phase 1-4 with precise details, added critical rules, face-api.js webcam pattern
- `planning/model-rebuild/PROMPTS.md` — Complete rewrite with critical rules, Kaggle datasets, phase-specific notes, face-api.js reference
- `planning/model-rebuild/SESSION_LOG.md` — This entry

### What's Ready for Next Session
Everything is documented and ready. Open a new chat in the `planning/model-rebuild/` folder and send the START prompt with Phase 3 (backend fixes can run immediately while Kaggle notebooks are prepared for Phase 1).

---

## Session 5: 2026-03-20 (ONNX-Unified Architecture Pivot)

### Context
User questioned whether Keras/TF.js was the best approach after 17+ failed TF.js conversion attempts. Agent proposed switching to ONNX Runtime Web for ALL browser ML — the detector already uses ONNX successfully. User agreed and requested a complete rewrite of all planning documents and notebooks.

### The ONNX Decision

**Problem**: TF.js conversion is inherently fragile:
- `convert_tf_saved_model()` → Grappler optimization → `_FusedConv2D` (unsupported)
- `save_keras_model()` → still risks Keras 3 topology mismatches
- Two separate ML runtimes in browser (ONNX RT Web + TF.js) = extra 1.5MB + complexity

**Solution**: ONNX-unified architecture:
- Train with Keras (TFRecords ready, familiar pipeline — KEEP)
- Export to ONNX via `tf2onnx.convert.from_keras()` (replaces ALL TF.js converters)
- Quantize via `onnxruntime.quantization.quantize_dynamic()` (replaces `tensorflowjs_converter --quantize_uint8`)
- Load in browser via `ort.InferenceSession.create()` (replaces `tf.loadLayersModel()`/`tf.loadGraphModel()`)
- **Remove TF.js entirely** from the project

**Why this is the definitive fix**:
1. ONNX has a standardized op set — no Grappler, no fused ops, no format confusion
2. One `.onnx` file per model (not model.json + weight shards)
3. ONNX Runtime Web already loaded for YOLOv8 detector — zero additional runtime cost
4. Same model works in Python (onnxruntime) and browser (onnxruntime-web)
5. Mature quantization pipeline

### Browser Code Audit (What Changes)

**`scan.html`** (current):
- Loads ONNX Runtime Web 1.18.0 (for detector) ✅ KEEP
- Loads TF.js 4.22.0 (for classifier) ❌ REMOVE
- `HieroglyphPipeline.isAvailable()` checks both `ort` and `tf` → UPDATE to `ort` only

**`explore.html`** (current):
- Lazy-loads TF.js + WASM backend for landmark identification ❌ REMOVE
- Uses `tf.loadLayersModel('/models/landmark/tfjs/model.json?v=13')` → REPLACE with ONNX
- Preprocessing: [1,384,384,3] with [0,255] range (ImageNet) → UPDATE to [1,3,224,224] with /255.0

**`hieroglyph-pipeline.js`** (current):
- ONNX detector: `ort.InferenceSession.create()` with CHW [1,3,640,640] ✅ WORKS
- TF.js classifier: `tf.loadGraphModel()` with NHWC [N,128,128,3] /255.0 ❌ CRASHES
- Need to replace classifier with ONNX: `ort.InferenceSession.create()` with NCHW [1,3,128,128]

**`base.html`**: No ML imports (clean) ✅

### Work Completed

1. **Rewrote PLAN.md** for ONNX: new Strategy section, Architecture Decisions with ONNX details, updated Phases, added ONNX Browser Loading Pattern code, updated Critical Rules, updated all tables
2. **Rewrote TASKS.md**: Phase 1 and 2 tasks now use tf2onnx export + onnxruntime quantization instead of TF.js converters. Phase 4 includes ONNX migration tasks (T070-T077) for browser code. Phase 5 includes TF.js removal verification.
3. **Rewrote PROGRESS.md**: Added ONNX pivot milestone, updated Phase 1-5 descriptions to reflect ONNX
4. **Rewrote CHECKLIST.md**: All TF.js references → ONNX, added TF.js removal checks
5. **Rewrote PROMPTS.md**: Complete rewrite with ONNX critical rules, updated export/load instructions
6. **Rewrote both training notebooks**: ONNX export cells replace TF.js export cells
7. **This SESSION_LOG entry**

### Notebook Bug Fixes (Session 4, carried forward)
Found and fixed 4 bugs during audit:
1. **Landmark val/train loss mismatch**: val_ds had sparse int labels but CategoricalFocalLoss expected one-hot → val_loss and EarlyStopping were meaningless. Fixed by adding `preprocess_eval_onehot()`.
2. **FocalLoss serialization**: Missing `@keras.saving.register_keras_serializable()` decorator → would break model save/load. Added decorator + `import keras`.
3. **MixUp Beta sampling**: Used `tf.random.gamma` incorrectly for Beta distribution. Fixed with proper `sample_beta()` using Γ(α)/(Γ(α)+Γ(β)).
4. **Comment accuracy**: Several comments said "sparse labels" where code actually used one-hot.

### Key Technical Notes

**ONNX Export Pattern** (replaces all TF.js export code):
```python
import tf2onnx
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType

# Export from Keras
spec = (tf.TensorSpec((None, 128, 128, 3), tf.float32),)  # or 224 for landmark
model_onnx, _ = tf2onnx.convert.from_keras(model, input_signature=spec)
with open("model.onnx", "wb") as f:
    f.write(model_onnx.SerializeToString())

# Quantize to uint8
quantize_dynamic("model.onnx", "model_uint8.onnx", weight_type=QuantType.QUInt8)

# Validate
sess = ort.InferenceSession("model_uint8.onnx")
output = sess.run(None, {sess.get_inputs()[0].name: test_input})
```

**Browser Loading Pattern** (replaces all `tf.loadLayersModel`/`tf.loadGraphModel`):
```javascript
const session = await ort.InferenceSession.create('/models/path/model_uint8.onnx', {
    executionProviders: ['wasm']
});
// Preprocessing: resize → /255.0 → transpose NHWC→NCHW
const tensor = new ort.Tensor('float32', nchwData, [1, 3, H, W]);
const output = await session.run({ [session.inputNames[0]]: tensor });
const probs = output[session.outputNames[0]].data;
```

**NOTE on input format**: tf2onnx may convert the model to expect NCHW input (this is the ONNX convention). Check `session.inputNames` and input shape at runtime. If the model still expects NHWC, adjust accordingly. The actual behavior depends on tf2onnx's automatic transpose insertion.

### Decisions Made
1. **ONNX for everything** — single runtime, no TF.js anywhere
2. **Keep Keras for training** — TFRecords ready, pipeline validated
3. **tf2onnx for export** — direct from Keras, no SavedModel intermediary needed
4. **onnxruntime.quantization for uint8** — replaces tensorflowjs_converter
5. **Remove TF.js completely** — CDN imports, lazy-loads, all `tf.*` calls
6. **Models serve at `/models/hieroglyph/classifier/model_uint8.onnx`** and `/models/landmark/onnx/model_uint8.onnx`
7. **NCHW format in browser** — ONNX convention, same as detector already uses

### Files Updated
- `planning/model-rebuild/PLAN.md` — Complete ONNX rewrite
- `planning/model-rebuild/TASKS.md` — All phases updated for ONNX
- `planning/model-rebuild/PROGRESS.md` — Added ONNX pivot, updated all phases
- `planning/model-rebuild/CHECKLIST.md` — TF.js → ONNX checks
- `planning/model-rebuild/PROMPTS.md` — Complete rewrite with ONNX rules
- `planning/model-rebuild/SESSION_LOG.md` — This entry
- `planning/model-rebuild/notebooks/hieroglyph_classifier.ipynb` — ONNX export
- `planning/model-rebuild/notebooks/landmark_classifier.ipynb` — ONNX export

### What's Ready for Next Session
All planning docs and notebooks are updated for ONNX-unified architecture. The next session should:
1. **Phase 1**: Upload hieroglyph notebook to Kaggle → run → download `hieroglyph_classifier_uint8.onnx`
2. **Phase 2**: Upload landmark notebook to Kaggle → run → download `landmark_classifier_uint8.onnx`
3. **Phase 3**: Backend Python fixes (can start immediately, no model dependency)
4. **Phase 4**: Browser ONNX migration (after models are trained)
5. **Phase 5**: Integration testing
