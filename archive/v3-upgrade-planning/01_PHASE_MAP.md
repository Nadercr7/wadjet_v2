# PHASE MAP — Detailed Phase Definitions

> Every phase: Goals → Files Touched → Entry Conditions → Exit Criteria → Effort → Rollback → Commit Template

---

## Phase 0: Credentials & Setup Verification

**Goal**: Verify all external accounts, API keys, and environment variables are correct before any code changes.

**Files Touched**: `.env`, `.env.example` (create), `app/config.py`

**Entry Conditions**: User has access to Google Cloud Console, Resend dashboard, HF account

**Exit Criteria**:
- [ ] All 12 existing env vars verified working
- [ ] `GOOGLE_CLIENT_SECRET` retrieved and added to `.env`
- [ ] `JWT_SECRET` generated (64-char random) and added to `.env`
- [ ] `CSRF_SECRET` generated and added to `.env`
- [ ] `.env.example` created with all variable names (no values)
- [ ] `config.py` Settings model updated with missing fields
- [ ] Google OAuth redirect URI configured in Google Cloud Console
- [ ] Resend sending domain status confirmed
- [ ] Server starts without config errors

**Effort**: S (30-60 min, mostly user actions)

**Rollback**: Delete `.env.example`, revert `config.py` changes

**Commit Template**: `chore(setup): add missing env vars and .env.example`

---

## Phase 1: Security Comprehensive Audit (REQ-7)

**Goal**: Audit the entire codebase for OWASP Top 10 vulnerabilities, fix critical issues, harden for production.

**Files Touched**:
- `app/auth/jwt.py` — Fixed secret handling
- `app/auth/dependencies.py` — Token validation hardening
- `app/api/auth.py` — Rate limiting, input validation
- `app/api/scan.py` — File upload validation
- `app/rate_limit.py` — Review limits
- `app/main.py` — CORS, CSP, security headers
- `app/config.py` — Production vs dev config separation
- `.env` — Secret rotation
- `docker-compose.yml` — Fix `data/:ro` mount issue

**Entry Conditions**: Phase 0 complete (all env vars set)

**Exit Criteria**:
- [ ] JWT secret is fixed (not auto-generated)
- [ ] CSRF protection verified on all state-changing endpoints
- [ ] File upload validation hardened (magic bytes, size limits, allowed types)
- [ ] Rate limiting on auth endpoints (5/min login, 3/min register)
- [ ] Security headers: CSP, X-Frame-Options, X-Content-Type-Options, HSTS
- [ ] Token refresh race condition fixed in `app.js`
- [ ] Docker-compose `data/` mount changed to `:rw`
- [ ] No secrets in logs or error responses
- [ ] Password reset doesn't leak user existence
- [ ] All 12 security issues from audit addressed

**Effort**: S (1 session, ~2-3 hours)

**Rollback**: `git checkout -- app/auth/ app/api/auth.py app/main.py`

**Commit Template**: `security(audit): fix {issue} [OWASP-{category}]`

### Known Issues to Fix

| # | Issue | OWASP | Severity |
|---|-------|-------|----------|
| 1 | JWT_SECRET auto-generated per restart | A07:Security Misconfiguration | Critical |
| 2 | CSRF_SECRET auto-generated per restart | A07:Security Misconfiguration | Critical |
| 3 | Token refresh race condition in app.js | A04:Insecure Design | High |
| 4 | docker-compose `data/:ro` but SQLite writes | A07:Security Misconfiguration | High |
| 5 | No CSP header on responses | A05:Security Misconfiguration | Medium |
| 6 | File upload only checks extension, not magic bytes | A04:Insecure Design | Medium |
| 7 | /api/auth/register no rate limit beyond global | A07:Security Misconfiguration | Medium |
| 8 | Admin email hardcoded in feedback endpoint | A01:Broken Access Control | Low |
| 9 | CLASSIFIER_PATH default points to float32 (not uint8) | A07:Security Misconfiguration | Low |
| 10 | Error responses may include stack traces | A09:Security Logging | Medium |
| 11 | No password complexity requirements | A07:Security Misconfiguration | Low |
| 12 | BASE_URL defaults to render.com | A07:Security Misconfiguration | Low |

---

## Phase 2: Google OAuth + Resend Email (REQ-2)

**Goal**: Add Google one-tap sign-in alongside existing email/password. Add Resend-powered email verification and password reset.

**Files Touched**:
- `app/api/auth.py` — Google OAuth callback, email verification, password reset endpoints
- `app/auth/oauth.py` — NEW: Google OAuth helper (token verification)
- `app/auth/email.py` — NEW: Resend email sender (verification, reset templates)
- `app/db/models.py` — Add `google_id`, `auth_provider`, `email_verified` columns to User
- `app/db/schemas.py` — Update user schemas
- `app/db/crud.py` — `get_user_by_google_id()`, `verify_user_email()`
- `app/config.py` — Add `google_client_secret` field
- `app/templates/partials/nav.html` — Google sign-in button
- `app/templates/dashboard.html` — Connected accounts section
- `app/static/js/app.js` — Google Sign-In client JS
- `alembic/versions/` — New migration for user columns
- `requirements.txt` — Add `google-auth`, `resend`

**Entry Conditions**:
- `GOOGLE_CLIENT_SECRET` in `.env`
- OAuth redirect URI configured in Google Cloud Console
- Resend API key working

**Exit Criteria**:
- [ ] Google Sign-In button on login/register UI
- [ ] Google OAuth callback processes token, creates/links user
- [ ] Existing email/password auth still works
- [ ] Email verification sent on registration
- [ ] Password reset email with secure token
- [ ] User `auth_provider` tracked (email, google, both)
- [ ] Google-only users cannot "reset password"
- [ ] Alembic migration runs cleanly
- [ ] 12+ test cases pass

**Effort**: L (2-3 sessions, ~6-8 hours)

**Rollback**: `alembic downgrade -1`, then `git checkout -- app/api/auth.py app/db/`

**Commit Template**: `feat(auth): {description}`

---

## Phase 3: Scan Pipeline Full Upgrade (REQ-6)

**Goal**: Fix current pipeline issues, add TTS narration to results, improve UX with step-by-step feedback.

**Files Touched**:
- `app/core/hieroglyph_pipeline.py` — Pipeline orchestration fixes
- `app/core/transliteration.py` — Fix transliteration accuracy
- `app/api/scan.py` — Streaming progress SSE, result TTS
- `app/api/audio.py` — Fix TTS architecture (connect tts_service.py)
- `app/core/tts_service.py` — Integrate into scan results
- `app/templates/scan.html` — Step-by-step progress UI, audio playback
- `app/static/js/tts.js` — Fix TTS client to use all 3 tiers
- `app/config.py` — Fix classifier path default to uint8 model

**Entry Conditions**: Phase 2 complete (auth stable)

**Exit Criteria**:
- [ ] Scan pipeline: detect → classify → transliterate → translate works end-to-end
- [ ] TTS reads scan results aloud (Gemini → Groq → Browser fallback)
- [ ] Scan page shows step-by-step progress (SSE or polling)
- [ ] Classifier uses uint8 quantized model by default
- [ ] `/api/tts` endpoint actually calls `tts_service.py` (not bypass)
- [ ] Upload handles HEIC, WebP, large DSLR photos (resize)
- [ ] Results include confidence scores and Gardiner codes
- [ ] 8+ test cases pass

**Effort**: L (2-3 sessions, ~6-8 hours)

**Rollback**: `git checkout -- app/core/ app/api/scan.py app/api/audio.py`

**Commit Template**: `feat(scan): {description}`

---

## Phase 4: Stories Enrichment (REQ-5)

**Goal**: Replace placeholder stories with historically accurate Egyptian mythology. Add smart Cloudflare image generation with golden-age art style.

**Files Touched**:
- `data/stories/*.json` — Rewrite all 5 stories with real history
- `app/core/stories_engine.py` — Enhanced generation + caching
- `app/core/image_service.py` — Improved prompts, art style consistency
- `app/api/stories.py` — New endpoints for enriched content
- `app/templates/stories.html` — Updated listing with previews
- `app/templates/story_reader.html` — Enhanced reading experience
- `app/static/js/tts.js` — Narration integration for stories

**Entry Conditions**: Phase 2 complete, Cloudflare FLUX.1 working

**Exit Criteria**:
- [ ] 5 stories rewritten with real Egyptian history/mythology
- [ ] Each story: 5+ chapters, 10+ glyph annotations, 3+ interactions
- [ ] Cloudflare images generated with consistent "golden papyrus" art style
- [ ] Image caching works (generated once, served from `/static/cache/images/`)
- [ ] TTS narration works for all story chapters
- [ ] Story listing page shows preview images
- [ ] Interactive elements (quizzes, choices) work correctly
- [ ] 6+ test cases pass

**Effort**: L (2-3 sessions, ~6-8 hours)

**Rollback**: `git checkout -- data/stories/ app/core/stories_engine.py`

**Commit Template**: `feat(stories): {description}`

---

## Phase 5: Version Promotion (REQ-1)

**Goal**: Promote v3-beta to production. Replace v2 on HuggingFace Spaces. Archive old code.

**Files Touched**:
- `Dockerfile` — Fix port 7860, optimize layers
- `render.yaml` — Remove or update
- `.env` — Production values
- `app/config.py` — `BASE_URL`, `ENVIRONMENT=production`
- Git remotes, tags, branches

**Entry Conditions**: Phases 1-4 complete and tested

**Exit Criteria**:
- [ ] v2 code archived with `v2.0.0` tag on old repo
- [ ] v3-beta repo has `origin` remote pointing to `github.com/Nadercr7/wadjet_v2`
- [ ] v3-beta repo has `hf` remote pointing to `huggingface.co/spaces/nadercr7/wadjet-v2`
- [ ] Code pushed to both remotes
- [ ] HF Space builds and runs on port 7860
- [ ] All features work on live URL
- [ ] `v3.0.0` tag created
- [ ] Old Wadjet Space README updated to point to new version
- [ ] `BASE_URL` set to HF Space URL

**Effort**: M (1-2 sessions, ~3-4 hours)

**Rollback**: Re-push old code from `v2.0.0` tag

**Commit Template**: `chore(promote): {description}`

---

## Phase 6: New Logo — W-as-Serpent (REQ-3)

**Goal**: Create a world-class serpent-W logo that looks like big brands. Generate all required sizes and formats.

**Files Touched**:
- `app/static/images/logo.svg` — Primary vector logo
- `app/static/images/logo-*.png` — Various sizes (16, 32, 64, 128, 192, 512)
- `app/static/images/favicon.ico` — Multi-size favicon
- `app/static/images/og-wadjet.png` — OpenGraph image (1200×630) — update
- `app/templates/base.html` — Favicon links, logo references
- `app/templates/partials/nav.html` — Logo in navbar
- `app/templates/landing.html` — Hero logo display

**Entry Conditions**: Phase 5 complete. Logo design direction decided.

**Exit Criteria**:
- [ ] SVG logo: W-shaped serpent, clean at 16px and 512px
- [ ] Works on dark (#0A0A0A) and light backgrounds
- [ ] Gold (#D4AF37) primary with ivory (#F5F0E8) variant
- [ ] Favicon set: 16×16, 32×32, apple-touch-icon 180×180
- [ ] OG image updated with new logo
- [ ] Logo visible in nav, landing hero, and dashboard

**Effort**: M (1-2 sessions, iterative design)

**Rollback**: `git checkout -- app/static/images/ app/templates/`

**Commit Template**: `feat(brand): {description}`

---

## Phase 7: Animated Loading Screen (REQ-4)

**Goal**: Build a mesmerizing load animation centered on the W-serpent logo, shown on initial page load and during scan processing.

**Files Touched**:
- `app/static/css/input.css` — Loading animation keyframes + component classes
- `app/templates/base.html` — Loading overlay markup
- `app/static/js/app.js` — Loading state management (Alpine store)
- `app/templates/scan.html` — Scan-specific loading states

**Entry Conditions**: Phase 6 complete (logo exists)

**Exit Criteria**:
- [ ] SVG logo draws stroke path on page load (1-2 sec)
- [ ] Gold particle effect around logo during animation
- [ ] Smooth fade-out when page is ready
- [ ] Scan page uses same animation during processing
- [ ] No layout shift after loading screen dismisses
- [ ] Animation CSS is under 5KB
- [ ] Graceful fallback if JS disabled (loading screen auto-hides via CSS)

**Effort**: M (1-2 sessions, ~3-4 hours)

**Rollback**: Remove loading overlay from `base.html`, revert CSS additions

**Commit Template**: `feat(loading): {description}`

---

## Phase 8: Polish + Additional Fixes (REQ-8)

**Goal**: Clean up technical debt, implement remaining recommendations, final QA pass.

**Files Touched**: Various — depends on remaining items

**Entry Conditions**: Phases 1-7 complete

**Exit Criteria**:
- [ ] Orphaned v2 classifier model file removed
- [ ] `.env.example` complete and up-to-date
- [ ] `CHANGELOG.md` updated for v3.0.0
- [ ] All deprecation warnings resolved
- [ ] Dead code removed (unused imports, commented blocks)
- [ ] Performance audit: no blocking requests, images lazy-loaded
- [ ] Accessibility quick check (color contrast, alt text, ARIA)
- [ ] Final smoke test on live URL
- [ ] All tests green

**Effort**: S (1 session, ~2 hours)

**Rollback**: Selective `git checkout` per file

**Commit Template**: `fix: {description}` or `chore: {description}`
