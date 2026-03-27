# Wadjet v2 — Detector Rebuild Progress Tracker

> **Total: 77 tasks across 3 phases**
> **Progress: D-PREP COMPLETE, D-TRAIN & D-INTEGRATE pending**

---

## Phase D-PREP: Data Preparation — ✅ COMPLETE

### D1: V1 Raw Image Re-Annotation (DONE)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D1.1 | Set up GroundingDINO (transformers) | ✅ | Installed in `scripts/dataprep-env/` |
| D1.2 | Set up Label Studio | ⏭️ | Skipped — used auto-annotations directly |
| D1.3 | Write `annotate_with_gdino.py` | ✅ | Fixed box_threshold API, MAX_DIM=1200, resume |
| D1.4 | Run GroundingDINO on V1 images | ✅ | ~229 usable (CPU, ~65s/image) |
| D1.5 | Import proposals into Label Studio | ⏭️ | Skipped |
| D1.6 | Verify/correct V1 annotations | ⏭️ | Used CLIP cleaning + validation instead |

### D2: HuggingFace Datasets (DONE)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D2.1 | Request HLA dataset access | ✅ | Via Kaggle download |
| D2.2 | Download HLA dataset | ✅ | Downloaded from Kaggle |
| D2.3 | Write `convert_hla_to_yolo.py` | ✅ | COCO → YOLO converter |
| D2.4 | Convert HLA annotations | ✅ | Limited yield after filtering |
| D2.5 | Download Signs Segmentation | ✅ | Via Kaggle |
| D2.6 | Convert Signs Segmentation | ✅ | 289 images → single-class YOLO |

### D3: Museum Scraping (PARTIAL — enough data from other sources)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D3.1 | Met Museum spider | ✅ | REST API, CC0, 338 images scraped |
| D3.2 | British Museum spider | ⏭️ | Skipped — had enough data |
| D3.3 | Wikimedia Commons spider | ✅ | MediaWiki API, 121 images scraped |
| D3.4-D3.9 | Other museum spiders | ⏭️ | Skipped — had enough data |
| D3.10 | Run spiders | ✅ | Met (338) + Wiki (121). Not annotated (CPU too slow) |
| D3.11 | Deduplicate | ✅ | 11,320 duplicates removed in merge |
| D3.12 | Write CLIP filter | ✅ | CLIP scoring with positive/negative prompts |
| D3.13 | Run CLIP filter | ✅ | 343 non-hieroglyph images removed (threshold 0.18) |
| D3.14 | Annotate filtered scraped | ⏭️ | Scraped images not included (no annotations) |

### D4: Search Existing Datasets (DONE)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D4.1 | Search Kaggle datasets | ✅ | Found mohiey (32,362 YOLO), assemelqirsh, others |
| D4.2 | Search HuggingFace Hub | ✅ | Found HLA + Signs Segmentation |
| D4.3 | Download + convert | ✅ | mohiey → single-class (8,650 after dedup) = 84% of final dataset |

### D5: Synthetic Composites (DONE)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D5.1 | Write `generate_synthetic_composites.py` | ✅ | Grid-based glyph placement, color matching, edge blend |
| D5.2 | Collect stone textures (~200) | ✅ | Generated 200 via `create_stone_textures.py` (12 palettes, fractal noise) |
| D5.3 | Generate composites | ✅ | 1,500 generated → 951 after dedup. 9% of final dataset |

### D6: Roboflow (SKIPPED)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D6.1 | Download Roboflow dataset | ⏭️ | Skipped — had enough data |
| D6.2 | Convert to single-class | ⏭️ | Skipped |

### D7: CLIP-Filtered Web Images (SKIPPED)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D7.1 | Scrape web images | ⏭️ | Skipped — had enough from Kaggle + synthetic |
| D7.2 | CLIP filter | ⏭️ | Applied to merged dataset instead |
| D7.3 | Annotate filtered images | ⏭️ | Skipped |

### D8: Merge, Split & Upload (DONE except upload)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D8.1 | Write `merge_detection_datasets.py` | ✅ | pHash dedup, source-stratified splits |
| D8.2 | Write `validate_dataset.py` | ✅ | Full validation with previews |
| D8.3 | Split train/val/test | ✅ | train 7,655 / val 2,051 / test 605 |
| D8.4 | Ensure real stone in test | ✅ | Source-stratified across v1_raw, signs_seg, hla |
| D8.5 | Create `hieroglyph_det.yaml` | ✅ | `data/detection/merged/data.yaml` |
| D8.6 | Create `dataset-metadata.json` | ✅ | Kaggle metadata ready |
| D8.7 | Run `validate_dataset.py` | ✅ | All CHK-A1–A13 passed, CLIP cleaned, 6/6 final sweep PASS |
| D8.8 | Upload to Kaggle | ✅ | Uploaded: `nadermohamedcr7/wadjet-hieroglyph-detection` (1.3 GB, status=ready) |

**Gate**: ✅ Dataset ready: **10,311 images** (1.25 GB), YOLO format verified, CLIP-cleaned, source-stratified.

**Final dataset composition:**
| Source | Images | % |
|--------|--------|---|
| mohiey_single | 8,650 | 84% |
| synthetic | 951 | 9% |
| signs_seg | 289 | 3% |
| v1_raw | 229 | 2% |
| hla_annotated | 192 | 2% |
| **Total** | **10,311** | **100%** |

---

## Phase D-TRAIN: Model Training (0/15) — NEXT

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T1.1 | Create Kaggle notebook | ⬜ | `planning/model-rebuild/pytorch/detector/hieroglyph_detector.ipynb` |
| T1.2 | Create kernel-metadata.json | ⬜ | NvidiaTeslaT4, correct id + dataset_sources |
| T1.3 | Apply all 36 Kaggle fixes | ⬜ | See MASTER_PLAN §2.1 |
| T2.1 | Push to Kaggle | ⬜ | Requires D8.8 (dataset upload) first |
| T2.2 | Monitor training | ⬜ | |
| T2.3 | Download outputs | ⬜ | |
| T3.1 | Evaluate metrics | ⬜ | mAP50 ≥ 0.85 |
| T3.2 | Real stone test (20 photos) | ⬜ | ≥ 12/20 |
| T3.3 | Measure AI fallback rate | ⬜ | < 50% |
| T3.4 | Iterate if needed | ⬜ | |
| T4.1 | Export ONNX (end2end) | ⬜ | |
| T4.2 | Quantize uint8 | ⬜ | |
| T4.3 | Validate ONNX shape | ⬜ | [1, 300, 6] |
| T4.4 | Save model_metadata.json | ⬜ | |
| T4.5 | Download to local | ⬜ | |

**Gate**: ⬜ mAP50 ≥ 0.85, real stone ≥ 12/20, ONNX uint8 < 20MB, output [1,300,6], fallback < 50%

---

## Phase D-INTEGRATE: Backend Integration (0/14)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| I1.1 | Update postprocess.py output parser | ⬜ | [1,300,6] not [1,5,8400] |
| I1.2 | Remove NMS code | ⬜ | Model handles NMS internally |
| I1.3 | Keep preprocess() | ⬜ | Letterbox 640 still needed |
| I1.4 | Update config defaults | ⬜ | |
| I2.1 | Replace detector model | ⬜ | |
| I2.2 | Add model_metadata.json | ⬜ | |
| I3.1 | Test scan API locally | ⬜ | |
| I3.2 | Verify AI fallback | ⬜ | |
| I3.3 | Test clean composites | ⬜ | |
| I3.4 | Test camera mode | ⬜ | |
| I4.1 | Commit to git | ⬜ | |
| I4.2 | Push to GitHub | ⬜ | |
| I4.3 | Push to HF Spaces | ⬜ | |
| I4.4 | Verify live deployment | ⬜ | |

**Gate**: ⬜ Scan page works end-to-end on live site

---

## Timeline Log

| Date | Session | Work Done |
|------|---------|-----------|
| 2026-03-24 | 16 | Research complete, architecture decided (YOLO26s), all planning docs created. Tools inventory. dataprep-env created. |
| 2026-03-24 | 18 | D-PREP executed: Downloaded 4 Kaggle datasets, scraped Met+Wiki, GDino annotations, synthetic composites (200 textures + 1,500 composites). Merged 21,974 → 10,654 after dedup → CLIP-cleaned 343 → **10,311 final images**. Split: train 7,655 / val 2,051 / test 605. All CHK-A1–A13 passed. Dataset READY at `data/detection/merged/` (1.25 GB). |
| 2026-03-24 | 18 | UI fixes: Chat scroll (data-lenis-prevent), rich markdown formatting, G24 dictionary, ONNX high-confidence protection, AI fallback ONNX re-classification, 30% hybrid threshold. Commits: 5271a79, 79f8b14, 2b3d1f2, 6b2936a — all pushed to HF. |
| | | **Next: Upload dataset to Kaggle (D8.8) → Phase D-TRAIN** |
