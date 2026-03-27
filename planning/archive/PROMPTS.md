# Wadjet v2 — AI Prompts

> Two prompts for working with an AI assistant: one to START a phase, one to CONTINUE.
> Copy-paste the appropriate prompt into the chat to begin or resume work.

---

## START Prompt

Use this to **begin a new phase**. Replace `[PHASE_ID]` with the phase (e.g., `P2`, `P3`, `P4`).

```
I'm working on Wadjet v2 — an AI-powered Egyptian heritage web app with DUAL-PATH architecture:
- **Hieroglyphs path:** Scan hieroglyphs, translate inscriptions, dictionary, write in hieroglyphs
- **Landmarks path:** Explore 52 Egyptian landmarks, identify from photos
- **Shared:** Thoth AI chatbot, quiz

**Tech stack:** FastAPI + Jinja2 + TailwindCSS v4 + Alpine.js + HTMX, Python 3.13
**Design:** Black & Gold theme (dark bg #0A0A0A, gold accent #D4AF37)
**Fonts:** Playfair Display (headings) + Inter (body) + Noto Sans Egyptian Hieroglyphs

The project is at: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\
The OLD project (v1) with reusable code is at: D:\Personal attachements\Projects\Final_Horus\Wadjet\

Please read these files FIRST (in this order):
1. CLAUDE.md — Project instructions, full resource inventory, coding conventions
2. planning/CONSTITUTION.md — NON-NEGOTIABLE rules and constraints (supersedes everything)
3. planning/PLAN.md — Master plan with architecture, design system, asset mapping
4. planning/PROGRESS.md — Phase tracker with all tasks
5. planning/SESSION_LOG.md — What happened in previous sessions

For up-to-date library docs, use context7 MCP server:
- FastAPI: resolve `/tiangolo/fastapi` then fetch docs
- TailwindCSS v4: resolve `/tailwindlabs/tailwindcss` then fetch docs
- Alpine.js: resolve `/alpinejs/alpine` then fetch docs

Then start working on Phase [PHASE_ID]. For each task:
1. Read the task description from PROGRESS.md
2. Do the work (create files, write code, copy assets)
3. Test that it works
4. Mark the task ✅ in PROGRESS.md
5. Move to the next task

When the phase is complete, update SESSION_LOG.md with what was done.

Rules:
- Read CONSTITUTION.md first — it overrides everything else
- Follow the design system exactly (colors, fonts, components from PLAN.md)
- Reuse code from v1 where the asset mapping in PLAN.md says to
- Keep pages simple and uncluttered — one purpose per page
- Step-by-step UX flows with progressive disclosure
- Mobile-first responsive design
- Test every page at localhost:8000 before marking done
- Arabic RTL support where text is Arabic
- Update PROGRESS.md after EVERY completed task (not in batches)
- NEVER use `--color-bg` in TailwindCSS v4 (conflicts with `bg-*` utility — use `--color-night`)
- CSS animations available: shimmer, fade-up, pulse-gold, btn-shimmer, gradient-sweep, border-beam, meteor, dot-glow, shine
- CSS hover effects: hvr-glow, hvr-sweep-gold, hvr-underline-gold, hvr-float-gold, hvr-grow
- 3D parallax: add `data-atropos` attribute to cards for Atropos tilt effect
- Scroll animations: add `data-animate` attribute to elements for GSAP scroll-triggered fade-in
- For feature specs, use templates in planning/templates/ (spec-template.md)
- Load relevant skills from CLAUDE.md "Skills" table when working on specific areas
- Run `scripts/copy_assets.py --dry-run` before copying v1 assets
```

---

## CONTINUE Prompt

Use this to **resume work** after a break or new chat session.

```
I'm continuing work on Wadjet v2 — an AI-powered Egyptian heritage web app with DUAL-PATH architecture (Hieroglyphs + Landmarks).

Project: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\
Old v1 project: D:\Personal attachements\Projects\Final_Horus\Wadjet\

Please read (in this order):
1. CLAUDE.md — Project instructions, full resource inventory, coding conventions
2. planning/CONSTITUTION.md — NON-NEGOTIABLE rules (read first, supersedes everything)
3. planning/PLAN.md — Full architecture and design system
4. planning/PROGRESS.md — See what's done (✅) and what's next (⬜)
5. planning/SESSION_LOG.md — Last session's notes and "Next session" section

For up-to-date library docs, use context7 MCP server:
- FastAPI: `/tiangolo/fastapi` | TailwindCSS v4: `/tailwindlabs/tailwindcss` | Alpine.js: `/alpinejs/alpine`

Then pick up from the first ⬜ task and continue working. Follow the same rules:
- CONSTITUTION.md overrides all other docs
- Match the Black & Gold design system from PLAN.md
- Mark each task ✅ in PROGRESS.md immediately after completing it
- NEVER use `--color-bg` in TailwindCSS v4 (use `--color-night` instead)
- Test at localhost:8000
- When the current phase is done, update SESSION_LOG.md
- Then ask me before starting the next phase
```

---

## Phase-Specific Notes

### P0: Foundation
- Create venv with `python -m venv .venv`
- TailwindCSS v4: use standalone CLI (download from GitHub releases for Windows)
- Base template needs: `<script src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js" defer></script>`
- HTMX: `<script src="https://unpkg.com/htmx.org@2.0.4"></script>`
- Dev command: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### P1: Design System
- All colors as CSS custom properties in input.css `@theme` block
- Google Fonts: Playfair Display (700) + Inter (400, 500, 600)
- Hieroglyph font: copy from v1 `hieroglyph_model/data/reference/fonts/`
- Component classes: define in input.css `@layer components {}`

### P2: Scan Feature
- Copy pipeline files listed in PLAN.md "Reusable Assets" table
- Adapt import paths (v1 uses `hieroglyph_model.src.*`, v2 uses `app.core.*`)
- Both server-side (Python pipeline) and client-side (JS pipeline) paths
- Camera access requires HTTPS or localhost
- **Skills:** `fastapi-pro`, `fastapi-router-py`, `file-uploads`, `async-python-patterns`

### P3: Dictionary & Write
- Gardiner data: 700+ signs from gardiner_mapping.py
- Categories: A-Aa (26 categories + Aa)
- Write feature needs mapping from text → Unicode hieroglyphs
- **Skills:** `programmatic-seo` (template-based dictionary pages), `schema-markup` (JSON-LD for glyphs)

### P4: Explore
- 52 landmarks from attractions_data.py
- 55 metadata JSONs, 50 text descriptions
- Gemini generates AI descriptions on-demand
- **Skills:** `schema-markup` (landmark structured data), `seo-meta-optimizer`

### P5: AI Features
- Thoth: streaming chat via Gemini
- Quiz: generated from glyph + landmark data
- Gemini quota: 20 RPD, 10 RPM — implement delays
- **Skills:** `llm-app-patterns`, `prompt-engineering`, `prompt-engineering-patterns`
- **Resources:** `Repos/20-Prompts-GPT/` for Thoth system prompt inspiration

### P6: Polish
- Service Worker: cache models (31 MB total) for offline scan
- History: localStorage with 20-item cap, keyed by timestamp
- Share: Canvas API to render result as PNG
- **Skills:** `web-performance-optimization`, `wcag-audit-patterns`, `i18n-localization`, `scroll-experience`, `analytics-tracking`, `seo-audit`

### P7: Deploy
- Dockerfile and docker-compose.yml already exist — refine as needed
- render.yaml already configured for Render.com free tier
- Docker multi-stage: Python slim + TailwindCSS build
- Render.com free tier: 512 MB RAM, spin-down after 15 min
- Health check: GET /api/health returns 200
- **Skills:** `docker-expert`, `deployment-engineer`, `render-automation`
