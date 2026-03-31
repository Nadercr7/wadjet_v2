# WADJET v3 — TESTING PLAN

> Per-phase verification, test categories, and regression strategy.

---

## Test Infrastructure (Phase 0)

| Component | Tool | Config |
|-----------|------|--------|
| Test runner | pytest 8.0+ | `pytest.ini` — asyncio_mode=auto |
| Async support | pytest-asyncio 0.23+ | Auto mode — no manual markers |
| HTTP testing | httpx 0.27+ | AsyncClient with ASGITransport |
| Coverage | coverage + pytest-cov | Target: 80%+ on app/ |
| Fixtures | tests/conftest.py | test_client, test_db, auth_client |

---

## Test Categories

### 1. Security Tests (`tests/test_security.py`)

| Test | Phase | What It Verifies |
|------|-------|-----------------|
| CSRF blocks unprotected POST | P1 | POST to /api/user/favorites without CSRF token → 403 |
| CSRF allows exempt routes | P1 | POST to /api/auth/login without CSRF → 401 (not 403) |
| Rate limit not bypassable | P1 | Hit rate limit, retry with forged X-Forwarded-For → still blocked |
| Mandatory secrets in prod | P1 | Settings(environment="production", jwt_secret="") → ValueError |
| Path traversal blocked | P1 | load_story("../../etc/passwd") → None |
| Path traversal blocked | P1 | load_story("story-1") with resolve() outside STORIES_DIR → None |
| CSP header present | P2 | Any response has Content-Security-Policy header |
| OpenAPI hidden in prod | P2 | /docs → 404 when ENVIRONMENT=production |
| Chat stream is POST only | P2 | GET /api/chat/stream → 405 |
| Login timing oracle | P2 | avg(time for valid email) ≈ avg(time for invalid email) ±50ms |
| Audio size limit | P2 | Upload >25MB → 413 before full read |
| Input max lengths | P6 | Message >10000 chars → 422 |

### 2. Auth Tests (`tests/test_auth.py`)

| Test | What It Verifies |
|------|-----------------|
| Register creates user | POST /api/auth/register with valid data → 201 + user object |
| Register rejects duplicate email | Same email twice → 409 |
| Login returns tokens | POST /api/auth/login → 200 + access_token in body + refresh in cookie |
| Login rejects bad password | Wrong password → 401 |
| Login rejects nonexistent user | Unknown email → 401 (same error as bad password) |
| Token refresh works | POST /api/auth/refresh with valid refresh cookie → new tokens |
| Token refresh rotates | Old refresh token invalidated after refresh |
| Logout clears cookies | POST /api/auth/logout → refresh cookie cleared |
| Expired token rejected | Access token after TTL → 401 |
| Malformed token rejected | Random string as Bearer → 401 |

### 3. Database Tests (`tests/test_db.py`)

| Test | What It Verifies |
|------|-----------------|
| Cascade delete works | Delete user → all favorites/history/progress/tokens gone |
| FK indexes exist | Check index metadata on user_id columns |
| Upsert no race condition | Concurrent upsert_story_progress → no IntegrityError |
| Stats timezone works | get_user_stats with UTC datetimes → no crash |
| Stats returns correct counts | Known data → correct weekly/monthly counts |

### 4. API Route Tests (`tests/test_routes.py`)

| Test | What It Verifies |
|------|-----------------|
| Health check | GET /api/health → 200 + {"status": "healthy"} |
| All pages render | GET each of 14 page routes → 200 + contains `<html` |
| 404 page | GET /nonexistent → 404 |
| Story page validates ID | GET /stories/../../bad → 404 |
| Lesson bounds | GET /dictionary/lesson/0 → 404, /dictionary/lesson/6 → 404 |
| Explore search | POST /api/explore/search → results array |
| Dictionary lookup | GET /api/dictionary/A1 → glyph data or 404 |

### 5. Core Logic Tests (`tests/test_core.py`)

| Test | What It Verifies |
|------|-----------------|
| Story loading | load_story("isis-and-osiris") → valid story object |
| Story not found | load_story("nonexistent") → None |
| Gardiner lookup | gardiner_lookup("A1") → correct glyph data |
| Translation pipeline | translate_text("𓀀") → non-empty result |
| AI service fallback | Primary service fails → secondary called |

---

## Per-Phase Verification Checklist

### Phase 0 — Setup
- [ ] `pytest` runs and exits 0
- [ ] Test fixtures importable
- [ ] requirements-dev.txt installable

### Phase 1 — Security Critical
- [ ] CSRF test passes (protected route blocked, exempt route allowed)
- [ ] Rate limit test passes (forged IP doesn't bypass)
- [ ] Settings singleton test passes (dependencies.get_settings() is config.settings)
- [ ] Path traversal test passes
- [ ] Server starts with empty secrets in dev mode
- [ ] Server REFUSES to start with empty secrets in prod mode

### Phase 2 — Security High
- [ ] CSP header in responses
- [ ] /docs returns 404 in production config
- [ ] Chat requires POST for stream
- [ ] Login timing consistent (±50ms for valid vs invalid email)
- [ ] Large audio upload rejected early

### Phase 3 — Bug Fixes
- [ ] /api/user/stats returns 200 (not 500 timezone crash)
- [ ] Docker container reachable at port 8000
- [ ] /stories/bad-id returns 404
- [ ] /dictionary/lesson/0 returns 404

### Phase 4 — Database
- [ ] Migration up/down succeeds
- [ ] Cascade delete verified
- [ ] Concurrent upsert doesn't crash

### Phase 5 — Architecture
- [ ] No import errors after refactor
- [ ] All existing tests still pass (regression)

### Phase 6 — Input Validation
- [ ] Oversized inputs rejected with 422
- [ ] Invalid lang values rejected
- [ ] Password complexity enforced on register

### Phase 7 — Frontend
- [ ] No console errors on any page
- [ ] CSRF token refreshes after expiry
- [ ] Language preference synced between localStorage and cookie
- [ ] TTS blob URLs revoked after use

### Phase 8 — Performance
- [ ] API key rotation works (not always key[0])
- [ ] Stats query uses index (check EXPLAIN)
- [ ] Services initialize with asyncio.Lock (no double-init)

### Phase 9 — Test Coverage
- [ ] coverage report shows 80%+ on app/
- [ ] All tests in categories 1-5 written and passing

### Phase 10 — DevOps
- [ ] Docker builds and runs cleanly
- [ ] render.yaml validates
- [ ] Health check endpoint works
- [ ] .env.example has all required vars documented

---

## Regression Strategy

After EVERY phase:
1. Run full test suite: `pytest -v`
2. Start server: `uvicorn app.main:app --reload`
3. Hit key pages manually: /, /scan, /chat, /stories, /dashboard
4. Check browser console for JS errors
5. Check server logs for Python errors

After Phases 4 and 9 specifically:
- Run: `pytest --cov=app --cov-report=html`
- Review htmlcov/index.html for gaps
