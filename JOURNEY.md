# The Wadjet Journey — From Horus to v2

---

## Prologue: Horus AI

It started as a graduation project called **Horus AI** — a Flask web app with a single Keras classifier that could identify hieroglyphs from uploaded photos. The stack was straightforward: Flask for routing, a 254 MB Keras model (`last_model_bgd.keras`) for classification, and a handful of HTML templates with basic CSS. The frontend had a quiz page, a recommendation engine, and an image upload flow. It worked, barely. The model was monolithic, the UI was functional but rough, and the entire thing lived in a single folder with `app.py` at the root.

But it proved the concept: you could point a camera at hieroglyphs and get something back. That was enough to justify the next step.

---

## Chapter 1: Wadjet v1 — The First Real Attempt

The rewrite started with ambition. Flask was swapped for **FastAPI** with Jinja2 templates. TailwindCSS replaced hand-written CSS. The scope exploded — from a single hieroglyph classifier to a dual-purpose platform covering both hieroglyphs and Egyptian landmarks.

**What v1 built:**
- A two-stage hieroglyph pipeline: YOLOv8 detection → TF.js classification (171 Gardiner sign classes)
- A landmark explorer with 52 sites and a TF.js EfficientNetV2-S model for photo identification
- A Gemini-powered chatbot (Thoth) with multi-turn conversation
- A dictionary of ~177 Gardiner signs with phonetic and semantic data
- A write feature that converted English text to hieroglyphic sequences
- Deployment on HuggingFace Spaces with Docker

**Where v1 fell short:**
- The YOLOv8 detector was trained on just 261 auto-labeled images with OpenCV contour detection. It looked good on synthetic test images but failed catastrophically on real stone inscriptions.
- The TF.js classifier had a `_FusedConv2D` fused op that crashed ONNX Runtime — the same model worked in the browser but not on the server.
- 110 out of 171 class labels in `label_mapping.json` were wrong. They'd been sorted alphabetically in production but generated in filesystem order during training. Every classification was a coin flip.
- The codebase had 121 planned phases. Scope creep was real.
- Data quality was poor: 53 GB of training data sitting locally, barely curated, with duplicate images and inconsistent annotations.

V1 was deployed and functional, but the models were unreliable, the UX was cluttered, and the code needed a clean start.

---

## Chapter 2: Wadjet v2 — Clean Architecture

### Session 1–2: Foundation (March 19, 2026)

I started v2 by surveying everything available. My `Repos/` folder had SaaS boilerplates, UI component libraries (magicui, motion-primitives, react-bits), planning templates (spec-kit), and prompt engineering resources. I catalogued every reusable asset from v1: 6 ML model files (~300 MB), 12 Python source files, 1 JS pipeline file, 105+ data files, 1 hieroglyph font file.

**Key decision #1**: No React, no Next.js. Jinja2 + Alpine.js is simpler, reuses Python directly, and deploys as a single container. The entire interactivity layer would be Alpine.js `x-data` components with HTMX for server-driven updates.

**Key decision #2**: The **Black & Gold** design system. `--color-night: #0A0A0A` backgrounds, `--color-gold: #D4AF37` accents, Playfair Display headings, Inter body text. No light mode, no white backgrounds, no blue links. This became non-negotiable and was codified in `CONSTITUTION.md`.

The scaffold went up fast: `create_app()` factory, Pydantic settings, dependency injection, TailwindCSS v4 CLI for CSS builds. All 7 placeholder routes working by end of session 2.

**Bug found immediately**: TailwindCSS v4 uses `bg-*` utilities internally. Naming a CSS variable `--color-bg` shadows the entire background utility namespace. Hours lost debugging why `bg-surface` didn't work. Renamed to `--color-night`, documented the rule everywhere.

### Session 3: Dual-Path Architecture

The original plan was hieroglyphs-first. I changed it to **equal dual-path** — the landing page at `/` presents Hieroglyphs and Landmarks as two equal cards with equal visual weight. Each path gets its own hub page (`/hieroglyphs`, `/landmarks`) that links to sub-features. This architectural decision shaped everything that followed.

New pages: `hieroglyphs.html` (Scan + Dictionary + Write hub), `landmarks.html` (Explore + Identify hub). Updated nav with grouped hierarchy. Added breadcrumbs to every sub-page.

### Session 4–5: Infrastructure & Resources

Two sessions spent building the foundation that would support everything:
- **CONSTITUTION.md**: 7 non-negotiable principles (dual-path, Black & Gold, stack lock, zero budget, one purpose per page, offline-capable, reuse v1)
- **CLAUDE.md**: Comprehensive project instructions for context — tech stack, design tokens, routes, commands, skill mappings
- **Dockerfile**: Multi-stage build (Node 22 Alpine for CSS, Python 3.13 slim for runtime)
- **copy_assets.py**: Automated v1→v2 asset copy (15+ file mappings)
- **CSS animations**: Extracted `gradient-sweep`, `border-beam`, `meteor`, `dot-glow`, `shine` from magicui's React components as pure CSS @keyframes
- **CDN libraries**: Atropos.js for 3D parallax cards, GSAP + ScrollTrigger for scroll animations, Lenis for smooth scrolling

### Session 6: Scan Feature (Phase P2)

The core feature. Ran `copy_assets.py` to pull models from v1, then rebuilt the entire scan flow:
- **Server API**: `POST /api/scan` runs the full ONNX pipeline in a thread pool executor (non-blocking async)
- **Client pipeline**: ONNX Runtime Web + TF.js loaded on demand with progress callbacks
- **Scan page**: Alpine.js component with drag-and-drop upload, camera capture with `getUserMedia`, 4-step progressive results (Detection → Classification → Transliteration → Translation), bounding box canvas overlay, glyph cards with confidence bars, timing display
- **Server/Browser toggle**: Users choose between accurate server-side inference and fast offline browser inference

Translation was disabled by default — the FAISS + Gemini system wasn't wired yet. That came later.

### Session 7: Dictionary & Write (Phase P3)

- **Dictionary API**: 3 endpoints — list/search/filter signs, categories with counts, single sign lookup. 172 signs across 20 Gardiner categories. Category pills, full-text search, type filter, color-coded badges, click-to-detail modal.
- **Write API**: 2 endpoints — convert text to hieroglyphs in alpha mode (English letter → nearest uniliteral) or MdC mode (greedy longest-match transliteration parsing). Palette picker with 167 signs across 4 type tabs.

### Session 8: Explore & Identify (Phase P4)

- **Explore API**: 56 landmarks (20 curated + 36 Wikipedia-sourced) with 3-tier data fallback (curated → Wikipedia → model-only). Category/city/search filtering.
- **Identify mode**: TF.js EfficientNetV2-S (~39 MB) loaded on demand, 384×384 preprocessing, top-5 results linked to detail modals.
- **Explore page**: Browse mode with type pills and card grid, detail modal with hero images and metadata, identify mode with drag-and-drop.

### Session 9: AI Features (Phase P5)

- **Gemini Service**: Async wrapper with round-robin rotation across 17 API keys. Auto-retry on 429/RESOURCE_EXHAUSTED. `generate_text`, `generate_json`, `generate_text_stream` methods.
- **Thoth Chatbot**: Multi-turn session management with LRU store (500 sessions, 10 message pairs each). Thoth personality prompt — wise Egyptian god of knowledge. SSE streaming for live text rendering.
- **Quiz Engine**: 60 static questions generated from landmark data (identify monument, match city, date era) + Gemini-generated questions with JSON schema validation. Quick Quiz (10 static) and AI Quiz (custom category/difficulty/count) modes.
- **Recommendation Engine**: Tag-based scoring with haversine geo-distance for related landmarks.
- **Discover Section**: Landing page got a "Daily Glyph" (7 rotating hieroglyphs), quiz CTA, and "Featured Landmark" (7 rotating sites) using deterministic day-of-year selection.

### Session 10: Polish & UX (Phase P6)

- **History**: `WadjetHistory` in localStorage — 20-item cap per category, thumbnail generation for scan history, clickable write history, browseable chat history
- **Offline**: Service Worker with 3 strategies (cache-first for models, stale-while-revalidate for static, network-first for pages)
- **Page transitions**: CSS View Transitions API with gold loading progress bar
- **Toast notifications**: Success/error/info variants with auto-dismiss
- **Accessibility**: Skip-to-content link, ARIA roles/labels/live regions, keyboard focus-visible ring
- **Performance**: GZip middleware (500+ byte threshold), DNS prefetch
- **Mobile**: 100vh→100dvh for chat, touch target fixes, font size adjustments

All 53 base tasks across 8 phases complete. The app was deployed to HuggingFace Spaces.

---

## Chapter 3: The Model Crisis

### Session 10–11: The ONNX Catastrophe

With the app deployed, the models started failing. The root cause: the original Keras/TF.js classifiers produced `_FusedConv2D` operations that ONNX Runtime couldn't execute. `tf2onnx` conversion failed on Kaggle due to DNS restrictions. The models that worked in v1's browser-only flow couldn't work in v2's server-side ONNX flow.

**The decision**: Rebuild all models from scratch using PyTorch → native `torch.onnx.export()`. Train on Kaggle's free T4 GPUs. This became Phase P8.

**Cleanup**: 51 old TF/Keras scripts moved to `scripts/archive/`. Dataset metadata created for Kaggle upload. Kernel metadata files set up.

### Session 12: Data Preparation

- **Hieroglyph classification**: 16,638 train images, 171 classes, minimum 80 per class. 67 under-represented classes augmented (rotation, brightness, contrast — no horizontal flip because hieroglyph direction matters).
- **Landmark classification**: 25,710 train images, 52 classes, minimum 300 per class. Merged v1 splits with eg-landmarks Kaggle dataset + augmentation.
- **Translation corpus**: Verified 14,433 vectors in FAISS index, corpus.jsonl intact.

### Session 13: Kaggle Training — The Lessons

Training on Kaggle required solving a cascade of environment issues:

1. **v1**: `$env:PYTHONUTF8 = "1"` required for Unicode output
2. **v2**: VS Code strips `kernelspec` from .ipynb — had to inject before push
3. **v3**: `lightning` package not pre-installed on Kaggle — switched to `pytorch_lightning`
4. **v4**: `total_mem` API renamed to `total_memory` in PyTorch 2.10
5. **v5**: Data root path wrong, P100 GPU CUDA errors — switched to T4, added auto-discovery code
6. **v8**: `convert_py_to_ipynb.py` left raw `Cell N:` lines without `#` prefix → SyntaxError
7. **v9**: `accelerator` field in kernel-metadata.json is IGNORED by Kaggle CLI — must use CLI flag

**The critical training fix**: Mixed precision (`"16-mixed"`) creates fused operations that break ONNX export. Changed to `"32-true"`. ImageNet normalization (mean/std subtract) was another trap — backend and browser both do `/255` only. Training must match.

**Results:**
- **Hieroglyph Classifier**: MobileNetV3-Small → **98.18% top-1, 99.91% top-5** (171 classes)
- **Landmark Classifier**: EfficientNet-B0 → **93.80% top-1, 97.40% top-3** (52 classes)

Both exported to ONNX float32 + quantized uint8. Deployed to `models/`.

---

## Chapter 4: The Hieroglyph Pipeline Rebuild

### Session 14–15: 21 Bugs, 7 Phases

A thorough audit of the hieroglyph scanning pipeline found 21 bugs — 4 critical, 8 high, 6 medium, 3 low. The most devastating: 110/171 class labels were wrong due to filesystem sort order vs alphabetical sort mismatch in `label_mapping.json`. Every classification was effectively random.

The rebuild was planned across 7 phases totaling 57 tasks:
- **H-FIX** (19 tasks): All critical bug fixes
- **H-VISION** (8 tasks): AI-first reading with Gemini Vision
- **H-TRANSLATE** (6 tasks): RAG translation engine rewrite
- **H-AUDIO** (5 tasks): Text-to-speech and speech-to-text
- **W-WRITE** (7 tasks): Smart write mode with real Egyptian translation
- **L-LANDMARKS** (6 tasks): Landmark descriptions and AI identify fallback
- **H-DETECTOR** (6 tasks): Detector rebuild from scratch

### Session 16–17: H-FIX — The Bug Sweep

19 bugs fixed in sequence:
- FP32 classifier switchover (uint8 was producing 0% accuracy)
- BGR→RGB conversion (OpenCV loads BGR, model expects RGB)
- Label mapping path fix (wrong file referenced)
- Asyncio deprecation fix (`get_event_loop()` replaced)
- Reading order fix (RTL/LTR detection using facing sign heuristic)
- Bilingual translation: 2 Gemini calls → 1 (English + Arabic in single prompt)
- New `/api/translate` endpoint (JS pipeline was calling non-existent endpoint)
- JS Gardiner map expanded from 125→171 entries
- Camera CPU burn fix (continuous frame capture eating resources)
- Batch JS classification (sequential → batched for speed)

### Session 17–18: H-VISION — AI-First Architecture

The architectural insight: Gemini Vision reads hieroglyphic inscriptions correctly most of the time. The ONNX pipeline was the weak link. Solution: make AI vision the PRIMARY reader, ONNX secondary.

```
Old:  Photo → ONNX Detect → ONNX Classify → Rule-Based Translit → RAG+Gemini Translate
New:  Photo → Gemini Vision (PRIMARY) → Full Reading + Translation
             → ONNX Pipeline (SECONDARY, parallel for visualization + offline)
             → Cross-Validate & Merge → Final Result
             → TTS → Audio playback
```

**New modules:**
- `ai_service.py`: Base class with multi-provider fallback chain (Gemini→Groq→Grok). 17 Gemini keys + 8 Groq keys + 8 Grok keys — all on free tiers.
- `ai_reader.py`: Egyptologist expert prompt generating structured `InscriptionReading` responses with Gardiner codes, transliteration, and translation.
- `cross_validator.py`: IoU-based bounding box matching to compare AI and ONNX readings, building confidence from agreement.
- Scan page: Auto/AI Vision/Fast Local mode selector with pill buttons.

### Session 19: H-TRANSLATE — RAG Rewrite

The old translation system used `all-MiniLM-L6-v2` (384-dim) for embeddings. Replaced with Gemini's `text-embedding-004` (768-dim Matryoshka embeddings) — eliminating the sentence-transformers dependency entirely.

- Rebuilt FAISS index: 15,604 vectors, 45.7 MB
- `TranslationCache`: LRU with 512 entries, 0.0ms cache hits
- Scholarly bilingual prompt: English + Arabic in a single Gemini call
- Quality: BLEU score 0.594, 70% pass rate on the evaluation set of 50 ground-truth inscriptions

### Session 19 (continued): H-AUDIO — Voice

- `tts.js`: Web Speech API for browser-side TTS in 4 languages (English, Arabic, French, German). Chromium 15-second utterance limit workaround.
- Server-side: Groq TTS endpoint (`/api/tts` using PlayAI model), Groq STT endpoint (`/api/stt` using Whisper large-v3-turbo). Listen buttons on scan results, microphone input for chat.

---

## Chapter 5: The Detector Rebuild

### Session 16: Why Rebuild

The v1 detector was the weakest link. Trained on 261 images with auto-generated OpenCV contour labels, it showed mAP50=0.875 on synthetic validation data but failed completely on real stone photos. Gemini Visionwas doing 90%+ of actual detection work. A real detector needed real data.

### The Data Quest (D-PREP — 48 tasks)

Building a proper detection dataset meant sourcing images from everywhere:
- **mohiey** (Kaggle): 8,650 pre-annotated hieroglyph images — the largest single source (84%)
- **Synthetic composites**: 951 images generated by placing Gardiner signs on procedural stone textures (12 color palettes, multi-octave fractal noise)
- **signs_segmentation** (HuggingFace): 289 segmented sign images
- **v1_raw**: 229 original images re-annotated with GroundingDINO
- **hla_annotated** (HuggingFace): 192 images converted from COCO polygon format to YOLO

Museum scraping was attempted — Met Museum API (338 images), Wikimedia Commons (121 images) — but GroundingDINO annotation was too slow on CPU and these were dropped.

**Dedup pipeline**: 21,974 raw images → 10,654 after perceptual hash dedup → 10,311 after CLIP relevance filtering (343 irrelevant images removed).

**Scripts created:**
- `annotate_with_gdino.py` — GroundingDINO auto-annotation with resume support
- `convert_hla_to_yolo.py` — COCO polygon/bbox → YOLO format
- `clip_filter_images.py` — CLIP relevance scoring
- `scrape_museums.py` — 4 spiders (Met, Wikimedia, Brooklyn, Europeana) with resume
- `generate_synthetic_composites.py` — Grid-based glyph placement on stone textures
- `create_stone_textures.py` — Procedural stone texture generation
- `merge_detection_datasets.py` — pHash dedup + merge + YAML generation
- `validate_dataset.py` — Full YOLO validation with visual previews

### Training (D-TRAIN)

**Architecture**: YOLO26s (January 2026 release) — NMS-free end-to-end with ProgLoss for small objects. Output shape `[1,300,6]` instead of old `[1,5,8400]` + NMS. Single-class detection (WHERE, not WHICH — classification is the separate model's job).

- **v1**: 88/150 epochs (12-hour Kaggle timeout). mAP50=0.710.
- **v2** (resumed from v1 checkpoint, 60 more epochs): mAP50=0.7515 test, Precision=0.721, Recall=0.692, AI fallback rate=2.1%.

Deployed `glyph_detector_uint8.onnx` at 9.9 MB.

### Integration (D-INTEGRATE — 17 tasks)

The output format change required rewriting both Python and JavaScript:
- `postprocess.py`: Entirely rewritten for `[1,300,6]` row format. Removed all NMS/merge code.
- `hieroglyph-pipeline.js`: `detect()` rewritten, `_nms()` and `_iou()` removed entirely.
- Tested: real stone images producing 3–35 detections, synthetic 8–22, blank images triggering AI fallback properly.

---

## Chapter 6: The Expansion

### Session 20: T1 + T4-P1 — Chat & Write Fixes

- **Thoth Chat formatting**: Fixed `renderMarkdown()` — proper heading hierarchy (H1 gold → H2 gold-light → H3 ivory), table rendering, list spacing, blockquote styling.
- **Write bugs**: Fixed template rendering, case sensitivity, Unicode handling, Smart mode button behavior.
- **Write AI mode**: Built reverse translation corpus (14,593 EN→MdC entries), Egyptologist AI persona prompt, Groq/Grok fallback chain, 60+ known phrase shortcuts. MdC alias fixes (j↔i, z→s). 96.3% of corpus entries successfully resolved.

### Session 20 (continued): T3 — Dictionary Expansion

The dictionary went from 177 signs to **1,023** across all 26 Gardiner categories. This required restructuring the data layer — a single Python file with 1,023 sign definitions and Unicode characters would be unmaintainable. Created `app/core/gardiner_data/` package with 26 files (a_man.py through aa_unclassified.py), plus a backward-compatible `gardiner.py` facade.

New API endpoints: pagination, `/alphabet` for learning the Egyptian alphabet, `/lesson/{1-5}` for a progressive course. Learn tab added to the dictionary page with 5 curated lessons.

### Session 21: T3.1 + T3.2 — Dictionary UX & Premium Learning

- Fixed display issues: "—" for silent determinatives, type-aware reading fields
- Added pronunciation guides and fun facts for 50 key signs
- Built premium learning experience: dedicated lesson pages (`lesson_page.html`), curated sign groups, progressive difficulty

### Session 21 (continued): T2 — Explore Expansion

Sites grew from 157 to **260+** landmarks across Egypt:
- 99 children sites (sub-sites within larger complexes)
- 25 parent sites with child relationships
- 8 attraction type categories (Pharaonic, Islamic, Coptic, Greco-Roman, Modern, Natural, Military, Experience)
- All 260 sites have 2–6 images (1,220 total image URLs)
- Added experience entries: Nile cruises, hot air balloon rides over Luxor
- Corrected Grand Egyptian Museum to "Inaugurated November 2025"

### Session 22: Final Features

- **Classifier v2**: Trained with stone-texture augmentation — 97.31% top-1 (slight drop from 98.18% v1), 55.63% stone-texture accuracy (beating the 50% target). Downloaded from Kaggle, deployed.
- **Cloudflare Workers AI**: Wired as Step 1c in the landmark identify fallback chain (Gemini→Groq→Cloudflare). Account verified, tokens in `.env`.
- **TLA API integration**: `tla_service.py` connecting to the Thesaurus Linguae Aegyptiae — 90,000 ancient Egyptian lemmas for translation reference.
- **L-LANDMARKS complete**: AI descriptions for all 260 sites using Gemini with disk-based enrichment cache. Groq Vision fallback for photo identification.
- **All 57 expansion tasks complete.**

---

## Chapter 7: Architecture & Design Decisions

### Why These Choices

**FastAPI + Jinja2 over Next.js/React**: A Python ML project should stay in Python. Server-side rendering with Jinja2 means one deployment, one language, one container. Alpine.js handles the interactivity that would otherwise need React (drag-and-drop, camera capture, progressive results, modals). HTMX handles the AJAX.

**Black & Gold**: Egyptian heritage deserves visual weight. Dark backgrounds make gold accents pop. The design system has 8 color tokens, 2 font families, and 10+ pre-built CSS animations — enough for consistency without rigidity.

**AI-First with ONNX Fallback**: Gemini Vision reads inscriptions better than any ONNX model we could train on available data. But Gemini needs internet. The ONNX pipeline works offline after first load via Service Worker. Auto mode tries both and cross-validates.

**11 Free API Providers**: Zero budget means maximizing free tiers. Gemini (17 keys × 20 RPD), Groq (8 keys), Grok (8 keys), Cloudflare Workers AI (10K requests/day), Voyage AI (200M token embedding/month), Cohere, OpenRouter, Google Cloud TTS (4M chars/month), ElevenLabs, Deepgram ($200 credit), TLA (free Egyptology API). Fallback chains ensure the app stays up even when one provider rate-limits.

**YOLO26s NMS-Free**: The January 2026 YOLO release removed NMS entirely — the network learns to suppress duplicates during training. Output is a clean `[1,300,6]` tensor, no post-processing needed (vs. the old `[1,5,8400]` + hand-written NMS in JS). This cut inference time by 43% vs YOLOv8s.

**PyTorch → ONNX (not Keras → tf2onnx)**: The Keras/TF.js stack failed because `tf2onnx` couldn't handle `_FusedConv2D` operations and wouldn't run on Kaggle due to DNS restrictions. PyTorch's `torch.onnx.export()` works natively, and `timm` provides every classifier architecture pretrained. Training in float32 only (no mixed precision) because ONNX doesn't preserve fused FP16 ops.

### The Numbers

| Metric | Value |
|--------|-------|
| Git commits | 38 |
| Development sessions | 22 |
| Base tasks (P0–P8) | 86 |
| Expansion tasks | 57 |
| Total tasks completed | 143 |
| Gardiner signs in dictionary | 1,023 |
| Heritage sites in explorer | 260+ |
| Detection training images | 10,311 |
| Hieroglyph classes | 171 |
| Landmark classes | 52 |
| Free AI providers integrated | 11 |
| Total API keys in rotation | 33+ |
| Python source files in app/ | 30+ |
| Template files | 12 |
| CSS animations | 10+ |
| Production model size (total) | ~42 MB |
| Runtime footprint | ~150 MB |

---

## Chapter 8: What's Next

The codebase is stable and deployed. Open development threads:

- **T4 Phase 2**: A real Egyptian translation engine — 500+ word lexicon, `write_translator.py`, shared service modules (groq_service.py, cloudflare_service.py, voyage_service.py, tts_service.py)
- **T5**: Landmark AI experience — multi-provider vision ensemble (Gemini→Groq Vision→Grok→Cloudflare→ONNX), weighted voting, richer identify results with top-3 and confidence meters, audio narration
- **Detector v3**: Training on Kaggle with the balanced 4,771-image dataset. Target: mAP50≥0.85, precision/recall≥0.80

The live demo runs at [huggingface.co/spaces/nadercr7/wadjet-v2](https://huggingface.co/spaces/nadercr7/wadjet-v2).

---

## Appendices

### A: Kaggle Dataset Locations

| Dataset | Slug | Size |
|---------|------|------|
| Hieroglyph Classification | `nadermohamedcr7/wadjet-hieroglyph-classification` | ~1 GB |
| Landmark Classification | `nadermohamedcr7/wadjet-landmark-classification` | ~15 GB |
| Detection v3 | `nadermohamedcr7/wadjet-hieroglyph-detection-v3` | 831 MB |
| Stone Textures | `nadermohamedcr7/wadjet-stone-textures` | 61 MB |

### B: Model Accuracy Summary

| Model | Architecture | Top-1 | Other |
|-------|-------------|-------|-------|
| Hieroglyph Classifier v1 | MobileNetV3-Small | 98.18% | Top-5: 99.91% |
| Hieroglyph Classifier v2 | MobileNetV3-Small | 97.31% | Stone: 55.63% |
| Landmark Classifier | EfficientNet-B0 | 93.80% | Top-3: 97.40% |
| Hieroglyph Detector v2 | YOLO26s | mAP50=0.7515 | P=0.721, R=0.692 |

### C: API Provider List

| Provider | Usage | Free Tier |
|----------|-------|-----------|
| Gemini | Primary AI (chat, vision, translation, embedding) | 17 keys × 20 RPD |
| Groq | Fallback AI, TTS, STT | 8 keys |
| Grok | Tiebreaker AI | 8 keys |
| Cloudflare Workers AI | Landmark identify fallback | 10K req/day |
| Voyage AI | Embeddings | 200M tokens/month |
| Cohere | Text generation fallback | Free tier |
| OpenRouter | Multi-model routing | Free tier |
| Google Cloud TTS | Server-side speech | 4M chars/month |
| ElevenLabs | Premium TTS | Free tier |
| Deepgram | STT | $200 credit |
| TLA | Ancient Egyptian lemma database | Free |

### D: Project Timeline

| Date | Sessions | Milestone |
|------|----------|-----------|
| Mar 19 | 1–10 | V2 foundation → full app (86 tasks across P0–P8) |
| Mar 20–21 | 11–13 | Model crisis → PyTorch rebuild on Kaggle |
| Mar 22–23 | 14–15 | Hieroglyph pipeline audit → 21 bugs documented |
| Mar 24 | 16 | Detector rebuild started (10,311 images, YOLO26s) |
| Mar 25 | 17–18 | H-FIX (19 bugs) + H-VISION (AI-first) complete |
| Mar 26 | 19–20 | H-TRANSLATE + H-AUDIO + expansion T1–T3 |
| Mar 27 | 21–22 | Dictionary 1,023 signs + Explore 260+ sites + final features |

---

*Built by Mr Robot*
