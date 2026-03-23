# Wadjet v2 — Master Plan

## Summary

Wadjet v2 is a ground-up rebuild of the Wadjet Egyptian heritage web application.
The previous version (v1) suffered from an architectural split: the home page used a
landmark classifier while all hieroglyph work (9 months of ML development) was hidden
on a secondary page. This rebuild unifies everything into a single, polished SaaS-style
application with a Black & Gold design, step-by-step UX flows, and professional-grade UI.

**One-liner:** An AI-powered Egyptian heritage app — scan hieroglyphs, translate
inscriptions, explore landmarks, and learn from Thoth the chatbot.

---

## Technical Context

### Language & Runtime
- **Backend:** Python 3.13 / FastAPI 0.115+
- **Templates:** Jinja2 with layout inheritance
- **CSS:** TailwindCSS v4 (standalone CLI)
- **Interactivity:** Alpine.js v3 + HTMX 2.x
- **Client ML:** ONNX Runtime Web 1.17+ / TensorFlow.js 4.x
- **Icons:** Lucide (inline SVG)

### Key Dependencies
| Package | Purpose |
|---|---|
| `fastapi` + `uvicorn` | Web framework + ASGI server |
| `jinja2` | Server-side templates |
| `python-multipart` | File upload handling |
| `pillow` | Image processing |
| `numpy` | Array ops |
| `onnxruntime` | Server-side YOLO detection |
| `tensorflow` | Keras model inference (server) |
| `google-genai` | Gemini API (translation, chat, descriptions) |
| `faiss-cpu` | Vector search for RAG translation |
| `sentence-transformers` | bge-m3 embeddings |
| `pydantic` | Data validation (v2) |
| `pydantic-settings` | Env-based config |

### ML Models (Carried from v1)
| Model | Format | Size | Purpose |
|---|---|---|---|
| YOLOv8s ONNX | `glyph_detector_uint8.onnx` | 11 MB | Hieroglyph detection |
| EfficientNetV2-S TF.js | `model.json` + 5 shards | 20 MB | Browser glyph classification |
| EfficientNetV2-S Keras | `efficientnet_v2s.keras` | 222 MB | Server glyph classification |
| Label mapping | `label_mapping.json` | 87 KB | 172 Gardiner classes |
| Landmark TF.js | `model.json` + 10 shards | 39 MB | 52-class landmark ID |
| FAISS index | `corpus.index` | 21 MB | RAG translation retrieval |
| TLA Corpus | `corpus.jsonl` | 2 MB | 15,604 translation pairs |

### Storage
- **Models:** `models/` directory (hieroglyph + landmark subdirs)
- **Data:** `data/` directory (translation corpus, landmark metadata)
- **User state:** Browser localStorage (history, preferences)
- **Cache:** In-memory (pipeline singletons, Gemini response cache)

### Platform
- **Dev:** Local Python venv + TailwindCSS standalone CLI
- **Production:** Docker container on Render (free tier)
- **CI:** None initially (manual deploy)

---

## Design System

### Color Palette
```
--color-night:        #0A0A0A     (near-black background)
--color-surface:      #141414     (card backgrounds)
--color-surface-alt:  #1E1E1E     (elevated surfaces)
--color-border:       #2A2A2A     (subtle borders)
--color-border-light: #3A3A3A     (hover borders)
--color-gold:         #D4AF37     (primary accent — Egyptian gold)
--color-gold-light:   #E8C547     (hover/active gold)
--color-gold-dark:    #B8941F     (muted gold)
--color-gold-glow:    #D4AF3720   (gold at 12% for glow effects)
--color-text:         #F0F0F0     (primary text)
--color-text-muted:   #8A8A8A     (secondary text)
--color-success:      #4CAF50     (success green)
--color-error:        #EF4444     (error red)
--color-warning:      #F59E0B     (warning amber)
```

### Typography
| Role | Font | Weight | Fallback |
|---|---|---|---|
| Display / H1 | Playfair Display | 700 | Georgia, serif |
| Headings H2-H4 | Playfair Display | 600 | Georgia, serif |
| Body | Inter | 400, 500, 600 | system-ui, sans-serif |
| Code / Technical | JetBrains Mono | 400 | monospace |
| Hieroglyphs | Noto Sans Egyptian Hieroglyphs | 400 | serif |

### Component Classes
- `.btn-gold` — Primary gold CTA (gradient, hover glow)
- `.btn-ghost` — Transparent with gold border
- `.btn-dark` — Dark bg with subtle border
- `.card` — Surface bg, border, rounded-xl, hover lift
- `.card-glow` — Card with gold glow on hover
- `.badge` — Small label (gold, success, muted variants)
- `.input` — Dark bg input with gold focus ring
- `.section` — Page section with consistent padding
- `.container-narrow` — Max-w-4xl centered content

### Animations & Interactions
- **Page enter:** Fade up (Alpine.js x-transition)
- **Cards:** Hover lift + subtle gold glow (`.hvr-glow`, `.hvr-float-gold`)
- **Cards 3D:** Atropos parallax tilt on hover (`data-atropos` on cards)
- **Buttons:** Shimmer sweep on hover (`.btn-shimmer`)
- **Gold text:** Animated gradient sweep (`.text-gold-animated`)
- **Nav links:** Underline from center (`.hvr-underline-gold`)
- **Loading:** Gold pulse dots or spinning ankh
- **Scroll:** GSAP ScrollTrigger fade-in (`data-animate` attribute)
- **Smooth scroll:** Lenis smooth scroll (auto-init in app.js)
- **Decorative:** Border beam, meteors, dot pattern backgrounds

---

## Architecture

### Project Structure
```
Wadjet-v2/
├── planning/             # Project management
│   ├── PLAN.md           # This file
│   ├── CONSTITUTION.md   # Non-negotiable rules and constraints
│   ├── PROGRESS.md       # Phase tracker
│   ├── SESSION_LOG.md    # Session history
│   ├── PROMPTS.md        # AI prompts (start + continue)
│   ├── CHECKLIST.md      # Pre-flight checklist
│   └── templates/        # Spec-kit templates for features
│       ├── spec-template.md
│       ├── tasks-template.md
│       └── checklist-template.md
│
├── app/                  # FastAPI application
│   ├── __init__.py
│   ├── main.py           # App factory, middleware, static mount
│   ├── config.py         # Pydantic Settings (env-based)
│   ├── dependencies.py   # Dependency injection (pipeline, gemini)
│   │
│   ├── api/              # Route modules
│   │   ├── __init__.py
│   │   ├── pages.py      # HTML page routes (GET /)
│   │   ├── scan.py       # POST /api/scan, /api/recognize
│   │   ├── translate.py  # POST /api/translate
│   │   ├── dictionary.py # GET /api/dictionary, /api/signs
│   │   ├── explore.py    # GET /api/landmarks
│   │   ├── chat.py       # POST /api/chat
│   │   └── health.py     # GET /api/health
│   │
│   ├── core/             # Business logic (adapted from v1)
│   │   ├── __init__.py
│   │   ├── hieroglyph_pipeline.py  # E2E detect→classify→translit→translate
│   │   ├── gemini_service.py       # Gemini wrapper (key rotation, retry)
│   │   ├── rag_translator.py       # FAISS RAG + Gemini translation
│   │   ├── gardiner.py             # Gardiner sign mapping (700+ signs)
│   │   ├── reading_order.py        # Glyph reading-order algorithm
│   │   ├── thoth_chat.py           # Thoth chatbot logic
│   │   ├── landmarks.py            # Landmark data + identification
│   │   └── quiz.py                 # Quiz engine
│   │
│   ├── utils/            # Utility modules
│   │   └── __init__.py
│   │
│   ├── static/           # Frontend assets
│   │   ├── css/
│   │   │   ├── input.css           # TailwindCSS source + animations
│   │   │   └── atropos.css         # Atropos 3D parallax styles
│   │   ├── dist/
│   │   │   └── styles.css          # Built TailwindCSS output
│   │   ├── js/
│   │   │   ├── app.js              # Alpine.js + HTMX + Atropos + GSAP init
│   │   │   ├── scan.js             # Scan page (camera, upload, results)
│   │   │   ├── hieroglyph-pipeline.js  # Client ML (ONNX + TF.js)
│   │   │   └── chat.js             # Chat streaming UI
│   │   ├── fonts/
│   │   │   └── NotoSansEgyptianHieroglyphs-Regular.ttf
│   │   └── images/
│   │       ├── logo.svg
│   │       └── og-image.png
│   │
│   └── templates/        # Jinja2 templates
│       ├── base.html               # Master layout (nav, footer, scripts)
│       ├── landing.html            # Home — dual-path choice page
│       ├── hieroglyphs.html        # Hieroglyphs hub page
│       ├── landmarks.html          # Landmarks hub page
│       ├── scan.html               # Scan hieroglyphs
│       ├── write.html              # Write in hieroglyphs
│       ├── dictionary.html         # Gardiner dictionary
│       ├── explore.html            # Explore landmarks
│       ├── landmark.html           # Single landmark detail
│       ├── chat.html               # Thoth chatbot
│       └── partials/
│           ├── nav.html            # Navigation bar
│           ├── footer.html         # Footer
│           ├── glyph-card.html     # Reusable glyph display card
│           └── landmark-card.html  # Reusable landmark card
│
├── models/               # ML models (copied from v1, git-ignored)
│   ├── hieroglyph/
│   │   ├── detector/               # glyph_detector_uint8.onnx
│   │   ├── classifier/             # TF.js model.json + shards
│   │   ├── classifier_keras/       # efficientnet_v2s.keras
│   │   └── label_mapping.json
│   └── landmark/
│       └── tfjs/                   # model.json + 10 shards
│
├── data/                 # Data files (copied from v1, git-ignored)
│   ├── translation/                # corpus.jsonl, corpus.index, corpus_ids.json
│   ├── metadata/                   # 55 landmark JSON files
│   ├── text/                       # 50 landmark description files
│   └── reference/                  # Gardiner PDFs, fonts
│
├── pyproject.toml        # Project metadata + tool config
├── requirements.txt      # Python dependencies
├── tailwind.config.js    # TailwindCSS theme configuration
├── Dockerfile            # Production container
├── docker-compose.yml    # Local Docker dev
├── render.yaml           # Render.com deploy config
├── .env.example          # Environment variable template
├── .gitignore
├── CLAUDE.md             # AI assistant project instructions
└── README.md
```

### Request Flow
```
Browser → FastAPI Router → Jinja2 Template (HTML pages)
                        → API Handler → Core Service → Response (JSON)

Scan Flow:
  User uploads image
  → POST /api/scan (multipart/form-data)
  → hieroglyph_pipeline.detect(image)     # YOLO ONNX
  → hieroglyph_pipeline.classify(crops)   # EfficientNet Keras
  → hieroglyph_pipeline.transliterate()   # Gardiner mapping
  → hieroglyph_pipeline.translate()       # RAG + Gemini
  → JSON response (glyphs, transliteration, translation)
  → Alpine.js renders results step-by-step

Client-Side Scan (offline-capable):
  Camera frame / uploaded image
  → hieroglyph-pipeline.js
  → ONNX Runtime Web (detection)
  → TF.js (classification)
  → JS transliteration (Gardiner map)
  → Display results (no server needed for detect+classify+translit)
  → POST /api/translate for RAG translation (requires server)
```

### Key Principles
1. **Equal dual-path** — Landing page presents two equal paths: Hieroglyphs and Landmarks. Users choose their journey.
2. **Step-by-step flows** — Each feature walks the user through clear steps
3. **Uncluttered pages** — One purpose per page, generous whitespace
4. **Progressive disclosure** — Show results incrementally, not all at once
5. **Offline-capable** — Client-side pipeline for core scan functionality
6. **Mobile-first** — All pages responsive, touch-friendly
7. **Black & Gold** — Consistent dark theme with gold accents everywhere

---

## Pages & User Flows

### 1. Landing Page (`/`)
- Hero: "Unlock the Secrets of Egypt" + badge "AI-Powered Egyptian Heritage"
- Two large side-by-side path cards:
  - **Hieroglyphs** → `/hieroglyphs` — Scan, Translate, Dictionary, Write
  - **Landmarks** → `/landmarks` — Explore 52 sites, Identify from photo
- Shared AI features section (Thoth, 2 ML Models, Offline)
- Footer with grouped links

### 1b. Hieroglyphs Hub (`/hieroglyphs`)
- Sub-hero with hieroglyph path branding
- Tool cards: Scan & Identify, Dictionary, Write
- How scanning works (3 steps)
- Bottom CTA → `/scan`

### 1c. Landmarks Hub (`/landmarks`)
- Sub-hero with landmarks path branding
- Tool cards: Explore All Sites, Identify from Photo
- 52 landmarks preview (Temples, Pyramids, Museums, Tombs)
- Bottom CTA → `/explore`

### 2. Scan (`/scan`)
- **Step 1:** Upload image or use camera
- **Step 2:** Detection runs → bounding boxes drawn on image
- **Step 3:** Classification → each glyph identified with Gardiner code
- **Step 4:** Transliteration → phonetic reading shown
- **Step 5:** Translation → English/Arabic meaning displayed
- Each step animates in sequentially

### 3. Dictionary (`/dictionary`)
- Category grid (Animals, Body Parts, Buildings, etc.)
- Click category → grid of glyph cards
- Each card: hieroglyph unicode, Gardiner code, transliteration, meaning
- Search bar for quick lookup
- Click glyph → detail popover

### 4. Write (`/write`)
- Text input → hieroglyph output
- Gardiner palette (clickable sign picker)
- Composition area showing built hieroglyphs
- Copy/share composed text

### 5. Explore (`/explore`)
- Category tabs (Temples, Pyramids, Museums, etc.)
- Landmark cards with image, name, brief info
- Click → detail page with AI-generated description
- Upload photo to identify landmark

### 6. Chat (`/chat`)
- Thoth chatbot interface
- Streaming message display
- Pre-set conversation starters
- Multi-turn context

### 7. Quiz (`/quiz`)
- Multiple choice hieroglyph questions
- Progressive difficulty
- Score tracking

---

## Reusable Assets from v1

### Critical (copy directly)
| Source (v1) | Destination (v2) | Notes |
|---|---|---|
| `hieroglyph_model/src/pipeline/pipeline.py` | `app/core/hieroglyph_pipeline.py` | Adapt imports |
| `hieroglyph_model/src/transliteration/gardiner_mapping.py` | `app/core/gardiner.py` | As-is |
| `hieroglyph_model/src/transliteration/engine.py` | `app/core/transliteration.py` | As-is |
| `hieroglyph_model/src/transliteration/reading_order.py` | `app/core/reading_order.py` | As-is |
| `hieroglyph_model/src/translation/rag_translator.py` | `app/core/rag_translator.py` | Adapt paths |
| `hieroglyph_model/src/detection/postprocess.py` | `app/core/postprocess.py` | As-is |
| `app/core/gemini_service.py` | `app/core/gemini_service.py` | Adapt imports |
| `app/core/thoth_chat.py` | `app/core/thoth_chat.py` | Adapt imports |
| `app/core/attractions_data.py` | `app/core/landmarks.py` | Adapt |
| `app/core/hieroglyphs_data.py` | `app/core/hieroglyphs_data.py` | As-is |
| `app/static/js/hieroglyph-pipeline.js` | `app/static/js/hieroglyph-pipeline.js` | Adapt paths |
| `hieroglyph_model/data/reference/fonts/*.ttf` | `app/static/fonts/` | Copy |

### Models (copy to models/)
- `hieroglyph_model/models/detection/glyph_detector_uint8.onnx` → `models/hieroglyph/detector/`
- `hieroglyph_model/models/tfjs_uint8/*` → `models/hieroglyph/classifier/`
- `hieroglyph_model/models/classification/efficientnet_v2s.keras` → `models/hieroglyph/classifier_keras/`
- `hieroglyph_model/data/processed/label_mapping.json` → `models/hieroglyph/`
- `app/static/model/*` → `models/landmark/tfjs/`

### Data (copy to data/)
- `hieroglyph_model/data/translation/*` → `data/translation/`
- `hieroglyph_model/data/embeddings/*` → `data/translation/`
- `data/metadata/*` → `data/metadata/`
- `data/text/*` → `data/text/`

---

## Constraints & Rules

1. **Budget:** $0 — free tier only (Render, Gemini free, no paid services)
2. **Gemini API:** 20 RPD per model per project across all 17 keys (same project)
3. **No React/Next.js** — Jinja2 + Alpine.js + HTMX for simplicity
4. **Single deployment** — one Docker container serves everything
5. **Models git-ignored** — too large for git, copied manually or via script
6. **Arabic support** — RTL layout for Arabic text, UI labels in English
7. **Ruff compliant** — no unicode in docstrings, clean Python
8. **Accessibility** — semantic HTML, ARIA labels, keyboard navigation
9. **User language:** Arabic (Egyptian dialect) — the developer communicates in Arabic

---

## External Resources & Libraries

### CDN Libraries (loaded in base.html)
| Library | Purpose | CDN |
|---------|---------|-----|
| Alpine.js 3.14 | Reactive UI state | jsdelivr |
| HTMX 2.0.4 | AJAX partial updates | unpkg |
| Atropos.js 2 | 3D parallax card tilt | jsdelivr |
| GSAP 3 + ScrollTrigger | Scroll animations | jsdelivr |
| Lenis 1 | Smooth scroll | jsdelivr |

### CSS Animation Library (in input.css)
All extracted from magicui, Hover.css — adapted for Black & Gold theme.

**Keyframe animations**: shimmer, fade-up, pulse-gold, btn-shimmer, gradient-sweep, border-beam, meteor, dot-glow, shine

**Component classes**: `.text-gold-animated`, `.dot-pattern`, `.dot-pattern-gold`, `.meteor`, `.border-beam`, `.btn-shimmer`

**Hover effects**: `.hvr-glow` (gold glow), `.hvr-sweep-gold` (background sweep), `.hvr-underline-gold` (nav link underline), `.hvr-float-gold` (float + shadow), `.hvr-grow` (scale up)

**3D parallax**: `.atropos` CSS in `atropos.css`, init via `data-atropos` attribute + app.js

**Scroll animations**: `data-animate` attribute on any element — GSAP auto-animates on scroll entry

### AI Skills Reference (from Repos/antigravity-awesome-skills)
Full mapping in `CLAUDE.md` — load the relevant skill when working on each phase.

### Feature Spec Templates (from Repos/spec-kit)
Copied to `planning/templates/` — use `spec-template.md` before building any feature, `tasks-template.md` to break into tasks, `checklist-template.md` for validation.

### Context7 MCP (Live Documentation)
- FastAPI: `/tiangolo/fastapi`
- TailwindCSS v4: `/tailwindlabs/tailwindcss`
- Alpine.js: `/alpinejs/alpine`
