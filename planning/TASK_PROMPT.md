# Wadjet — Task Prompt

> Copy this entire file into a new chat session.
> Replace `[TASK DESCRIPTION]` with what you want to do.
> Attach `CLAUDE.md` as the project instructions file.

---

## Your Task

**[TASK DESCRIPTION]**

---

## Project Context

You are working on **Wadjet**, an Egyptian heritage web app at:
```
D:\Personal attachements\Projects\Wadjet
```

**Git**: Branch `clean-main` → remotes `origin` (GitHub) + `hf` (HuggingFace Spaces).

**Stack**: FastAPI 0.115 + Jinja2 + TailwindCSS v4 + Alpine.js 3.14 + HTMX 2.0 + ONNX Runtime.  
**Design**: Black & Gold (`#0A0A0A` background, `#D4AF37` gold accent). No light mode. No exceptions.

---

## Before You Code — Research Phase

### Step 1: Read Project Files

Read these files in order to understand the project fully:
1. `CLAUDE.md` — complete project instructions (tech stack, design tokens, routes, commands, conventions)
2. `planning/CONSTITUTION.md` — non-negotiable rules (design system, stack lock, architecture)
3. `planning/EXPANSION_PLAN.md` — future features and expansion roadmap
4. `JOURNEY.md` — project history and decisions (context for why things are the way they are)

### Step 2: Explore the Codebase

- `app/api/` — route handlers (pages.py, scan.py, explore.py, chat.py, etc.)
- `app/core/` — business logic (gardiner.py, classifier.py, quiz_engine.py, etc.)
- `app/templates/` — Jinja2 templates (base.html + pages + partials)
- `app/static/css/input.css` — TailwindCSS source with all design tokens and components
- `app/static/js/` — Alpine.js components and ML pipeline

### Step 3: Check Online Resources

Use Context7 MCP or web search for latest docs when needed:
- FastAPI: resolve `/tiangolo/fastapi`
- TailwindCSS v4: resolve `/tailwindlabs/tailwindcss`
- Alpine.js: resolve `/alpinejs/alpine`

### Step 4: Check External Skills (if available)

Skills are at `D:\Personal attachements\Repos\antigravity-awesome-skills\`. Load the relevant ones:

| Task Type | Skills |
|-----------|--------|
| New feature | `fastapi-pro`, `fastapi-router-py`, `async-python-patterns` |
| UI / Design | `tailwind-patterns`, `tailwind-design-system`, `frontend-design`, `ui-ux-pro-max` |
| SEO | `seo-fundamentals`, `seo-audit`, `schema-markup`, `seo-meta-optimizer` |
| Performance | `web-performance-optimization`, `scroll-experience` |
| Security | `backend-security-coder`, `frontend-security-coder` |
| Deploy | `docker-expert`, `deployment-engineer`, `render-automation` |
| AI / Chat | `llm-app-patterns`, `prompt-engineering`, `prompt-engineering-patterns` |

### Step 5: Check Animation Libraries (for UI work)

CSS animation sources at `D:\Personal attachements\Repos\21-Frontend-UI\`:
- `magicui/` — extract CSS @keyframes from registry-ui.ts
- `animate-ui/` — background/button CSS effects
- `motion-primitives/` — spotlight, glow, text effects
- `Hover/` — pure CSS hover transitions
- `atropos/` — 3D parallax card tilt (vanilla JS)

---

## Planning Phase — Create Task Folder

**Before writing any code**, create a planning folder OUTSIDE the project:

```
D:\Personal attachements\Projects\Wadjet-Tasks\
└── [TASK-NAME]/
    ├── spec.md         ← Feature specification (use planning/templates/spec-template.md)
    ├── tasks.md        ← Task breakdown (use planning/templates/tasks-template.md)
    ├── checklist.md    ← Validation checklist (use planning/templates/checklist-template.md)
    ├── notes.md        ← Research notes, decisions, links
    └── progress.md     ← Progress tracking
```

### Writing the Spec (spec.md)

1. Copy `planning/templates/spec-template.md` as a starting point
2. Fill in: user scenarios, technical approach, acceptance criteria
3. Review it — ask yourself: "Is this complete? Are there edge cases?"

### Breaking into Tasks (tasks.md)

1. Copy `planning/templates/tasks-template.md`
2. Break the spec into small, testable tasks (max 30 min each)
3. Order by dependency — what must be done first?
4. Each task should have: clear objective, files to modify, acceptance test

### Checklist (checklist.md)

1. Copy `planning/templates/checklist-template.md`
2. Define quality gates: does it work? does it match the design system? is it responsive?

---

## Implementation Phase

### Rules

1. **One task at a time** — mark in-progress, complete it, mark done, move to next
2. **Test after every change** — run the server, check the route, verify the UI
3. **Respect the design system** — use `.btn-gold`, `.card-glow`, `text-gold-gradient` etc. from input.css
4. **No new dependencies** unless absolutely necessary — the stack is locked
5. **Max 300 lines per file** — split into modules if it grows
6. **Cache bust CSS** — bump `?v=N` in base.html after CSS changes
7. **Convention**: snake_case Python, kebab-case CSS, camelCase JS

### Testing

```bash
# Activate venv
.venv\Scripts\activate

# Build CSS (if you changed input.css)
npm run build

# Start server
uvicorn app.main:app --reload --port 8000

# Watch CSS (development)
npm run watch
```

Test every route you modified. Verify:
- Page loads without errors
- Design matches Black & Gold theme
- Mobile responsive
- No console errors

---

## After Implementation

1. Update `progress.md` in the task folder
2. Check all items in `checklist.md`
3. Run a final review: re-read the spec, verify every acceptance criterion
4. **Commit**: `git add -A && git commit -m "feat: [description]"`
5. **Push**: `git push origin clean-main` then `git push hf clean-main:main`

---

## Critical Reminders

- **NEVER** use `--color-bg` as a CSS variable — conflicts with TailwindCSS v4 `bg-*` namespace
- **NEVER** add React/Vue/Svelte — this is a Jinja2 + Alpine.js project
- **ALWAYS** use the existing design tokens from `input.css`
- **Footer**: "Built by Mr Robot" — do not change
- **Fonts**: Playfair Display (headings) + Inter (body) + Noto Sans Egyptian Hieroglyphs
