# Feature Specification: Hieroglyph Classifier (PyTorch Rebuild)

**Created**: 2026-03-20
**Status**: Ready for implementation
**Phase**: P8-B (training) → P8-C (backend integration) → P8-D (frontend)

---

## Context

The old Keras/TF.js EfficientNetV2-S classifier crashes with `_FusedConv2D` fused op
errors at ONNX Runtime inference. It is being replaced with a PyTorch MobileNetV3-Small
model exported natively to ONNX — no intermediate conversion libraries needed.

The existing YOLO-based **detector** (`glyph_detector_uint8.onnx`) works correctly
and is NOT being replaced.

---

## User Stories

### Story 1 — Scan a hieroglyph image (P1 — Core)

**Scenario**: A user uploads or photographs a hieroglyph inscription. The app
detects individual glyphs, classifies each one, and returns Gardiner codes with
transliterations and a combined translation.

**Why P1**: This is the signature feature of Wadjet. Without it the Scan page
is completely broken.

**Acceptance Scenarios**:

1. **Given** a clear photo of hieroglyphs, **When** the user uploads it to Scan,
   **Then** each glyph is bounded, classified with a Gardiner code (e.g. "G17"),
   confidence ≥ 15%, and a phonetic transliteration is shown.

2. **Given** a photo with 5+ glyphs, **When** classification runs,
   **Then** ≥ 70% of detected glyphs show correct Gardiner codes (human-verified).

3. **Given** a very low-quality or blurry image, **When** the pipeline runs,
   **Then** low-confidence glyphs are flagged (not silently wrong) and
   the UI shows a "low confidence" warning badge.

4. **Given** a correct sequence of glyphs, **When** transliteration runs,
   **Then** the combined phonetic reading is assembled left-to-right (or right-to-left
   per reading order module) and displayed as Unicode text.

5. **Given** a transliterated sequence ≥ 3 glyphs, **When** translation runs,
   **Then** an English/Arabic interpretation is produced via the RAG pipeline
   (Gemini + FAISS embeddings).

**Edge Cases**:
- Image with no hieroglyphs → "No glyphs detected" message, no crash
- Single glyph image → classified correctly, no translation attempted (too short)
- Unknown/rare glyph → shown as "?" with low confidence, does not crash the pipeline
- All 171 classes must be reachable (no silent holes in Gardiner mapping)

---

### Story 2 — Use the classifier from browser (P2 — Client-side)

**Scenario**: After the initial server-side scan, the user can run client-side
inference via ONNX Runtime Web (for offline use after PWA install).

**Why P2**: The service worker caches the ONNX model for offline use.
The browser-side pipeline must accept the new NCHW model format.

**Acceptance Scenarios**:

1. **Given** the app is loaded and the SW has cached models, **When** the user
   goes offline and scans an image, **Then** detection + classification run
   in-browser with ONNX Runtime Web (no server call needed).

2. **Given** the new `hieroglyph_classifier_uint8.onnx` model,
   **When** the browser preprocesses an image, **Then** the tensor is
   NCHW `[1, 3, 128, 128] float32` (NOT the old NHWC `[1, 128, 128, 3]`).

**Edge Cases**:
- Mobile browser with limited memory → uint8 quantized model (~3-5 MB) loads without OOM
- WASM fallback if WebGL unavailable → still correct output (shape verified)

---

## Requirements

### Model Architecture
- **Architecture**: MobileNetV3-Small (torchvision or timm)
- **Input**: `[1, 3, 128, 128]` float32, values in `[0.0, 1.0]`, NCHW
- **Output**: `[1, 171]` float32, softmax probabilities
- **Export**: `torch.onnx.export`, opset_version=17, dynamic batch axis
- **Production**: `quantize_dynamic` → uint8 → `hieroglyph_classifier_uint8.onnx`
- **Accuracy gate**: val top-1 accuracy ≥ 70%

### Training Data
- **Path**: `D:\Personal attachements\Projects\Final_Horus\Wadjet\hieroglyph_model\data\splits\classification\`
- **Format**: ImageFolder (train/val/test subdirs, one folder per Gardiner code)
- **Classes**: 171
- **Train images**: ~15,017

### Training Config
- **Phase 1**: Freeze backbone, train head only (5 epochs, lr=1e-3, AdamW)
- **Phase 2**: Unfreeze top 70% layers, cosine LR decay (30 epochs, lr=1e-4)
- **Loss**: FocalLoss(gamma=2.0) + class weights (sqrt-inverse-frequency)
- **Augmentation**: albumentations — brightness/contrast/saturation, rotation ±10°
- **CRITICAL**: NO horizontal flip (hieroglyphs are direction-sensitive)

### Backend Changes Required
| File | Change |
|------|--------|
| `app/core/hieroglyph_pipeline.py` | NHWC→NCHW preprocess, new model path, threshold 0.25→0.15 |
| `app/core/gardiner.py` | Complete 71→171 sign mapping |
| `app/core/rag_translator.py` | Remove disabled flag |
| `app/api/scan.py` | Confidence threshold 0.25→0.15 |

### Frontend Changes Required
| File | Change |
|------|--------|
| `app/static/js/hieroglyph-pipeline.js` | NHWC→NCHW, new model URL |
| `app/static/sw.js` | Bump cache `v15` |
| `app/templates/base.html` | Bump `?v=15` |

### Output Files
```
models/hieroglyph/classifier/
  hieroglyph_classifier.onnx          ← fp32 (backup)
  hieroglyph_classifier_uint8.onnx    ← production
  label_mapping.json                   ← {0: "A1", 1: "A55", ...}
  model_metadata.json                  ← {input_size: 128, num_classes: 171, format: "NCHW"}
```

### Story 3 — Real-Time Camera Scanning (P3 — Enhanced)

**Scenario**: The user switches to "Camera" mode on the Scan page. The camera 
activates and shows a live video feed. Gold bounding boxes appear in real-time
around detected hieroglyphs as the user moves the camera. The user taps "Capture"
to freeze the frame and run full classification.

**Why P3**: Detection-only overlays are already implemented. Classification in
real-time is very valuable but requires the NCHW fix first. This story unblocks
after Phase D.

**Acceptance Scenarios**:

1. **Given** camera mode is active with live video, **When** the user points at
   hieroglyphs, **Then** gold bounding boxes appear on the overlay canvas at
   approximately 10 fps with no UI jank (detection runs in `startCameraLoop()`).

2. **Given** camera mode is active, **When** the user taps "Capture",
   **Then** `captureAndClassify(video)` runs, the video pauses, and Gardiner codes
   + transliteration appear in the results panel within 3 seconds.

3. **Given** the app is offline (PWA + SW cache), **When** the user uses camera mode,
   **Then** both detection and classification run entirely client-side via ONNX
   Runtime Web WASM — no server call needed.

4. **Given** camera permissions denied, **When** the user clicks "Start Camera",
   **Then** a clear error message explains how to allow camera permissions —
   no crash, no blank screen.

**Implementation Notes**:
- `startCameraLoop(video, overlayCanvas, opts)` — already implemented, calls `detect()` only
- `captureAndClassify(video)` — already implemented, calls `processImage(canvas)`
- Phase D fix makes `classify()` and `_warmup()` NCHW-compatible → camera classify works
- The camera overlay canvas is positioned absolutely over the `<video>` element in CSS
- After NCHW fix, no template changes are needed for camera mode

---

## Non-Functional Requirements

- Inference latency: ≤ 100ms per glyph on CPU (ONNX Runtime, server-side)
- Model size: ≤ 8 MB uint8 (fits in browser cache budget)
- Must work in ONNX Runtime Web (browser) — no custom ops
- Must work with opset 17 (matches existing detector)
