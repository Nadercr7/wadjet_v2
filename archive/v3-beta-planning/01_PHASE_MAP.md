# WADJET v3 — PHASE MAP

> All work broken into sequential, clearly scoped phases.
> Each phase is atomic — it can be completed, tested, and committed independently.

---

## Phase 0: Project Setup & Foundation

**Goal**: Clean git state, test infrastructure ready, dependencies frozen, old planning archived.

**Done when**: `pytest` runs (even with 0 tests), `pip install -r requirements.txt` is reproducible, git has a clean checkpoint commit.

### Files Created
- `tests/__init__.py`
- `tests/conftest.py` — shared fixtures (test client, test DB, mock settings)
- `pytest.ini` — pytest config
- `requirements-dev.txt` — test/dev dependencies (pytest, httpx, pytest-asyncio, coverage)

### Files Modified
- `requirements.txt` — change `>=` to `~=` for reproducibility
- `.gitignore` — add `wadjet-v3-planning-ARCHIVED-*`, `htmlcov/`, `.coverage`, `tests/__pycache__/`
- `pyproject.toml` — add `[tool.pytest.ini_options]`

### Files Archived (already done)
- `wadjet-v3-planning/` → `wadjet-v3-planning-ARCHIVED-2026-03-29/`

### Start Condition
- Git is initialized, working tree is clean or committed

### End Condition
- `pytest` runs successfully (0 tests collected, 0 errors)
- `pip install -r requirements-dev.txt` works
- Git commit: `[WADJET] Phase 0 complete: Project Setup`

### Rollback
- Delete `tests/`, `pytest.ini`, `requirements-dev.txt`
- Revert `requirements.txt`, `.gitignore`, `pyproject.toml` changes
- `git checkout -- .`

---

## Phase 1: Security — Critical Fixes

**Goal**: Neutralize the 5 most dangerous vulnerabilities: CSRF actually works, rate limiting can't be spoofed, Settings singleton is unified, secrets are mandatory, path traversal defense-in-depth.

**Done when**: CSRF rejects unprotected POST/PUT/DELETE from cross-origin. Rate limit keys use real client IP. Settings is one instance. App refuses to start with empty JWT_SECRET in production. `stories_engine.py` validates story_id.

### Files Modified
- `app/main.py` — Rewrite CSRF exempt_urls to only exempt truly safe routes (GET-only, auth endpoints that handle their own security). Add notes documenting why each exemption exists.
- `app/config.py` — Add `@model_validator` that raises `ValueError` if `ENVIRONMENT=production` and `jwt_secret` or `csrf_secret` is empty.
- `app/dependencies.py` — Change `get_settings()` to return `from app.config import settings` (same singleton), not `Settings()`.
- `app/rate_limit.py` — Replace `_get_real_ip` with configurable trusted-proxy-depth approach. Add `TRUSTED_PROXY_DEPTH` env var (default: 1 for Render). When depth=0, use `get_remote_address()` (direct connection).
- `app/core/stories_engine.py` — Add `re.match(r'^[a-z0-9_-]+$', story_id)` guard in `load_story()` and `get_chapter()`.
- `.env.example` — Add `JWT_SECRET`, `CSRF_SECRET` with documentation.

### Start Condition
- Phase 0 complete

### End Condition
- Manual test: POST to `/api/user/profile` without CSRF token → 403
- Manual test: POST to `/api/auth/login` without CSRF token → succeeds (exempt)
- Manual test: `X-Forwarded-For` spoofing doesn't bypass rate limit
- Manual test: App startup fails with `ENVIRONMENT=production` and empty `JWT_SECRET`
- Manual test: `/stories/../../etc/passwd` returns 404 or None
- All existing functionality still works (scan, chat, explore, dictionary)
- Git commit: `[WADJET] Phase 1 complete: Security Critical Fixes`

### Rollback
- `git checkout -- app/main.py app/config.py app/dependencies.py app/rate_limit.py app/core/stories_engine.py .env.example`

---

## Phase 2: Security — High Priority

**Goal**: Fix remaining HIGH security issues: CSP header, chat auth + redesign, stream POST, SRI hash, OpenAPI gating, login timing oracle, audio validation.

### Files Modified
- `app/main.py` — Add CSP header to `security_headers` middleware. Disable `/docs` and `/openapi.json` when `is_production`.
- `app/api/chat.py` — Import `get_optional_user`. Add auth to `/clear`. Change `/stream` from GET to POST. Add rate limit to `/clear`.
- `app/core/thoth_chat.py` — Refactor `_build_prompt()` to use structured `messages` list (system/user/assistant roles) instead of text concatenation. Make sessions server-assigned UUIDs.
- `app/templates/chat.html` — Update SSE client to use `fetch()` + ReadableStream for POST-based streaming instead of `EventSource`.
- `app/templates/scan.html` — Add `integrity="sha384-..."` and `crossorigin="anonymous"` to ONNX Runtime CDN script tag.
- `app/api/auth.py` — Fix timing oracle: always run `verify_password` with dummy hash when user not found.
- `app/api/audio.py` — Check `Content-Length` before reading full file. Add magic bytes validation for audio. Stop accessing `groq._client` / `groq._headers()` directly.
- `app/api/explore.py` — Add `@limiter.limit("60/minute")` to `/{slug}` and `/{slug}/children`.
- `app/api/dictionary.py` — Add `@limiter.limit("30/minute")` to `/speak`.
- `app/api/write.py` — Add `@limiter.limit("60/minute")` to `/palette`.
- `app/api/quiz.py` — Add `@limiter.limit("60/minute")` to `/info`.

### Start Condition
- Phase 1 complete (CSRF is working correctly — exemption list is finalized)

### End Condition
- Response headers include `Content-Security-Policy`
- `/docs` returns 404 when `ENVIRONMENT=production`
- Chat clear requires valid auth token
- Chat stream accepts POST, rejects GET
- ONNX Runtime script has SRI hash
- Login takes same time for existing and non-existing emails
- Audio upload rejects early if `Content-Length` > 25MB
- All rate limits active on previously unprotected endpoints
- Git commit: `[WADJET] Phase 2 complete: Security High Priority`

### Rollback
- `git checkout -- app/main.py app/api/chat.py app/core/thoth_chat.py app/templates/chat.html app/templates/scan.html app/api/auth.py app/api/audio.py app/api/explore.py app/api/dictionary.py app/api/write.py app/api/quiz.py`

---

## Phase 3: Critical Bug Fixes

**Goal**: Fix all runtime crashes and deployment blockers.

### Files Modified
- `app/db/crud.py` — Fix `get_user_stats()` timezone mismatch: use `datetime.utcnow()` (naive UTC) consistently.
- `docker-compose.yml` — Fix port mapping to `"8000:7860"`.
- `Dockerfile` — Standardize to port 8000 in CMD if we want consistency. Or keep 7860 and fix compose. Decision: change Dockerfile CMD to `--port 8000` and EXPOSE to `8000` for consistency with dev. This also fixes Render (which reads `EXPOSE`).
- `app/api/chat.py` — Fix SSE generator: add `return` after error yield.
- `app/api/pages.py` — Add story existence check (call `load_story()`, return 404 if None). Add level bounds check for lessons (1-5).
- `render.yaml` — Fix service name `wadjet-v2` → `wadjet-v3`. Fix `buildCommand` to include `npm install`.

### Start Condition
- Phase 0 complete (can run independently from Phase 1)

### End Condition
- `GET /api/user/stats` returns 200 (not 500) for authenticated users
- `docker-compose up` makes app reachable at `localhost:8000`
- `/stories/nonexistent-slug` returns 404
- `/dictionary/lesson/99` returns 404
- SSE stream terminates cleanly on error
- Git commit: `[WADJET] Phase 3 complete: Critical Bug Fixes`

### Rollback
- `git checkout -- app/db/crud.py docker-compose.yml Dockerfile app/api/chat.py app/api/pages.py render.yaml`

---

## Phase 4: Database & Migrations

**Goal**: Fix data integrity issues — add missing indexes, cascade deletes, fix Alembic config, fix upsert race condition.

### Files Modified
- `app/db/models.py` — Add `index=True` to `StoryProgress.user_id`, `Favorite.user_id`, `RefreshToken.user_id`. Add `ondelete="CASCADE"` to all ForeignKey definitions.
- `alembic/env.py` — Read `DATABASE_URL` from environment with fallback to config.
- `alembic.ini` — Add comment noting URL is overridden by env.py.
- `app/db/crud.py` — Fix `upsert_story_progress()` race condition with try/except `IntegrityError` on insert.

### Files Created
- `alembic/versions/xxxx_add_indexes_and_cascades.py` — New migration (auto-generated then reviewed).

### Start Condition
- Phase 3 complete (Docker and server must work to test DB changes)

### End Condition
- `alembic upgrade head` succeeds
- `alembic downgrade -1` succeeds (rollback migration exists)
- Query `EXPLAIN` for user_id lookups shows index usage
- Deleting a user cascades to all child tables
- Concurrent story progress upserts don't crash
- Git commit: `[WADJET] Phase 4 complete: Database & Migrations`

### Rollback
- `alembic downgrade -1`
- `git checkout -- app/db/models.py alembic/env.py alembic.ini app/db/crud.py`

---

## Phase 5: Architecture Cleanup

**Goal**: Clean up the codebase structure — extract services, remove dead code, fix encapsulation, bound caches.

### Files Modified
- `app/core/ai_service.py` — Extract `GroqService` to separate file.
- `app/core/rag_translator.py` — Replace `groq._chat_completion()` and `grok._chat_completion()` calls with public API methods. Fix `GeminiEmbedder` to rotate keys.
- `app/core/tla_service.py` — Replace unbounded `self._cache` dict with `@lru_cache` (already imported). Remove dead `lru_cache` import if switching to `cachetools`.
- `app/core/thoth_chat.py` — Add TTL to `_SessionStore` (expire after 1 hour).
- `app/api/dictionary.py` — Replace unbounded `_tts_cache` with `cachetools.LRUCache(maxsize=500)`.
- `app/core/image_service.py` — Use shared `httpx.AsyncClient` instead of creating new one per call.

### Files Created
- `app/core/groq_service.py` — Extracted from `ai_service.py`.

### Files Deleted
- `app/core/rag_translator.py.bak` — Dead backup file.
- `app/utils/__init__.py` — Empty module (or repurpose with actual utilities).

### Start Condition
- Phase 1 complete (settings singleton finalized)

### End Condition
- `from app.core.groq_service import GroqService` works
- No private method access (`_chat_completion`, `_headers`) from outside their modules
- All caches have bounded size
- Chat sessions expire after inactivity
- No `.bak` files in source tree
- Git commit: `[WADJET] Phase 5 complete: Architecture Cleanup`

### Rollback
- `git checkout -- app/core/`
- Delete `app/core/groq_service.py` if it didn't exist before

---

## Phase 6: Input Validation & Prompt Hardening

**Goal**: Add missing validation on all user inputs. Harden AI prompts against injection.

### Files Modified
- `app/api/translate.py` — Add `max_length=2000` to `gardiner_sequence`.
- `app/api/user.py` — Add `preferred_lang` whitelist (`en`, `ar`). Add `max_length` to `item_id`. Narrow exception handling on favorites.
- `app/db/schemas.py` — Add `min_length=8` to password fields. Add `Literal["en", "ar"]` for `preferred_lang`.
- `app/api/scan.py` — Normalize MIME type from magic bytes instead of trusting `file.content_type`.
- `app/api/explore.py` — Same MIME normalization.
- `app/core/thoth_chat.py` — Add message length cap at service level (2000 chars).
- `app/core/write.py` — Sanitize user text before embedding in AI prompt (strip control chars, escape quotes).

### Start Condition
- Phase 2 complete (prompt hardening builds on chat redesign)

### End Condition
- Oversized gardiner_sequence returns 422
- Invalid `preferred_lang` returns 422
- Password < 8 chars returns 422
- Chat message > 2000 chars returns 422
- MIME type in AI calls matches magic bytes, not user content_type
- Git commit: `[WADJET] Phase 6 complete: Input Validation`

### Rollback
- `git checkout -- app/api/translate.py app/api/user.py app/db/schemas.py app/api/scan.py app/api/explore.py app/core/thoth_chat.py app/core/write.py`

---

## Phase 7: Frontend & UX Fixes

**Goal**: Fix client-side bugs and polish user experience.

### Files Modified
- `app/static/js/app.js` — Add automatic token refresh on 401 responses. Add blob URL revocation for TTS cache (cap at 50 entries).
- `app/static/js/tts.js` — Read language from cookie `wadjet_lang` instead of localStorage `wadjet-lang`. Remove localStorage-based lang detection.
- `app/templates/partials/nav.html` — Add `; Secure` to language cookie when not in dev mode.
- `app/static/css/input.css` — Fix header comment "v2" → "v3". Update `--color-gold-light` to `#E5C76B`, `--color-gold-dark` to `#B8962E`. Add missing `--color-ivory: #F5F0E8`, `--color-sand: #C4A265`, `--color-dust: #8B7355`.
- `app/templates/partials/seo.html` — Fix hreflang trailing slash for landing page.
- `app/templates/base.html` — Add `<meta name="robots" content="index, follow">`.

### Start Condition
- Phase 1 complete (CSRF is working — `app.js` fetch patch must be compatible)

### End Condition
- 401 response triggers automatic token refresh (not silent failure)
- TTS speaks in correct language matching UI language
- Language cookie has `Secure` flag in production
- CSS colors match CLAUDE.md spec
- Hreflang URLs are valid
- Git commit: `[WADJET] Phase 7 complete: Frontend & UX Fixes`

### Rollback
- `git checkout -- app/static/js/ app/templates/partials/ app/static/css/input.css app/templates/base.html`

---

## Phase 8: Performance Optimization

**Goal**: Fix key performance issues — key rotation, streaming retry, query optimization, race condition locks.

### Files Modified
- `app/core/rag_translator.py` — Fix `GeminiEmbedder._get_client()` to rotate through API keys.
- `app/core/gemini_service.py` — Add retry/key-rotation to `generate_text_stream()`.
- `app/db/crud.py` — Optimize `get_user_stats()` from 6 queries to 1-2.
- `app/api/write.py` — Add `threading.Lock` to lazy `_WRITE_CORPUS` initialization.
- `app/api/explore.py` — Add lock to `_landmark_pipeline` initialization. Replace `asyncio.get_event_loop()` with `asyncio.get_running_loop()`.
- `app/core/write.py` — Same lock for `_TRANSLIT_TO_SIGN` and `_ALPHA_TO_SIGN`.

### Start Condition
- Phase 5 complete (architecture cleanup must be done first — private method access fixed)

### End Condition
- Embedding requests rotate through available Gemini keys
- Chat streaming survives a 429 on one key
- `GET /api/user/stats` makes ≤2 DB queries
- No race condition on concurrent first-requests to write/explore
- Git commit: `[WADJET] Phase 8 complete: Performance Optimization`

### Rollback
- `git checkout -- app/core/rag_translator.py app/core/gemini_service.py app/db/crud.py app/api/write.py app/api/explore.py app/core/write.py`

---

## Phase 9: Test Coverage

**Goal**: Build comprehensive test suite covering all critical paths.

### Files Created
- `tests/test_auth.py` — Register, login, refresh, logout, invalid token, expired token
- `tests/test_security.py` — CSRF enforcement, rate limiting, path traversal, CSP header presence
- `tests/test_crud.py` — User CRUD, favorites, history, story progress, cascade deletes
- `tests/test_scan.py` — Upload validation, magic bytes, MIME check, pipeline integration
- `tests/test_chat.py` — Stream, clear with/without auth, session management
- `tests/test_stories.py` — Load all stories, chapter access, nonexistent story
- `tests/test_dictionary.py` — Search, pagination, categories, alphabet, speak
- `tests/test_explore.py` — List, detail, children, identify
- `tests/test_write.py` — Alpha mode, smart mode, palette
- `tests/test_user.py` — Profile, favorites, history, stats, limits

### Files Modified
- `tests/conftest.py` — Add fixtures for authenticated client, test database, mock AI services

### Start Condition
- Phases 1-6 complete (testing the fixed code, not the broken code)

### End Condition
- `pytest` passes with 0 failures
- Coverage report shows ≥70% on `app/api/auth.py`, `app/api/chat.py`, `app/db/crud.py`
- Coverage report shows ≥50% on `app/api/` overall
- Git commit: `[WADJET] Phase 9 complete: Test Coverage`

### Rollback
- Tests are additive — no rollback needed. Delete `tests/` to fully revert.

---

## Phase 10: DevOps, Docs & Final Polish

**Goal**: Production-ready deployment config, complete documentation, final cleanup.

### Files Modified
- `.env.example` — Complete with ALL env vars, descriptions, and example values
- `Dockerfile` — Add non-root user, HEALTHCHECK instruction
- `render.yaml` — Correct service name, add all env vars with `sync: false`
- `app/api/health.py` — Add DB connectivity check, AI service status
- `README.md` — Add "Getting Started" section with full setup instructions
- `CLAUDE.md` — Fix color value discrepancies to match updated CSS
- `package.json` — Fix license to "MIT", remove `"main": "index.js"`
- `pyproject.toml` — Fix `requires-python` to `>=3.13`

### Files Created
- `requirements.lock` — Frozen exact versions for CI reproducibility

### Start Condition
- Phases 3-4 complete (Docker and DB must be working)

### End Condition
- `docker-compose up` starts successfully, app reachable at `localhost:8000`
- `GET /api/health` checks DB and reports version
- New developer can set up project in <30 minutes following README
- `CLAUDE.md` colors match `input.css` colors
- Git commit: `[WADJET] Phase 10 complete: DevOps & Documentation`

### Rollback
- `git checkout -- .env.example Dockerfile render.yaml app/api/health.py README.md CLAUDE.md package.json pyproject.toml`
