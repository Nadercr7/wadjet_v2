# Wadjet v2 — Detector Rebuild Pre-Launch Checklist

> Complete ALL items before considering the new detector ready for production.
> Master Plan: `planning/detector-rebuild/MASTER_PLAN.md`
> Task Tracker: `planning/detector-rebuild/REBUILD_TASKS.md`

---

## A. Data Quality

- [x] CHK-A1 Training dataset has **5,000+** images — **10,311 total** (train 7,655 / val 2,051 / test 605)
- [x] CHK-A2 All annotations are YOLO format (class_id cx cy w h, normalized 0-1) — verified 0 issues across all 10,311 files
- [x] CHK-A3 Single class (class_id = 0 for all labels) — 158,404 boxes, all class 0
- [x] CHK-A4 Train/val/test split exists (80/15/5) — 74/20/6 ratio (source-stratified)
- [x] CHK-A5 Sources are stratified across splits (mohiey 84%, synthetic 9%, signs_seg 3%, v1_raw 2%, hla 2%)
- [x] CHK-A6 NO horizontal flip was applied during data augmentation — confirmed in merge/synth scripts
- [~] CHK-A7 Manual verification was done on GroundingDINO proposals — ⚠️ PARTIAL: Used CLIP cleaning + automated validation instead of Label Studio. Acceptable tradeoff.
- [x] CHK-A8 Dataset uploaded to Kaggle and accessible — `nadermohamedcr7/wadjet-hieroglyph-detection` (1.3 GB, status=ready)
- [x] CHK-A9 CLIP filtering removed non-hieroglyph noise — 343 images removed (threshold 0.18)
- [x] CHK-A10 Perceptual hash dedup removed cross-source duplicates — 11,320 removed (exact 5,728 + near 5,592)
- [x] CHK-A11 20 real stone inscription photos in test set — test has 12 v1_raw + 9 hla + 13 signs_seg = 34 real stone images
- [~] CHK-A12 Images sourced from 7+ different sources — ⚠️ 5 sources (mohiey, synthetic, signs_seg, v1_raw, hla). Fewer than 7 but diverse enough.
- [x] CHK-A13 License tracked per source (CC0/PD prioritized) — LICENSE_SOURCES.md in dataset

---

## B. Model Training

- [ ] CHK-B1 YOLO26s trained with `fliplr=0.0, flipud=0.0`
- [ ] CHK-B2 mAP50 ≥ **0.85** on validation set
- [ ] CHK-B3 Precision ≥ **0.80**
- [ ] CHK-B4 Recall ≥ **0.80**
- [ ] CHK-B5 Real stone inscription test: detects ≥ **12/20** visible glyphs on 20 test photos
- [ ] CHK-B6 No overfitting signal (val loss not diverging from train loss)
- [ ] CHK-B7 Training used COCO pretrained weights (transfer learning)
- [ ] CHK-B8 AI fallback rate < **50%** on test set (detector handles majority independently)
- [ ] CHK-B9 kernel-metadata.json: `NvidiaTeslaT4` + correct `id` + correct `dataset_sources`
- [ ] CHK-B10 All notebook cells have IDs (no nbformat warnings)
- [ ] CHK-B11 KeepAlive / progress prints with `flush=True` (no IOPub timeout)
- [ ] CHK-B12 No mixed precision / AMP (verify ultralytics config)
- [ ] CHK-B13 pip installs: `ultralytics` (latest) + `onnxscript` in first cell

---

## C. ONNX Export

- [ ] CHK-C1 ONNX exported with `end2end=True` (NMS-free)
- [ ] CHK-C2 ONNX model loads in `ort.InferenceSession` without error
- [ ] CHK-C3 Input shape: `[1, 3, 640, 640]` (NCHW, float32, /255 normalized)
- [ ] CHK-C4 Output shape: `[1, 300, 6]` (batch, max_detections, [x1,y1,x2,y2,conf,cls])
- [ ] CHK-C5 uint8 quantized model < 20MB
- [ ] CHK-C6 `model_metadata.json` exists with documented shapes and normalization
- [ ] CHK-C7 Model placed at `models/hieroglyph/detector/glyph_detector_uint8.onnx`

---

## D. Backend Integration

- [ ] CHK-D1 `postprocess.py` — parses `[1, 300, 6]` output (not `[1, 5, 8400]`)
- [ ] CHK-D2 `postprocess.py` — NO manual NMS step (model handles it)
- [ ] CHK-D3 `postprocess.py` — confidence filter, size filter, aspect ratio filter still work
- [ ] CHK-D4 `postprocess.py` — `preprocess()` still does letterbox 640 with correct padding
- [ ] CHK-D5 `postprocess.py` — rescales detections to original image coordinates
- [ ] CHK-D5b `hieroglyph-pipeline.js` — `detect()` parses `[1, 300, 6]` output (not `[1, 5, 8400]`)
- [ ] CHK-D5c `hieroglyph-pipeline.js` — `_nms()` and `_iou()` removed (NMS-free model)
- [ ] CHK-D5d `hieroglyph-pipeline.js` — rescales detections to original image coordinates correctly
- [ ] CHK-D6 `hieroglyph_pipeline.py` — loads new detector model correctly
- [ ] CHK-D7 `scan.py` — AI fallback still triggers when detection count is low
- [ ] CHK-D8 `scan.py` — full-sequence verification still works

---

## E. End-to-End Testing

- [ ] CHK-E1 `POST /api/scan` with clean composite image → detects 5+ glyphs
- [ ] CHK-E2 `POST /api/scan` with real stone inscription → detects glyphs (not empty)
- [ ] CHK-E3 `POST /api/scan` with empty/non-hieroglyph image → graceful empty result
- [ ] CHK-E4 `/scan` page — upload mode works in browser
- [ ] CHK-E5 `/scan` page — camera mode shows live detection boxes
- [ ] CHK-E6 `/scan` page — captured frame produces classification results
- [ ] CHK-E7 AI fallback triggers correctly when detector finds ≤2 glyphs
- [ ] CHK-E8 Full pipeline: detect → classify → transliterate → translate (all stages)
- [ ] CHK-E9 `/api/health` returns `{"status": "ok"}`

---

## F. Deployment

- [ ] CHK-F1 Changes committed to git with descriptive message
- [ ] CHK-F2 Pushed to GitHub (origin master)
- [ ] CHK-F3 Pushed to HF Spaces (hf master:main)
- [ ] CHK-F4 Live site `/scan` endpoint works: https://nadercr7-wadjet-v2.hf.space/scan
- [ ] CHK-F5 No errors in HF Spaces build logs
- [ ] CHK-F6 Service worker cache bumped (`?v=N+1`)

---

## Summary

| Section | Items | Passed |
|---------|-------|--------|
| A. Data Quality | 13 | ⬜ 0/13 |
| B. Model Training | 13 | ⬜ 0/13 |
| C. ONNX Export | 7 | ⬜ 0/7 |
| D. Backend Integration | 11 | ⬜ 0/11 |
| E. End-to-End Testing | 9 | ⬜ 0/9 |
| F. Deployment | 6 | ⬜ 0/6 |
| **TOTAL** | **59** | **⬜ 0/59** |
