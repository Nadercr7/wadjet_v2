# Model Rebuild — Pre-Launch Checklist

**Date**: ___________
**Reviewer**: ___________
**Architecture**: ONNX-Unified (no TF.js)

---

## Models (ONNX)

- [ ] CHK001: Hieroglyph classifier ONNX loads in browser via `ort.InferenceSession.create()`
- [ ] CHK002: Hieroglyph classifier ONNX produces correct Gardiner codes on test images
- [ ] CHK003: Landmark classifier ONNX loads in browser via `ort.InferenceSession.create()`
- [ ] CHK004: Landmark classifier ONNX correctly identifies test landmarks
- [ ] CHK005: YOLOv8 ONNX detector returns bounding boxes on hieroglyph photos (already working)
- [ ] CHK006: Model files are within size budget (hieroglyph <5MB, landmark <10MB — uint8 quantized)
- [ ] CHK007: Model warmup completes without errors (WASM provider)

## TF.js Removal Verification

- [ ] CHK008: Zero `@tensorflow/tfjs` CDN imports in any HTML file
- [ ] CHK009: Zero `tf.loadLayersModel` or `tf.loadGraphModel` calls in any JS file
- [ ] CHK010: Zero `tf.browser.fromPixels` calls (replaced with canvas getImageData)
- [ ] CHK011: Zero `tf.tensor` / `tf.tidy` / `tf.dispose` calls
- [ ] CHK012: `grep -r "tensorflow\|tfjs\|tf\." --include="*.html" --include="*.js"` returns ZERO matches (excluding comments/docs)

## Server Pipeline

- [ ] CHK013: `POST /api/scan` returns detections on real hieroglyph images
- [ ] CHK014: Classification returns correct Gardiner codes (spot-check 10 signs)
- [ ] CHK015: Transliteration produces valid MdC notation
- [ ] CHK016: Translation returns English text (Gemini API working)
- [ ] CHK017: Translation returns Arabic text
- [ ] CHK018: `POST /api/detect` returns bounding boxes only
- [ ] CHK019: Server uses ONNX Runtime (`onnxruntime`) for classifier inference

## Client Pipeline (Browser — All ONNX)

- [ ] CHK020: Client scan mode: upload → ONNX detect → ONNX classify → display results
- [ ] CHK021: ONNX detection runs in browser (onnxruntime-web WASM)
- [ ] CHK022: ONNX classification runs in browser (same onnxruntime-web)
- [ ] CHK023: Results display with correct formatting (Gardiner codes, confidence %, bboxes)
- [ ] CHK024: Bounding boxes drawn on result canvas

## Camera / Real-Time

- [ ] CHK025: Camera opens on scan page (with permission prompt)
- [ ] CHK026: Live detection overlay shows bounding boxes (ONNX per-frame)
- [ ] CHK027: Frame rate is smooth (≥2 FPS detection)
- [ ] CHK028: "Capture" freezes frame and runs ONNX classification
- [ ] CHK029: Front/back camera switching works
- [ ] CHK030: Camera properly stops when leaving page

## Dictionary

- [ ] CHK031: `/dictionary` shows all 171 Gardiner signs
- [ ] CHK032: Each sign has: code, transliteration, description, Unicode character
- [ ] CHK033: Search/filter works across all signs
- [ ] CHK034: Sign detail shows category and usage info

## Landmarks

- [ ] CHK035: `/explore` shows all curated landmarks
- [ ] CHK036: Landmark detail pages load with metadata
- [ ] CHK037: Landmark identification works (upload photo → ONNX classify → correct result)
- [ ] CHK038: Recommendations appear on landmark detail

## Translation

- [ ] CHK039: RAG retrieval returns relevant context from corpus
- [ ] CHK040: Gemini API responds within timeout (30s)
- [ ] CHK041: Key rotation works when hitting rate limits
- [ ] CHK042: Error messages shown gracefully when translation fails

## Performance

- [ ] CHK043: First scan load time < 5 seconds (including ONNX WASM init + model download)
- [ ] CHK044: Subsequent scans < 2 seconds
- [ ] CHK045: Model files cached by service worker
- [ ] CHK046: Service worker cache version is current
- [ ] CHK047: No memory leaks on repeated scans (ONNX tensors properly released)

## Cross-Browser

- [ ] CHK048: Chrome desktop — all features work
- [ ] CHK049: Firefox desktop — all features work
- [ ] CHK050: Safari desktop — all features work (WASM provider)
- [ ] CHK051: Chrome Android — camera + scan work
- [ ] CHK052: Safari iOS — camera + scan work

## Notes

_Record any issues found during checklist review:_

1. ___
2. ___
3. ___
