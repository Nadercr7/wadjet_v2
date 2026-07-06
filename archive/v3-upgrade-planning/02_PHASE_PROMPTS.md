# PHASE PROMPTS — Self-Contained Execution Prompts

> Paste each prompt at the start of its session to get full context.  
> Every prompt is self-contained: no cross-referencing needed.

---

## Phase 0 Prompt: Credentials & Setup

```
CONTEXT: I'm working on Wadjet v3-beta (D:\Personal attachements\Projects\Wadjet-v3-beta).
Egyptian heritage web app: FastAPI + Jinja2 + Alpine.js + HTMX + TailwindCSS v4 + ONNX Runtime.
Read planning/comprehensive-upgrade/09_CREDENTIALS_AND_SETUP_CHECKLIST.md for the full checklist.

TASK — Phase 0: Credentials & Setup Verification
1. Read the current .env file to verify all 12 existing env vars
2. Add missing env vars: GOOGLE_CLIENT_SECRET (user provides), JWT_SECRET, CSRF_SECRET
3. Add google_client_secret field to app/config.py Settings model
4. Create .env.example with all variable names (no secret values)
5. Verify server starts without config errors

RULES:
- Never log or display secret values
- .env.example must have descriptive comments
- Generate JWT_SECRET and CSRF_SECRET with: secrets.token_hex(32)
- Keep config.py consistent with existing code style

DONE WHEN: All env vars present, server starts, .env.example exists.
COMMIT: chore(setup): add missing env vars and .env.example
```

---

## Phase 1 Prompt: Security Audit

```
CONTEXT: I'm working on Wadjet v3-beta (D:\Personal attachements\Projects\Wadjet-v3-beta).
Egyptian heritage web app: FastAPI + Jinja2 + Alpine.js + HTMX + TailwindCSS v4 + ONNX Runtime.
Read planning/comprehensive-upgrade/01_PHASE_MAP.md Phase 1 for the 12 issues list.

TASK — Phase 1: Security Comprehensive Audit

KNOWN ISSUES (fix all 12):
1. JWT_SECRET auto-generated per restart → already set in Phase 0 → verify
2. CSRF_SECRET auto-generated per restart → already set in Phase 0 → verify
3. Token refresh race condition in app/static/js/app.js → add mutex/lock
4. docker-compose.yml data/:ro mount → change to :rw 
5. No CSP header → add in app/main.py middleware
6. File upload only checks extension → add magic bytes check in scan.py
7. /api/auth/register rate limit → already has 5/min → verify adequate
8. Admin email hardcoded in feedback → move to config.py admin_email
9. CLASSIFIER_PATH default points to float32 → fix to uint8 (hieroglyph_classifier_uint8.onnx if exists, else keep)
10. Error responses may include stack traces → catch in exception handler
11. No password complexity requirements → add minimum 8 chars in RegisterRequest schema
12. BASE_URL defaults to render.com → update to HF Space URL

ADDITIONAL CHECKS:
- Review all endpoints for auth bypass
- Check CORS settings in main.py
- Verify no secrets in logs
- Check for SQL injection (parameterized queries)
- Verify CSRF on all state-changing endpoints

APPROACH:
- Fix issues in priority order (Critical → High → Medium → Low)
- Run existing tests after each fix
- Don't break existing functionality

DONE WHEN: All 12 issues resolved, tests pass, no OWASP Top 10 gaps.
COMMIT EACH FIX: security(audit): fix {issue} [OWASP-{category}]
```

---

## Phase 2 Prompt: Google OAuth + Resend

```
CONTEXT: I'm working on Wadjet v3-beta (D:\Personal attachements\Projects\Wadjet-v3-beta).
Egyptian heritage web app: FastAPI + Jinja2 + Alpine.js + HTMX + TailwindCSS v4 + ONNX Runtime.
Read planning/comprehensive-upgrade/04_AUTH_PLAN.md for the full integration plan.

CURRENT AUTH SYSTEM:
- app/api/auth.py: register, login, refresh, logout (email/password)
- app/auth/jwt.py: create_access_token, create_refresh_token, decode_token
- app/auth/password.py: hash_password, verify_password (bcrypt)
- app/auth/dependencies.py: get_current_user, require_auth
- app/db/models.py User: id, email, password_hash, display_name, preferred_lang, tier
- Tokens: AccessToken (JWT, 30min), RefreshToken (7 days, stored in DB)
- Cookies: wadjet_refresh (HttpOnly), wadjet_session (non-HttpOnly)

TASK — Phase 2: Add Google OAuth + Resend Email
1. Create Alembic migration: add google_id, auth_provider, email_verified to User
2. Create app/auth/oauth.py: verify Google ID token server-side
3. Add Google OAuth callback endpoint to auth.py: POST /api/auth/google
4. Create app/auth/email.py: send verification & password reset via Resend
5. Add email verification endpoint: POST /api/auth/verify-email
6. Add password reset flow: POST /api/auth/forgot-password, POST /api/auth/reset-password
7. Update nav.html: add Google Sign-In button
8. Update dashboard.html: show connected accounts
9. Update app.js: handle Google client library + credential response
10. Add requirements: google-auth, resend

KEY CONSTRAINTS:
- google_client_secret must be read from config.py Settings
- Google-only users have password_hash="" and auth_provider="google"
- Google-only users cannot use password reset
- Existing email/password users unaffected
- Email verification is OPTIONAL (not blocking login) for now
- Resend from address: use verified domain or onboarding@resend.dev for dev
- Google redirect URI: POST callback (not redirect), uses Google's JS library

SECURITY:
- Verify Google token with google.oauth2.id_token.verify_oauth2_token()
- Use nonce for CSRF protection on Google button
- Rate limit OAuth endpoint (10/minute)
- Never store Google access tokens long-term

DONE WHEN: Google sign-in works, email verification sends, password reset sends, existing auth unbroken.
COMMIT: feat(auth): add Google OAuth sign-in
COMMIT: feat(auth): add Resend email verification and password reset
```

---

## Phase 3 Prompt: Scan Pipeline Upgrade

```
CONTEXT: I'm working on Wadjet v3-beta (D:\Personal attachements\Projects\Wadjet-v3-beta).
Egyptian heritage web app with hieroglyph scanning pipeline.
Read planning/comprehensive-upgrade/06_SCAN_PIPELINE_AUDIT.md for current state audit.

CURRENT PIPELINE:
1. app/api/scan.py: receives uploaded image, calls pipeline
2. app/core/hieroglyph_pipeline.py: HieroglyphPipeline.process_image()
   - Loads YOLOv8s ONNX detector, MobileNetV3 ONNX classifier
   - Detects → crops → classifies → transliterates → translates
3. app/core/transliteration.py: TransliterationEngine (Gardiner → transliteration)
4. app/core/rag_translator.py: RAGTranslator (FAISS + Gemini embeddings → AI translation)
5. app/core/tts_service.py: TTSService (Gemini → Groq → Browser) — NOT connected to scan
6. app/api/audio.py: /api/tts endpoint — bypasses tts_service.py, goes straight to Groq

TASK — Phase 3: Fix Pipeline + Add TTS to Scan Results
1. Fix TTS architecture: /api/tts should call tts_service.py (use all 3 tiers)
2. Fix classifier path config default: use uint8 model if it exists
3. Add scan result TTS: after translation, offer "Listen" button → calls /api/tts
4. Improve scan UX: show step-by-step progress (detect → classify → translate)
5. Handle large images: auto-resize before ONNX inference (max 1024px)
6. Handle more formats: HEIC, WebP conversion before processing
7. Add confidence scores to scan results UI
8. Improve error handling: specific messages for each failure mode

APPROACH:
- Fix TTS service first (standalone improvement)
- Then fix scan pipeline issues
- Then add TTS to scan results
- Test end-to-end with real images

DONE WHEN: Scan works end-to-end, TTS reads results, progress shows per step.
COMMIT: feat(scan): fix TTS service architecture
COMMIT: feat(scan): add step-by-step progress and result narration
```

---

## Phase 4 Prompt: Stories Enrichment

```
CONTEXT: I'm working on Wadjet v3-beta (D:\Personal attachements\Projects\Wadjet-v3-beta).
Egyptian heritage web app with 5 interactive mythology stories.
Read planning/comprehensive-upgrade/07_STORIES_ENRICHMENT_PLAN.md for story structure.

CURRENT STORIES (data/stories/):
1. the_eye_of_horus.json — Myth of Horus losing his eye battling Set
2. the_book_of_thoth.json — Forbidden knowledge of Thoth's magical book
3. the_journey_of_ra.json — Ra's nightly journey through the Duat
4. the_weighing_of_the_heart.json — Osiris judges the dead
5. the_tears_of_isis.json — Isis's tears creating the Nile floods

TASK — Phase 4: Rewrite Stories with Real History + Smart Images
1. Rewrite all 5 stories with historically accurate Egyptian mythology
   - Source: Pyramid Texts, Book of the Dead, Papyrus of Ani, Temple inscriptions
   - Each story: 5+ chapters, real Egyptian names, timeline context
2. Add glyph annotations: 10+ hieroglyphs per story with Gardiner codes
3. Add interactive elements: quiz questions, choices that affect narrative
4. Improve image generation prompts for Cloudflare FLUX.1:
   - Consistent "golden papyrus" art style across all stories
   - Include specific Egyptian elements: ankh, was-scepter, djed pillar
   - Cache all generated images in /static/cache/images/
5. Add TTS narration per chapter via existing tts_service
6. Optionally add 3 new story concepts (research during phase):
   - The Building of the Great Pyramid (Khufu era)
   - Akhenaten's Religious Revolution
   - Cleopatra's Last Stand

IMAGE PROMPT TEMPLATE:
"Ancient Egyptian papyrus illustration of {scene}, golden and amber tones, 
hieroglyphic borders, Art Deco meets ancient Egypt, detailed ink work on 
aged papyrus background, museum quality artifact illustration"

DONE WHEN: 5 stories rewritten, images generate, narration plays, interactions work.
COMMIT: feat(stories): rewrite {story} with historical accuracy
COMMIT: feat(stories): add smart image generation pipeline
```

---

## Phase 5 Prompt: Version Promotion

```
CONTEXT: I'm working on Wadjet v3-beta (D:\Personal attachements\Projects\Wadjet-v3-beta).
Read planning/comprehensive-upgrade/03_VERSION_PROMOTION_PLAN.md for full procedure.

CURRENT STATE:
- v3-beta: branch master, NO git remotes, tag v3.0.0-beta
- Old Wadjet (D:\Personal attachements\Projects\Wadjet): branch clean-main
  - origin: github.com/Nadercr7/wadjet_v2  
  - hf: huggingface.co/spaces/nadercr7/wadjet-v2
- HF Space: Docker SDK, port 7860, currently sleeping

TASK — Phase 5: Promote v3 to Production
1. On OLD Wadjet repo: tag current state as v2.0.0-archive
2. On v3-beta: add git remotes
   - origin: git@github.com:Nadercr7/wadjet_v2.git (or https)
   - hf: https://huggingface.co/spaces/nadercr7/wadjet-v2
3. Fix Dockerfile: EXPOSE 7860, CMD with --port 7860
4. Update config.py BASE_URL default to HF Space URL
5. Set ENVIRONMENT=production in HF Space env vars
6. Set all secrets in HF Space Settings → Variables
7. Push to both remotes
8. Verify HF Space builds and starts
9. Tag as v3.0.0
10. Update CHANGELOG.md

ENV VARS TO SET ON HF:
- ENVIRONMENT=production
- JWT_SECRET=<generated>
- CSRF_SECRET=<generated>
- GEMINI_API_KEYS=<all 17>
- GROK_API_KEYS=<all 8>
- GROQ_API_KEYS=<all 8>
- CLOUDFLARE_ACCOUNT_ID=<value>
- CLOUDFLARE_API_TOKEN=<value>
- GOOGLE_CLIENT_ID=<value>
- GOOGLE_CLIENT_SECRET=<value>
- RESEND_API_KEY=<value>
- HF_TOKEN=<value>

DONE WHEN: HF Space runs v3, all features accessible, v3.0.0 tagged.
COMMIT: chore(promote): prepare v3 for production deployment
```

---

## Phase 6 Prompt: New Logo

```
CONTEXT: Wadjet — Egyptian heritage web app. Design system: Black (#0A0A0A) + Gold (#D4AF37).
Read planning/comprehensive-upgrade/05_DESIGN_SYSTEM.md for full visual spec.

TASK — Phase 6: Create W-as-Serpent Logo
The logo should be the letter W shaped like (or incorporating) an Egyptian cobra/serpent.
Think Nike swoosh simplicity, Chanel interlocking elegance, Apple minimalism.

REQUIREMENTS:
- SVG format, clean paths, no raster embedded
- Works at 16×16 (favicon) through 512×512 (splash)
- Primary: gold (#D4AF37) on dark (#0A0A0A)
- Secondary: ivory (#F5F0E8) on dark
- Tertiary: dark on gold (reversed)
- The W should naturally read as a letter W
- The serpent should be subtle, not cartoonish
- Egyptian uraeus (rearing cobra) is the reference

DELIVERABLES:
- app/static/images/logo.svg — Primary vector
- app/static/images/logo-dark.svg — For light backgrounds
- Favicon set: 16, 32, 180 (apple-touch-icon), 192, 512
- app/static/images/og-wadjet.png — Updated 1200×630 OG image
- Update base.html favicon references
- Update nav.html with logo
- Update landing.html hero with logo

DONE WHEN: Logo renders crisp at all sizes, integrated into all templates.
COMMIT: feat(brand): add W-serpent logo and favicon set
```

---

## Phase 7 Prompt: Animated Loading Screen

```
CONTEXT: Wadjet — Black + Gold design. Logo SVG exists (Phase 6).
Read planning/comprehensive-upgrade/05_DESIGN_SYSTEM.md §Loading Animation.

TASK — Phase 7: Build Animated Loading Screen
1. Add loading overlay to base.html (above all content)
2. SVG stroke-dasharray animation: logo draws itself (1.5s)
3. Gold particle shimmer around logo during draw
4. Text "Wadjet" fades in below logo after draw (0.5s)
5. Overlay fade-out + scale-down when page ready (0.3s)
6. CSS only (no GSAP dependency for loading screen)
7. Graceful degradation: if JS disabled, `<noscript>` hides overlay immediately

ALSO:
- Scan page: reuse animation during scan processing
- Scan page: add hieroglyph-specific loading states
  - "Detecting hieroglyphs..." → "Classifying symbols..." → "Translating..."

CSS APPROACH:
- @keyframes in input.css under @layer components
- .loading-overlay, .loading-logo, .loading-text classes
- Alpine.js x-data controls show/hide state
- No layout shift: overlay is position:fixed

DONE WHEN: Loading shows on every page load, dismisses cleanly, no CLS.
COMMIT: feat(loading): add SVG logo loading animation
COMMIT: feat(loading): add scan-specific loading states
```

---

## Phase 8 Prompt: Polish & Final Fixes

```
CONTEXT: Wadjet v3 is live on HF Space. All major features complete.
Read planning/comprehensive-upgrade/10_QUALITY_GATES.md for the QA checklist.

TASK — Phase 8: Final Polish
1. Update CHANGELOG.md with full v3.0.0 release notes
2. Remove orphaned v2 classifier model file if present
3. Clean dead code: unused imports, commented blocks
4. Performance check:
   - Images: lazy-load below fold, WebP where possible
   - CSS: verify TailwindCSS purge is working
   - JS: no render-blocking scripts
5. Accessibility quick check:
   - All images have alt text
   - Color contrast meets WCAG AA (gold on dark = 7.5:1 ✓)
   - Interactive elements keyboard-accessible
   - ARIA labels on icon buttons
6. Final smoke test:
   - Every route loads
   - Auth flow works (register, login, Google, logout)
   - Scan pipeline works end-to-end
   - Stories load with images and narration
   - Dashboard shows user data
   - Chat works (Thoth responds)
7. Resolve any remaining deprecation warnings
8. Verify all env vars documented in .env.example

DONE WHEN: All routes work, tests pass, no console errors, CHANGELOG updated.
COMMIT: chore: v3.0.0 final polish
TAG: v3.1.0 (if post-launch fixes)
```
