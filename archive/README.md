# Wadjet Archive

This folder preserves the full development history and planning docs of the Wadjet project, from the original Horus AI prototype through v1, v2, and v3.

---

## Code History

### `original-horus/`
The very first project — "Horus AI", a Flask + Keras hieroglyph classifier built as a graduation project. Contains:
- `app.py` — Flask application (48 KB)
- `last_model_bgd.keras` — Original 254 MB Keras classifier
- `HORUS AI .mp4` — 93 MB presentation video
- `Horus-AI.pdf`, `Horus-AI-Guardian...pdf` — Project reports
- `static/`, `templates/` — Flask frontend
- `model_test/` — Test hieroglyph images
- Documentation: COMPREHENSIVE_README.md, TECHNICAL_DOCUMENTATION.md, PROJECT_DIAGRAMS.md

### `original-horus-docs/`
Supplementary documentation generated during Horus analysis.

### `v1-reference/`
Key files from Wadjet v1 — the first rewrite that introduced FastAPI, dual-path architecture, and TF.js browser inference.
- `core/` — Python business logic (pipeline.py, gardiner_mapping.py, attractions_data.py, etc.)
- `js/` — Client-side JavaScript (hieroglyph-pipeline.js, camera.js, classifier.js, detection.js)
- `templates/` — Selected Jinja2 templates

### `v2-training/`
Training artifacts and data catalogs from v2 model development.
- `DATA_CATALOG.md` — Dataset descriptions
- Kaggle results and old model version notes

### `v2-scripts/`
51 old utility scripts from v2 — data preparation, TF/Keras migration, model conversion.

### `v2-notebooks/`
Kaggle training notebooks (5 total) used during v2 model training.

---

## Planning Docs

### `v2-planning/` *(gitignored — local only)*
v2 UX overhaul and rebuild planning docs:
- `CONSTITUTION.md`, `DEPLOYMENT_PLAN.md`, `EXPANSION_PLAN.md`, `MIGRATION_PLAN.md`
- `UX_OVERHAUL_PLAN.md`, `UX_AUDIT_PROMPT.md`, `UX_FIXES_PLAN.md`
- Subdirs: `detector-rebuild/`, `hieroglyph-rebuild/`, `model-rebuild/`, `rebuild/`, `ux-overhaul/`

### `v3-beta-planning/`
v3 beta development phase plans (11 phases):
- `00_MASTER_PLAN.md` — Overall strategy
- `01_PHASE_MAP.md` — Phase breakdown (0–10)
- `02_PHASE_PROMPTS.md` — Per-phase execution prompts
- `03_TESTING_PLAN.md` — Test strategy
- `04_DEPENDENCIES_AND_RISKS.md` — Risk register
- `05_QUALITY_CHECKLIST.md` — QA gates per phase

### `v3-upgrade-planning/`
Comprehensive v3.0.0 upgrade plans (post-beta):
- `00_MASTER_PLAN.md` — Upgrade strategy
- `03_VERSION_PROMOTION_PLAN.md` — HuggingFace deployment
- `04_AUTH_PLAN.md` — Google OAuth + email verification
- `05_DESIGN_SYSTEM.md` — Black & gold design system spec
- `06_SCAN_PIPELINE_AUDIT.md` — Multi-provider scan pipeline
- `07_STORIES_ENRICHMENT_PLAN.md` — 13 stories expansion
- `10_QUALITY_GATES.md` — OWASP + final QA checklist

### `v3-planning-snapshot/` *(gitignored — local only)*
Timestamped snapshot of v3 planning state from 2026-03-29.
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

## See Also
- `JOURNEY.md` in the project root — complete narrative of the development journey
- `CHANGELOG.md` — version-by-version release notes
