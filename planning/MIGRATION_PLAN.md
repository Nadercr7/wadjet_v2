# Wadjet — Clean Migration Plan

> **Goal**: COPY the working Wadjet v2 project to a clean folder `D:\Personal attachements\Projects\Wadjet\`,
> with a complete archive + journey file, then verify everything works and push to GitHub + HuggingFace.
>
> **Created**: 2026-03-27
> **Status**: READY FOR EXECUTION
>
> ## ⚠️ CRITICAL SAFETY RULE
> **COPY everything. NEVER move or delete from `Final_Horus/`.**
> The old folder MUST remain fully functional and untouched at all times.
> Test EVERYTHING in the new location BEFORE any git push.
> Only delete `Final_Horus/` after explicit user approval (Phase 7).
> If ANY step fails → STOP and report. Do NOT fix by modifying the old folder.

---

## Table of Contents

1. [Situation Analysis](#1-situation-analysis)
2. [Migration Steps](#2-migration-steps)
3. [File-by-File Inventory](#3-file-by-file-inventory)
4. [Path Reference Updates](#4-path-reference-updates)
5. [Archive Structure](#5-archive-structure)
6. [JOURNEY.md Outline](#6-journeymd-outline)
7. [Git Strategy](#7-git-strategy)
8. [Data Reference Catalog](#8-data-reference-catalog)
9. [Verification Checklist](#9-verification-checklist)
10. [Risk Mitigations](#10-risk-mitigations)

---

## 1. Situation Analysis

### Current State

```
D:\Personal attachements\Projects\Final_Horus\          (~95 GB total)
├── [ROOT FILES] — Original "Horus AI" project            (~350 MB)
│   ├── app.py, class_labels.py, llm_utils.py, model_utils.py, t.py
│   ├── last_model_bgd.keras (254 MB), inspect_model.py
│   ├── HORUS AI .mp4 (93 MB video)
│   ├── Horus-AI.pdf (1.9 MB), Horus-AI-Guardian...pdf (669 KB)
│   ├── COMPREHENSIVE_README.md, TECHNICAL_DOCUMENTATION.md, PROJECT_DIAGRAMS.md
│   ├── README.md, requirements.txt, gitattributes, UPGRADE_ANALYSIS.md
│   ├── static/, templates/, uploads/ — Flask app dirs
│   └── model_test/ — test images (3.3 MB)
│
├── horus_env/ — Original Python venv (11 MB)
├── .hf_cache/ — HuggingFace cache (87 MB)
│
├── Wadjet/ — V1 (65 GB)
│   ├── data/ (53 GB) — training datasets + FAISS + corpus
│   ├── hieroglyph_model/ (7.5 GB) — training artifacts
│   ├── model/ (865 MB) — TF.js + Keras models
│   ├── .venv/ (3.7 GB), .venv-labelstudio/ (716 MB)
│   ├── app/ (42 MB) — FastAPI + Jinja2 (the v1 application)
│   ├── scripts/, tests/, planning/, docs/, benchmarks/, evaluation/
│   └── site/, docs-site/, wandb/, logs/
│
└── Wadjet-v2/ — V2 (30.5 GB) ← THE WORKING PROJECT
    ├── app/ (2 MB) — THE APPLICATION CODE
    ├── models/ (639 MB) — ML models (only ~30 MB actually used in prod)
    ├── data/ (27 GB) — training datasets (NOT needed for runtime)
    │   ├── detection/ (10.9 GB) -- training data
    │   ├── landmark_classification/ (15 GB) — training data
    │   ├── hieroglyph_classification/ (1 GB) — training data
    │   ├── embeddings/ (96 MB) — FAISS index (NEEDED for runtime)
    │   ├── metadata/ (6.6 MB) — NEEDED
    │   ├── text/ (0.2 MB) — NEEDED
    │   ├── translation/ (6.2 MB) — NEEDED
    │   ├── reference/ (6.6 MB) — Gardiner reference images
    │   ├── expanded_sites.json (1 MB) — NEEDED
    │   └── landmark_enrichment_cache.json — NEEDED
    ├── planning/ (1 MB) — ALL planning docs
    ├── scripts/ (1.1 GB incl. dataprep-env/) — utility scripts
    ├── kaggle_logs/ (769 MB) — training run logs
    ├── tmp_kaggle_output/ (217 MB) — temp Kaggle outputs
    ├── tmp_kaggle_hiero/ (36 MB) — temp
    ├── tmp_pull_test/ (empty)
    └── .venv/ (not measured, excluded)
```

### What Actually Needs to Run the App
- `app/` — 2 MB (all Python + templates + static + JS + CSS)
- `models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx` — ~1.8 MB
- `models/hieroglyph/classifier/hieroglyph_classifier.onnx` — ~6.5 MB
- `models/hieroglyph/classifier/model.json` + shards — ~20 MB (TF.js browser classifier)
- `models/hieroglyph/classifier/label_mapping.json`, `model_metadata.json`
- `models/hieroglyph/detector/glyph_detector_uint8.onnx` — ~10 MB
- `models/hieroglyph/detector/model_metadata.json`
- `models/hieroglyph/label_mapping.json`
- `models/landmark/landmark_classifier_uint8.onnx` — ~4.2 MB
- `models/landmark/landmark_label_mapping.json`, `model_metadata.json`
- `data/embeddings/` — 96 MB (FAISS index for RAG translation)
- `data/metadata/` — 6.6 MB (Gardiner data JSON files)
- `data/text/` — 0.2 MB (landmark text descriptions)
- `data/translation/` — 6.2 MB (translation corpus)
- `data/expanded_sites.json` — 1 MB (260+ heritage sites)
- `data/landmark_enrichment_cache.json` — enrichment cache
- Config files: `.env`, `requirements.txt`, `package.json`, `pyproject.toml`, etc.
- `CLAUDE.md`, `README.md`

**Total runtime footprint: ~150 MB** (from 30 GB!)

### Git State
- **Repo**: https://github.com/Nadercr7/wadjet_v2.git
- **HF**: https://huggingface.co/spaces/nadercr7/wadjet-v2
- **Active branch**: `clean-main` (HEAD at `0c9a823`)
- **Other branch**: `master` (old, at `165d48c`)
- **Remotes**: `origin` (GitHub), `hf` (HuggingFace)
- **Both synced** at `0c9a823`
- **LFS tracked**: *.onnx, *.ttf, *.index, *.woff*, images — in `.gitattributes`
- **37 commits** in history

---

## 2. Migration Steps

### Phase 0: README Push (BEFORE migration — push NOW to current repo)

| Step | Action | Detail |
|------|--------|--------|
| 0.1 | **README already updated** | New README.md is written — Black & Gold, no AI traces, HTML badges, proper sections |
| 0.2 | **Commit README** | `git add README.md && git commit -m "docs: project README overhaul"` |
| 0.3 | **Push to GitHub** | `git push origin clean-main` — updates the GitHub page immediately |
| 0.4 | **Push to HF** | `git push hf clean-main:main` — updates HuggingFace space page |

### Phase 1: Preparation (No Destructive Actions)

| Step | Action | Detail |
|------|--------|--------|
| 1.1 | **Create target directory** | `D:\Personal attachements\Projects\Wadjet\` |
| 1.2 | **Copy .git/** | Copy entire `.git/` folder to preserve full history, remotes, branches, LFS |
| 1.3 | **Copy runtime app files** | `app/`, config files (see §3 inventory) |
| 1.4 | **Copy runtime models** | Only the ONNX + TF.js models actually used (see §3) |
| 1.5 | **Copy runtime data** | Only embeddings, metadata, text, translation, expanded_sites, enrichment_cache, reference |
| 1.6 | **Copy planning/** | ALL planning files as-is |
| 1.7 | **Copy scripts/** | Active scripts only (NOT dataprep-env/, archive/) |
| 1.8 | **Copy CLAUDE.md, README.md** | Root config/docs |
| 1.9 | **Create .venv** | Fresh venv in new location |
| 1.10 | **npm install** | Fresh node_modules for TailwindCSS |

### Phase 2: Archive Creation

| Step | Action | Detail |
|------|--------|--------|
| 2.1 | **Create `archive/` folder** | Under new Wadjet root |
| 2.2 | **Original Horus** | Copy root files from Final_Horus (app.py, PDFs, video, keras model, docs, model_test/) |
| 2.3 | **V1 reference** | Copy key V1 files: app/core/*.py, app/static/js/*.js, planning/, app/templates/scan.html, app/templates/explore.html |
| 2.4 | **V2 training metadata** | Create DATA_CATALOG.md with dataset locations (Kaggle, local descriptions), NOT the actual images |
| 2.5 | **V2 Kaggle logs** | Copy kaggle_logs/ summary files (NOT full checkpoints — just logs + final results) |
| 2.6 | **V2 old model versions** | Copy models/hieroglyph/classifier/_backup_v1/, models/hieroglyph/classifier_keras/, models/landmark/saved_model/ metadata, tmp_kaggle_output/classifier_v2/ results |
| 2.7 | **V2 old scripts** | Copy scripts/archive/ as-is |
| 2.8 | **V2 planning history** | Already in planning/ (archive/, rebuild/, detector-rebuild/, hieroglyph-rebuild/, model-rebuild/) |
| 2.9 | **Session log** | Already in planning/archive/SESSION_LOG.md |
| 2.10 | **archive/README.md** | Create index explaining everything in the archive |

### Phase 3: JOURNEY.md

| Step | Action | Detail |
|------|--------|--------|
| 3.1 | **Write JOURNEY.md** | Full narrative from Horus → V1 → V2, based on SESSION_LOG.md + repo memory + planning docs |
| 3.2 | **Include all sessions** | Sessions 1-22, every feature, every decision, every model rebuild |
| 3.3 | **Include data references** | Where datasets are (Kaggle), what models were trained, what metrics achieved |
| 3.4 | **Include architecture evolution** | Flask → FastAPI, Keras → PyTorch → ONNX, 261 → 10,311 detection images |

### Phase 4: Path Reference Updates

| Step | Action | Detail |
|------|--------|--------|
| 4.1 | **Update CLAUDE.md** | `Final_Horus\Wadjet-v2` → `Wadjet`, update V1 reference to archive |
| 4.2 | **Update planning docs** | All `cd "D:\...\Final_Horus\Wadjet-v2"` → `cd "D:\...\Wadjet"` |
| 4.3 | **Update scripts** | `copy_assets.py` V1/V2 paths (mark as ARCHIVE — no longer needed) |
| 4.4 | **Update other scripts** | Any that reference `Final_Horus\Wadjet\` for V1 data |
| 4.5 | **Note**: Runtime code has NO path issues | app/, templates, JS, CSS — all use relative paths. Only scripts + planning docs have absolute paths. |

### Phase 5: LOCAL Testing (BEFORE any push)

| Step | Action | Detail |
|------|--------|--------|
| 5.1 | **CSS builds** | `npm run build` → dist/styles.css |
| 5.2 | **Server starts** | `uvicorn app.main:app --reload --port 8000` → no errors |
| 5.3 | **All routes work** | Visit /, /hieroglyphs, /landmarks, /scan, /dictionary, /write, /explore, /chat |
| 5.4 | **API health** | `GET /api/health` → 200 with model status |
| 5.5 | **Dictionary works** | Categories load, search works |
| 5.6 | **Write works** | Alpha mode "hello" → hieroglyphs |
| 5.7 | **Explore works** | 260+ landmarks load, search/filter works |
| 5.8 | **Archive intact** | All archive files readable, JOURNEY.md complete |
| 5.9 | **STOP if any test fails** | Do NOT proceed to Phase 6. Report the failure. |

### Phase 6: Git Commit + Push (ONLY after Phase 5 passes)

| Step | Action | Detail |
|------|--------|--------|
| 6.1 | **Verify git status** | `git status` in new folder — should show archive/ + JOURNEY.md as new |
| 6.2 | **Stage & commit** | `git add . && git commit -m "chore: clean migration + archive + JOURNEY.md"` |
| 6.3 | **Push to GitHub** | `git push origin clean-main` |
| 6.4 | **Push to HuggingFace** | `git push hf clean-main:main` |
| 6.5 | **Verify GitHub** | `git log origin/clean-main --oneline -1` matches local HEAD |
| 6.6 | **Verify HF** | `git log hf/main --oneline -1` matches local HEAD |

### Phase 7: Cleanup (ONLY AFTER FULL VERIFICATION — needs EXPLICIT user approval)

| Step | Action | Detail |
|------|--------|--------|
| 7.1 | **Report to user** | "Everything verified and pushed. Old folder is untouched. Want to rename/delete it?" |
| 7.2 | **WAIT for explicit approval** | Do NOT proceed without user saying yes |
| 7.3 | **Optional**: Rename | `Final_Horus` → `Final_Horus_ARCHIVED` as safety net |
| 7.4 | **Optional**: Delete | Only if user explicitly requests |

---

## 3. File-by-File Inventory

### ✅ COPY to new `Wadjet/` (runtime essential)

```
# Root config
.env
.env.example
.gitignore
.gitattributes
.github/                      (CI/CD workflows if any)
CLAUDE.md                     (→ update paths inside)
README.md
requirements.txt
package.json
pyproject.toml
render.yaml
Dockerfile
docker-compose.yml

# Application
app/                          (entire folder, 2 MB)
  __init__.py
  config.py
  dependencies.py
  main.py
  api/                        (all route modules)
  core/                       (all business logic)
  static/                     (css/, js/, fonts/, images/, dist/)
  templates/                  (all .html files)
  utils/

# Models (only production-used)
models/hieroglyph/
  label_mapping.json
  classifier/
    hieroglyph_classifier.onnx           (fp32, ~6.5 MB — LFS)
    hieroglyph_classifier_uint8.onnx     (quantized, ~1.8 MB — LFS)
    hieroglyph_classifier_uint8_v2.onnx  (v2 classifier — LFS)
    label_mapping.json
    model_metadata.json
    model.json + group1-shard*.bin       (TF.js browser model, ~20 MB — LFS)
  detector/
    glyph_detector_uint8.onnx            (~10 MB — LFS)
    model_metadata.json
models/landmark/
  landmark_classifier_uint8.onnx         (~4.2 MB — LFS)
  landmark_label_mapping.json
  model_metadata.json

# Runtime data
data/
  expanded_sites.json                    (260+ heritage sites)
  landmark_enrichment_cache.json
  embeddings/                            (FAISS index, 96 MB — LFS)
    corpus.index
    corpus_ids.json
  metadata/                              (Gardiner data, 6.6 MB)
    gardiner_*.json (26 files)
  text/                                  (landmark descriptions, 0.2 MB)
  translation/                           (corpus.jsonl, 6.2 MB)
  reference/                             (Gardiner reference images, 6.6 MB)

# Planning (ALL)
planning/                                (entire folder, 1 MB)

# Scripts (active only)
scripts/
  build_expanded_sites.py
  build_gardiner_data.py
  build_heritage_sites.py
  build_translation_index.py
  build_write_corpus.py
  copy_assets.py                         (→ mark as ARCHIVE reference)
  gen_unicode.py
  generate_heritage_data.py
  generate_landmark_details.py
  populate_images.py
  sites_data/                            (data helper modules)
```

### ❌ DO NOT COPY (available elsewhere or not needed)

```
# Training datasets (27 GB) — on Kaggle, see §8
data/detection/              (10.9 GB → Kaggle: wadjet-hieroglyph-detection-v3)
data/hieroglyph_classification/ (1 GB → Kaggle: wadjet-hieroglyph-classification)
data/landmark_classification/   (15 GB → Kaggle: wadjet-landmark-classification)

# Old model versions (in archive instead)
models/hieroglyph/classifier/_backup_v1/
models/hieroglyph/classifier_keras/      (254 MB Keras)
models/hieroglyph/detection/             (duplicate of detector/)
models/landmark/onnx/
models/landmark/saved_model/
models/landmark/tfjs*/ (4 old TF.js folders)
models/landmark/landmark_classifier.onnx (fp32 duplicate)

# Temp folders
tmp_kaggle_output/
tmp_kaggle_hiero/
tmp_pull_test/
kaggle_logs/

# Dev/build artifacts
scripts/dataprep-env/        (1 GB+ Python venv for data prep)
scripts/archive/             (51 old TF/Keras scripts)
scripts/__pycache__/
scripts/test_*.py            (already gitignored)
scripts/_*.py, scripts/_*.wav
.venv/
node_modules/

# One-off analysis/debug scripts (not needed for production)
scripts/analyze_*.py
scripts/annotate_with_gdino.py
scripts/audit_*.py
scripts/check_*.py
scripts/clip_*.py
scripts/convert_*.py
scripts/create_*.py
scripts/debug_crops.py
scripts/deploy_new_models.py
scripts/evaluate_*.py
scripts/eval_translation.py
scripts/final_sweep.py
scripts/fix_*.py
scripts/inspect_*.py
scripts/kaggle_annotate_scraped.py
scripts/merge_*.py
scripts/prepare_*.py
scripts/quick_scan_test.py
scripts/run_checklist.py
scripts/scrape_museums.py
scripts/test_*.py
scripts/validate_dataset.py
scripts/verify_*.py
```

---

## 4. Path Reference Updates

### Files with `D:\Personal attachements\Projects\Final_Horus\` references:

#### In scripts/ (active — update):
| File | Reference | Action |
|------|-----------|--------|
| `scripts/copy_assets.py` | V1 and V2 paths | Add `# ARCHIVE — paths no longer valid, kept for reference` header |

#### In scripts/ (not copying — no action needed):
- `scripts/analyze_v1.py` — references V1 Wadjet
- `scripts/analyze_model.py` — references V1 + V2
- `scripts/annotate_with_gdino.py` — references V1 data
- `scripts/archive/*` — 50+ scripts with old paths

#### In planning/ (historical — update selectively):
| File | References | Action |
|------|------------|--------|
| `CLAUDE.md` | V1 path, `Wadjet-v2/` structure | **UPDATE**: change V1 ref to archive, fix structure |
| `planning/EXPANSION_PLAN.md` | 6× `cd "D:\...\Wadjet-v2"` | **UPDATE** to `cd "D:\...\Wadjet"` |
| `planning/rebuild/MASTER_PLAN.md` | V1 paths, kaggle paths | **ADD NOTE** at top: "Paths reference old location" |
| `planning/archive/PROMPTS.md` | V1 + V2 paths | **ADD NOTE**: historical |
| `planning/hieroglyph-rebuild/START_PROMPTS.md` | V1 path | **ADD NOTE**: historical |
| `planning/model-rebuild/kaggle-archive/PROMPTS.md` | V1 + V2 paths | **ADD NOTE**: historical |
| `planning/detector-rebuild/MASTER_PLAN.md` | V1 data paths | **ADD NOTE**: historical |

#### In runtime code (NONE — safe):
- `app/` — all relative paths ✅
- `templates/` — all relative ✅
- `static/js/` — all relative ✅
- `.env` — no absolute paths ✅

---

## 5. Archive Structure

```
archive/
├── README.md                           ← Index explaining everything
│
├── original-horus/                     ← The very first Horus AI project
│   ├── app.py                         (Flask app, 48 KB)
│   ├── class_labels.py                (label definitions)
│   ├── llm_utils.py                   (LLM utilities)
│   ├── model_utils.py                 (model loading)
│   ├── inspect_model.py               (model inspection)
│   ├── t.py                           (test script)
│   ├── requirements.txt
│   ├── last_model_bgd.keras           (254 MB — original Keras model)
│   ├── HORUS AI .mp4                  (93 MB — presentation video)
│   ├── Horus-AI.pdf                   (project report)
│   ├── Horus-AI-Guardian...pdf        (extended report)
│   ├── COMPREHENSIVE_README.md
│   ├── TECHNICAL_DOCUMENTATION.md
│   ├── PROJECT_DIAGRAMS.md
│   ├── UPGRADE_ANALYSIS.md
│   ├── README.md
│   ├── gitattributes
│   ├── model_test/                    (test images, 3.3 MB)
│   ├── static/                        (Flask static files, 3.6 MB)
│   └── templates/                     (Flask templates, 0.2 MB)
│
├── v1-reference/                       ← Key files from Wadjet v1
│   ├── README.md                      (explains what V1 was)
│   ├── core/                          (pipeline.py, gardiner_mapping.py, translation modules)
│   ├── js/                            (hieroglyph-pipeline.js original)
│   └── templates/                     (scan.html, explore.html originals)
│
├── v2-training/                        ← Training artifacts & results
│   ├── DATA_CATALOG.md               (where all datasets live — Kaggle slugs, sizes, class counts)
│   ├── kaggle-results/               (final training logs + metrics only, NOT checkpoints)
│   │   ├── classifier_v1_results.md  (98.18% top-1)
│   │   ├── classifier_v2_results.md  (97.31% top-1, 55.63% stone)
│   │   ├── landmark_results.md       (93.80% top-1)
│   │   └── detector_v2_results.md    (mAP50=0.710)
│   └── model-versions/              (old model files for reference)
│       ├── classifier_v1_backup/    (from models/hieroglyph/classifier/_backup_v1/)
│       └── classifier_keras/        (efficientnet_v2s.keras)
│
├── v2-scripts/                         ← Old/utility scripts (from scripts/archive/)
│   └── (51 files from scripts/archive/)
│
└── v2-notebooks/                       ← Kaggle training notebooks
    ├── hieroglyph_classifier.ipynb
    ├── landmark_classifier.ipynb
    └── hieroglyph_detector.ipynb
```

---

## 6. JOURNEY.md Outline

The JOURNEY.md will be a comprehensive narrative document covering:

```markdown
# The Wadjet Journey — From Horus to v2

## Prologue: Horus AI (Before Wadjet)
- Original graduation/coursework project
- Flask + Keras, single hieroglyph classifier
- The 254 MB Keras model, simple web UI

## Chapter 1: Wadjet v1 — The First Rewrite
- Why rewrite: modern stack, dual-path (hieroglyphs + landmarks)
- FastAPI + Jinja2 + TailwindCSS + TF.js
- 52 landmarks, 171 Gardiner signs
- YOLOv8 detection (261 auto-labeled images)
- HuggingFace Spaces deployment
- Problems: fragile models, poor UX, mixed code quality

## Chapter 2: Wadjet v2 — Clean Architecture
### Session 1-5: Foundation & Scaffold (2026-03-19)
(planning, CONSTITUTION, design system, infrastructure)

### Session 6-9: Core Features (2026-03-19)
(Scan, Dictionary, Write, Explore, Chat — all 53 base tasks)

### Session 10: Strategy Decision — Kaggle Training
(PyTorch → ONNX, not Keras/TF.js)

### Session 11-12: Data Preparation
(16,638 train hieroglyph images, 25,710 landmark images)

### Session 13: Model Rebuild — Classifiers on Kaggle
(MobileNetV3-Small 98.18%, EfficientNet-B0 93.80%)

### Session 14-15: Detector Rebuild Planning
(10,311 images from 7 sources, YOLO26s NMS-free)

### Session 16: Detector Training & Integration
(mAP50=0.710, 80 tasks complete)

### Session 17-18: Hieroglyph Pipeline Rebuild
(19 bug fixes, AI Vision reader, Gemini+Groq+Grok ensemble)

### Session 19: Translation & Audio
(RAG translator rewrite, TTS + STT)

### Session 20-21: Expansion Plan
(Dictionary 177→1023, Explore 157→260+, Write fixes, Chat formatting)

### Session 22: Final Features
(Classifier v2, Cloudflare fallback, TLA API, 57/57 tasks)

## Chapter 3: Architecture & Design Decisions
- Black & Gold design system
- Dual-path: Hieroglyphs + Landmarks
- AI-first with ONNX fallback
- 11 free API providers
- Zero budget constraint

## Chapter 4: The Numbers
- 37 git commits
- 22 development sessions
- 57 expansion tasks completed
- 86 base tasks completed
- 1,023 Gardiner signs in dictionary
- 260+ heritage sites
- 10,311 detection training images
- 171 hieroglyph classes, 52 landmark classes
- 11 free AI providers integrated

## Chapter 5: What's Next
- T4 Phase 2: Real Egyptian Translation Engine
- T5: Landmark AI Experience
- Training v3 on Kaggle (detector + classifier)

## Appendices
- A: Kaggle Dataset Locations
- B: API Provider List
- C: Model Accuracy Summary
- D: Git Commit History (full)
```

---

## 7. Git Strategy

### The Plan
1. **COPY `.git/` directory** from Wadjet-v2 to new Wadjet (preserves full history, remotes, branches, LFS)
2. **Do NOT change remotes** — GitHub + HF URLs stay the same
3. **Old folder stays 100% intact** — can still `cd` into it and run the app
4. **Working tree changes** in the NEW folder will be:
   - **Not present**: training data dirs, tmp dirs, old model versions, dataprep scripts (never copied)
   - **Added**: archive/, JOURNEY.md
   - **Modified**: CLAUDE.md, EXPANSION_PLAN.md (path updates)
5. **Single commit**: `chore: clean migration — archive + JOURNEY.md, remove training data`
6. **Push** to both `origin` (GitHub) and `hf` (HuggingFace) — only AFTER local testing passes

### Why COPY not MOVE
- Old folder stays fully functional as safety net
- COPY preserves LFS objects locally (no re-download)
- COPY preserves all branches, stash, reflog
- If anything goes wrong, old folder is untouched
- `.git/` IS the history — everything else is just the working tree

### Branch Strategy
- Continue on `clean-main` (already the active branch)
- `master` branch stays as historical reference (can be deleted later)

---

## 8. Data Reference Catalog

### Kaggle Datasets (training data lives here — NOT in local project)

| Dataset | Kaggle Slug | Owner | Size | Classes | Split |
|---------|-------------|-------|------|---------|-------|
| Hieroglyph Classification | `nadermohamedcr7/wadjet-hieroglyph-classification` | nadermohamedcr7 | ~1 GB | 171 | train only |
| Landmark Classification | `nadermohamedcr7/wadjet-landmark-classification` | nadermohamedcr7 | ~15 GB | 52 | train only |
| Detection v3 (Balanced) | `nadermohamedcr7/wadjet-hieroglyph-detection-v3` | nadermohamedcr7 | 831 MB | 1 (hieroglyph) | train/val/test |
| Stone Textures | `nadermohamedcr7/wadjet-stone-textures` | nadermohamedcr7 | 61 MB | - | - |

### Kaggle Kernels (training notebooks live here)

| Kernel | Slug | Status | Best Result |
|--------|------|--------|-------------|
| Hieroglyph Classifier v1 | `nadermohamedcr7/wadjet-hieroglyph-classifier` | ✅ Complete | 98.18% top-1 |
| Hieroglyph Classifier v2 | `naderelakany/wadjet-hieroglyph-classifier-v2` | ✅ Complete | 97.31% top-1 |
| Landmark Classifier | `nadermohamedcr7/wadjet-landmark-classifier` | ✅ Complete | 93.80% top-1 |
| Hieroglyph Detector v3 | `naderelakany/wadjet-hieroglyph-detector-v3` | 🔄 Training | Target: mAP50≥0.85 |

### How to Re-Download Data (if ever needed)
```bash
# Install kaggle CLI
pip install kaggle
# Set credentials
cp ~/Downloads/kaggle.json ~/.kaggle/
# Download datasets
kaggle datasets download nadermohamedcr7/wadjet-hieroglyph-classification -p data/
kaggle datasets download nadermohamedcr7/wadjet-hieroglyph-detection-v3 -p data/
kaggle datasets download nadermohamedcr7/wadjet-landmark-classification -p data/
```

### GitHub Repository
- **URL**: https://github.com/Nadercr7/wadjet_v2
- **Branch**: `clean-main`
- **LFS**: ONNX models, images, fonts, FAISS index
- **Does NOT contain**: training datasets (gitignored)

### HuggingFace Space
- **URL**: https://huggingface.co/spaces/nadercr7/wadjet-v2
- **Branch**: `main` (tracks `clean-main` from GitHub)
- **Deployed**: Docker-based, auto-builds on push

---

## 9. Verification Checklist

### Pre-Migration
- [ ] Wadjet-v2 `git status` is clean (no uncommitted changes)
- [ ] Wadjet-v2 server starts and all routes work
- [ ] Note current HEAD commit hash
- [ ] Verify disk space on D:\ (~500 MB needed for new folder)

### Post-Copy (Phase 1-4 complete)
- [ ] New `Wadjet/` folder exists at `D:\Personal attachements\Projects\Wadjet\`
- [ ] Old `Final_Horus/Wadjet-v2/` is UNTOUCHED (verify with `git -C <old_path> status`)
- [ ] `git log --oneline -1` in new folder shows same HEAD commit as old
- [ ] `git remote -v` shows same origin + hf remotes
- [ ] `git branch` shows `clean-main` as active

### Local Testing (Phase 5 — BEFORE any push)
- [ ] `.venv` created and all packages installed
- [ ] `npm install` + `npm run build` succeeds (CSS builds)
- [ ] `uvicorn app.main:app --reload --port 8000` starts without errors
- [ ] `GET /` — landing page loads
- [ ] `GET /hieroglyphs` — hub page loads
- [ ] `GET /landmarks` — hub page loads
- [ ] `GET /scan` — scan page loads with upload/camera UI
- [ ] `GET /dictionary` — 1,023 signs load with categories
- [ ] `GET /write` — write page with palette
- [ ] `GET /explore` — 260+ landmarks load
- [ ] `GET /chat` — Thoth chat page loads
- [ ] `GET /api/health` — returns 200 with status
- [ ] Dictionary: search "bird" → get results
- [ ] Write: type "hello" in alpha mode → hieroglyphs appear
- [ ] Explore: search "pyramid" → get landmarks
- [ ] Archive files all present and readable
- [ ] JOURNEY.md is complete

### Git Sync (Phase 6 — ONLY after Phase 5 passes)
- [ ] `git add . && git status` shows expected changes
- [ ] `git commit` succeeds
- [ ] `git push origin clean-main` succeeds
- [ ] `git push hf clean-main:main` succeeds
- [ ] GitHub repo shows new commit

### Final Verification
- [ ] Old folder STILL works: `git -C "D:\...\Final_Horus\Wadjet-v2" status` → clean

---

## 10. Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| **Old folder damaged** | COPY everything, NEVER move/delete. Old folder stays 100% functional. |
| **LFS data loss** | COPY `.git/` (not clone) — LFS objects copied intact |
| **Missing file** | Full inventory in §3 — checked every runtime file |
| **Broken paths in code** | Grep found NO absolute paths in app/ or templates/ — only in scripts + planning docs |
| **Git remote confusion** | Don't change remotes — both GitHub + HF URLs are project-level, not folder-level |
| **Training data needed later** | DATA_CATALOG.md has exact Kaggle slugs + download commands |
| **HF deployment breaks** | Test locally first (Phase 5), push only after all tests pass (Phase 6) |
| **Forgot a model file** | Cross-referenced .gitignore whitelist with models/ inventory |
| **Archive too large** | Only keeping summary logs from Kaggle, not full checkpoints (769 MB → ~5 MB) |
| **JOURNEY.md incomplete** | Based on SESSION_LOG.md (422 lines) + repo memory (199 lines) + all planning docs |
| **Old folder left behind** | Phase 7 asks user before any action. Old folder is safety net, not garbage. |
| **Step fails mid-migration** | STOP immediately. Old folder is untouched. New folder can be deleted and retried. |

---

## Execution Time Estimate

| Phase | Action | Time |
|-------|--------|------|
| Phase 1 | Copy files + create venv + npm install | ~10 min |
| Phase 2 | Create archive (copy + organize) | ~5 min |
| Phase 3 | Write JOURNEY.md | ~10 min |
| Phase 4 | Update path references | ~5 min |
| Phase 5 | Git commit + push | ~5 min |
| Phase 6 | Full verification | ~10 min |
| **Total** | | **~45 min** |

---

## Start Prompt

When user says "GO", execute this plan:
1. Phase 1-4: Build + archive + JOURNEY.md + path updates (ALL COPY, nothing deleted)
2. Phase 5: Test EVERYTHING locally
3. Phase 6: Git commit + push (ONLY if Phase 5 passes)
4. STOP before Phase 7 — report results and wait for user approval
5. If ANY step fails → STOP immediately and report. Do NOT modify old folder.
