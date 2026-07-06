# WADJET v3 — DEPENDENCIES & RISKS

> External dependencies, cross-file impact map, and risk mitigation.

---

## New Dependencies Added

### Phase 0 — Dev-Only
| Package | Version | Purpose | Risk |
|---------|---------|---------|------|
| pytest | ~=8.0 | Test runner | None — dev only |
| pytest-asyncio | ~=0.23 | Async test support | None — dev only |
| httpx | ~=0.27 | Async HTTP test client | None — dev only |
| coverage | ~=7.0 | Code coverage | None — dev only |
| pytest-cov | ~=5.0 | Coverage plugin | None — dev only |

### Production Changes
| Change | Phase | Impact |
|--------|-------|--------|
| Pin `>=` → `~=` in requirements.txt | P0 | Prevents surprise major version breaks |
| No new production deps added | All | Zero supply chain risk |

---

## Cross-File Impact Map

### Phase 1: Security — Critical
```
config.py          → model_validator added (affects ALL Settings consumers)
dependencies.py    → get_settings() now returns config.settings (affects ALL DI users)
main.py            → CSRF exempt list shrinks (affects ALL API POST/PUT/DELETE routes)
rate_limit.py      → IP extraction logic changes (affects ALL rate-limited endpoints)
stories_engine.py  → Path validation added (affects /stories/{id} route)
.env / .env.example → New vars: TRUSTED_PROXY_DEPTH
```

**Blast radius**: Wide — CSRF and rate limiting touch every endpoint.  
**Rollback**: Revert main.py CSRF list to restore old behavior. Revert rate_limit.py.

### Phase 2: Security — High
```
main.py            → CSP header added (affects ALL responses)
main.py            → OpenAPI gated (affects /docs, /openapi.json)
chat.py            → GET→POST, JSON body (affects chat.html EventSource→fetch)
thoth_chat.py      → Prompt format change (affects chat quality)
chat.html          → EventSource→ReadableStream (frontend breaking change)
scan.html          → SRI hash added (no behavior change)
auth.py            → Timing fix (no behavior change)
audio.py           → Size + type validation (may reject edge-case files)
explore.py, dictionary.py, write.py, quiz.py → Rate limits added
```

**Blast radius**: Chat is a breaking change (GET→POST + new frontend).  
**Rollback**: Revert chat.py + chat.html. CSP/OpenAPI are additive.

### Phase 3: Bug Fixes
```
crud.py            → Timezone fix (affects /api/user/stats)
Dockerfile         → Port change (affects Docker deployment)
docker-compose.yml → Already correct after Dockerfile fix
chat.py            → SSE yield fix (minor)
pages.py           → Route validation (affects /stories/{id}, /dictionary/lesson/{level})
render.yaml        → Service name + build command (affects Render deployment)
```

**Blast radius**: Low — each fix is isolated.  
**Rollback**: Per-fix revert.

### Phase 4: Database
```
models.py          → Index + cascade changes (requires migration)
alembic/env.py     → Dynamic URL (affects migration commands)
alembic/versions/  → New migration file (schema change)
crud.py            → Upsert race fix (affects story progress saves)
```

**Blast radius**: MEDIUM — schema migration can't be easily undone in production SQLite.  
**Rollback**: `alembic downgrade -1` — but only if migration has proper downgrade.

### Phases 5-10
Lower risk — architecture cleanup, validation, frontend, performance, tests, devops.
Cross-file impacts are limited within each phase.

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | CSRF change breaks legitimate requests | MEDIUM | HIGH | Test with browser DevTools — verify app.js adds X-CSRFTOKEN to all fetches. Check HTMX configRequest listener. |
| R2 | Rate limit change blocks real users behind proxy | LOW | MEDIUM | Default trusted_proxy_depth=1 matches Render's setup. Test with curl from Render. |
| R3 | Chat GET→POST breaks existing bookmarks/links | LOW | LOW | Chat stream is AJAX — no bookmarkable URLs. Only chat.html calls it. |
| R4 | CSP blocks legitimate resources | MEDIUM | HIGH | Test all pages after CSP is added. Check console for CSP violations. Iterate on the policy. |
| R5 | SQLite migration fails on production DB | LOW | HIGH | Test migration on copy of production DB first. Keep pre-migration backup. |
| R6 | Pin to `~=` breaks on next `pip install` | LOW | LOW | `~=` allows patch versions. Only major breaks are blocked. |
| R7 | Timing fix in login adds latency | LOW | LOW | bcrypt verify is already ~100ms. Dummy verify adds ~100ms on "user not found" only. |
| R8 | Audio magic bytes check rejects valid files | LOW | MEDIUM | Check common browser recording formats (WebM, WAV). Allow unknown types through with a warning log. |

---

## Security-Sensitive Changes

These changes affect the security posture and need extra review:

| Change | File | Why It Matters |
|--------|------|---------------|
| CSRF exempt list | main.py | Wrong list = either broken app or no CSRF protection |
| IP extraction | rate_limit.py | Wrong depth = either blocked users or bypassed limits |
| Secret enforcement | config.py | Wrong condition = production without secrets, or dev that won't start |
| CSP header | main.py | Too strict = broken pages, too loose = XSS possible |
| Path validation | stories_engine.py | Wrong regex = either blocked stories or traversal possible |
| Cascade delete | models.py | Deleting user data is irreversible |

---

## API Contract Changes

| Endpoint | Change | Breaking? | Migration |
|----------|--------|-----------|-----------|
| POST /api/chat/stream | Was GET, now POST | YES (frontend) | Update chat.html in same phase |
| POST /api/chat/stream | Body: JSON instead of query params | YES (frontend) | Update chat.html in same phase |
| POST /api/user/* | Now requires CSRF token | NO | app.js already sends it |
| POST /api/explore/* | Now rate-limited | NO | Transparent to frontend |
| POST /api/dictionary/* | Now rate-limited | NO | Transparent to frontend |
| POST /api/audio/* | Now validates file size/type | SOFT | May reject edge-case uploads |
| /docs, /openapi.json | Hidden in production | NO | Only affects developers |

---

## External Service Dependencies

| Service | Used By | Failure Mode | Fallback |
|---------|---------|-------------|----------|
| Gemini API | chat, translate, TTS | 429/500 | → Groq → Grok → Browser TTS |
| Groq API | chat, TTS | 429/500 | → Grok → Browser TTS |
| Grok API | chat | 429/500 | → error message |
| Cloudflare Workers AI | image generation | 429/500 | → SDXL → placeholder images |
| SQLite | all data | Disk full / corruption | No fallback — critical |

---

## Migration & Rollback Scripts

### Pre-Phase 4: Database Backup
```bash
# Before running any migration
cp data/wadjet.db data/wadjet.db.backup-$(date +%Y%m%d)
```

### Phase 4 Rollback
```bash
# If migration fails
alembic downgrade -1
# If that also fails
cp data/wadjet.db.backup-YYYYMMDD data/wadjet.db
```

### Phase 1 Quick Rollback (CSRF)
```python
# In main.py, restore the old exempt list:
exempt_urls=["/api/"]  # This re-exempts everything (unsafe but restores function)
```

### Full Phase Rollback
```bash
# Each phase should be a single git commit
# To rollback phase N:
git revert HEAD  # If it's the latest commit
# Or:
git revert <phase-N-commit-hash>
```
