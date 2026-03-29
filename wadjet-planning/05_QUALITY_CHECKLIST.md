# WADJET v3 — QUALITY CHECKLIST

> Final gate checklist per phase. Every box must be checked before marking a phase complete.

---

## Universal Checks (Every Phase)

### Code Quality
- [ ] No new linting errors: `ruff check app/`
- [ ] Type hints on all new/modified function signatures
- [ ] No hardcoded secrets, API keys, or credentials in code
- [ ] No `print()` statements — use `logging` module
- [ ] Files under 300 lines (split if exceeded)
- [ ] snake_case for Python, kebab-case for CSS, camelCase for JS

### Git Discipline
- [ ] All changes committed with `[WADJET] Phase N: description`
- [ ] No untracked files left behind
- [ ] No merge conflicts

### No Regressions
- [ ] `pytest -v` passes (all existing tests green)
- [ ] Server starts: `uvicorn app.main:app --reload --port 8000`
- [ ] Landing page loads: GET / → 200
- [ ] No Python tracebacks in server output during manual check

---

## Phase-Specific Gates

### Phase 0 — Setup
- [x] `pytest` exits 0 (1 smoke test passes)
- [x] `requirements-dev.txt` installs cleanly
- [x] `requirements.txt` uses `~=` pinning
- [x] `.gitignore` updated
- [x] Git commit: `[WADJET] Phase 0 complete`

### Phase 1 — Security Critical
- [x] CSRF rejects unprotected POST to /api/user/favorites → 403
- [x] CSRF allows POST to /api/auth/login → 401 (not 403)
- [x] Rate limit holds with forged X-Forwarded-For (depth=1 behind proxy; depth=0 for direct)
- [x] `ENVIRONMENT=production JWT_SECRET="" python -c "from app.config import settings"` → ValueError
- [x] `ENVIRONMENT=development JWT_SECRET="" python -c "from app.config import settings"` → OK
- [x] `get_settings()` returns the SAME object as `config.settings`
- [x] load_story("../../etc/passwd") → None
- [x] .env.example has JWT_SECRET, CSRF_SECRET, TRUSTED_PROXY_DEPTH
- [x] Git commit: `[WADJET] Phase 1 complete: Security Critical`

### Phase 2 — Security High
- [x] Response headers include Content-Security-Policy
- [x] CSP doesn't break any page (check console on /, /scan, /chat, /stories, /explore)
- [x] GET /docs → 404 with ENVIRONMENT=production
- [x] GET /api/chat/stream → 405
- [x] POST /api/chat/stream with JSON body → works (SSE stream)
- [x] Chat page works end-to-end in browser
- [x] Login timing: <50ms variance between valid and invalid emails (test 10x each)
- [x] POST audio >25MB → 413
- [x] All added rate limits work (test with burst requests)
- [x] Git commit: `[WADJET] Phase 2 complete: Security High`

### Phase 3 — Bug Fixes
- [x] GET /api/user/stats → 200 (authenticated)
- [x] `docker build -t wadjet . && docker run -p 8000:8000 wadjet` → app at localhost:8000
- [x] GET /stories/nonexistent → 404
- [x] GET /stories/osiris-myth → 200
- [x] GET /dictionary/lesson/0 → 404
- [x] GET /dictionary/lesson/3 → 200
- [x] render.yaml service name is `wadjet-v3`
- [x] Git commit: `[WADJET] Phase 3 complete: Bug Fixes`

### Phase 4 — Database
- [x] `alembic upgrade head` succeeds
- [x] `alembic downgrade -1` succeeds
- [x] `alembic upgrade head` again succeeds (roundtrip)
- [x] Backup of wadjet.db exists before migration
- [x] User deletion cascades to all child tables
- [x] Story progress upsert works under concurrency
- [x] Git commit: `[WADJET] Phase 4 complete: Database`

### Phase 5 — Architecture
- [ ] No circular imports
- [ ] No private method access across modules
- [ ] Dead code removed (quiz_engine if deprecated)
- [ ] All caches have size limits (LRU maxsize or TTL)
- [ ] All existing tests pass (regression)
- [ ] Git commit: `[WADJET] Phase 5 complete: Architecture`

### Phase 6 — Input Validation
- [ ] All string inputs have max_length
- [ ] Language parameter only accepts en/ar
- [ ] Password requires 8+ chars, 1 upper, 1 lower, 1 digit
- [ ] File uploads validated by MIME type
- [ ] No 500 errors from malformed input (test with empty strings, special chars)
- [ ] Git commit: `[WADJET] Phase 6 complete: Input Validation`

### Phase 7 — Frontend & UX
- [ ] No console errors on any page
- [ ] 401 response triggers token refresh, then retries
- [ ] Language preference synced: localStorage → cookie and vice versa
- [ ] TTS audio plays and blob URL is revoked after
- [ ] CSS colors match CLAUDE.md design system
- [ ] meta descriptions present on all pages
- [ ] All existing tests pass
- [ ] Git commit: `[WADJET] Phase 7 complete: Frontend & UX`

### Phase 8 — Performance
- [ ] Gemini key rotation uses round-robin (not always key[0])
- [ ] Embedding service rotates keys
- [ ] Services use asyncio.Lock for initialization (no double-init)
- [ ] Stats queries use indexes (EXPLAIN shows index scan)
- [ ] Streaming endpoints retry once on transient failure
- [ ] Git commit: `[WADJET] Phase 8 complete: Performance`

### Phase 9 — Test Coverage
- [ ] `pytest --cov=app --cov-report=term-missing` → 80%+ coverage
- [ ] Security tests written and passing
- [ ] Auth tests written and passing
- [ ] Database tests written and passing
- [ ] API route tests written and passing
- [ ] Core logic tests written and passing
- [ ] Git commit: `[WADJET] Phase 9 complete: Tests`

### Phase 10 — DevOps & Docs
- [ ] .env.example is complete and documented
- [ ] Dockerfile builds without warnings
- [ ] docker-compose up → app reachable
- [ ] render.yaml validates against Render's spec
- [ ] README.md has: setup, env vars, dev commands, deployment
- [ ] Health check endpoint works: GET /api/health → 200
- [ ] Git commit: `[WADJET] Phase 10 complete: DevOps & Docs`

---

## OWASP Top 10 Checklist (Phase 9 Gate)

| # | Category | Status | How We Address It |
|---|----------|--------|------------------|
| A01 | Broken Access Control | ☐ | Auth on all protected routes, CSRF active, path traversal blocked |
| A02 | Cryptographic Failures | ☐ | bcrypt for passwords, HS256 JWT with strong secrets, SHA-256 token hashing |
| A03 | Injection | ☐ | SQLAlchemy parameterized queries, Jinja2 auto-escaping, input validation |
| A04 | Insecure Design | ☐ | Rate limiting, fallback chains, defense-in-depth |
| A05 | Security Misconfiguration | ☐ | CSP headers, OpenAPI gated, mandatory prod secrets, no debug in prod |
| A06 | Vulnerable Components | ☐ | Deps pinned with ~=, SRI on CDN scripts |
| A07 | Auth Failures | ☐ | Timing-safe login, token rotation, refresh token revocation |
| A08 | Data Integrity | ☐ | CSRF protection, input validation, cascade deletes |
| A09 | Logging & Monitoring | ☐ | Structured logging, health check endpoint |
| A10 | SSRF | ☐ | No user-controlled URL fetching in backend |

---

## Final Sign-Off

Before declaring the project audit-clean:

- [ ] All 10 phases complete and committed
- [ ] All phase-specific gates passed
- [ ] Full test suite green: `pytest -v`
- [ ] Coverage ≥ 80%: `pytest --cov=app`
- [ ] OWASP checklist all checked
- [ ] Docker build + run successful
- [ ] Manual smoke test of all 14 pages
- [ ] No TODO/FIXME/HACK comments introduced
- [ ] CHANGELOG.md updated with audit fix summary
