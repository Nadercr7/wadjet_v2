# Wadjet Archive

This folder preserves the full development history of the Wadjet project, from the original Horus AI prototype through v1 and v2.

## Structure

### `original-horus/`
The very first project — "Horus AI", a Flask + Keras hieroglyph classifier built as a graduation project. Contains:
- `app.py` — Flask application (48 KB)
- `last_model_bgd.keras` — Original 254 MB Keras classifier
- `HORUS AI .mp4` — 93 MB presentation video
- `Horus-AI.pdf`, `Horus-AI-Guardian...pdf` — Project reports
- `static/`, `templates/` — Flask frontend
- `model_test/` — Test hieroglyph images
- Documentation: COMPREHENSIVE_README.md, TECHNICAL_DOCUMENTATION.md, PROJECT_DIAGRAMS.md

### `v1-reference/`
Key files from Wadjet v1 — the first rewrite that introduced FastAPI, dual-path architecture, and TF.js browser inference.
- `core/` — Python business logic (pipeline.py, gardiner_mapping.py, attractions_data.py, etc.)
- `js/` — Client-side JavaScript (hieroglyph-pipeline.js, camera.js, classifier.js, detection.js)
- `templates/` — Original scan.html and explore.html templates

### `v2-training/`
All training artifacts and results from the v2 model rebuilds:
- `DATA_CATALOG.md` — Where every dataset lives (Kaggle slugs, sizes, class counts, download commands)
- `kaggle-results/` — Final metrics for each model training run
- `model-versions/` — Old model files kept for reference

### `v2-scripts/`
51 utility scripts from the v2 development cycle that are no longer needed for production — data preparation, model analysis, TF/Keras migration tools, dataset validation.

### `v2-notebooks/`
Kaggle training notebooks (5 total):
- `hieroglyph_classifier.ipynb` — MobileNetV3-Small, 171 classes
- `landmark_classifier.ipynb` — EfficientNet-B0, 52 classes
- `hieroglyph_detector.ipynb` — YOLO26s v1
- `hieroglyph_detector_v2.ipynb` — YOLO26s v2 (resumed training)
- `hieroglyph_detector_v3.ipynb` — YOLO26s v3 (balanced dataset)

### `v3-beta-planning/`
Planning docs for the v3 beta rewrite (originally `wadjet-planning/` at v3-beta root):
- `00_MASTER_PLAN.md` through `05_QUALITY_CHECKLIST.md` — 11-phase beta plan
- `PHASE_PROMPT_TEMPLATE.txt` — Template for phase execution prompts

### `v3-upgrade-planning/`
Comprehensive upgrade planning for v3's final push (originally `comprehensive-upgrade/`):
- Version promotion, auth, design system, scan pipeline audit
- Stories enrichment, testing, credentials setup, quality gates

### `v3-planning-snapshot/`
Snapshot of v3 planning state from 2026-03-29 (originally `wadjet-v3-planning-ARCHIVED-2026-03-29/`):
- Constitution, spec, plan, progress, work-log
- Phase prompts (0–10), version replacement script

## See Also
- `Wadjet-v3-beta/` — The active v3 production codebase (separate folder)
- `planning/` — v2-era planning documents, rebuild plans, and session logs
