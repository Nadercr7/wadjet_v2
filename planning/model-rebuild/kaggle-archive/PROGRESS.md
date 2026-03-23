# Model Rebuild — Progress Tracker

**Started**: 2026-03-20
**Last Updated**: 2026-03-20 Session 7 — **Phase 3+4 Complete, Awaiting Kaggle Models**

---

## Phase 0: Planning & Preparation ✅
| Task | Status | Notes |
|------|--------|-------|
| Deep research repos folder | ✅ | 57 folders, 883 skills inventoried |
| Analyze all backend problems | ✅ | 10+1 issues (4 critical, 3 high, 4 medium) |
| Research best practices | ✅ | Originally TF.js, now pivoted to ONNX |
| Create planning files | ✅ | PLAN, PROGRESS, TASKS, PROMPTS, SESSION_LOG, CHECKLIST |
| Deep research: Kaggle datasets | ✅ | Found 4 additional datasets (33K+ images, up to 767 classes) |
| Deep research: face-api.js patterns | ✅ | Webcam loop, preprocessing, uint8 quant patterns documented |
| Deep research: V1 conversion root cause | ✅ | convert_tf_saved_model → graph-model → _FusedConv2D |
| Deep research: V1 training config | ✅ | mixed_float16 bug + full augment pipeline documented |
| Update all planning docs | ✅ | PLAN, TASKS, PROMPTS, SESSION_LOG all updated with findings |
| T007: Audit rare classes | ✅ | 7 classes <30 imgs (D156=6, P13=6, O11=11, V25=11, S24=16, T21=16, N18=28) |
| T009: Validate label_mapping.json | ✅ | All 171 idx↔gardiner consistent; fixed 5 missing descriptions + 2 corrupt unicode |
| T003: Map overlapping Gardiner codes | ✅ | All 171 codes expected in 767-class external dataset |
| T008: Decide rare class strategy | ✅ | KEEP all 171 — Focal Loss + class weights compensate |
| T001-T006: External data merge | ⏭️ | DEFERRED — use existing 15K images first |
| **Architecture pivot to ONNX** | ✅ | Session 5: TF.js → ONNX-unified (removes TF.js entirely) |
| **Rewrite all planning docs for ONNX** | ✅ | PLAN, TASKS, PROGRESS, PROMPTS, SESSION_LOG, CHECKLIST |
| **Rewrite training notebooks for ONNX** | ✅ | Both notebooks updated with ONNX export |
| **Session 6: Deep research & validation** | ✅ | Exhaustive repos/online research, NHWC/NCHW fix, gap analysis |

## Phase 1: Hieroglyph Classifier (ONNX)
| Task | Status | Notes |
|------|--------|-------|
| Create Kaggle training notebook | ✅ | T010-T025 — `notebooks/hieroglyph_classifier.ipynb` (ONNX export) |
| Upload to Kaggle & run | ✅ | Pushed via CLI: `naderelakany/wadjet-hieroglyph-classifier-onnx` |
| Download trained ONNX model | ⬜ | `hieroglyph_classifier_uint8.onnx` — awaiting kernel completion |
| Copy to models/hieroglyph/classifier/ | ⬜ | Replace current broken TF.js files |
| Validate ONNX in Python | ⬜ | |
| Validate ONNX in browser | ⬜ | |

## Phase 2: Landmark Classifier (ONNX)
| Task | Status | Notes |
|------|--------|-------|
| Create Kaggle training notebook | ✅ | T035-T044 — `notebooks/landmark_classifier.ipynb` (ONNX export) |
| Upload to Kaggle & run | ✅ | Pushed via CLI: `naderelakany/wadjet-landmark-classifier-onnx` |
| Download trained ONNX model | ⬜ | `landmark_classifier_uint8.onnx` — awaiting kernel completion |
| Copy to models/landmark/onnx/ | ⬜ | Directory created, metadata placed |
| Validate ONNX in browser | ⬜ | |

## Phase 3: Backend Fixes ✅
| Task | Status | Notes |
|------|--------|-------|
| Server-side ONNX migration | ✅ | hieroglyph_pipeline.py → ort.InferenceSession |
| Fix gardiner.py (all 171 signs) | ✅ | Already complete (172 entries confirmed) |
| Fix client result format mismatch | ✅ | camelCase in pipeline.js |
| Enable translation pipeline | ✅ | dependencies.py: enable_translation=True |
| Lower detection threshold | ✅ | postprocess.py: 0.25→0.15, config.py added setting |
| Fix classifier_input_size default | ✅ | 384→128 in hieroglyph_pipeline.py |
| Wire recommendation engine | ✅ | explore.py landmark detail returns recommendations |
| Unify Gemini key loading | ✅ | GEMINI_API_KEYS (comma-sep) in rag_translator.py |

## Phase 4: Browser Integration — ONNX-Unified + Camera ✅
| Task | Status | Notes |
|------|--------|-------|
| Rewrite hieroglyph-pipeline.js for ONNX | ✅ | Full rewrite, ZERO TF.js, ort.InferenceSession only |
| Rewrite explore.html landmark ID for ONNX | ✅ | Lazy ONNX load, 224×224 NHWC preprocessing |
| Remove TF.js CDN from scan.html | ✅ | Removed @tensorflow/tfjs@4.22.0 |
| Remove TF.js from explore.html | ✅ | Replaced lazy TF.js + 3 backends with lazy ONNX load |
| Implement setTimeout webcam loop | ✅ | startCameraLoop/stopCameraLoop in pipeline.js |
| Add canvas overlay for bounding boxes | ✅ | Gold boxes + confidence % overlay |
| Update SW cache | ✅ | v13→v14, ONNX model paths |
| Remove tensorflow from requirements.txt | ✅ | Server uses onnxruntime only |
| Fix explore.py metadata path | ✅ | tfjs/ → onnx/ |
| Create landmark ONNX metadata | ✅ | models/landmark/onnx/model_metadata.json |

## Phase 5: Integration & Testing
| Task | Status | Notes |
|------|--------|-------|
| Deploy new ONNX models | ⬜ | Awaiting Kaggle kernel completion |
| Verify zero TF.js references | ✅ | grep confirmed: zero in app/ code |
| End-to-end testing | ⬜ | After model deployment |
| Performance profiling | ⬜ | |
