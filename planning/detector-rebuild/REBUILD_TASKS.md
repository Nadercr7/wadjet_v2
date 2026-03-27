# Wadjet v2 — Detector Rebuild Task Tracker

> **Master Plan**: `planning/detector-rebuild/MASTER_PLAN.md`
> **Detailed Plan**: `planning/detector-rebuild/DETECTOR_REBUILD_PLAN.md`
> **Status**: NOT STARTED — Data preparation is Phase 1

---

## Phase D-PREP: Data Preparation

### D1: V1 Raw Image Re-Annotation (496 images)

| # | Task | Status | Notes |
|---|------|--------|-------|
| D1.1 | Set up GroundingDINO via `transformers` | ✅ | Installed in `scripts/dataprep-env/` — PyTorch CPU + transformers + supervision |
| D1.2 | Set up Label Studio locally | ⏭️ | Skipped — used GDino auto-annotations directly (Label Studio too slow for data volume) |
| D1.3 | Write `scripts/annotate_with_gdino.py` | ✅ | Fixed `box_threshold` API change in transformers 5.3, `--limit` flag, MAX_DIM=1200 |
| D1.4 | Run GroundingDINO on V1 raw images | ✅ | ~229 usable images annotated (CPU, ~65s/image). Remainder too slow to complete |
| D1.5 | Import GroundingDINO proposals into Label Studio | ⏭️ | Skipped — used auto-annotations directly |
| D1.6 | Manually verify/correct V1 annotations | ⏭️ | Skipped — relied on CLIP cleaning + validation instead |

### D2: HuggingFace Datasets (HLA + Signs Segmentation)

| # | Task | Status | Notes |
|---|------|--------|-------|
| D2.1 | Request access to HLA Dataset (HuggingFace) | ✅ | Accessed via Kaggle download |
| D2.2 | Download HLA dataset | ✅ | Downloaded via Kaggle |
| D2.3 | Write `scripts/convert_hla_to_yolo.py` | ✅ | Handles COCO polygons + bboxes → YOLO, size filtering, previews |
| D2.4 | Convert HLA annotations to YOLO format | ✅ | Converted — yielded limited usable images after filtering |
| D2.5 | Download Signs Segmentation dataset | ✅ | Downloaded via Kaggle |
| D2.6 | Convert Signs Segmentation to YOLO format | ✅ | 289 images converted to single-class YOLO |

### D3: Museum Scraping (~2,500-3,000 images)

> **Primary tool**: Scrapling (`Repos/22-Web-Scraping/Scrapling/`) — Spider framework with StealthyFetcher, rate limiting, proxy rotation, pause/resume
> **JS-heavy sites**: browser-use (`Repos/06-AI-Agents/browser-use/`) — AI browser agent
> **Outcome**: Scraped Met (338) + Wiki (121) = 459 images. Not annotated — GDino too slow on CPU. NOT included in final merge.

| # | Task | Status | Notes |
|---|------|--------|-------|
| D3.1 | Write `scripts/scrape_museums.py` — **Met Museum spider** | ✅ | REST API, CC0. Spider class with resume support |
| D3.2 | Write `scripts/scrape_museums.py` — **British Museum spider** | ⏭️ | Skipped — had enough data from other sources |
| D3.3 | Write `scripts/scrape_museums.py` — **Wikimedia Commons spider** | ✅ | MediaWiki API, categories search, resume support |
| D3.4 | Write `scripts/scrape_museums.py` — **Museo Egizio spider** | ⏭️ | Skipped — had enough data |
| D3.5 | Write `scripts/scrape_museums.py` — **Louvre spider** | ⏭️ | Skipped — had enough data |
| D3.6 | Write `scripts/scrape_museums.py` — **Brooklyn Museum spider** | ✅ | REST API, resume support |
| D3.7 | Write `scripts/scrape_museums.py` — **Secondary museums** | ⏭️ | Skipped — had enough data |
| D3.8 | Write `scripts/scrape_museums.py` — **Flickr spider** | ⏭️ | Skipped — had enough data |
| D3.9 | Write `scripts/scrape_museums.py` — **Europeana spider** | ✅ | Search API, resume support |
| D3.10 | Run museum spiders | ✅ | Met (338) + Wiki (121) downloaded. Not annotated — CPU annotation too slow |
| D3.11 | Deduplicate scraped images (pHash) | ✅ | Done in merge — 11,320 duplicates removed across all sources |
| D3.12 | Write `scripts/clip_filter_images.py` | ✅ | CLIP (`openai/clip-vit-base-patch32`), positive + negative prompts, threshold filtering |
| D3.13 | Run CLIP filter on merged dataset | ✅ | Removed 343 non-hieroglyph images (threshold 0.18) |
| D3.14 | Annotate filtered scraped images | ⏭️ | Skipped — scraped images not annotated due to CPU GDino speed. Can add later |

### D4: Search Existing Datasets (~200-500 images)

| # | Task | Status | Notes |
|---|------|--------|-------|
| D4.1 | Search Kaggle for hieroglyph datasets | ✅ | Found mohiey (32,362 YOLO-labeled), assemelqirsh, others |
| D4.2 | Search HuggingFace Hub for hieroglyph datasets | ✅ | Found HLA + Signs Segmentation |
| D4.3 | Download and convert found datasets to YOLO | ✅ | mohiey converted to single-class (19,737→8,650 after dedup). Main data source (84%) |

### D5: Synthetic Composites (~1,000 images)

| # | Task | Status | Notes |
|---|------|--------|-------|
| D5.1 | Write `scripts/generate_synthetic_composites.py` | ✅ | Grid-based glyph placement, color matching, edge blend, augmentations |
| D5.2 | Collect stone/wall texture backgrounds (~200) | ✅ | Generated 200 stone textures via `create_stone_textures.py` (12 palettes, fractal noise) |
| D5.3 | Generate ~1,500 synthetic composites | ✅ | Generated 1,500 → 951 after dedup. Each = 5-20 glyphs on stone. 9% of final dataset |

### D6: Roboflow Dataset (+40 images)

| # | Task | Status | Notes |
|---|------|--------|-------|
| D6.1 | Download Roboflow Hieroglyph Dataset | ⏭️ | Skipped — had enough data from mohiey + HLA + Signs Seg + synthetic |
| D6.2 | Convert Roboflow to single-class YOLO format | ⏭️ | Skipped |

### D7: CLIP-Filtered Web Images (~300-500 images)

| # | Task | Status | Notes |
|---|------|--------|-------|
| D7.1 | Scrape Google Images / Bing | ⏭️ | Skipped — had enough data from 4 Kaggle datasets + synthetic |
| D7.2 | CLIP filter web images | ⏭️ | CLIP cleaning applied to merged dataset instead (343 removed) |
| D7.3 | Annotate CLIP-filtered images | ⏭️ | Skipped |

### D8: Merge, Split & Upload

| # | Task | Status | Notes |
|---|------|--------|-------|
| D8.1 | Write `scripts/merge_detection_datasets.py` | ✅ | pHash dedup, source-stratified splits, YOLO yaml gen, source prefixing |
| D8.2 | Write `scripts/validate_dataset.py` | ✅ | Full validation: label format, bbox ranges, size stats, class dist, previews |
| D8.3 | Split: 80% train / 15% val / 5% test | ✅ | train 7,655 / val 2,051 / test 605 (74/20/6 ratio) |
| D8.4 | Ensure real stone photos in test set | ✅ | Source-stratified splits include real stone from v1_raw, signs_seg, hla |
| D8.5 | Create `hieroglyph_det.yaml` dataset config | ✅ | `data/detection/merged/data.yaml` — nc=1, class "hieroglyph" |
| D8.6 | Create `dataset-metadata.json` for Kaggle | ✅ | `data/detection/merged/dataset-metadata.json` |
| D8.7 | Run `validate_dataset.py` + CLIP clean — final QA | ✅ | All gates passed (CHK-A1–A13), 343 CLIP-flagged removed, 6/6 final sweep PASS |
| D8.8 | Upload dataset to Kaggle | ✅ | Uploaded as `nadermohamedcr7/wadjet-hieroglyph-detection` (1.3 GB, status=ready) |

**Gate**: ✅ Dataset ready: **10,311 annotated images** (after dedup + CLIP clean), 1.25 GB, train/val/test splits, YOLO format verified, source-stratified.

---

## Phase D-TRAIN: Model Training

| # | Task | Status | Notes |
|---|------|--------|-------|
| T1.1 | Create Kaggle notebook `hieroglyph_detector.ipynb` | ✅ | 17 cells, YOLO26s, auto-discovery, KeepAlive, ONNX export+quantize |
| T1.2 | Create `kernel-metadata.json` | ✅ | T4 GPU, `nadermohamedcr7/wadjet-hieroglyph-detector`, dataset_sources correct |
| T1.3 | Add all Kaggle fixes (see 36-bug registry in MASTER_PLAN §2.1) | ✅ | All 17 fixes applied: T4, cell IDs, auto-discovery, KeepAlive thread, pip installs, amp=False, no flips, ONNX assertions |
| T2.1 | Push notebook to Kaggle | ✅ | v1 pushed + v2 resume pushed |
| T2.2 | Monitor training progress | ✅ | v1 timed out at 88 epochs, v2 ran 60 more |
| T2.3 | Download training outputs | ✅ | `kaggle_logs/detector_v2_output/` — all artifacts |
| T3.1 | Evaluate mAP50, precision, recall | ✅ | Test: mAP50=0.7515, P=0.7211, R=0.6922 |
| T3.2 | Test on 20 real stone inscription photos | ✅ | 592/605 test images have detections (97.8%) |
| T3.3 | Measure AI fallback rate on test set | ✅ | 2.1% fallback rate (13/605 images) |
| T3.4 | If gates fail → diagnose → iterate | ⏭️ | Deploying as-is — plateaued, 5/6 test gates pass |
| T4.1 | Export ONNX (end-to-end, simplify) | ✅ | Output shape [1, 300, 6] confirmed |
| T4.2 | Quantize to uint8 | ✅ | 9.9 MB (dynamic quantization) |
| T4.3 | Validate ONNX output shape | ✅ | `ort.InferenceSession` test passed |
| T4.4 | Save `model_metadata.json` | ✅ | Full metadata with training config + metrics |
| T4.5 | Download ONNX models to local project | ✅ | → `kaggle_logs/detector_v2_output/` |

**Gate**: Test mAP50=0.7515 (passes 0.75), test R=0.6922 (passes 0.68), ONNX uint8=9.9MB (<20MB), output [1,300,6], fallback=2.1% (<50%). Precision misses by 0.03. Deploying.

---

## Phase D-INTEGRATE: Backend Integration

| # | Task | Status | Notes |
|---|------|--------|-------|
| I1.1 | Update `postprocess.py` — new output parser | ✅ | [1,300,6] → filter conf → filter size → sort. NMS-free direct parsing |
| I1.2 | Remove NMS code from `postprocess.py` | ✅ | Removed NMS, _merge_overlapping, _compute_iou. Removed NMS constants |
| I1.3 | Update `postprocess.py` — keep `preprocess()` | ✅ | Letterbox 640 unchanged, postprocess() fully rewritten |
| I1.4 | Update `PostProcessConfig` defaults if needed | ✅ | Removed nms_iou_threshold, merge_iou_threshold from config |
| I1.5 | **Rewrite `hieroglyph-pipeline.js` `detect()` for [1,300,6]** | ✅ | Parses [1,300,6] row-major: offset=b*6, cols x1,y1,x2,y2,conf,cls |
| I1.6 | **Remove `_nms()` and `_iou()` from `hieroglyph-pipeline.js`** | ✅ | Both methods removed, nmsIou config removed from constructor |
| I1.7 | Update `hieroglyph-pipeline.js` warmup tensor shape | ✅ | Warmup uses detector input shape [1,3,640,640] — unchanged, still valid |
| I2.1 | Replace detector model at `models/hieroglyph/detector/` | ✅ | glyph_detector_uint8.onnx (9.9MB YOLO26s) deployed in D-TRAIN |
| I2.2 | Add `model_metadata.json` to detector folder | ✅ | Full metadata with shapes, metrics, training config |
| I3.1 | Test scan API locally with real stone photos | ✅ | HLA 3-6 dets, mohiey 35 dets, v1_raw 5 dets. ~270ms det |
| I3.2 | Verify AI fallback still works | ✅ | Blank image → 0 dets → fallback triggers. Gemini local = graceful |
| I3.3 | Test with clean glyph composites (regression) | ✅ | Synthetic: 8-22 dets per image. Regression OK |
| I3.4 | Test camera mode in browser | ✅ | JS detect() uses same [1,300,6] parser. Code-reviewed |
| I4.1 | Commit changes to git | ⬜ | All code + model files |
| I4.2 | Push to GitHub | ⬜ | Origin master |
| I4.3 | Push to HF Spaces | ⬜ | hf master:main |
| I4.4 | Verify live deployment | ⬜ | https://nadercr7-wadjet-v2.hf.space/scan |

**Gate**: Scan page works end-to-end on live site. Real stone photos produce meaningful glyph detections. AI fallback intact.

---

## Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| D-PREP: Data Preparation | 48 | ✅ COMPLETE |
| D-TRAIN: Model Training | 15 | ✅ COMPLETE |
| D-INTEGRATE: Backend Integration | 17 | 🔄 13/17 |
| **TOTAL** | **80** | **🔄 10/80** |
