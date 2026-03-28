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
