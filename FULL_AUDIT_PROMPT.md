# Wadjet v3 Beta — Full Audit Prompt

> **How to use**: Open the workspace `D:\Personal attachements\Projects\Wadjet-v3-beta` in VS Code, then send this entire file content as a prompt to GitHub Copilot (Agent mode).
>
> **Output**: All findings go to `D:\Personal attachements\Projects\Wadjet-Analysis\` — one file per audit area (see §Output below).

---

## Identity & Context

You are auditing **Wadjet v3 Beta** — an AI-powered Egyptian heritage web app.

- **Workspace**: `D:\Personal attachements\Projects\Wadjet-v3-beta`
- **Repos folder** (skills, libs, references): `D:\Personal attachements\Repos`
- **UI/UX audit standards**: `D:\Personal attachements\Repos\impeccable` — Anthropic-based frontend design skill with 7 reference files. READ these before auditing UI:
  - `source/skills/frontend-design/SKILL.md` — master design skill (anti-patterns, aesthetic guidelines)
  - `source/skills/frontend-design/reference/typography.md` — type systems, font pairing, modular scales
  - `source/skills/frontend-design/reference/color-and-contrast.md` — OKLCH, tinted neutrals, dark mode, a11y
  - `source/skills/frontend-design/reference/spatial-design.md` — spacing systems, grids, visual hierarchy
  - `source/skills/frontend-design/reference/motion-design.md` — easing curves, staggering, reduced motion
  - `source/skills/frontend-design/reference/interaction-design.md` — forms, focus states, loading patterns
  - `source/skills/frontend-design/reference/responsive-design.md` — mobile-first, fluid design, container queries
  - `source/skills/frontend-design/reference/ux-writing.md` — button labels, error messages, empty states
- **Frontend UI libraries** (for comparison/inspiration): `D:\Personal attachements\Repos\21-Frontend-UI` — contains magicui, animate-ui, motion-primitives, react-bits, headlessui, tailwind templates
- **Security references**: `D:\Personal attachements\Repos\18-Security` — contains OWASP Top10, PayloadsAllTheThings, gitleaks, sqlmap references
- **Prompt engineering references**: `D:\Personal attachements\Repos\20-Prompts-GPT` — for evaluating Thoth's system prompt quality and prompt injection resistance
- **Output folder**: `D:\Personal attachements\Projects\Wadjet-Analysis\`
- **Owner**: Nader (HF: nadercr7)
- **Live URL**: https://nadercr7-wadjet-v2.hf.space
- **Stack**: FastAPI 0.115+ · Python 3.13 · Jinja2 · Alpine.js 3.14 · HTMX 2.0.4 · TailwindCSS v4.2 · ONNX Runtime · SQLite (async) · JWT auth
- **AI providers**: Gemini (17 keys) · Grok (8 keys) · Groq (free) · Cloudflare Workers AI (free)
- **TTS fallback chain**: Gemini 2.5 Flash TTS → Groq Orpheus → Browser SpeechSynthesis
- **Image gen**: Cloudflare FLUX.1 schnell → SDXL → placeholders
- **Key files**: Read `CLAUDE.md` for full project context, `CHANGELOG.md` for history, `JOURNEY.md` for narrative

---

## Instructions

Perform a **complete, deep, exhaustive audit** of every aspect of this project. Leave nothing unchecked. For each area below, read every relevant file, trace every pipeline end-to-end, test logic mentally (and with actual test images/data where specified), and document every finding.

**Severity levels** for each finding:
- 🔴 **CRITICAL** — Broken, security vulnerability, data loss, or completely non-functional
- 🟠 **HIGH** — Major bug, significant logic error, poor UX that blocks users
- 🟡 **MEDIUM** — Works but incorrectly, degraded experience, inconsistency
- 🟢 **LOW** — Minor improvement, polish, optimization, nice-to-have
- ✅ **PASS** — Verified working correctly

For each finding, provide:
1. **File(s)** affected (with line numbers)
2. **What's wrong** (specific, not vague)
3. **Why it matters**
4. **Suggested fix** (concrete code or approach, not just "fix it")

---

## Audit Areas

### 1. HIEROGLYPH PIPELINE (Full End-to-End)

Trace the complete scan pipeline from camera/upload to final translation output:

1. **Camera & Upload** (`scan.html`, `app.js`, `hieroglyph-pipeline.js`)
   - Does the camera work? Is it real-time video (not just photo capture)?
   - Upload flow: file input → magic byte validation → size limits
   - Image preprocessing before inference

2. **Detection** (`app/core/hieroglyph_pipeline.py`, `app/core/reading_order.py`)
   - ONNX detector loading and inference
   - Bounding box extraction, NMS, confidence filtering
   - Sliding window approach — does it work for large inscriptions?
   - Reading order algorithm — right-to-left, top-to-bottom for hieroglyphs

3. **Classification** (`app/core/hieroglyph_pipeline.py`, `app/core/ensemble.py`)
   - ONNX classifier inference per detected glyph
   - Label mapping (171 classes) — verify `label_mapping.json` matches model output
   - Ensemble with AI vision (Gemini → Grok → Groq → Cloudflare)
   - Cross-validation logic (`cross_validator.py`) — does majority vote work correctly?
   - Confidence weighting and top-5 results

4. **Translation** (`app/core/rag_translator.py`, `app/core/transliteration.py`, `app/core/ai_reader.py`)
   - Gardiner code → transliteration mapping
   - RAG-based translation (FAISS index + corpus)
   - AI reader integration for full inscription context
   - English AND Arabic translation — are both actually produced?

5. **TTS for scan results** (`app/core/tts_service.py`, `app/api/audio.py`, `tts.js`)
   - Can the user HEAR the pronunciation of detected hieroglyphs?
   - Is `tts_service.py` actually connected to the `/api/tts` endpoint? (Known issue: was DISCONNECTED)
   - Gemini TTS → Groq fallback → Browser fallback chain
   - Audio caching in `/static/cache/audio/`

6. **Test with known images**: 
   - Find or reference test hieroglyph images in `tests/` or `data/`
   - Trace what the pipeline SHOULD return for known Gardiner signs (e.g., A1 = seated man, G17 = owl/m)
   - Check if `postprocess.py` correctly maps raw model output to human-readable results
   - Document any accuracy issues or mapping errors

### 2. LANDMARK PIPELINE (Full End-to-End)

1. **Explore page** (`explore.html`, `app/api/explore.py`, `app/core/landmarks.py`)
   - 260+ sites data loading — from where? JSON? DB?
   - Search, filter, infinite scroll
   - Category organization (Pharaonic, Islamic, Coptic, Greco-Roman, Modern)
   - Parent-child relationships (e.g., Karnak → individual temples)

2. **Landmark identification** (`app/api/scan.py` or separate endpoint?, `app/core/landmark_pipeline.py`)
   - Upload photo → ONNX classifier → identify which of 52 landmarks
   - Label mapping verification
   - Confidence display, top-N results

3. **Recommendation engine** (`app/core/recommendation_engine.py`)
   - What algorithm? Content-based? Collaborative?
   - Does it actually return useful recommendations?

4. **Landmark enrichment** (`data/landmark_enrichment_cache.json`, `data/expanded_sites.json`)
   - Is enrichment data complete for all 260+ sites?
   - Image URLs — are they all still valid/accessible?

### 3. TRANSLATION & LANGUAGE QUALITY

1. **i18n system** (`app/i18n/en.json`, `app/i18n/ar.json`, `app/i18n/__init__.py`)
   - Are ALL UI strings in both language files?
   - Missing keys? Untranslated strings hardcoded in templates?
   - Arabic text quality — is it natural Egyptian Arabic or robotic MSA?
   - RTL layout support — does switching to Arabic flip the layout correctly?

2. **Hieroglyph translation quality**
   - Check `data/translation/` — what's in there? Is the corpus comprehensive?
   - Common inscriptions: can it translate "Ankh", "Djed", "Was"?
   - Does the transliteration map cover all 171 classified signs?

3. **Gardiner data quality** (`app/core/gardiner.py`, `app/core/gardiner_data/`, `app/core/hieroglyphs_data.py`)
   - 1,023 signs — verify completeness across all 26 categories
   - Pronunciation guides accuracy
   - Unicode glyph rendering — do all signs display correctly?

### 4. STORIES SYSTEM

1. **Story data** (`data/stories/*.json`) — all 13 stories
   - JSON structure validity
   - Content quality — are stories complete? Any placeholder text?
   - Hieroglyphs taught per story — accurate?

2. **Story reader** (`story_reader.html`, `app/api/stories.py`, `app/core/stories_engine.py`)
   - Interactive elements: glyph_discovery, choose_glyph, arrange_sentence, write_word
   - Do all 4 interaction types actually work?
   - AI illustration generation — triggered when? Cached where?
   - TTS narration for stories — functional?

3. **Story listing** (`stories.html`)
   - All 13 stories listed? Thumbnails?
   - Progress tracking — does it persist?

### 5. SECURITY AUDIT

1. **Authentication** (`app/auth/`, `app/api/auth.py`)
   - JWT implementation: access + refresh tokens
   - Token refresh race condition (Known issue from memory notes)
   - bcrypt password hashing — proper salt rounds?
   - Google OAuth flow — secure? Token validation?
   - Email verification via Resend — works?
   - Session management — logout actually invalidates tokens?

2. **CSRF** (`starlette-csrf` middleware in `main.py`)
   - Applied to ALL POST endpoints?
   - Token rotation?

3. **Rate limiting** (`app/rate_limit.py`, endpoint decorators)
   - All endpoints covered?
   - Limits reasonable? (10-60/min)
   - Per-IP or per-user?

4. **Input validation**
   - Magic byte validation for image uploads — verify all endpoints
   - File size limits enforced?
   - SQL injection protection (SQLAlchemy parameterized queries)
   - XSS in user-generated content (feedback, chat, usernames)
   - Path traversal in any file operations
   - SSRF in any URL-fetching features

5. **Security headers** (check `main.py` middleware)
   - CSP, X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy
   - CORS configuration

6. **Secrets management**
   - `.env` not in git?
   - No hardcoded secrets in source?
   - Production enforcement (jwt_secret, csrf_secret required)

7. **OWASP Top 10 check**: Go through each category explicitly
   - Reference `D:\Personal attachements\Repos\18-Security\Top10\` for the official OWASP guidelines
   - Cross-reference with `PayloadsAllTheThings` for real-world attack vectors
   - Check with `gitleaks` patterns for leaked secrets in git history

### 6. DATABASE & DATA PERSISTENCE

1. **Schema** (`app/db/models.py`, `app/db/schemas.py`)
   - User model completeness
   - Relationships and foreign keys
   - Migration state (`alembic/versions/`)

2. **CRUD operations** (`app/db/crud.py`)
   - All needed operations exist?
   - Proper async session handling?
   - Race conditions?

3. **Data persistence bug** (Known issue: feedback, login, history, dashboard data gets wiped on push/commit/deploy)
   - SQLite file location — `data/wadjet.db`
   - Docker volume mount — `docker-compose.yml` mounts `data/` as `:ro` but SQLite WRITES there
   - HuggingFace Spaces — ephemeral filesystem? Data loss on redeploy?
   - This is a CRITICAL issue — investigate thoroughly and propose solution

4. **Favorites, history, progress** (`app/api/user.py`, dashboard)
   - Scan history saved?
   - Chat history saved?
   - Favorites (landmarks, stories) persisted?
   - User progress (lessons, stories) tracked?

### 7. UX & FRONTEND QUALITY

> **IMPORTANT**: Before auditing this section, READ all 7 reference files from `D:\Personal attachements\Repos\impeccable\source\skills\frontend-design\reference\` and the `SKILL.md`. Use these as the gold standard for evaluating Wadjet's frontend. Apply the impeccable anti-pattern checklist to catch generic AI aesthetics.

0. **Impeccable Design Audit** (apply impeccable's standards to the ENTIRE frontend)
   - **Typography**: Is Wadjet using overused fonts (Inter, Roboto, Arial)? Is there a proper modular type scale with fluid sizing? Font pairing — display vs body? Weight/size hierarchy clear?
   - **Color & Theme**: Is the gold-on-dark palette well-executed or generic? Tinted neutrals or flat grays? Any gray text on colored backgrounds? Pure black (#000) or pure white (#fff) misuse? OKLCH or modern color functions used?
   - **Spatial Design**: Visual rhythm through varied spacing or same padding everywhere? Cards nested inside cards? Everything centered when left-align would be better? Grid broken intentionally for emphasis?
   - **Motion**: Purposeful animations or decorative fluff? Page load orchestration? Staggered reveals? `prefers-reduced-motion` respected? Exponential easing or linear/ease defaults?
   - **Interaction Design**: Focus states visible? Loading patterns clear? Form validation UX? Touch targets ≥48px? Hover states meaningful? Keyboard shortcuts?
   - **UX Writing**: Button labels descriptive or vague ("Submit", "Click here")? Error messages helpful or cryptic? Empty states designed or blank? Confirmation dialogs clear?
   - **Anti-patterns to flag**: glassmorphism overuse, sparklines as decoration, rounded rectangles with generic shadows, modals where inline would work, icon+heading+text card grids, hero metric layout templates, gradient text for "impact", dark mode with glowing accents as the lazy default

1. **Navigation flow**
   - Landing → Hieroglyphs hub → Scan/Dictionary/Write
   - Landing → Landmarks hub → Explore
   - Cross-links between features
   - Back navigation — does it work intuitively?

2. **Page count & organization**
   - List ALL pages: landing, hieroglyphs, landmarks, scan, dictionary, lessons (×5), write, explore, chat, stories, story_reader (×13), dashboard, settings, quiz(→redirect), welcome, feedback_admin
   - Are there too many? Should any be merged?
   - Is the information architecture clear?

3. **Loading experience** (reference impeccable's motion-design.md for animation standards)
   - Animated loading overlay — does it work on all pages? Is it skippable?
   - Section loaders on scan, explore, dashboard, stories, dictionary, lessons
   - Skeleton screens or spinners during AJAX? — skeletons preferred over spinners
   - Loading state for camera initialization?
   - Progressive image loading for landmarks gallery?
   - Staggered content reveals or everything pops in at once?

4. **Responsive design** (reference impeccable's responsive-design.md for fluid design standards)
   - Mobile layout — all pages responsive? Test at 320px, 375px, 768px, 1024px, 1440px
   - Touch targets big enough (48px min)? Check ALL buttons, links, interactive elements
   - Camera/scan experience on mobile — full-screen viewfinder? Orientation handling?
   - Nav menu on mobile — hamburger? Bottom nav? Slide-out?
   - Fluid typography with clamp()? Or hard breakpoints?
   - Container queries used anywhere? Should they be?
   - Landscape mode handling on mobile scan view

5. **Error states** (reference impeccable's interaction-design.md and ux-writing.md)
   - What happens when AI providers are down? — visible fallback UI or silent failure?
   - No internet → offline mode works? — is there a clear offline indicator?
   - Invalid image upload → clear error message? — not just "Error" but what went wrong and what to do
   - API failures → graceful degradation? — retry button? Cached fallback?
   - Empty states — is every page designed for the "no data yet" case? (no scans, no favorites, no history)
   - Rate limit hit → user-friendly message? Not a raw 429 error?

6. **Accessibility** (reference impeccable's color-and-contrast.md for contrast standards)
   - Keyboard navigation — can you Tab through ALL interactive elements?
   - Screen reader support — proper ARIA roles, live regions for dynamic content?
   - Focus management — focus trap in modals? Focus restore on close?
   - Color contrast — gold on dark meets WCAG AA (4.5:1 text, 3:1 large text)? Use OKLCH perceptual checks
   - `aria-labels` on all interactive elements — camera button, scan button, nav icons, etc.
   - Skip navigation link?
   - Landmark roles (`<main>`, `<nav>`, `<aside>`)?
   - Image alt text — especially for hieroglyph results and landmark photos

7. **Thoth chatbot** (`chat.html`, `app/api/chat.py`, `app/core/thoth_chat.py`)
   - Streaming responses?
   - Personality consistent?
   - Voice input (STT) → voice output (TTS)?
   - Chat history persistence
   - Error handling when Gemini is down

### 8. CODE QUALITY

1. **Python backend** — review ALL files in `app/`
   - Type hints consistency
   - Error handling — try/except too broad? Missing?
   - Async patterns — proper await? Blocking calls in async?
   - Import organization
   - Dead code / unused imports
   - Functions >50 lines that should be split
   - Proper logging (not print statements)

2. **JavaScript** (`app/static/js/app.js`, `tts.js`, `hieroglyph-pipeline.js`)
   - Alpine.js store patterns
   - HTMX integration correctness
   - Error handling in fetch calls
   - Token refresh logic — race condition? (Known issue)
   - Memory leaks (event listeners, intervals)
   - Camera/WebRTC cleanup

3. **HTML/Jinja2 templates** — review ALL templates
   - Template inheritance correct?
   - Proper escaping of user content
   - SEO tags (`partials/seo.html`)
   - No broken template variables
   - Consistent use of partials

4. **CSS** (`input.css`)
   - Unused custom classes?
   - Conflicting styles?
   - CSS variable organization — are design tokens well-structured? (reference impeccable SKILL.md)
   - TailwindCSS v4 compatibility issues (e.g., `--color-bg` bug)
   - Modern CSS features: is the project using `oklch()`, `color-mix()`, `light-dark()`, `clamp()` for fluid sizing?
   - Custom properties vs hardcoded values — are colors/spacing/fonts tokenized?
   - Dark mode implementation — proper `prefers-color-scheme` or manual toggle?
   - Is the CSS fighting TailwindCSS or working with it?

### 9. PERFORMANCE

1. **Backend performance**
   - Model loading — lazy or eager? Memory impact?
   - FAISS index size and search speed
   - Database query efficiency
   - API response times for key endpoints
   - GZip middleware configured?

2. **Frontend performance**
   - Bundle sizes (JS, CSS, vendor scripts)
   - Image optimization (lazy loading, proper formats)
   - ONNX model loading time
   - Service worker caching strategy
   - Render-blocking resources

3. **ML inference performance**
   - ONNX Runtime Web vs server-side — which is used where?
   - Quantized model sizes vs accuracy tradeoff
   - Batch inference for multiple glyphs?

### 10. DEPLOYMENT & DEVOPS

1. **Docker** (`Dockerfile`, `docker-compose.yml`)
   - Multi-stage build correct?
   - `data/` volume mount — `:ro` but needs `:rw` for SQLite
   - All models included in image?
   - CSS built during docker build?

2. **HuggingFace Spaces** (README.md frontmatter, `render.yaml`)
   - Port 7860 configured?
   - Persistent storage for user data?
   - Environment variables set?
   - Ephemeral filesystem issue for SQLite data

3. **CI/CD**
   - Any GitHub Actions?
   - Test automation?
   - Linting in CI?

4. **Environment configuration**
   - `.env.example` complete?
   - All needed vars documented?
   - Dev vs prod config differences

### 11. TESTING

1. **Existing tests** — review ALL files in `tests/`
   - Test coverage — what's tested? What's NOT?
   - Test quality — are assertions meaningful?
   - Mock usage — proper? Over-mocked?
   - Integration tests vs unit tests balance

2. **Missing tests**
   - Hieroglyph pipeline end-to-end
   - landmark pipeline
   - Auth flows (register, login, refresh, logout, OAuth)
   - Story interactions
   - TTS chain
   - Offline mode

3. **Run the tests**
   - Execute `pytest` and report results
   - Any failures? Analyze root causes

### 12. OFFLINE / SERVICE WORKER

1. **Service worker** (`app/static/sw.js`)
   - Cache strategy for each resource type
   - ML model caching
   - Offline page rendering
   - Cache versioning and cleanup
   - Registration in `base.html`

2. **Self-hosted vendor scripts** (`app/static/vendor/`)
   - All CDN scripts properly self-hosted?
   - Versions match what's expected?
   - Subresource integrity?

### 13. SEO & META

1. **SEO partial** (`partials/seo.html`)
   - Open Graph tags
   - Twitter Card tags
   - Structured data (JSON-LD)
   - Canonical URLs
   - Robots.txt and sitemap

2. **Per-page SEO**
   - Each page has unique title and description?
   - Proper heading hierarchy (h1 → h2 → h3)?

### 14. QUIZ & WRITE FEATURES

1. **Quiz** (`app/api/quiz.py`, `app/core/quiz_engine.py`)
   - Redirects to /stories now — is the redirect clean?
   - Old quiz code still in codebase? Should it be removed?

2. **Write feature** (`write.html`, `app/api/write.py`, `app/core/`)
   - English → hieroglyph conversion
   - Smart mode vs letter-by-letter mode
   - Corpus data (`data/text/`) — complete?

### 15. THOTH AI CHATBOT (Deep Dive)

1. **System prompt** (`app/core/thoth_chat.py`)
   - Personality: god of knowledge, scholarly but accessible
   - Context awareness — does it know about the app features?
   - Safety: can it be jailbroken? Prompt injection resistant?
   - Reference `D:\Personal attachements\Repos\20-Prompts-GPT` for prompt engineering best practices
   - Test common injection patterns: "ignore previous instructions", "you are now...", role confusion, delimiter attacks
   - Check if user input is properly sandboxed from the system prompt

2. **Streaming** (`app/api/chat.py`)
   - SSE implementation correct?
   - Error mid-stream handling?
   - Token counting / rate limiting?

3. **Multi-provider** — fallback when Gemini is down?

### 16. RECOMMENDATION ENGINE

1. **Algorithm** (`app/core/recommendation_engine.py`)
   - What features does it use?
   - Cold start problem?
   - Quality of recommendations

### 17. MISCELLANEOUS

1. **Feedback system** (`app/api/feedback.py`, `feedback_admin.html`)
   - Users can submit feedback?
   - Admin can view feedback?
   - Data persists? (Same SQLite issue?)

2. **Welcome page** (`welcome.html`) — what is it? When shown?

3. **Scripts** (`scripts/`) — are build scripts functional?

4. **Dead code** — any files, routes, or functions that are never used?

5. **Console errors** — any `console.log` left? (Claimed zero in CHANGELOG)

6. **Git hygiene** — `.gitignore` complete? Any large files committed?

---

## Output Structure

Create the following files in `D:\Personal attachements\Projects\Wadjet-Analysis\`:

```
Wadjet-Analysis/
├── 00-EXECUTIVE-SUMMARY.md        # Overall health score, top 10 critical findings, quick wins
├── 01-HIEROGLYPH-PIPELINE.md      # §1 findings — full pipeline audit
├── 02-LANDMARK-PIPELINE.md        # §2 findings — explore + identify
├── 03-TRANSLATION-LANGUAGE.md     # §3 findings — i18n, translation quality, Arabic
├── 04-STORIES-SYSTEM.md           # §4 findings — stories, interactions, narration
├── 05-SECURITY.md                 # §5 findings — auth, CSRF, rate limiting, OWASP
├── 06-DATABASE-PERSISTENCE.md     # §6 findings — schema, data loss bug, Docker volumes
├── 07-UX-FRONTEND.md              # §7 findings — navigation, responsive, accessibility, pages
├── 08-CODE-QUALITY.md             # §8 findings — Python, JS, HTML, CSS review
├── 09-PERFORMANCE.md              # §9 findings — backend, frontend, ML inference
├── 10-DEPLOYMENT.md               # §10 findings — Docker, HF Spaces, CI/CD
├── 11-TESTING.md                  # §11 findings — coverage, results, missing tests
├── 12-OFFLINE-SW.md               # §12 findings — service worker, vendor scripts
├── 13-SEO-META.md                 # §13 findings — SEO tags, structured data
├── 14-FEATURES-MISC.md            # §14-17 findings — quiz, write, Thoth, recs, feedback, etc.
└── 99-MASTER-ISSUE-LIST.md        # ALL findings as a flat numbered list sorted by severity
                                   # Format: [ID] [🔴/🟠/🟡/🟢/✅] [Area] — Description — File(s) — Fix
```

### File Format for Each Audit File

```markdown
# [Area Name] Audit

## Summary
- Total findings: X (🔴 N critical, 🟠 N high, 🟡 N medium, 🟢 N low, ✅ N pass)
- Overall health: X/10

## Findings

### [AREA-001] 🔴 Short Title
- **File(s)**: `path/to/file.py` L42-58
- **What**: Specific description of the issue
- **Impact**: What breaks or degrades
- **Fix**: Concrete code change or approach
  ```python
  # Before
  ...
  # After
  ...
  ```

### [AREA-002] ✅ Short Title
- **File(s)**: `path/to/file.py`
- **Status**: Verified working correctly
- **Notes**: Any caveats

...
```

### Executive Summary Format

```markdown
# Wadjet v3 Beta — Audit Executive Summary

**Date**: [date]
**Auditor**: GitHub Copilot
**Scope**: Full codebase, all features, security, UX, performance

## Overall Health Score: X/10

## Stats
- Total files reviewed: X
- Total findings: X
- 🔴 Critical: X | 🟠 High: X | 🟡 Medium: X | 🟢 Low: X | ✅ Pass: X

## Top 10 Critical / High-Priority Findings
1. ...
2. ...

## Quick Wins (can fix in <30 min each)
1. ...
2. ...

## Architecture Observations
- ...

## Recommendations Priority Order
1. ...
2. ...
```

---

## Special Instructions

1. **Be brutally honest** — don't sugarcoat. If something is broken, say it's broken.
2. **Be specific** — "the code has issues" is useless. "Line 47 of `scan.py` catches Exception broadly, masking ORM errors" is useful.
3. **Read EVERY file** — don't skip any Python, JS, HTML, or JSON file. This is a FULL audit.
4. **Test the pipelines mentally** — trace data flow from user input to final output. Where can it break?
5. **Check the known issues from memory**:
   - TTS service disconnected from `/api/tts` endpoint
   - Token refresh race condition in `app.js`
   - Docker-compose mounts `data/` as `:ro` but SQLite writes there
   - Data loss on HuggingFace redeploy (feedback, history, dashboard)
6. **Compare against claims** — CHANGELOG says "zero console.log", "zero TODO", "98.2% accuracy". Verify.
7. **Check image URLs** — in landmark data, are links to images still valid?
8. **Don't hold back on code quality** — if a function is messy, say so. If there's dead code, flag it.
9. **Suggest concrete improvements** — not just "this could be better" but exactly HOW.
10. **Run `pytest`** if possible and include output in testing report.

---

## Duration Expectation

This is a multi-hour deep audit. Take your time. Read everything. Missing a critical bug is worse than being thorough. Use subagents for parallel exploration where possible.

**START NOW. Read `CLAUDE.md` first, then systematically work through each audit area.**
