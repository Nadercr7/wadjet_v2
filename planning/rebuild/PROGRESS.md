# Wadjet v2 — Phase Tracker

> **Total: 86 tasks across 8 phases**
> **Progress: 85 / 86 = 99%** — Phases P0–P6 + P8 COMPLETE. P7 Deploy: E.1–E.4 done, E.5–E.6 (push + smoke test) remain.

---

## Phase P0: Foundation (8/8) ✅

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P0.1 | Create project structure & venv | ✅ | Folders, __init__.py, venv |
| P0.2 | Install FastAPI + core deps | ✅ | uvicorn, jinja2, pydantic-settings |
| P0.3 | Set up TailwindCSS v4 | ✅ | Standalone CLI + input.css + build |
| P0.4 | Configure Alpine.js + HTMX | ✅ | CDN in base.html |
| P0.5 | Create base.html + Black & Gold theme | ✅ | Master layout, CSS custom properties |
| P0.6 | Create landing page | ✅ | Dual-path choice hub (Hieroglyphs + Landmarks) |
| P0.7 | Configure linting (ruff + pyproject) | ✅ | Ruff rules in pyproject.toml |
| P0.8 | Verify dev server + hot reload | ✅ | uvicorn --reload + tailwind CLI tested |

**Gate:** ✅ Landing page renders at localhost:8000 with Black & Gold theme, no errors.

---

## Phase P1: Design System (6/6) ✅

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P1.1 | Define color tokens in CSS | ✅ | Custom properties in input.css (--color-night, --color-gold, etc.) |
| P1.2 | Configure typography | ✅ | Playfair Display + Inter + Noto Hieroglyphs |
| P1.3 | Build component classes | ✅ | .btn-gold, .btn-ghost, .card, .card-glow, .badge-gold, .input |
| P1.4 | Build layout partials | ✅ | nav.html (dual-path), footer.html (grouped links) |
| P1.5 | Add transitions & animations | ✅ | Shimmer, fade-up, pulse-gold, card hover glow |
| P1.6 | Mobile responsive breakpoints | ✅ | All components responsive, mobile menu working |

**Gate:** ✅ All component classes render correctly. Nav + footer on every page. Mobile looks good.

---

## Phase P2: Scan Feature — Core (8/8) ✅

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P2.1 | Copy hieroglyph models | ✅ | ONNX, TF.js uint8, label_mapping, Keras, embeddings |
| P2.2 | Adapt HieroglyphPipeline | ✅ | Fixed imports (app.core.*), paths (models/hieroglyph/), all modules verified |
| P2.3 | Create scan API endpoints | ✅ | POST /api/scan, /api/detect + thread pool + file validation |
| P2.4 | Build scan page UI | ✅ | Upload/camera tabs, drag-drop, file validation, Alpine.js scanApp |
| P2.5 | Step-by-step scan flow | ✅ | Progressive 4-step reveal with transitions (detect→classify→translit→translate) |
| P2.6 | Results visualization | ✅ | Canvas bboxes, glyph cards with confidence bars, Gardiner→Unicode, timing |
| P2.7 | Integrate client-side pipeline | ✅ | v2 model URLs, server/browser mode toggle, progress bar, pipeline.dispose() |
| P2.8 | Error handling + loading states | ✅ | Error/empty states, spinner, camera-denied, file-too-large, network errors |

**Gate:** Upload image → detect glyphs → classify → transliterate → translate. Full E2E working.

---

## Phase P3: Dictionary & Write (6/6) ✅

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P3.1 | Create Gardiner dictionary API | ✅ | GET /api/dictionary + /categories + /{code}, search/filter by category/type |
| P3.2 | Build dictionary page | ✅ | Category pills, search bar, type filter, 6-col sign grid, Alpine.js dictionaryApp |
| P3.3 | Glyph detail view | ✅ | Modal with full Gardiner info — code, transliteration, phonetic, type, category, description, logographic, determinative class |
| P3.4 | Create write API | ✅ | POST /api/write (alpha+mdc modes), GET /api/write/palette (4 sign groups) |
| P3.5 | Build write page | ✅ | Alpha/MdC mode toggle, debounced input, quick examples, glyph breakdown, Gardiner palette picker |
| P3.6 | Copy/share composed text | ✅ | Clipboard API + fallback, Web Share API, "Copied!" feedback |

**Gate:** ✅ Dictionary shows 172 signs by category with search. Write converts text to hieroglyphs with palette.

---

## Phase P4: Explore — Landmarks (6/6) ✅

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P4.1 | Copy landmark data + model | ✅ | 54 metadata, 50 text JSONs, TF.js model (52 classes) |
| P4.2 | Adapt landmark service | ✅ | app/core/landmarks.py — 20 curated + Pydantic models + indexes |
| P4.3 | Create explore API endpoints | ✅ | app/api/explore.py — list, categories, detail (curated+wiki+model fallback) |
| P4.4 | Build explore page | ✅ | Category pills, city filter, search, card grid with thumbnails |
| P4.5 | Build landmark detail page | ✅ | Modal with image, highlights, features, wiki extract, maps/wiki links |
| P4.6 | AI landmark identification | ✅ | TF.js EfficientNetV2-S, 384×384, top-5 results, view detail flow |

**Gate:** ✅ Browse 56 landmarks. Click → detail modal with rich info. Upload → identify via TF.js.

---

## Phase P5: AI Features (6/6) ✅

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P5.1 | Adapt Thoth chatbot backend | ✅ | gemini_service.py rewritten, thoth_chat.py with session store, streaming |
| P5.2 | Build chat page | ✅ | SSE streaming UI, Alpine.js chatApp, conversation starters, markdown rendering |
| P5.3 | Adapt quiz engine | ✅ | 60 static questions (3 types) + Gemini-generated quizzes, quiz_engine.py |
| P5.4 | Build quiz page | ✅ | Quick quiz + AI quiz modes, score tracking, progress bar, hint system |
| P5.5 | Adapt recommendation engine | ✅ | Tag-based scoring (type/era/city/proximity), recommendation_engine.py |
| P5.6 | "Discover" section on landing | ✅ | Daily glyph, quiz CTA, featured landmark, rotating content |

**Gate:** ✅ Chat works with SSE streaming. Quiz generates 60 static + AI questions. Recommendations + Discover on landing.

---

## Phase P6: Polish & UX (8/8) ✅

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P6.1 | History (localStorage) | ✅ | WadjetHistory util in app.js, scan/write/chat history, 20-item cap, thumbnails |
| P6.2 | Share feature | ✅ | Canvas export → PNG download, Web Share API for scan results |
| P6.3 | Offline support | ✅ | Service Worker (sw.js), static + model caching, network-first for pages |
| P6.4 | Page transitions | ✅ | CSS View Transitions, gold loading progress bar, page-enter animation |
| P6.5 | Toast notifications | ✅ | Alpine store toast, success/error/info with icons, auto-dismiss |
| P6.6 | Accessibility | ✅ | Skip-to-content, ARIA roles/labels/live, focus-visible ring, semantic HTML |
| P6.7 | Performance optimization | ✅ | GZip middleware, DNS prefetch, fetchpriority, lazy load images |
| P6.8 | Final mobile testing | ✅ | All 9 routes 200, touch targets fixed, dvh viewport, readability |

**Gate:** ✅ App feels polished. Offline SW caches models. Smooth transitions. Accessible. All routes 200.

---

## Phase P8: ML Rebuild — PyTorch + Gemini Vision (Session 9+ Plan)

> ⚠️ **P8 MUST BE COMPLETED BEFORE P7 (Deploy).** Models must work before deploy.

> **Full plan**: `planning/rebuild/MASTER_PLAN.md`
> **Task list**: `planning/rebuild/REBUILD_TASKS.md`
> **Strategy**: PyTorch local training on Kaggle GPU. Hieroglyph: MobileNetV3-Small (171 classes). Landmark: EfficientNet-B0 (52 classes) + Gemini Vision as enrichment/fallback.

### Reason for Rebuild
- Old models: Keras/TF.js → `_FusedConv2D` fused op crash in ONNX Runtime
- Kaggle training: abandoned (persistent DNS failures, tf2onnx not pre-installed) — RESOLVED in new plan (torch.onnx.export is built-in)
- Solution: PyTorch (`torch.onnx.export` native) + EfficientNet-B0 landmark model + Gemini Vision as enrichment/low-confidence fallback

### Data Preparation (Session 10) ✅

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P8.D1 | Hieroglyph data audit | ✅ | 171 classes, 15,017 train, 67 weak classes identified |
| P8.D2 | Install albumentations | ✅ | albumentations 2.0.8 via pip |
| P8.D3 | Prepare hieroglyph classification dataset | ✅ | `scripts/prepare_hieroglyph_data.py` → `data/hieroglyph_classification/` — 16,638 train (min=80, augmented), 171 classes |
| P8.D4 | Copy FAISS embeddings | ✅ | `data/embeddings/corpus.index` (21.4MB) + `corpus_ids.json` |
| P8.D5 | Copy translation corpus | ✅ | `data/translation/corpus.jsonl` + train/val/test splits |
| P8.D6 | Landmark data audit | ✅ | 52 classes, 21,151 train, min=176, max=1450, avg=407 — well balanced |
| P8.D7 | Download eg-landmarks dataset | ✅ | `data/downloads/eg-landmarks/` — 279 classes, 37 match our 52, +1938 images |
| P8.D8 | Build EG_TO_V1 class mapping | ✅ | 42-entry dict in `scripts/prepare_landmark_data.py` |
| P8.D9 | Write landmark prep script | ✅ | `scripts/prepare_landmark_data.py` — dry-run verified: 23,089 train / 4,506 val / 4,497 test |
| P8.D10 | Execute landmark prep script | ✅ | `data/landmark_classification/` — 25,710 train (min=300, 52 classes), merged v1 splits + eg-landmarks + augmented |

### Model Training — Phase A: Kaggle Setup

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P8.A1 | Install Kaggle CLI | ✅ | `.venv\Scripts\kaggle.exe` — verified working |
| P8.A2 | Upload hieroglyph dataset to Kaggle | ✅ | Uploaded 2026-03-21 (~1GB). `kaggle datasets list --mine` confirms. |
| P8.A2b | Upload landmark dataset to Kaggle | ✅ | Uploaded 2026-03-23 (~14GB). Fixed apostrophe in Pompey's filenames. |
| P8.A3 | Copy ONNX detector to project | ✅ | `models/hieroglyph/detection/glyph_detector_uint8.onnx` (11 MB) |
| P8.A4 | Create training notebooks + kernel-metadata | ✅ | Both notebooks + kernel-metadata.json created |

### Model Training — Phase B: Hieroglyph Classifier (Kaggle)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P8.B1 | Create hieroglyph training notebook | ✅ | Notebook with all fixes: T4 GPU, float32, /255 norm, no h-flip, auto-discovery |
| P8.B2 | Train MobileNetV3-Small (171 classes) | ✅ | Phase 1: epoch 3 val_acc=77.95%, Phase 2: epoch 20 val_acc=98.26% |
| P8.B3 | Export ONNX + quantize uint8 | ✅ | fp32=6.47MB, uint8=1.77MB, opset=18, NCHW [1,3,128,128] |
| P8.B4 | Copy model to `models/hieroglyph/classifier/` | ✅ | + label_mapping.json (171 classes) + model_metadata.json |

### Model Training — Phase B2: Landmark Classifier (Kaggle)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P8.B2.1 | Create landmark training notebook | ✅ | Notebook with all fixes: T4 GPU, float32, /255 norm, h-flip allowed, auto-discovery |
| P8.B2.2 | Train EfficientNet-B0 (52 classes) | ✅ | Phase 1: epoch 6 val_acc=82.69%, Phase 2: epoch 26 val_acc=93.63% |
| P8.B2.3 | Export ONNX + quantize uint8 | ✅ | fp32=15.52MB, uint8=4.17MB, opset=18, NCHW [1,3,224,224] |
| P8.B2.4 | Copy model to `models/landmark/` | ✅ | + landmark_label_mapping.json (52 classes) + model_metadata.json |

### Backend Integration — Phase C

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P8.C1 | Fix hieroglyph_pipeline.py (NCHW) | ✅ | Fixed _classify_crops transpose + _get_classifier auto-detect + label_mapping loader |
| P8.C2 | Complete gardiner.py (71→171 signs) | ✅ | Already 172 signs mapped — covers all 171 model classes |
| P8.C3 | Re-enable translation pipeline | ✅ | Already enabled; fixed FAISS path (data/embeddings/) + config paths |
| P8.C4 | Create landmark_pipeline.py | ✅ | app/core/landmark_pipeline.py — ONNX wrapper, NCHW, softmax, top-k |
| P8.C5 | Add hybrid identify endpoint | ✅ | POST /api/explore/identify — ONNX→Gemini hybrid, 3 confidence tiers |
| P8.C6 | Add identify_landmark() + describe_landmark() to gemini_service | ✅ | Vision identification + text enrichment |

### Frontend — Phase D

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P8.D.1 | Fix JS classifier preprocessing (NCHW) | ✅ | _warmup() [1,3,s,s] + classify() planar NCHW + label_mapping flat format support |
| P8.D.2 | Replace TF.js in explore.html with HTMX | ✅ | Removed all client-side ONNX; HTMX form hx-post="/api/explore/identify" + HTML partial response |
| P8.D.3 | Add identify_result.html partial | ✅ | partials/identify_result.html — Jinja2 with confidence bar, top3, detail links |
| P8.D.4 | Bump SW cache + base.html v numbers | ✅ | wadjet-v15; styles.css?v=15; fixed landmark model paths in SW |

**Gate:** ✅ All pages render. Identify returns HTML partial for HTMX. Hieroglyph pipeline uses NCHW. No TF.js remnants.

---

## Phase P7: Deploy (3/5)

> ⚠️ **Only start P7 after P8 is fully complete** — models must work before deploy.

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P7.1 | Dockerfile + docker-compose | ✅ | Multi-stage TW v4 CSS builder + python:3.13-slim. COPY models/ + data/. Image: 1.78GB. All 9 pages 200 in container |
| P7.2 | Environment configuration | ✅ | .gitignore whitelist (8 essential models), .dockerignore excludes training data. Starlette 1.0 API. faiss optional. render.yaml env vars |
| P7.3 | Production TailwindCSS build | ✅ | CSS built in Docker stage via @tailwindcss/cli v4.2.2 |
| P7.4 | Deploy to Render | ⬜ | Needs: create GitHub repo → git push → connect Render |
| P7.5 | Smoke test + verify | ⬜ | Pending deploy |

**Gate:** App live on Render. All features working. No console errors.
- ⬜ Not started
- 🔄 In progress
- ✅ Completed
- ❌ Blocked
- ⏭️ Skipped
