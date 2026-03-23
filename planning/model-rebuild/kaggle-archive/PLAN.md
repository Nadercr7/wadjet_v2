# Wadjet v2 — Model Rebuild & Backend Fix: Master Plan

**Created**: 2026-03-20
**Updated**: 2026-03-20 Session 6 — **Deep Research Complete, Ready for Execution**
**Status**: Active
**Goal**: Fix ALL backend/ML issues, retrain models, unify on ONNX Runtime Web, get everything working end-to-end with real-time camera

---

## Problem Summary

### Critical Issues (Must Fix)
| # | Issue | Root Cause | Impact |
|---|-------|-----------|--------|
| 1 | **Browser classifier crashes** | TF.js graph-model has `_FusedConv2D` ops unsupported by WebGL/WASM | Client-side scan completely broken |
| 2 | **Browser landmark model crashes** | Same `_FusedConv2D` / Keras 3 nested Functional issue | Client-side landmark ID broken |
| 3 | **Gardiner mapping only 71/171 signs** | `gardiner.py` missing triliterals, determinatives, logograms | 59% of transliterations show `[UNK_X]` |
| 4 | **Translation disabled at 2 levels** | `enable_translation=False` + `?translate=false` in frontend | Translation never runs |

### High Issues
| # | Issue | Root Cause | Impact |
|---|-------|-----------|--------|
| 5 | Camera mode is capture-only | No continuous scanning loop | "Real-time" scan doesn't exist |
| 6 | Client result format mismatch | camelCase JS vs snake_case template | Even if model loads, display breaks |
| 7 | Detection threshold too high | `CONF_THRESHOLD=0.25` misses real photos | Server scan returns 0 on real images |

### Medium Issues
| # | Issue | Root Cause | Impact |
|---|-------|-----------|--------|
| 8 | Default classifier_input_size=384 vs model=224 | Config mismatch | Self-corrects but confusing |
| 9 | Recommendation engine not wired | `recommend()` never called | Missing feature |
| 10 | Gemini key inconsistency | RAGTranslator vs GeminiService use different env var patterns | Maintenance burden |
| 11 | **Two ML runtimes in browser** | TF.js + ONNX Runtime Web loaded separately | Extra ~1.5MB download, two APIs, confusion |

---

## Strategy: ONNX-Unified Architecture

### Why ONNX Instead of TF.js?
After 17+ iterations of TF.js conversion failures, the root causes are:
- `_FusedConv2D` from Grappler optimization during SavedModel→GraphModel conversion
- `mixed_float16` generating Cast/DT_HALF ops TF.js doesn't support
- Keras 3 `.keras` format incompatible with TF.js topology

**ONNX solves ALL of these permanently:**
1. **No fused ops** — ONNX has a standardized op set, no Grappler optimization
2. **No format confusion** — one `.onnx` file, no layers-model vs graph-model
3. **Already in the browser** — ONNX Runtime Web is loaded for YOLOv8 detector
4. **Remove TF.js entirely** — save ~1.5MB, single runtime for all models
5. **Mature quantization** — `onnxruntime.quantization` is well-tested
6. **Same code server & browser** — both use ONNX Runtime

### The Clean Solution
1. **Train with Keras** (TFRecords already prepared, familiar pipeline)
2. **Export to ONNX** via `tf2onnx.convert.from_keras()` — direct, no SavedModel
3. **Quantize** via `onnxruntime.quantization.quantize_dynamic()` — uint8
4. **Load in browser** via `ort.InferenceSession.create()` — unified API
5. **Remove TF.js** from scan.html and explore.html entirely

---

## Architecture Decisions

### Browser ML Runtime: ONNX-Only
| Decision | Choice | Rationale |
|----------|--------|-----------|  
| Runtime | **ONNX Runtime Web 1.18.0** | Already loaded for detector; single runtime for all |
| Provider | **WASM** (primary), **WebGL** (if faster) | WASM works everywhere; WebGL faster on some GPUs |
| Remove TF.js | **Yes — completely** | Eliminates _FusedConv2D risk, saves 1.5MB bundle |

### Hieroglyph Classifier
| Decision | Choice | Rationale |
|----------|--------|-----------|  
| Architecture | **MobileNetV3-Small** | Smallest, fastest, sufficient for glyph crops |
| Input size | **128×128** | Glyphs are small crops from detector |
| Training precision | **float32 only** | Clean ONNX export |
| Export format | **ONNX** via `tf2onnx.convert.from_keras()` | Direct from Keras, no intermediary |
| Quantization | **uint8** via `onnxruntime.quantization` | ~2-3MB final |
| Input format (browser) | **NHWC [1,128,128,3]** float32, [0,1] normalized | Keras native format; tf2onnx preserves NHWC by default |
| Fallback | Server-side uses same ONNX model via `onnxruntime` Python | Unified |

### Landmark Classifier
| Decision | Choice | Rationale |
|----------|--------|-----------|  
| Architecture | **EfficientNetV2-B0** | Good accuracy/size balance for 52 classes |
| Input size | **224×224** | Standard, fast inference |
| Training precision | **float32 only** | Clean export |
| Export format | **ONNX** | Same pipeline as hieroglyph |
| Quantization | **uint8** | ~5-8MB final |
| Input format (browser) | **NHWC [1,224,224,3]** float32, [0,1] normalized | Keras native format; consistent with hieroglyph classifier |

### Hieroglyph Detector
| Decision | Choice | Rationale |
|----------|--------|-----------|  
| Keep as-is | **YOLOv8 ONNX** | Already works perfectly in browser and server |
| Note | Lower confidence threshold to 0.15 | Current 0.25 misses real photos |

## Phases

### Phase 0: Planning & Data Preparation ✅
- [x] Deep research repos folder (57 folders, 883 skills)
- [x] Analyze all backend problems (10 issues found)
- [x] Design architecture decisions
- [x] Create planning files
- [x] Deep research: Kaggle datasets, face-api.js, V1 root cause, V1 training config
- [x] Audit rare classes, validate label_mapping.json
- [x] Architecture pivot: TF.js → ONNX-unified (Session 5)

### Phase 1: Hieroglyph Classifier — Train & Export ONNX
- Train MobileNetV3-Small on 171-class hieroglyph dataset (Kaggle GPU)
- Data: `naderelakany/wadjet-tfrecords` → `classification/` subdirectory (15,017 train)
- Export to ONNX via `tf2onnx.convert.from_keras()`
- Quantize to uint8 via `onnxruntime.quantization`
- Validate ONNX in Python + browser

### Phase 2: Landmark Classifier — Train & Export ONNX
- Train EfficientNetV2-B0 on 52-class landmark dataset (Kaggle GPU)
- Data: `naderelakany/wadjet-tfrecords` → `train/`/`val/`/`test/` directories (~46K train)
- Export to ONNX, quantize to uint8
- Validate

### Phase 3: Backend Python Fixes (No Model Dependency)
- Fix `gardiner.py` — all 171 sign mappings
- Fix client result format mismatch
- Enable translation pipeline
- Lower detection threshold + make configurable
- Wire recommendation engine
- Unify Gemini key patterns
- Update server-side pipeline to use ONNX for classification too

### Phase 4: Browser Integration — ONNX-Unified
- Replace TF.js classifier loading with ONNX in `hieroglyph-pipeline.js`
- Replace TF.js landmark loading with ONNX in `explore.html`
- Remove ALL TF.js CDN imports from scan.html and explore.html
- Implement real-time camera scanning (`setTimeout` loop from face-api.js)
- Canvas overlay for bounding boxes
- Front/back camera switching

### Phase 5: Integration & Testing
- Deploy new ONNX models to `models/` directories
- Bump service worker cache version
- End-to-end testing: upload scan, camera scan, dictionary, translation
- Performance profiling (target: <3s first scan, <1s subsequent)
- Cross-browser testing

---

## ONNX Browser Loading Pattern

```javascript
// Unified loading — same for detector, classifier, landmark
async function loadOnnxModel(url) {
    const session = await ort.InferenceSession.create(url, {
        executionProviders: ['wasm'],
        graphOptimizationLevel: 'all'
    });
    return session;
}

// Preprocessing — NCHW for detector (YOLO), NHWC for classifiers (Keras)
function preprocessNCHW(imageData, size) {
    // For YOLOv8 detector (PyTorch origin → NCHW)
    const floats = new Float32Array(3 * size * size);
    const pixelCount = size * size;
    for (let i = 0; i < pixelCount; i++) {
        floats[i]                  = imageData[i * 4]     / 255.0; // R → ch0
        floats[pixelCount + i]     = imageData[i * 4 + 1] / 255.0; // G → ch1
        floats[2 * pixelCount + i] = imageData[i * 4 + 2] / 255.0; // B → ch2
    }
    return new ort.Tensor('float32', floats, [1, 3, size, size]);
}

function preprocessNHWC(imageData, size) {
    // For Keras classifiers (tf2onnx preserves NHWC by default)
    const floats = new Float32Array(size * size * 3);
    const pixelCount = size * size;
    for (let i = 0; i < pixelCount; i++) {
        floats[i * 3]     = imageData[i * 4]     / 255.0; // R
        floats[i * 3 + 1] = imageData[i * 4 + 1] / 255.0; // G
        floats[i * 3 + 2] = imageData[i * 4 + 2] / 255.0; // B
    }
    return new ort.Tensor('float32', floats, [1, size, size, 3]);
}

// Inference — same pattern for all models
async function classify(session, inputTensor) {
    const feeds = {};
    feeds[session.inputNames[0]] = inputTensor;
    const output = await session.run(feeds);
    const probs = output[session.outputNames[0]].data;
    return softmax(probs);
}
```

---

## File Inventory

### Training Data (Ready)
| Dataset | Location | Images | Classes |
|---------|----------|--------|---------|  
| Hieroglyph | `naderelakany/wadjet-tfrecords` → `classification/` | 15,017 train / 1,152 val / 1,154 test | 171 |
| Landmark | `naderelakany/wadjet-tfrecords` → `train/`/`val/`/`test/` | ~46K train / 4.5K val / 4.5K test | 52 |

### Current Models (Browser)
| Model | Format | Status | Action |
|-------|--------|--------|--------|  
| Hieroglyph Detector | ONNX (`glyph_detector_uint8.onnx`) | ✅ Works | Keep as-is |
| Hieroglyph Classifier | TF.js graph-model | ❌ `_FusedConv2D` crash | **Replace with ONNX** |
| Landmark Classifier | TF.js layers-model | ❌ `_FusedConv2D` crash | **Replace with ONNX** |

### Key Labels/Mappings
| File | Content |
|------|---------|  
| `models/hieroglyph/label_mapping.json` | 171 classes, idx↔Gardiner code mapping (fixed Session 3) |
| `models/landmark/tfjs/model_metadata.json` | 52 class names + display names |

## CRITICAL RULES (Non-Negotiable)

### Training
1. **float32 ONLY** — NO `mixed_float16` (causes fused ops in any export format)
2. **NO horizontal flip** for hieroglyphs (orientation matters — Rule #31)
3. Use **MobileNetV3-Small** (hieroglyph) or **EfficientNetV2-B0** (landmark)

### Export
4. Export via **`tf2onnx.convert.from_keras(model)`** → `.onnx` file
5. Quantize via **`onnxruntime.quantization.quantize_dynamic()`** → uint8
6. **NEVER** use `convert_tf_saved_model()` or `save_keras_model()` — we're ONNX now
7. **NEVER** use TF.js converter in any form

### Browser
8. Load with **`ort.InferenceSession.create(url)`** — NOT `tf.loadLayersModel` / `tf.loadGraphModel`
9. **Remove TF.js entirely** from the project (CDN imports, all `tf.*` calls)
10. Webcam loop: **`setTimeout(() => onPlay())`** pattern (from face-api.js)
11. Video input: create canvas, draw frame, getImageData → ONNX tensor
12. Preprocessing classifiers: resize → /255.0 → flatten HWC → `new ort.Tensor('float32', ..., [1,H,W,3])` (NHWC)
13. Preprocessing detector: resize → /255.0 → transpose to CHW → `new ort.Tensor('float32', ..., [1,3,H,W])` (NCHW)

---

## Success Criteria

1. **Browser scan works**: Upload → ONNX detect → ONNX classify → Gardiner codes displayed
2. **Real-time camera**: Camera → continuous ONNX detection overlay → tap to classify
3. **Server scan works**: Same flow via server API (ONNX models in Python)
4. **Landmark ID works**: Upload landmark photo → ONNX classify → correct landmark shown
5. **No TF.js in project**: Zero TF.js CDN imports, zero `tf.*` calls
6. **Translation works**: Server scan returns English + Arabic translation
7. **Dictionary complete**: All 171 Gardiner signs browsable with transliterations
8. **Performance**: First scan <5s (including ONNX WASM init), subsequent <2s
9. **Model size**: Hieroglyph classifier <5MB, Landmark classifier <10MB (uint8 quantized)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Kaggle GPU quota exceeded | Use efficient architectures (B0/MobileNetV3), short training |
| New model accuracy lower | Keep server-side Keras model as fallback, iterate on augmentation |
| ONNX export fails | tf2onnx is mature; fallback: SavedModel → tf2onnx CLI conversion |
| Data insufficient for 171 classes | Already have synthetic augmentation + new Kaggle datasets available |
| Browser memory issues | uint8 quantization reduces model to ~2-8MB |
| ONNX Runtime Web too large | Already loaded for detector (~800KB WASM); no additional cost |

---

## Deep Research Findings (Session 2 — 2026-03-20)

### ROOT CAUSE CONFIRMED

Both V1 conversion scripts (`scripts/convert_tfjs.py` and `hieroglyph_model/scripts/h2_12_13_export_tfjs.py`) used:
```python
tfjs.converters.convert_tf_saved_model(saved_model_dir, output_dir)
```
This creates a **graph-model** which:
1. Fuses `Conv2D + BatchNorm + Activation` into `_FusedConv2D` during Grappler optimization
2. `_FusedConv2D` is NOT supported by TF.js WebGL/WASM backends → crash
3. `mixed_float16` training adds `Cast DT_HALF` nodes → also crashes

**FIX (ONNX approach — Session 5 decision)**: Instead of fighting TF.js conversion, export directly from Keras to ONNX via `tf2onnx.convert.from_keras(model)`. ONNX has a standardized op set — no Grappler optimization, no fused ops, no format confusion. Load in browser with `ort.InferenceSession.create()` (ONNX Runtime Web is already loaded for the YOLOv8 detector). This eliminates TF.js entirely and unifies all browser ML under one runtime.

### Additional Kaggle Datasets (Unused)

| Dataset | Classes | Images | License | URL |
|---------|---------|--------|---------|-----|
| `mohieymohamed/heroglyphics-signs` | **767** | **33,000** | Apache 2.0 | kaggle.com/datasets/mohieymohamed/heroglyphics-signs |
| `alexandrepetit881234/egyptian-hieroglyphs` | **95** | 3,895 | CC BY 4.0 | kaggle.com/datasets/alexandrepetit881234/egyptian-hieroglyphs |
| `ayatollahelkolally/hieroglyphs-dataset` | **171** | 4,031 | MIT | kaggle.com/datasets/ayatollahelkolally/hieroglyphs-dataset |
| `ahmedelkelany/egyptian-hieroglyphic-layout-analysis` | Layout | 900 | — | Object detection bboxes for hieroglyphs |

**Key insight**: The `heroglyphics-signs` dataset has 767 classes and 33K images. Even though we only use 171 classes, the overlapping classes can massively boost our training data. Consider merging applicable classes.

### V1 Training Configuration (What Went Wrong)

| Setting | V1 Value | V2 Fix |
|---------|----------|--------|
| Architecture | EfficientNetV2-S | **MobileNetV3-Small** or **EfficientNetV2-B0** (lighter) |
| Mixed Precision | `mixed_float16` ← **THE BUG** | **float32 only** |
| Input Size | 384×384 (landmark) / 224 (hieroglyph) | 224×224 (landmark) / 128×128 (hieroglyph) |
| Export Method | `convert_tf_saved_model()` → graph-model ← **THE BUG** | **`tf2onnx.convert.from_keras()`** → ONNX |
| Browser Load | `tf.loadGraphModel()` | **`ort.InferenceSession.create()`** |
| Browser Runtime | TF.js + ONNX RT Web (dual) | **ONNX RT Web only** (unified) |
| Loss | Categorical Focal (γ=2.0) | Keep (works well) |
| Augmentation | Albumentations (offline) + Online (brightness/contrast/rotation) | Keep (good pipeline) |
| Tracking | W&B | Keep |

### face-api.js Patterns (Browser ML Reference)

Working example of browser-based ML: `D:\Personal attachements\Repos\face-api.js\`

| Pattern | face-api.js | Apply to Wadjet |
|---------|-------------|-----------------|
| Model format | Custom weights-only (architecture in code) | **ONNX** (single .onnx file, no topology JSON) |
| Weight quantization | **uint8 at rest**, dequantized on load | Same — `onnxruntime.quantization.quantize_dynamic()` |
| Webcam loop | `setTimeout(() => onPlay())` (NOT requestAnimationFrame) | **Use this pattern** — natural throttling |
| Preprocessing | `tf.browser.fromPixels(canvas)` → pad → resize → normalize | Canvas → getImageData → Float32Array → `ort.Tensor` |
| Video input | Pass `<video>` element directly to `tf.browser.fromPixels` | Draw video frame to canvas → getImageData → ONNX tensor |
| Backend selection | None (consumer provides) — defaults to WebGL | WASM (default), WebGL (optional via `executionProviders`) |
| Model caching | None (browser HTTP cache only) | Same — browser HTTP cache + service worker |

### Available Skills (from Repos)

| Phase | Skill | Path |
|-------|-------|------|
| Model Training | `computer-vision-expert` | `Repos/antigravity-awesome-skills/skills/computer-vision-expert/` |
| Model Training | `ml-engineer` | `Repos/antigravity-awesome-skills/skills/ml-engineer/` |
| Model Training | `data-scientist` | `Repos/antigravity-awesome-skills/skills/data-scientist/` |
| Backend | `fastapi-pro` | `Repos/antigravity-awesome-skills/skills/fastapi-pro/` |
| Backend | `fastapi-router-py` | `Repos/antigravity-awesome-skills/skills/fastapi-router-py/` |
| Frontend | `tailwind-patterns` | `Repos/antigravity-awesome-skills/skills/tailwind-patterns/` |
| Frontend | `scroll-experience` | `Repos/antigravity-awesome-skills/skills/scroll-experience/` |
| AI/Thoth | `gemini-api-dev` | `Repos/antigravity-awesome-skills/skills/gemini-api-dev/` |
| AI/Thoth | `rag-engineer` | `Repos/antigravity-awesome-skills/skills/rag-engineer/` |
| AI/Thoth | `prompt-engineering-patterns` | `Repos/antigravity-awesome-skills/skills/prompt-engineering-patterns/` |
| Deploy | `docker-expert` | `Repos/antigravity-awesome-skills/skills/docker-expert/` |
| Deploy | `render-automation` | `Repos/antigravity-awesome-skills/skills/render-automation/` |

### Available Animation Libraries

| Library | Location | What to Extract |
|---------|----------|----------------|
| magicui | `Repos/21-Frontend-UI/magicui/` | CSS @keyframes from `registry.json` |
| react-bits | `Repos/21-Frontend-UI/react-bits/` | Silk, Iridescence, Aurora backgrounds |
| Hover.css | `Repos/21-Frontend-UI/Hover/css/hover.css` | Pure CSS hover transitions |
| motion-primitives | `Repos/21-Frontend-UI/motion-primitives/` | Spotlight, glow, text effects |
| animate-ui | `Repos/21-Frontend-UI/animate-ui/` | TailwindCSS v4 animated components |
| atropos | `Repos/21-Frontend-UI/atropos/` | 3D parallax tilt (already integrated) |

### Repos Directory Structure (57 top-level folders)

```
01-Google-AI/        → keras/ (full source), tensorflow/, jax/, Gemini cookbook
02-OpenAI/           → whisper, evals, SDKs
03-Anthropic/        → Claude Code, prompt engineering guide
04-Meta-PyTorch/     → PyTorch, torchtune (fine-tuning recipes)
05-LangChain/        → LangChain, LangGraph, LangSmith
06-AI-Agents/        → AutoGen, CrewAI, GPT-Researcher
07-HuggingFace/      → transformers, peft, accelerate, datasets, diffusers, TRL
08-RAG-VectorDB/     → ChromaDB, LlamaIndex, Qdrant, RAGFlow
14-AI-Learning/      → fast.ai course22 (model selection notebook!), GenAI agents
16-DevOps/           → label-studio (data annotation), wandb (experiment tracking)
20-Prompts-GPT/      → 170+ persona prompts, system prompts from Cursor/Devin/etc.
21-Frontend-UI/      → magicui, react-bits, Hover.css, atropos, shadcn/ui
face-api.js/         → Browser-based ML reference implementation
notebooks/           → 180+ Unsloth fine-tuning notebooks (DeepSeek OCR, PaddleOCR)
spec-kit/            → Project templates (spec, tasks, checklist, constitution)
antigravity-awesome-skills/ → 883 skills (CV, ML, FastAPI, Docker, SEO, etc.)
```

### Conclusion: Nothing Needs Cloning

All resources are local. The ONNX pivot (Session 5) means we also remove all TF.js dependencies:
- **Remove**: `@tensorflow/tfjs` CDN imports from `scan.html` and `explore.html`
- **Remove**: All `tf.*` API calls from `hieroglyph-pipeline.js` and `explore.html`
- **Keep**: `onnxruntime-web` CDN (already loaded for YOLOv8 detector)
- **Add**: `tf2onnx` and `onnxruntime` to Kaggle notebook pip installs

All needed resources are already in the Repos folder. The Kaggle datasets will be downloaded directly in the Kaggle notebook. No new repos need to be cloned.

---

## Deep Research Findings (Session 6 — 2026-03-20)

### tf2onnx Official Documentation (github.com/onnx/tensorflow-onnx)

**Supported versions**: tf2onnx supports TF 2.13+, Python 3.10-3.12, ONNX opset 14-18 (default opset 15).

**`from_keras()` API confirmed**:
```python
model_proto, _ = tf2onnx.convert.from_keras(
    model,
    input_signature=spec,
    opset=17,                     # Explicit opset (our notebooks already use 17)
    inputs_as_nchw=None,          # We DON'T use this — keep NHWC native
    output_path="model.onnx"      # Can save directly (optional)
)
```

**CRITICAL: Input format decision**:
- `from_keras()` **preserves NHWC by default** (Keras native format)
- The `inputs_as_nchw` parameter would add a Transpose op at the start of the ONNX model
- **Decision**: Keep NHWC for classifiers (safe, no extra ops), NCHW for detector (YOLOv8, PyTorch origin)
- Browser needs two preprocessing paths: `preprocessNCHW()` for detector, `preprocessNHWC()` for classifiers
- This is safer than forcing NCHW because `inputs_as_nchw` has potential edge cases we can't test locally

**Quantization**: `quantize_dynamic()` for uint8 is correct for classification models. If accuracy drops, fallback to `quantize_static()` with calibration data (requires `CalibrationDataReader`).

**tf2onnx maintainer status**: Project is looking for a new maintainer (as of 2025). The tool is mature and stable but development has slowed. This is acceptable since we only need `from_keras()` which is well-tested.

### ONNX Runtime Web Documentation (onnxruntime.ai)

**Key optimization options**:
1. **ORT format**: Models can be converted to `.ort` format for smaller binary size and faster init
2. **Custom build**: ONNX Runtime can be built with only needed ops to reduce WASM size
3. **Execution providers**: `wasm` (CPU, works everywhere), `webgl` (GPU), `webgpu` (latest GPU API)
4. **Session options**: `graphOptimizationLevel: 'all'` for maximum optimization

**Our approach is standard**: Load ONNX → create session → feed tensor → get output. This is the well-documented happy path.

### Repos Folder Exhaustive Inventory

| Folder | Relevance | Action |
|--------|-----------|--------|
| `01-Google-AI/03-ML-Frameworks/keras/` | Has Keras source but NO ONNX examples | None needed |
| `04-Meta-PyTorch/` | PyTorch, torchtune — not our stack | None |
| `07-HuggingFace/` | transformers, peft — LLM tools, not CV | None |
| `14-AI-Learning/` | fast.ai, GenAI agents — general ML | Reference only |
| `notebooks/` (180+) | ALL are LLM fine-tuning (GRPO, LoRA, etc.) | None for us |
| `face-api.js/` | Webcam ML patterns (already documented) | ✅ Already used |
| `antigravity-awesome-skills/` | 883 skills, ~30 relevant | ✅ Already cataloged |
| ONNX-related repos | **NONE exist** in Repos folder | tf2onnx is pip-only |

### Skill Deep-Dive Results

**computer-vision-expert** (SKILL.md read):
- Covers YOLO26, SAM 3, VLMs, ONNX/TensorRT deployment, edge optimization
- Relevant for: Phase 4 browser ONNX integration, real-time detection loop
- Key patterns: NMS-free architectures, model quantization strategies

**ml-engineer** (SKILL.md read):
- Covers PyTorch 2.x, TF 2.x, ONNX cross-framework interop, model serving
- Quantization/pruning/distillation, edge deployment (TF Lite, PyTorch Mobile, ONNX Runtime)
- Relevant for: Phase 1-2 training, Phase 3 server-side ONNX

**data-scientist** (SKILL.md read):
- General ML/statistics skill (supervised/unsupervised, deep learning, feature engineering)
- Covers CNNs, image classification, model evaluation, experiment tracking
- Relevant for: Training strategy, hyperparameter tuning, evaluation metrics

### Gap Analysis

| Gap | Severity | Resolution |
|-----|----------|-----------|
| ~~PLAN said NCHW for classifiers~~ | Medium | **FIXED** — Updated to NHWC (Keras native) |
| No ONNX repos in local folder | Low | Not needed — tf2onnx and onnxruntime are pip packages |
| No useful notebooks in 180+ collection | Low | All LLM-focused — our own notebooks are purpose-built |
| tf2onnx seeking new maintainer | Low | Tool is mature, `from_keras()` is stable |
| V1 had `mixed_precision: True` | High | Already addressed — V2 uses float32 ONLY |
| V1 had `random_flip_horizontal: True` | Medium | Fixed for hieroglyphs (no flip), kept for landmarks |
| No static quantization fallback documented | Low | Added `quantize_static()` as backup in PLAN |

### Conclusion: Ready for Execution

All research is complete. No repos need cloning. No additional data sources need downloading before training (existing 15K hieroglyph + 46K landmark images are sufficient; external 33K dataset is a deferred backup). Both notebooks are ready for Kaggle upload. The PLAN, TASKS, PROMPTS, and CHECKLIST are comprehensive and accurate.
