# WADJET v3 — PHASE EXECUTION PROMPTS

> Each prompt is self-contained — pasteable cold with zero prior context needed.
> Designed for the Copilot agent to execute each phase independently.

---

## PHASE 0 PROMPT: Project Setup & Foundation

```
You are working on Wadjet v3 Beta at D:\Personal attachements\Projects\Wadjet-v3-beta.

CONTEXT: This is a FastAPI + Jinja2 + Alpine.js Egyptian heritage web app. We are performing
a comprehensive security/quality audit fix-up. This is Phase 0 — establishing test
infrastructure and dependency hygiene before any code changes.

WHAT TO DO:

1. Check git status. If there are uncommitted changes, commit them with message:
   "[WADJET] Pre-Phase 0 checkpoint"

2. Create test infrastructure:
   - Create `tests/__init__.py` (empty)
   - Create `tests/conftest.py` with:
     - pytest-asyncio fixture for async test support
     - `test_client` fixture using httpx.AsyncClient + FastAPI TestClient
     - `test_db` fixture that creates a fresh in-memory SQLite DB per test
     - `mock_settings` fixture that provides settings with known JWT_SECRET
     - `authenticated_client` fixture that creates a test user + returns client with valid token
   - Create `pytest.ini` with asyncio_mode=auto, testpaths=tests

3. Create `requirements-dev.txt`:
   pytest>=8.0
   pytest-asyncio>=0.23
   httpx>=0.27
   coverage>=7.0
   pytest-cov>=5.0

4. Modify `requirements.txt`: Change all `>=` to `~=` (compatible release operator).
   Example: `fastapi>=0.135.0` → `fastapi~=0.135.0`

5. Modify `.gitignore`: Add these lines:
   wadjet-v3-planning-ARCHIVED-*
   htmlcov/
   .coverage
   .pytest_cache/

6. Run: pip install -r requirements-dev.txt
7. Run: pytest (should show "0 tests collected", no errors)
8. Git commit: "[WADJET] Phase 0 complete: Project Setup"

DO NOT TOUCH:
- Any file in app/ (no production code changes)
- Any template, CSS, or JS file
- Docker or deployment configs
- The database

TEST AFTER:
- `pytest` exits with code 0
- `python -c "from tests.conftest import *"` doesn't error
```

---

## PHASE 1 PROMPT: Security — Critical Fixes

```
You are working on Wadjet v3 Beta at D:\Personal attachements\Projects\Wadjet-v3-beta.
Phase 0 is complete — test infrastructure exists, deps are pinned.

CONTEXT: The audit found 5 critical security issues that must be fixed first:
1. CSRF middleware is completely inoperative (ALL /api/* routes are exempt)
2. Rate limiting bypassable via X-Forwarded-For header spoofing
3. Two Settings instances — jwt/csrf secrets diverge between config.settings and get_settings()
4. JWT/CSRF secrets are ephemeral (auto-generated on restart)
5. stories_engine.py has no defense-in-depth against path traversal

What came before: Phase 0 set up test infrastructure.

WHAT TO DO:

### Fix 1: CSRF — Make it actually work
File: `app/main.py`

The current CSRF exempt_urls list exempts EVERY /api/* route. The app uses `app.js` to add
`x-csrftoken` header to all mutating fetch() calls. HTMX requests also get the CSRF header
via `htmx:configRequest` event listener in app.js.

Therefore: Only exempt routes that legitimately cannot carry CSRF tokens:
- /api/health (GET only)
- /api/auth/login, /api/auth/register, /api/auth/refresh (auth bootstrap — no session yet)
- /api/auth/logout (deletes session, safe to exempt)
- /docs, /openapi.json (read-only)

Remove ALL other exemptions. The `app.js` global fetch interceptor already adds the CSRF
token to all POST/PUT/DELETE requests, so they will pass CSRF validation.

### Fix 2: Rate Limiting
File: `app/rate_limit.py`

Replace `_get_real_ip()` with a configurable approach:
- Add `TRUSTED_PROXY_DEPTH` to Settings (default: 1)
- If depth=0: use get_remote_address(request) — direct connection, no proxy trust
- If depth=N: take the Nth-from-right IP in X-Forwarded-For (rightmost trusted entry)
- This way, Render (which adds 1 proxy hop) works with depth=1

Also update `app/config.py` to add `trusted_proxy_depth: int = 1`.

### Fix 3: Settings Singleton
File: `app/dependencies.py`

Change get_settings() from:
  @lru_cache
  def get_settings() -> Settings:
      return Settings()

To:
  def get_settings() -> Settings:
      from app.config import settings
      return settings

Remove the @lru_cache — it's not needed when returning the same singleton.
Remove the `from app.config import Settings` import (now unused).

### Fix 4: Mandatory Secrets in Production
File: `app/config.py`

Add a model_validator that checks: if ENVIRONMENT != "development", then jwt_secret and
csrf_secret must not be empty. Raise ValueError with clear message.

### Fix 5: Path Traversal Defense-in-Depth
File: `app/core/stories_engine.py`

In both `load_story()` and `get_chapter()` (or wherever story_id is used to build a path),
add at the top:
  import re
  if not re.match(r'^[a-z0-9_-]+$', story_id):
      return None

Also in both functions, after constructing the path, verify:
  if not path.resolve().is_relative_to(STORIES_DIR.resolve()):
      return None

### Fix 6: Update .env.example
Add with clear comments:
  # REQUIRED in production — generate with: python -c "import secrets; print(secrets.token_hex(32))"
  JWT_SECRET=
  CSRF_SECRET=
  # Trusted proxy depth (0=direct, 1=one reverse proxy like Render)
  TRUSTED_PROXY_DEPTH=1

DO NOT TOUCH:
- Templates, CSS, JS (frontend changes are Phase 7)
- Database models or migrations
- AI service files
- Chat or audio endpoints (those are Phase 2)

TEST AFTER:
1. Start the server: uvicorn app.main:app --reload --port 8000
2. Test CSRF blocks unprotected POST:
   curl -X POST http://localhost:8000/api/user/favorites -H "Content-Type: application/json" -d '{"item_type":"landmark","item_id":"test"}'
   → Should return 403 (CSRF rejected)
3. Test CSRF allows auth routes:
   curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"test"}'
   → Should return 401 (invalid creds), NOT 403 (CSRF)
4. Test rate limiting can't be spoofed (hit limit, then try with fake X-Forwarded-For)
5. Verify app starts normally with ENVIRONMENT=development and empty secrets
6. Verify app REFUSES to start with ENVIRONMENT=production and empty JWT_SECRET
```

---

## PHASE 2 PROMPT: Security — High Priority

```
You are working on Wadjet v3 Beta at D:\Personal attachements\Projects\Wadjet-v3-beta.
Phase 1 is complete — CSRF works, rate limiting is real, Settings is unified, secrets are enforced.

CONTEXT: Fixing remaining HIGH security issues — CSP header, chat authentication, stream
method change, SRI hash, OpenAPI gating, timing oracle, audio validation, missing rate limits.

WHAT TO DO:

### 1. Content-Security-Policy Header
File: `app/main.py` — in `security_headers` middleware, add:
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'

Note: 'unsafe-inline' for scripts is needed because Alpine.js and the templates use inline
event handlers. This can be tightened with nonces in a future phase.

### 2. OpenAPI Gating
File: `app/main.py` — in `create_app()`, set:
  docs_url=None if settings.is_production else "/docs"
  redoc_url=None  
  openapi_url=None if settings.is_production else "/openapi.json"

### 3. Chat Auth & Redesign  
File: `app/api/chat.py`:
- Import `get_optional_user` from `app.auth.dependencies`
- Add `@limiter.limit("10/minute")` to `/clear`
- Add `user = Depends(get_optional_user)` to `/clear` — if user is None, still allow
  but require session_id to be a valid UUID format
- Change `/stream` from @router.get to @router.post
- In stream endpoint, accept message/session_id as JSON body not query params

File: `app/core/thoth_chat.py`:
- Refactor _build_prompt to return a list of dicts [{role: "system", content: ...}, ...]
  instead of concatenated text. This prevents prompt injection via user message.
- Session IDs: when creating new session, generate UUID server-side

File: `app/templates/chat.html`:
- Replace EventSource with fetch() + ReadableStream for POST-based SSE
- Pattern:
    const response = await fetch('/api/chat/stream', {
      method: 'POST', headers: {'Content-Type': 'application/json', ...csrf},
      body: JSON.stringify({message, session_id})
    });
    const reader = response.body.getReader();
    // Process SSE chunks...

### 4. SRI Hash on CDN Script
File: `app/templates/scan.html`:
- Find the <script src="https://cdn.jsdelivr.net/npm/onnxruntime-web@1.18.0/dist/ort.min.js">
- Add integrity and crossorigin attributes
- To get the hash: fetch the file and compute sha384

### 5. Login Timing Oracle Fix
File: `app/api/auth.py`:
- When user is not found, still run verify_password against a dummy hash:
    DUMMY_HASH = "$2b$12$LJ3m4ys3Lp.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    if not user:
        verify_password("dummy", DUMMY_HASH)  # constant-time waste
        raise HTTPException(401, "Invalid email or password")

### 6. Audio Endpoint Fixes
File: `app/api/audio.py`:
- Before `await file.read()`, check Content-Length header:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 25 * 1024 * 1024:
        raise HTTPException(413, "File too large")
- Add magic bytes validation for audio (WAV: RIFF, MP3: ID3/\xff\xfb, OGG: OggS, FLAC: fLaC, WebM: \x1a\x45)
- Replace groq._client.post() with a public method on GroqService

### 7. Missing Rate Limits
Files: explore.py, dictionary.py, write.py, quiz.py
- Add @limiter.limit decorators to all unprotected endpoints (see Phase Map for specifics)

DO NOT TOUCH:
- Database models or migrations
- The scan pipeline or translation logic
- AI service core logic (just the public API surface)

TEST AFTER:
- Check response headers for Content-Security-Policy
- /docs returns 404 with ENVIRONMENT=production
- POST /api/chat/clear without auth token → 401 or requires UUID format
- POST /api/chat/stream with JSON body works
- GET /api/chat/stream → 405 Method Not Allowed
- Login timing is consistent for valid and invalid emails (~same response time)
- Large audio upload rejected early (before full read)
```

---

## PHASE 3 PROMPT: Critical Bug Fixes

```
You are working on Wadjet v3 Beta at D:\Personal attachements\Projects\Wadjet-v3-beta.
This phase can run after Phase 0, independently from Phase 1.

CONTEXT: Fixing runtime crashes and deployment blockers.

WHAT TO DO:

### 1. Timezone Crash in Stats
File: `app/db/crud.py`
Find: datetime.now(timezone.utc).replace(...)
Replace with: datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
This creates a naive UTC datetime matching the naive datetimes stored by SQLAlchemy's func.now().

### 2. Docker Port Consistency
File: `Dockerfile`
Change: EXPOSE 7860 → EXPOSE 8000
Change CMD: --port 7860 → --port 8000

File: `docker-compose.yml`
Port mapping is now "8000:8000" which matches the new Dockerfile.
(Currently it says "8000:8000" which will now work correctly.)

### 3. SSE Error Handling
File: `app/api/chat.py`
In the event_generator, after the error yield, add `return` to terminate the generator.

### 4. Story/Lesson Validation in Pages
File: `app/api/pages.py`
- For /stories/{story_id}: after the regex check, call load_story(story_id). If None, return 404.
- For /dictionary/lesson/{level}: add bounds check `if level < 1 or level > 5: raise HTTPException(404)`

### 5. render.yaml Fixes
File: `render.yaml`
- Change `name: wadjet-v2` → `name: wadjet-v3`
- Change buildCommand to: `npm install && npx @tailwindcss/cli -i app/static/css/input.css -o app/static/dist/styles.css --minify && pip install -r requirements.txt`
- Add missing env vars list (with sync: false)

TEST AFTER:
- Start server, login, hit /api/user/stats → 200 (not 500)
- docker-compose build && docker-compose up → app reachable at localhost:8000
- /stories/nonexistent → 404
- /dictionary/lesson/0 → 404
- /dictionary/lesson/3 → 200
```

---

## PHASE 4 PROMPT: Database & Migrations

```
You are working on Wadjet v3 Beta. Phase 3 is complete.

CONTEXT: Database integrity fixes — add missing indexes, cascade deletes, fix Alembic config.

WHAT TO DO:

### 1. Fix Models
File: `app/db/models.py`
- StoryProgress.user_id: add index=True
- Favorite.user_id: add index=True  
- RefreshToken.user_id: add index=True
- ALL ForeignKey("users.id") calls: add ondelete="CASCADE"

### 2. Fix Alembic
File: `alembic/env.py`
After `config = context.config`, add:
  import os
  db_url = os.environ.get("DATABASE_URL")
  if db_url:
      config.set_main_option("sqlalchemy.url", db_url)

### 3. Generate Migration
Run: alembic revision --autogenerate -m "add_indexes_and_cascades"
Review the generated file — ensure it uses batch_alter_table for SQLite compatibility.

### 4. Fix Upsert Race Condition
File: `app/db/crud.py`
In upsert_story_progress(), wrap the insert in try/except IntegrityError:
  try:
      db.add(progress)
      await db.flush()
  except IntegrityError:
      await db.rollback()
      # Re-fetch and update instead
      existing = await get_story_progress(db, user_id, story_id)
      if existing:
          # update fields...

TEST AFTER:
- alembic upgrade head — succeeds
- alembic downgrade -1 — succeeds  
- Delete a user → verify all child rows cascade-deleted
- Concurrent story progress saves don't crash
```

---

## PHASES 5-10 PROMPTS

*Phases 5-10 follow the same pattern. Each prompt contains:*
- What phase this is and what came before
- Exact files to touch with exact changes
- How to test locally
- What "done" looks like
- What NOT to touch

*These prompts are detailed in the Phase Map (01_PHASE_MAP.md). The execution prompts
for Phases 5-10 will be written in detail when we reach those phases, as the exact changes
may be influenced by decisions made in Phases 1-4.*

### Phase 5 Brief: Architecture Cleanup
Extract GroqService, delete dead code, bound caches, fix private method access.

### Phase 6 Brief: Input Validation
Add max_length, lang whitelist, password complexity, MIME normalization.

### Phase 7 Brief: Frontend & UX
Token auto-refresh, lang sync, blob cleanup, CSS color fixes, SEO fixes.

### Phase 8 Brief: Performance
Key rotation for embeddings, streaming retry, stats query optimization, lazy init locks.

### Phase 9 Brief: Test Coverage
Write tests for all critical paths — auth, security, CRUD, API routes.

### Phase 10 Brief: DevOps & Docs
Complete .env.example, harden Dockerfile, fix render.yaml, update README, health check.
