# QUALITY GATES — Definition of Done + QA Checklists

> Every phase must pass its quality gate before moving to the next.

---

## Global Quality Rules

1. **No regressions**: All existing tests must pass after every phase
2. **No secrets in code**: No API keys, tokens, or passwords in committed files
3. **No force pushes**: Never use `--force` on shared branches
4. **Commit convention**: `type(scope): description` — types: feat, fix, security, chore
5. **No dead code**: Remove commented-out code blocks when no longer needed
6. **CSS cache busting**: Bump `?v=N` in `base.html` after CSS changes

---

## Phase-Level Quality Gates

### Phase 0: Credentials & Setup ✅ Gate

- [ ] All 12 existing env vars verified (Section 1 of checklist)
- [ ] 5 missing env vars added to `.env`
- [ ] `.env.example` created with all variable names
- [ ] `app/config.py` has `google_client_secret` field
- [ ] Server starts without errors: `uvicorn app.main:app --reload`
- [ ] `pytest tests/ -v` — all existing tests pass

### Phase 1: Security Audit ✅ Gate

- [ ] All 12 known security issues resolved
- [ ] Security headers present: CSP, X-Frame-Options, X-Content-Type-Options
- [ ] File upload validates magic bytes (not just extension)
- [ ] Error responses never include stack traces
- [ ] Rate limits working on auth endpoints
- [ ] No timing oracle on login (constant-time response)
- [ ] `pytest tests/test_security.py -v` — all pass
- [ ] `pytest tests/ -v` — all existing tests still pass
- [ ] Manual test: upload a `.exe` renamed to `.jpg` → rejected

### Phase 2: Google OAuth + Resend ✅ Gate

- [ ] Google Sign-In button renders on login UI
- [ ] New user can sign in with Google → account created
- [ ] Existing user can link Google account
- [ ] Email verification email sends (check inbox or Resend dashboard)
- [ ] Password reset email sends  
- [ ] Google-only user cannot trigger password reset
- [ ] Existing email/password login still works (no regression)
- [ ] Alembic migration runs cleanly (`alembic upgrade head`)
- [ ] Alembic migration rolls back cleanly (`alembic downgrade -1`)
- [ ] `pytest tests/test_auth.py -v` — all 14+ tests pass
- [ ] `pytest tests/ -v` — all tests pass

### Phase 3: Scan Pipeline ✅ Gate

- [ ] Scan end-to-end: upload → detect → classify → translate → results
- [ ] TTS reads scan results aloud (click Listen button)
- [ ] `/api/tts` calls `tts_service.py` (not direct Groq)
- [ ] Large image (4000×3000) auto-resized, processed
- [ ] WebP image accepted and processed
- [ ] Non-image upload rejected with clear message
- [ ] Progress feedback visible during scan (step-by-step)
- [ ] Config uses uint8 classifier model
- [ ] `pytest tests/test_scan.py tests/test_audio.py -v` — all pass
- [ ] `pytest tests/ -v` — all pass

### Phase 4: Stories ✅ Gate

- [ ] All 5 stories rewritten with historical sources cited
- [ ] Each story has 5+ chapters
- [ ] Each chapter has 2+ glyph annotations
- [ ] Each chapter has 1 interactive element (quiz/choice)
- [ ] Story images generate from Cloudflare FLUX.1
- [ ] Images cache in `/static/cache/images/stories/`
- [ ] Narration plays on chapter "Listen" button
- [ ] Story progress saves to database (logged-in users)
- [ ] `pytest tests/test_stories.py -v` — all pass
- [ ] `pytest tests/ -v` — all pass

### Phase 5: Version Promotion ✅ Gate

- [ ] v3-beta has `origin` and `hf` git remotes
- [ ] Code pushed to both remotes successfully
- [ ] HF Space build completes without errors
- [ ] All routes accessible on live URL
- [ ] Auth flow works end-to-end on live
- [ ] Scan works on live
- [ ] Stories load on live
- [ ] Chat responds on live
- [ ] `v3.0.0` tag created and pushed
- [ ] `CHANGELOG.md` updated

### Phase 6: Logo ✅ Gate

- [ ] SVG logo renders at 16×16, 32×32, 512×512
- [ ] Logo works on dark (#0A0A0A) background
- [ ] Favicon shows in browser tab
- [ ] Logo appears in navbar
- [ ] Logo appears on landing hero
- [ ] OG image updated with new logo

### Phase 7: Loading Animation ✅ Gate

- [ ] Loading overlay appears on page load
- [ ] SVG stroke animation plays smoothly
- [ ] Loading dismisses when page is ready (< 3 seconds)
- [ ] No layout shift (CLS = 0) after loading
- [ ] `<noscript>` fallback hides loading without JS
- [ ] Scan page has step-specific loading states
- [ ] Loading animation CSS < 5KB

### Phase 8: Polish ✅ Gate

- [ ] `CHANGELOG.md` has complete v3.0.0 release notes
- [ ] `.env.example` matches all actual env vars
- [ ] No dead code (unused imports, commented blocks)
- [ ] All images have `alt` attributes
- [ ] All interactive elements keyboard-accessible
- [ ] No console errors in browser
- [ ] All routes return 200 (smoke test)
- [ ] `pytest tests/ -v` — 100% pass
- [ ] Final deployment to HF Space works

---

## Pre-Launch Checklist (Before Going Public)

### Performance
- [ ] No render-blocking scripts (defer/async)
- [ ] Images lazy-loaded below fold
- [ ] CSS purged (no unused styles)
- [ ] GZIP/Brotli compression enabled (HF handles this)
- [ ] Static assets have cache-control headers

### Security
- [ ] All secrets in environment variables, not code
- [ ] `.env` in `.gitignore`
- [ ] CSP restricts inline scripts (if feasible with Alpine/HTMX)
- [ ] HTTPS enforced (HF gives this automatically)
- [ ] Rate limiting on all public API endpoints
- [ ] No OWASP Top 10 vulnerabilities

### SEO (Quick Check)
- [ ] `<title>` tag on every page
- [ ] `<meta name="description">` on every page
- [ ] OG tags on every page (title, description, image)
- [ ] `robots.txt` accessible
- [ ] `sitemap.xml` accessible
- [ ] Canonical URLs set

### Accessibility
- [ ] Color contrast: gold on dark ≥ 4.5:1 (AA) ✓ Already passes
- [ ] All images have `alt` text
- [ ] Form inputs have `<label>` elements
- [ ] Focus indicators visible on all interactive elements
- [ ] Skip navigation link exists
- [ ] Page language set (`<html lang="en">`)

---

## Monitoring After Launch

### What to Watch
- HF Space build logs: check for errors on rebuilds
- Resend dashboard: email delivery rates
- Browser console: JS errors (check periodically)
- User feedback: via the feedback widget

### Known Limitations to Document
- SQLite: data lost on Space rebuild (if not using PostgreSQL)
- Cold start: 15-30s if Space was sleeping
- Image generation: first request takes 2-5s (no pre-cache)
- ONNX models: first inference slower (warm-up)
