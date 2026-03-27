# Wadjet v2 — Known Issues & Root Causes

> This file explains WHY things are broken and what the fix is.
> It is the ground truth for understanding the current state before working on P8.

---

## ISSUE 1: Hieroglyph Classifier Crashes

**Symptom**: `onnxruntime.capi.onnxruntime_pybind11_state.InvalidGraph: _FusedConv2D`
error when calling the ONNX classifier in any environment (browser or server).

**Root Cause**:
The original Keras model (`efficientnet_v2s.keras`) used TensorFlow's internal
`_FusedConv2D` op — a TF-only fused kernel that is **not part of the ONNX standard**.
When converted via `tf2onnx`, this op is embedded in the graph as a custom op.
ONNX Runtime does not have a handler for `_FusedConv2D`, so it crashes on load.

**Why it wasn't caught earlier**:
We discovered this when trying to run the ONNX model. The Kaggle training notebooks
ran fine because TF ran the model natively using TF kernels. The crash only appears
when loading the ONNX file in a non-TF environment.

**Fix**:
Train a new classifier from scratch using **PyTorch** (`torch.onnx.export` is native
ONNX and never produces TF-specific ops). File: `planning/model-rebuild/pytorch/hieroglyph_classifier.ipynb`.

**Status**: ⬜ Not started — Phase P8-B

---

## ISSUE 2: Landmark Classifier Crashes (same root cause)

**Symptom**: TF.js throws an error when loading `EfficientNetV2-S` converted model.
Same `_FusedConv2D` / fused op crash as Issue 1.

**Root Cause**: Same as Issue 1 — Keras EfficientNetV2 uses `_FusedConv2D` in TF.
Any TF→ONNX or TF→TF.js conversion of this model will have the same problem.

**Fix**:
Train a **new landmark classifier from scratch using PyTorch** (EfficientNet-B0 via timm),
export to ONNX with `torch.onnx.export()`, quantize to uint8 — same approach as
the hieroglyph classifier.

Architecture: `timm.create_model('efficientnet_b0', pretrained=True, num_classes=52)`
Input: [1, 3, 224, 224] NCHW → Output: [1, 52] softmax probabilities
Training: 2-phase (head → fine-tune), CrossEntropy + class weights, full augment with h-flip
Dataset: 52 Egyptian landmark classes, ~30k images, well-balanced (min=176, max=1450 per class)

**Gemini Vision role (complementary, not primary)**:
- After the local model predicts, Gemini Vision can enrich the result with a
  description, interesting facts, and confidence verification for display purposes.
- If the local model confidence < 0.5, call Gemini as fallback for identification.
- If Gemini API fails → use local model result only (graceful degradation).

This hybrid approach gives us:
  - Fast, offline-capable local prediction (no API cost per request)
  - Rich AI-generated descriptions using Gemini
  - Double-checking on low-confidence cases

**Data prepared at**: `data/landmark_classification/` ✅ READY (25,710 train, 52 classes, min=300)
Data merged from: v1 splits (21,151) + eg-landmarks extra (+1,938 for 37 classes) + augmentation (33 weak classes → 300 min)
Prep script: `scripts/prepare_landmark_data.py` (executed ✅)

**Kaggle upload**: Single dataset from `data/landmark_classification/` — no longer needs v1 path or eg-landmarks separate upload.

**Status**: ⬜ Not started — Phase B2 (train after Phase B hieroglyph training)

---

## ISSUE 3: Gardiner Mapping Only 71/171 Signs

**Symptom**: The scan pipeline classifies 171 classes but only 71 have human-readable
Gardiner names + descriptions in `app/core/gardiner.py`.
The other 100 would show as raw codes (e.g. "A55") with no description.

**Root Cause**:
`gardiner.py` was partially migrated from v1. The v1 `gardiner_mapping.py` had the
71 most common signs. The remaining 100 were in separate data files that weren't
merged.

**Fix**:
After Phase B training, the `label_mapping.json` output gives all 171 class codes.
Use that file + the v1 `data/reference/` JSONs to complete all 171 entries in
`app/core/gardiner.py`.

**Status**: ⬜ Not started — Phase P8-C (task C.5)

---

## ISSUE 4: Translation Pipeline Disabled

**Symptom**: RAG translation never runs. Scan results show glyphs + transliteration
but no English/Arabic translation.

**Root Causes** (two places):
1. `app/core/rag_translator.py` — has a flag `TRANSLATION_ENABLED = False`
2. `app/api/scan.py` — confidence threshold `CONFIDENCE_THRESHOLD = 0.25` is too strict,
   rejects most detections before translation even starts

**Fix**:
- Remove the `TRANSLATION_ENABLED = False` flag in `rag_translator.py`
- Lower threshold to `0.15` in both `scan.py` and `hieroglyph_pipeline.py`

**Status**: ⬜ Not started — Phase P8-C (tasks C.4, C.6)

---

## ISSUE 5: Client-side JS Preprocessing Uses Wrong Tensor Format

**Symptom**: Even if the server ONNX model works, the browser-side
`hieroglyph-pipeline.js` sends the old Keras NHWC `[1, 128, 128, 3]` tensor
to the new PyTorch NCHW `[1, 3, 128, 128]` model → wrong results or an
`Invalid input shape` error from ONNX Runtime.

**Root Cause**:
The old Keras model used NHWC (Height-Width-Channel) layout.
PyTorch models use NCHW (Channel-Height-Width) layout.
The JS file builds NHWC tensors for the classifier in **two places**:

1. **`classify()` method** — pixel loop uses interleaved NHWC layout:
   ```javascript
   floats[p * 3]     = imgData[p * 4]     / 255.0;   // R (NHWC)
   floats[p * 3 + 1] = ...                             // G (NHWC)
   floats[p * 3 + 2] = ...                             // B (NHWC)
   inputTensor = new ort.Tensor('float32', floats, [1, size, size, 3]);  // WRONG
   ```

2. **`_warmup()` method** — dummy tensor shape is NHWC:
   ```javascript
   var dummyCls = new ort.Tensor('float32', new Float32Array(1 * s * s * 3), [1, s, s, 3]);  // WRONG
   ```
   The `_warmup()` runs at model load. If the shape is wrong, the warmup will
   actually crash or silently warm up the wrong path — making Phase A harder to debug.

**Fix**:
Both methods must be updated simultaneously in `app/static/js/hieroglyph-pipeline.js`:

*`_warmup()`:*
```javascript
// OLD:
var dummyCls = new ort.Tensor('float32', new Float32Array(1 * s * s * 3), [1, s, s, 3]);
// NEW:
var dummyCls = new ort.Tensor('float32', new Float32Array(1 * 3 * s * s), [1, 3, s, s]);
```

*`classify()`:*
```javascript
// OLD: interleaved NHWC loop + [1, size, size, 3]
for (var p = 0; p < pixelCount; p++) {
    floats[p * 3]     = imgData[p * 4]     / 255.0;
    floats[p * 3 + 1] = imgData[p * 4 + 1] / 255.0;
    floats[p * 3 + 2] = imgData[p * 4 + 2] / 255.0;
}
var inputTensor = new ort.Tensor('float32', floats, [1, size, size, 3]);

// NEW: planar NCHW loop + [1, 3, size, size]
for (var p = 0; p < pixelCount; p++) {
    floats[p]                    = imgData[p * 4]     / 255.0;  // R plane
    floats[pixelCount + p]       = imgData[p * 4 + 1] / 255.0;  // G plane
    floats[2 * pixelCount + p]   = imgData[p * 4 + 2] / 255.0;  // B plane
}
var inputTensor = new ort.Tensor('float32', floats, [1, 3, size, size]);
```

Note: The `startCameraLoop()` calls `detect()` only — detection already uses NCHW ✅.
The `captureAndClassify()` calls `processImage()` which calls `classify()` — so it
inherits the NHWC bug and will also be fixed automatically when `classify()` is fixed.

**Status**: ⬜ Not started — Phase P8-D (task D.2)

---

## ISSUE 6: Kaggle Was Abandoned for Keras — Now Re-Enabled for PyTorch

**Old symptom (resolved)**: Kaggle GPU kernels failed for the Keras/TF approach:
- `tf2onnx` is not pre-installed, and `pip install tf2onnx` requires outbound internet
- Kaggle had persistent DNS failures blocking pip on those sessions
- Even if tf2onnx ran, Keras EfficientNetV2's `_FusedConv2D` ops break ONNX Runtime anyway

**Why Kaggle works now**:
- `torch`, `torchvision`, `timm`, `onnx`, `onnxruntime`, `albumentations` are **pre-installed** on Kaggle
- `torch.onnx.export()` is built-in — no conversion library install needed
- Only `pytorch-lightning` might need `!pip install lightning` (one-liner, fast)

**Decision**: Use Kaggle GPU (T4/P100) for training. Much faster than local CPU.
Old TF/Keras notebooks archived in `planning/model-rebuild/kaggle-archive/`.

**Workflow**: Write notebook locally → upload to Kaggle → run on GPU → download ONNX outputs.

**Status**: ✅ Re-enabled — training on Kaggle with PyTorch

---

## Non-Issues (Things That Work Fine)

| Component | Status | Notes |
|-----------|--------|-------|
| YOLO Detector (`glyph_detector_uint8.onnx`) | ✅ Works | PyTorch-native ONNX, never had TF issues |
| Thoth Chatbot | ✅ Works | Gemini API, streaming, session store |
| Quiz Engine | ✅ Works | Static + Gemini-generated questions |
| Dictionary | ✅ Works | 171 Gardiner signs displayed + search |
| Write (hieroglyphs) | ✅ Works | Alpha/MdC mode, Unicode conversion |
| Landmark Browse | ✅ Works | 52 cards, detail modal, JSON data |
| Transliteration | ✅ Works | JS transliteration table works |
| Reading Order | ✅ Works | `reading_order.py` logic intact |
| RAG FAISS index | ✅ Works | Needs translation re-enabled (Issue 4) |
| Frontend (all 9 pages) | ✅ Works | P0-P6 complete, polished |
