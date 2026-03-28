# Wadjet v3 Beta — Work Log

> Append-only log of all changes made during development.

---

## 2026-03-28 — Phase 0: Setup

- Copied `Wadjet/` → `Wadjet-v3-beta/` (excluding .venv, node_modules, .git, __pycache__)
- Initialized git repo with baseline commit (528 files, tag: v2-baseline)
- Created `wadjet-v3-planning/` folder with constitution, spec, plan, progress, work-log
- Created prompt files for all 11 phases (0-10)

---

## 2026-03-28 — Phase 0: AI Media Enhancement Planning

**API Research Completed:**
- Fetched Cloudflare Workers AI docs → found FREE image gen models (FLUX.1 schnell, SDXL, DreamShaper, etc.)
- Fetched Gemini API TTS docs → found FREE TTS (gemini-2.5-flash-preview-tts, 30 voices, 73+ langs including Arabic!)
- Fetched Gemini Veo docs → Veo 3.1 video gen is PAID ONLY ($0.15-$0.60/video) — skipped
- Fetched Groq TTS docs → found FREE Orpheus (English + Arabic Saudi, expressive)
- Confirmed Imagen 4 is PAID ONLY ($0.02-$0.06/image) — use Cloudflare FLUX instead
- Confirmed Lyria 3 music is PAID ONLY ($0.04-$0.08/song) — skipped

**Files Updated:**
- `constitution.md`: Added "AI Generation Services (Smart Defaults)" section, voice presets, fallback chains, Rule 11, new pip deps (google-genai, httpx), updated Out of Scope
- `spec.md`: Added section 3.10 (AI Media Generation Service), updated 3.6 (Thoth Chat TTS upgrade), updated 3.7 (Stories with AI illustrations + narrative voice), renumbered 3.11 (Dashboard)
- `plan.md`: Updated phase names, added AI Provider Stack table, added Bonus Improvements table (10 items), added Version Replacement section
- `phase-4-ux.md`: Renamed to "UX, Accessibility & TTS Service", added Gemini TTS service creation, narration button on all pages, media API endpoint, expanded testing checklist
- `phase-8-stories.md`: Added AI image gen (Cloudflare FLUX), narrative TTS (Gemini), Ken Burns CSS animation, image_service.py and tts_service.py code, scene_image_prompt + tts_voice in story JSON schema, expanded testing checklist
- `phase-10-finalize.md`: Added version replacement script (PowerShell), AI Media Services changelog section, expanded testing checklist

**Key Decisions:**
- ✅ Gemini 2.5 Flash TTS as primary TTS (FREE, best quality, Arabic)
- ✅ Cloudflare FLUX.1 schnell as primary image gen (FREE, fast)
- ✅ No video generation (no free API) → Ken Burns animations instead
- ✅ Smart defaults: system picks best provider, no user selector
- ✅ Version replacement via PowerShell script in Phase 10

---

## 2026-03-28 — Phase 1: Security Hardening

**Bugs Fixed:**
- **C2**: Content-Type bypass → replaced with magic byte validation (JPEG `FF D8 FF`, PNG `89 50 4E 47`, WebP `RIFF...WEBP`) in scan.py and explore.py
- **C3**: Quiz answers client-side → removed `_correct` and `correct_answer` from client JS; AI questions now use HMAC-signed hashes verified server-side via `/api/quiz/check-ai`
- **C5**: Error message leakage → all 500 errors now return generic "An error occurred processing your request." while logging full tracebacks server-side
- **C6**: No CSRF protection → added `starlette-csrf` middleware with cookie + `x-csrftoken` header; exempts GET, health, docs
- **H3**: Quiz dedup infinite loop → reviewed pool building (uses sequential IDs, no dedup loop possible)
- **H6**: No rate limiting → added `slowapi` rate limiter (30/min on scan/detect/read/chat/translate/write, 20/min on identify, 10/min on quiz generate)
- **M14**: Deterministic quiz seed → removed `random.seed(n)` from question pool building; `get_random_question` uses `secrets.choice`

**Files Created:**
- `app/rate_limit.py` — shared `slowapi.Limiter` instance (avoids circular imports)

**Files Modified:**
- `requirements.txt` — added `slowapi>=0.1.9`, `starlette-csrf>=3.0.0`
- `app/config.py` — added `csrf_secret` setting
- `app/main.py` — CSRF middleware, rate limiter init, `re` import
- `app/api/scan.py` — magic byte validation, rate limiting, error sanitization
- `app/api/chat.py` — rate limiting import
- `app/api/quiz.py` — HMAC answer signing, `/check-ai` endpoint, rate limiting
- `app/api/write.py` — rate limiting import
- `app/api/translate.py` — error sanitization, rate limiting
- `app/api/explore.py` — magic byte validation, rate limiting
- `app/core/quiz_engine.py` — `secrets.choice`, removed deterministic seeds
- `app/templates/quiz.html` — removed `_correct`, all answers verified server-side

**Test Results (all pass):**
- ✅ Upload .exe → 400 "Unsupported file type"
- ✅ PNG magic bytes with wrong Content-Type → accepts correctly
- ✅ Empty file → 400
- ✅ Quiz HTML: no `_correct` or answer text in source
- ✅ Quiz answer checked server-side (static + AI)
- ✅ HMAC check-ai rejects bad signatures
- ✅ POST without CSRF → 403
- ✅ 35 scan requests → 429 triggered at request #28
- ✅ 10 quiz requests → 10 unique questions (non-deterministic)
- ✅ All error responses return generic message, server logs full traceback

---

## 2026-03-28 — Phase 2: Self-Host CDN Scripts + Offline Fix

**Bugs Fixed:**
- **C1**: 6 CDN scripts not cached → downloaded Alpine.js, HTMX, GSAP, ScrollTrigger, Lenis, Atropos to `app/static/vendor/`; all pages now load fully offline
- **M8**: HTMX script lacked `defer` → all 6 vendor scripts now have `defer` attribute
- **M11**: No SRI on CDN scripts → solved by self-hosting (no external origin = no SRI needed)
- **M12**: `tts.js` not in service worker pre-cache → added to `STATIC_ASSETS` array
- **M18**: Cache invalidation wiped model cache on version bump → `MODEL_CACHE` is now version-independent (`wadjet-models`), persists across SW updates
- **H8**: Models used network-first strategy → switched to cache-first (models only change on explicit version bump)

**Folder Created:**
- `app/static/vendor/` — 6 self-hosted JS files (237 KB total)
  - `alpine.min.js` (44.7 KB), `htmx.min.js` (50.9 KB), `gsap.min.js` (72.8 KB)
  - `scrolltrigger.min.js` (44.2 KB), `lenis.min.js` (17.7 KB), `atropos.min.js` (6.9 KB)

**Files Modified:**
- `app/templates/base.html` — replaced 6 CDN `<script>` tags with local `/static/vendor/` paths, all with `defer`; removed CDN DNS prefetch for jsdelivr and unpkg (kept Google Fonts)
- `app/static/sw.js` — bumped `CACHE_VERSION` to `wadjet-v20`; added 7 entries to `STATIC_ASSETS` (6 vendor + tts.js); `MODEL_CACHE` now version-independent; models switched from `networkFirst` to `cacheFirst`

**Test Results (all pass):**
- ✅ All 6 vendor scripts served locally (200, correct sizes)
- ✅ No CDN references in page HTML for the 6 vendor scripts
- ✅ All 6 vendor script tags have `defer` attribute
- ✅ `tts.js` present in HTML and SW pre-cache list
- ✅ Service worker v20 with all vendor scripts in pre-cache
- ✅ CDN DNS prefetch removed, Google Fonts prefetch kept
- ✅ All 8 pages load with 200 status
- ✅ `MODEL_CACHE` is version-independent, `STATIC_CACHE` is versioned
- ✅ Models use cache-first strategy

---

## 2026-03-28 — Phase 3: Database & Auth Foundation

**Bug Fixed:**
- **M16**: In-memory sessions → replaced with SQLite + SQLAlchemy async + JWT auth

**Packages Added:**
- `sqlalchemy[asyncio]>=2.0`, `aiosqlite>=0.20.0`, `alembic>=1.14`, `python-jose[cryptography]>=3.3`, `bcrypt>=4.0`, `pydantic[email]>=2.0`

**Modules Created:**
- `app/db/` — database.py (async engine + session factory + init_db), models.py (5 ORM models: User, ScanHistory, StoryProgress, Favorite, RefreshToken), schemas.py (Pydantic v2 request/response), crud.py (all CRUD operations with SHA-256 token hashing)
- `app/auth/` — password.py (bcrypt 12 rounds), jwt.py (HS256 access 30min + refresh 7d with jti), dependencies.py (get_current_user + get_optional_user)
- `app/api/auth.py` — 4 endpoints: POST register (201, 5/min), POST login (200, 10/min), POST refresh (200, httpOnly cookie, 10/min), POST logout (200)
- `app/api/user.py` — 3 endpoints: GET profile, GET history, GET favorites (all require auth)

**Files Modified:**
- `requirements.txt` — 6 new dependencies
- `app/config.py` — added jwt_secret + database_url settings
- `app/main.py` — DB init in lifespan, auth routers, CSRF exemption for /api/auth/, auto-gen jwt_secret
- `app/templates/partials/nav.html` — Sign In/Sign Up buttons (desktop + mobile) with Alpine.js conditional rendering
- `app/templates/base.html` — Login + Signup modals with form validation and error display
- `app/static/js/app.js` — Alpine.store('auth') with register, login, logout, refreshToken, localStorage persistence
- `.gitignore` — added *.db

**Test Results (all 14 pass):**
- ✅ T1: SQLite DB auto-created with 5 tables
- ✅ T2: Register returns 201 + token + user data
- ✅ T3: Duplicate email returns 409
- ✅ T4: Weak password returns 422
- ✅ T5: Login returns 200 + new token
- ✅ T6: Wrong password returns 401
- ✅ T7: Profile with valid token returns user data
- ✅ T8: Profile with bad token returns 401
- ✅ T9: Refresh token rotation works
- ✅ T10: Logout invalidates refresh token
- ✅ T11: All 8 pages work without auth (guest mode preserved)
- ✅ T12: Password stored as bcrypt hash ($2b$12$...)
- ✅ T13: JWT contains only sub + exp + jti (no sensitive data)
- ✅ T14: User data persists in SQLite file

---

## Phase 4 — UX, Accessibility & TTS Service
**Date**: 2026-03-28
**Commit**: `a9d6859` — `[Phase 4] UX, accessibility & TTS service — nav fix, Gemini TTS, WCAG contrast, labels, narration`

### Changes (12 files, 420 insertions)
- **H1**: Added `/write` to desktop and mobile nav in `nav.html`
- **C4+H2**: Created `app/core/tts_service.py` — Gemini TTS with key rotation, voice presets (Orus/Charon/Rasalgethi/Aoede), director's notes per context, WAV disk caching
- **C4+H2**: Added `POST /api/audio/speak` endpoint in `audio.py` — Gemini→Groq→204 fallback, 20/min rate limit
- **C4+H2**: Created `app/templates/partials/narration_button.html` — floating 🔊 button, Alpine.js, server TTS with browser fallback
- **C4+H2**: Upgraded chat.html TTS — server-first with `speakMessage()` method, context-aware (thoth_chat voice)
- **H4**: Fixed Was Scepter from R11/𓊹 to S42/𓌂 in `landing.html`
- **H5**: Fixed `--color-text-dim` contrast from #5A5A5A (3.1:1) to #7E7E7E (4.7:1) in `input.css`
- **H7**: Expanded Glyph of Day from 7 to 32 entries across Gardiner categories
- **M10**: Added sr-only labels + id attributes to dictionary.html and explore.html search inputs
- **M13**: Added `@font-face` for Noto Sans Egyptian Hieroglyphs in `input.css`
- **M15**: Fixed favicon href to `/static/images/favicon.svg` in `base.html`
- **M17**: Enhanced scan confidence with dynamic color coding (green/gold/red) and "confidence" label
- **Infra**: Added `app/static/cache/` to `.gitignore`, added narration block to `base.html`

### Testing Results (15/15 automated PASS, 6 manual/skip)
- ✅ T1: /write in desktop nav
- ✅ T2: /write in mobile nav
- ✅ T3: /write page loads (200)
- ✅ T7: Chat uses server TTS (/api/audio/speak)
- ✅ T8: Browser TTS fallback present
- ✅ T9: Narration button on landing, explore, dictionary
- ✅ T10: Narration uses server TTS
- ✅ T13: Was Scepter S42 (R11 is only Djed Pillar in glyph array)
- ✅ T14: text-dim #7E7E7E in compiled CSS
- ✅ T15: 32 Glyph of Day entries
- ✅ T16: Dictionary search has label
- ✅ T17: Explore search has label
- ✅ T18: Noto Sans Egyptian Hieroglyphs loaded
- ✅ T19: Favicon SVG in place
- ✅ T20-T21: Confidence shown with color coding
- ✅ BONUS: /api/audio/speak returns 200 with CSRF token, audio cached to disk

### Phase 4 Audit — 14 Issues Found & Fixed
**Commit**: `e261148` — `[Phase 4] Audit fixes — async I/O, blob URL cleanup, S42 glyph, context validation, z-index overlap`

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| 1 | HIGH | Blocking sync I/O in async `tts_service.py` (mkdir, exists, write_bytes) | Wrapped with `asyncio.to_thread()` |
| 2 | HIGH | Blob URL memory leak in `narration_button.html` (never revoked) | Added `_revokeUrl()` on stop/ended |
| 3 | HIGH | Blob URL memory leak in `chat.html` `speakMessage()` | Added `_cleanupAudio()` with `revokeObjectURL` |
| 4 | HIGH | S42 Was Scepter glyph was U+FFFD (corrupted) | Replaced with correct `𓌂` (U+13302) |
| 5 | MEDIUM | Relative `CACHE_DIR` path fragile outside project root | Changed to `Path(__file__).parent.parent / "static" / ...` |
| 6 | MEDIUM | TOCTOU race condition on cache file write | Atomic write via `.tmp` + `rename()` |
| 7 | MEDIUM | `data-narration-context` never set on `<body>` | Added `{% block body_attrs %}` to base.html, set per-page |
| 8 | MEDIUM | Double-click race in chat TTS toggle | Changed to check `ttsActiveId === msgId` only (not `ttsState`) |
| 9 | MEDIUM | Narration button (z-50) covered by toast (z-9998) | Moved narration to `bottom-20` |
| 10 | MEDIUM | Duplicate Gardiner code S29 (`𓊃` mislabeled) | Corrected to O34 (door bolt) |
| 11 | LOW | `context` field accepts arbitrary strings | Added `pattern=r"^[a-z_]{1,30}$"` |
| 12 | LOW | `hasContent` always `true` | Added `init()` with `getText().length > 10` check |
| 13 | LOW | N35+A1 entries merged on one line | Split to separate lines |
| 14 | LOW | `--color-gold-light`/`dark` drift from CLAUDE.md | Noted, not changed (functional) |

---

## Phase 5 — Performance Optimization
**Date**: 2026-03-28
**Commit**: `0001680` — `[Phase 5] Performance — cache-first models, lazy loading, HTMX infinite scroll pagination`

### Changes (6 files, 69 insertions)

**H8 — Model cache strategy**: Verified `sw.js` already uses `cacheFirst()` for `/models/*` with version-independent `wadjet-models` cache. No change needed (fixed in Phase 2).

**M7 — Lazy loading images**:
- Audited all templates: `landing.html`, `landmarks.html`, `dictionary.html` have zero `<img>` tags (all Unicode/SVG/emoji)
- `explore.html` card images already had `loading="lazy"` and `aspect-[4/3]` wrapper
- `scan.html` history thumbnails were missing `loading="lazy"` → added

**M9 — Explore infinite scroll pagination**:
- `app/api/explore.py` — added `page` (default 1, ge=1) and `per_page` (default 24, ge=1, le=100) query params to `list_landmarks()`. Response now includes `total`, `page`, `has_more` fields alongside `landmarks` and `count`
- `app/templates/explore.html` — added Alpine.js infinite scroll:
  - New state: `currentPage`, `hasMore`, `loadingMore`
  - `fetchLandmarks()` rewritten to send `page=1&per_page=24`, reset pagination state
  - New `loadMore()` method: fetches next page, appends results via spread operator
  - Infinite scroll trigger: `x-intersect:enter.margin.200px="loadMore()"` with loading spinner
- Downloaded Alpine Intersect plugin (`alpine-intersect.min.js`, 897 bytes) to `app/static/vendor/`
- Added Intersect plugin script to `base.html` before `alpine.min.js` (plugins must load before core)
- Added `alpine-intersect.min.js` to SW pre-cache list, bumped `CACHE_VERSION` to `wadjet-v21`

**Font preload**: Added `<link rel="preload" ... as="style">` for Google Fonts CSS in `base.html`

### Files Modified
- `app/api/explore.py` — pagination params + slice logic + response fields
- `app/templates/explore.html` — Alpine infinite scroll + loadMore() + trigger div
- `app/templates/scan.html` — `loading="lazy"` on history thumbnail
- `app/templates/base.html` — Alpine Intersect plugin script + font preload
- `app/static/sw.js` — cache version v21, Alpine Intersect in pre-cache

### Files Created
- `app/static/vendor/alpine-intersect.min.js` — Alpine Intersect plugin (897 bytes)

### Testing Results (all pass)
- ✅ T1: Page 1 returns 24 landmarks, total=163, has_more=true
- ✅ T2: Page 7 (last) returns 19 landmarks, has_more=false
- ✅ T3: 6×24 + 19 = 163 total (math checks out)
- ✅ T4: Search "pyramid" returns 19 results, all fit in page 1, has_more=false
- ✅ T5: Explore page HTML contains `x-intersect`, `loadMore`, `alpine-intersect`
- ✅ T6: `loading="lazy"` present in scan.html (1) and explore.html (2)
- ✅ T7: Font `<link rel="preload">` present in served HTML
- ✅ T8: Health endpoint returns ok
- ✅ T9: Landing, scan pages load with 200 status
- ✅ T10: No Python/JS errors in any modified file
