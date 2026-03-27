# Wadjet v2 — Project Instructions

> Comprehensive project context: tech stack, design system, routes, commands, conventions.
> Read alongside `planning/CONSTITUTION.md` before making any changes.

---

## Project Identity

**Wadjet v2** is an AI-powered Egyptian heritage web app with **dual-path architecture**:
- **Hieroglyphs path**: Scan → Detect → Classify → Translate hieroglyphs, Dictionary (1,000+ Gardiner signs), Write in hieroglyphs
- **Landmarks path**: Explore 260+ Egyptian landmarks, Identify from photos
- **Shared**: Thoth AI chatbot (Gemini-powered), Quiz

**One-liner**: Scan hieroglyphs, translate inscriptions, explore landmarks, learn from Thoth.

---

## Tech Stack (Locked — No Substitutions)

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | FastAPI | 0.115+ |
| Runtime | Python | 3.13 |
| Templates | Jinja2 | Layout inheritance |
| CSS | TailwindCSS | v4.2.2 (CLI) |
| Interactivity | Alpine.js | 3.14 (CDN) |
| AJAX | HTMX | 2.0.4 (CDN) |
| Client ML | ONNX Runtime Web + TF.js | 1.17+ / 4.x |
| AI | Gemini API | 17-key rotation |
| Icons | Lucide | Inline SVG |
| 3D Effects | Atropos.js | CDN |
| Scroll | GSAP ScrollTrigger + Lenis | CDN |

---

## Design System — Black & Gold (NON-NEGOTIABLE)

### Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--color-night` | `#0A0A0A` | Page background |
| `--color-surface` | `#141414` | Card/section background |
| `--color-gold` | `#D4AF37` | Primary accent, CTAs, highlights |
| `--color-gold-light` | `#E5C76B` | Hover states, secondary gold |
| `--color-gold-dark` | `#B8962E` | Active states |
| `--color-sand` | `#C4A265` | Muted text, subtle elements |
| `--color-ivory` | `#F5F0E8` | Primary text on dark |
| `--color-dust` | `#8B7355` | Disabled / tertiary text |

### Fonts
- **Headings**: Playfair Display (600, 700) — elegant serif
- **Body**: Inter (400, 500, 600) — clean sans-serif
- **Hieroglyphs**: Noto Sans Egyptian Hieroglyphs — Unicode glyphs

### Critical CSS Rule
**NEVER** use `--color-bg` as a variable name in TailwindCSS v4. It conflicts with the `bg-*` utility namespace. Always use `--color-night` instead.

### Available CSS Animations
Pre-built in `input.css`:
- `shimmer` — scanning line effect
- `fade-up` — entry reveal
- `pulse-gold` — gold pulse glow
- `btn-shimmer` — button perimeter light
- `gradient-sweep` — animated gold gradient text
- `border-beam` — orbiting border glow
- `meteor` — falling gold streaks
- `dot-glow` — pulsing dot pattern
- `shine` — border shine sweep

### Component Classes
Defined in `input.css @layer components`:
- `.btn-gold` — primary CTA button
- `.btn-ghost` — outlined secondary button
- `.card` — dark surface card
- `.card-glow` — card with gold hover glow
- `.badge-gold` — small gold badge
- `.input` — styled form input
- `.text-gold-animated` — animated gradient text
- `.dot-pattern` / `.dot-pattern-gold` — background dots
- `.meteor` — meteor streak element
- `.border-beam` — border beam animation

---

## Project Structure

```
Wadjet/
├── app/
│   ├── main.py              # create_app() factory
│   ├── config.py             # Pydantic Settings
│   ├── dependencies.py       # get_settings() DI
│   ├── api/
│   │   ├── health.py         # GET /api/health
│   │   └── pages.py          # 8 HTML routes
│   ├── core/                  # Business logic (P2+)
│   ├── utils/                 # Utilities
│   ├── static/
│   │   ├── css/input.css      # TailwindCSS source
│   │   ├── dist/styles.css    # Compiled CSS (git-ignored)
│   │   ├── js/app.js          # Alpine.js + HTMX globals
│   │   ├── fonts/             # Hieroglyph font (after copy)
│   │   └── images/            # Static images (after copy)
│   └── templates/
│       ├── base.html          # Master layout
│       ├── landing.html       # Dual-path choice hub
│       ├── hieroglyphs.html   # Hieroglyphs hub
│       ├── landmarks.html     # Landmarks hub
│       ├── scan.html, dictionary.html, write.html, explore.html, chat.html
│       └── partials/          # nav.html, footer.html
├── models/                    # ML models (production ONNX + TF.js)
├── data/                      # Runtime data (embeddings, metadata, corpus)
├── planning/                  # CONSTITUTION, PLAN, PROGRESS, PROMPTS, SESSION_LOG, CHECKLIST
├── scripts/                   # Build & data scripts
├── Dockerfile                 # Multi-stage production build
├── docker-compose.yml         # Local container setup
└── render.yaml                # Render.com deploy config
```

---

## Routes

| Route | Template | Path |
|-------|----------|------|
| `/` | landing.html | Choice hub |
| `/hieroglyphs` | hieroglyphs.html | Hieroglyphs hub |
| `/landmarks` | landmarks.html | Landmarks hub |
| `/scan` | scan.html | Hieroglyph scanner |
| `/dictionary` | dictionary.html | Gardiner dictionary |
| `/write` | write.html | Write in hieroglyphs |
| `/explore` | explore.html | Landmark explorer |
| `/chat` | chat.html | Thoth AI chatbot |
| `/api/health` | JSON | Health check |

---

## Development Commands

```bash
# Activate venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Unix

# Install dependencies
pip install -r requirements.txt
npm install

# Build CSS
npm run build                   # One-time minified build
npm run watch                   # Watch mode for development

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Copy assets from v1
python scripts/copy_assets.py --dry-run    # Preview
python scripts/copy_assets.py --execute    # Copy

# Docker
docker build -t wadjet .
docker-compose up
```

---

## External Resources (from D:\Personal attachements\Repos\)

### Skills (antigravity-awesome-skills)
Load these skills when working on specific areas:

| Phase / Task | Skills to Load |
|-------------|---------------|
| **P2: Scan Feature** | `fastapi-pro`, `fastapi-router-py`, `file-uploads`, `async-python-patterns` |
| **P3: Dictionary** | `programmatic-seo` (template-based pages at scale), `schema-markup` (JSON-LD for glyphs) |
| **P4: Explore** | `schema-markup` (landmark structured data), `seo-meta-optimizer` |
| **P5: AI Features** | `llm-app-patterns`, `prompt-engineering`, `prompt-engineering-patterns` |
| **P6: Polish** | `web-performance-optimization`, `accessibility-compliance-accessibility-audit`, `wcag-audit-patterns`, `i18n-localization`, `scroll-experience`, `analytics-tracking` |
| **P7: Deploy** | `docker-expert`, `deployment-engineer`, `render-automation` |
| **Design** | `tailwind-patterns`, `tailwind-design-system`, `theme-factory`, `frontend-design`, `ui-ux-pro-max` |
| **SEO** | `seo-fundamentals`, `seo-audit`, `seo-structure-architect`, `schema-markup`, `seo-meta-optimizer` |
| **Security** | `backend-security-coder`, `frontend-security-coder`, `auth-implementation-patterns` |

### Animation Libraries (extract CSS, don't import React)
| Library | Location | What to Extract |
|---------|----------|----------------|
| magicui | `Repos/21-Frontend-UI/magicui/` | CSS @keyframes from `registry-ui.ts` |
| animate-ui | `Repos/21-Frontend-UI/animate-ui/` | Background/button CSS effects |
| motion-primitives | `Repos/21-Frontend-UI/motion-primitives/` | Spotlight, glow, text effects |
| react-bits | `Repos/21-Frontend-UI/react-bits/` | Background effects (Silk, Iridescence), text anims |
| Hover.css | `Repos/21-Frontend-UI/Hover/` | Pure CSS hover transitions |
| Atropos | `Repos/21-Frontend-UI/atropos/` | 3D parallax card tilt (vanilla JS) |

### Templates (spec-kit)
| Template | When to Use |
|----------|------------|
| `spec-template.md` | Before building any new feature — write spec first |
| `tasks-template.md` | Breaking a spec into tasks |
| `checklist-template.md` | Pre-launch validation |

### Chatbot Resources (20-Prompts-GPT)
| Resource | Value |
|----------|-------|
| `awesome-chatgpt-prompts/prompts.csv` | Prompt database for Thoth personality |
| `system-prompts-and-models-of-ai-tools/` | Real system prompts from deployed products |
| `TheBigPromptLibrary/SystemPrompts/` | Production system prompt examples |

### Context7 MCP (Live Documentation)
Use context7 to fetch up-to-date docs during development:
- FastAPI: resolve `/tiangolo/fastapi`
- TailwindCSS v4: resolve `/tailwindlabs/tailwindcss`
- Alpine.js: resolve `/alpinejs/alpine`

---

## Archive Reference

The `archive/` folder contains the full project history:
- **original-horus/**: The original Horus AI Flask project (app.py, Keras model, PDFs, video)
- **v1-reference/**: Key files from Wadjet v1 (core/*.py, js/*.js, templates/)
- **v2-training/**: Training artifacts (DATA_CATALOG.md, Kaggle results, old model versions)
- **v2-scripts/**: 51 old utility scripts (data prep, TF/Keras migration)
- **v2-notebooks/**: Kaggle training notebooks (5 total)

See `JOURNEY.md` for the full development narrative.

---

## Coding Conventions

1. **Python**: Format with `ruff`, type hints on function signatures, async where I/O-bound
2. **Templates**: Jinja2 `{% extends "base.html" %}`, use `{% block %}` for content/head/scripts
3. **CSS**: Use TW4 utility classes; custom styles in `input.css` under `@layer components`
4. **JS**: Alpine.js `x-data` for state, HTMX `hx-get`/`hx-post` for server interaction
5. **Naming**: snake_case Python, kebab-case CSS classes, camelCase JS
6. **Files**: One purpose per file, max 300 lines before splitting
7. **Cache busting**: Bump `?v=N` in base.html `<link>` after CSS changes

---

## Footer

"Built by Mr Robot" — this is the footer attribution. Do not change.
