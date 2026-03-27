# Wadjet v2 — Constitution

> This document defines the non-negotiable rules and constraints for the Wadjet v2 project.
> Every feature, every PR, every AI session must respect these principles. The constitution
> supersedes any other document when there is a conflict.

---

## Core Principles

### I. Dual-Path Architecture
The app serves **two equal paths**: Hieroglyphs and Landmarks. Neither path is
primary or secondary. The landing page presents both equally and the user chooses.
- `/` → choice page (two paths)
- `/hieroglyphs` → hub for Scan, Dictionary, Write
- `/landmarks` → hub for Explore, Identify
- `/chat` → shared (Thoth AI, serves both paths)

### II. Black & Gold Design System (NON-NEGOTIABLE)
Every page must use the exact design tokens defined in `app/static/css/input.css`:
- **Background:** `--color-night: #0A0A0A` (near-black)
- **Surfaces:** `--color-surface: #141414`, `--color-surface-alt: #1E1E1E`
- **Gold accent:** `--color-gold: #D4AF37` (Egyptian gold)
- **Text:** `--color-text: #F0F0F0`, `--color-text-muted: #8A8A8A`
- **Typography:** Playfair Display (headings), Inter (body), Noto Sans Egyptian Hieroglyphs
- **Component classes:** `.btn-gold`, `.btn-ghost`, `.card`, `.card-glow`, `.badge-gold`, `.input`
- No light mode. No white backgrounds. No blue links. Always dark + gold.

### III. Stack Lock — No Substitutions
| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | FastAPI | 0.115+ |
| Templates | Jinja2 | 3.1+ |
| CSS | TailwindCSS v4 | 4.x (CLI) |
| Interactivity | Alpine.js | 3.14+ |
| Partial updates | HTMX | 2.0+ |
| Client ML (detect) | ONNX Runtime Web | 1.17+ |
| Client ML (classify) | ONNX Runtime Web | 1.17+ (PyTorch-exported) |
| Server ML | ONNX Runtime | 1.19+ |
| AI API | Gemini (google-genai) | 1.0+ |
| Translation | FAISS + bge-m3 | - |

> **Note**: TF.js and TensorFlow/Keras are being **removed** (Phase P8).
> New classifier is PyTorch → ONNX (not Keras/TF.js). Landmark identification is Gemini Vision (not a trained model).

**Forbidden:** React, Next.js, Vue, Svelte, any SPA framework. Jinja2 + Alpine.js is the rendering layer.

### IV. Zero Budget
- All services must be free tier: Render free, Gemini free API, Kaggle P100 free
- Gemini quota: 20 RPD per project across all 17 keys (same GCP project)
- No paid APIs, no paid hosting, no paid databases
- All ML models run locally (browser or server), not in cloud

### V. One Purpose Per Page
Each page does exactly one thing well. No cramming multiple features onto a single page.
- Generous whitespace, step-by-step flows, progressive disclosure
- Mobile-first responsive design (sm → md → lg breakpoints)
- Arabic RTL support where Arabic text appears (not for UI chrome)

### VI. Offline-Capable
Core scanning (detect → classify → transliterate) must work without internet after first load.
- Service Worker caches ML models (~31 MB total)
- Translation requires server (RAG + Gemini) — graceful fallback message
- Client-side pipeline: ONNX Runtime Web (detection) + TF.js (classification) + JS transliteration

### VII. Reuse v1 Code
Before writing new code, check if v1 already has a working implementation.
Asset mapping is in `planning/archive/PLAN.md` (archived v1→v2 asset map).
The active rebuild plan is in `planning/rebuild/MASTER_PLAN.md`.
- Adapt imports: `hieroglyph_model.src.*` → `app.core.*`
- Adapt paths: relative to Wadjet-v2 root, not v1 root
- Test adapted code before marking done

---

## Constraints

### File Size Limits
- Models are **git-ignored** (300+ MB total). Copied manually or via `scripts/copy_assets.py`
- Docker image: target < 500 MB (multi-stage build, slim base)
- CSS build output: `app/static/dist/styles.css` is git-ignored

### Naming Conventions
- Python: snake_case for files, functions, variables. PascalCase for classes.
- Templates: kebab-case for partials (e.g., `glyph-card.html`), snake_case for pages
- CSS: BEM-ish with Tailwind utility-first (no custom BEM classes)
- API routes: `/api/{resource}` for JSON, `/{page}` for HTML

### Quality
- Ruff linter: `ruff check` must pass (config in `pyproject.toml`)
- Every page tested at `localhost:8000` before marking task complete
- No unhandled exceptions in production — every pipeline stage has try/except
- All API endpoints return proper HTTP status codes + JSON errors

### TailwindCSS v4 Specifics
- Config in `@theme {}` block inside `input.css` (NOT `tailwind.config.js`)
- Never name a CSS variable `--color-bg` (conflicts with TW4 `bg-*` utility namespace)
- Use CLI build: `npx @tailwindcss/cli -i app/static/css/input.css -o app/static/dist/styles.css`
- Cache bust CSS link in `base.html`: `?v=N` (increment N after every CSS change)

---

## Governance

- This constitution supersedes all other documents when there is a conflict
- Amendments must be documented with date and rationale
- Every AI session should read this file first (referenced in PROMPTS.md)

**Version:** 1.0 | **Ratified:** 2026-03-19 | **Last Amended:** 2026-03-19
