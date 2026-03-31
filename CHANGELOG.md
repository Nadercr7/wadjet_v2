# Changelog

## v3.1.1 (2026-03-31)

Archive externalization. All project history moved outside the production repo.

### 📦 Archive Organization
- Moved all archive content (174 tracked + 100 local files) out of v3-beta repo
- Renamed external `Wadjet/` → `Wadjet-v2/` for clear naming
- Copied v3-specific planning docs to `Wadjet-v2/archive/` (v3-beta-planning, v3-upgrade-planning, v3-planning-snapshot)
- Deleted empty `Wadjet-v2-archive/` and `_wadjet_temp_backup/` folders
- Updated `.gitignore`, `.dockerignore`, `CLAUDE.md` to remove archive references
- Updated `JOURNEY.md` with v3 upgrade chapter and archive chapter
- External folder structure: `Wadjet-v2/` (full v2 codebase + all history) + `Wadjet-v3-beta/` (production only)

## v3.1.0 (2026-03-31)

Post-launch polish. Final quality pass: cleanup, performance, accessibility, brand consistency.

### 🎨 Brand & Logo
- AI-generated Wadjet cobra-W logo (PNG) replaces old SVG placeholder
- Full favicon set: 16/32/180/192/512px + dark/ivory variants
- OG images regenerated with new logo
- Replaced all 18 old `𓂀` hieroglyph brand marks with logo.png across 11 templates

### ✨ Animated Loading Screen
- Full-page loading overlay: logo scale-in (ease-out-expo 600ms) + gold shimmer ring + "WADJET" text fade-up + progress bar
- Smart dismiss: min 1.8s display, `is-leaving` transition (opacity + scale 300ms), 5s absolute fallback
- Branded section loaders on all content pages (scan, explore, dashboard, stories, dictionary, lessons)
- Scan page: `scan-step` CSS classes (is-active/is-pending/is-done) for 4-step progress
- `prefers-reduced-motion: reduce` support — all animations skip to instant
- `<noscript>` hides loader immediately

### 🧹 Cleanup
- Removed 8 orphaned v2 model files: TF.js descriptor (`model.json`), 5 weight shards (`.bin`), 2 unused ONNX variants
- Cleaned `.dockerignore` of now-deleted file references
- Added `ADMIN_EMAIL` to `.env.example`

### ♿ Accessibility (Verified)
- All images have alt text (meaningful or decorative `alt=""`)
- All icon-only buttons have `aria-label`
- All below-fold images use `loading="lazy"`
- WCAG AA color contrast (gold #D4AF37 on dark #0A0A0A = 7.5:1)
- Skip-to-content link for keyboard navigation

### ⚡ Performance (Verified)
- TailwindCSS v4 purge active — only used utilities in compiled CSS
- No render-blocking scripts (vendor scripts `defer`, app scripts sync at end-of-body)
- Zero `console.log` calls in production JS
- Zero `TODO`/`FIXME`/`HACK` comments in codebase

---

## v3.0.0 (2026-07-12)

Production release. Promoted from v3.0.0-beta with additional features and deployment fixes.

### 🔐 Google OAuth & Email Verification
- Google Sign-In (one-tap + redirect flow) via `google-auth` library
- Resend-powered email verification with branded HTML templates
- OAuth account linking for existing email users
- Alembic migration for OAuth + email fields

### 🔬 Scan Pipeline Upgrade
- Sliding-window detector replaces single-shot connected-components
- Grok `grok-4-latest` ensemble for top-3 AI classification
- Groq Scout 17B 16E as secondary vision model
- Cloudflare Workers AI as tertiary vision model
- Multi-provider majority-vote with confidence weighting
- Pipeline returns top-5 results across all providers

### 📖 Stories Enrichment
- 8 new interactive stories (13 total): The Eye of Horus, The Book of Thoth, The Journey of Ra, The Weighing of the Heart, The Tears of Isis, The Great Pyramid, Akhenaten's Revolution, Cleopatra's Last Stand
- 88 new hieroglyphs taught across new stories
- Golden papyrus art style for AI-generated illustrations
- 4 interaction types: glyph_discovery, choose_glyph, arrange_sentence, write_word

### 🚀 Deployment
- Dockerfile updated for HuggingFace Space (port 7860)
- Production config with enforced secrets validation
- Docker Compose updated for local development parity

---

## v3.0.0-beta (2026-03-28)

Major upgrade from v2 → v3 beta. 11 phases of development across security, offline support, authentication, UX, performance, internationalization, SEO, storytelling, SaaS features, and finalization.

### 🔒 Security (Phase 1)
- Magic byte validation for image uploads (JPEG, PNG, WebP — not just Content-Type)
- CSRF protection on all POST endpoints (`starlette-csrf` middleware)
- Rate limiting on all API endpoints (`slowapi` — 10–60/min per route)
- Quiz answers no longer exposed in client-side JavaScript (HMAC-signed server verification)
- Error messages sanitized — generic to user, full traceback in server logs
- Security response headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`

### 🌐 Offline & CDN (Phase 2)
- All 6 CDN scripts self-hosted in `/static/vendor/` (Alpine.js, HTMX, GSAP, ScrollTrigger, Lenis, Atropos)
- Service worker completely rewritten — full offline support with versioned static cache
- ML models use cache-first strategy with version-independent `wadjet-models` cache
- `tts.js` added to SW pre-cache

### 🔑 Database & Auth (Phase 3)
- SQLite database via SQLAlchemy async (PostgreSQL-ready)
- JWT-based authentication (HS256, 30-min access + 7-day refresh tokens)
- User registration with bcrypt password hashing (12 rounds)
- 5 ORM models: User, ScanHistory, StoryProgress, Favorite, RefreshToken
- Login/signup modals in navigation with Alpine.js state management

### 🎨 UX & Accessibility (Phase 4)
- `/write` page added to navigation
- Was Scepter corrected from R11 to S42/𓌂
- WCAG AA contrast compliance (`text-dim` #5A5A5A → #7E7E7E, 4.7:1 ratio)
- All form inputs have proper labels and aria attributes
- Confidence percentage shown in scan results with color-coded indicators
- Glyph of the Day expanded from 7 to 32 entries across all Gardiner categories
- Favicon path and SVG MIME type fixed
- Noto Sans Egyptian Hieroglyphs `@font-face` properly loaded
- **Gemini 2.5 Flash TTS** — 30 voices, Arabic support, style-controllable director's notes
- Smart TTS fallback chain: Gemini → Groq Orpheus → Browser SpeechSynthesis
- Floating narration button (🔊) on content pages with server-first TTS
- WAV audio disk caching for instant replay

### ⚡ Performance (Phase 5)
- Lazy loading for below-fold images
- Explore page: infinite scroll pagination (24 cards per page via Alpine Intersect)
- Search debounce (300ms) on explore/dictionary
- Google Fonts preloaded
- Async cache I/O for enrichment data

### 🌍 Arabic & i18n (Phase 6)
- Full Arabic language support (Modern Standard Arabic) with persistent language toggle
- RTL layout via `dir="rtl"` + Tailwind CSS `rtl:` variants
- Cairo font for Arabic text rendering
- 300+ bilingual UI strings across 18 sections (`en.json` + `ar.json`)
- Arabic landmark names, glyph descriptions, and story content
- Write page: Arabic examples and placeholder text
- Mtime-based i18n cache (hot-reload without server restart)
- Chat starters show in Arabic when language is Arabic
- STT language follows page language setting

### 📊 SEO (Phase 7)
- Open Graph + Twitter Card meta tags on all pages
- JSON-LD structured data (WebApplication schema)
- Dynamic `robots.txt` + `sitemap.xml` (14 URLs including lesson pages)
- Canonical URLs with hreflang alternates (en, ar, x-default)
- Per-page SEO overrides (title, description, og:image)
- GPTBot allowed on content pages (only `/api/` blocked)

### 📖 Stories of the Nile (Phase 8 — NEW)
- 5 interactive Egyptian mythology stories replacing Quiz in navigation
  - The Osiris Myth (4 chapters, beginner)
  - Journey of Ra (3 chapters, beginner)
  - Creation from Nun (2 chapters, beginner)
  - The Eye of Ra (2 chapters, intermediate)
  - The Contendings of Horus & Set (3 chapters, intermediate)
- 3 learning interaction types: glyph discovery, choose glyph, write word
- All answers server-verified via HMAC (never exposed to client)
- **Cloudflare FLUX.1** AI-generated story illustrations with SDXL fallback
- Ken Burns cinematic animations on story images
- Narrative TTS with Gemini voice (Aoede preset)
- Progress tracking per story (localStorage for guests, server-synced for users)
- Full bilingual content (English + Arabic)

### 🏗️ SaaS Dashboard (Phase 9 — NEW)
- User dashboard with aggregate stats (total scans, stories completed, favorites)
- Recent scan history display with clickable entries
- Story progress tracking with visual progress bars
- Favorites system for landmarks and glyphs (heart toggle)
- Account settings page (profile edit, language preference, password change)
- Free tier with soft usage limits and sign-in prompts
- `/quiz` route redirected (301) to `/stories`

### 🏷️ Finalization (Phase 10)
- Beta badge next to logo in navigation
- Version bumped to `3.0.0-beta` across all config files
- Service worker cache version: `wadjet-v30-beta`
- Comprehensive changelog documenting all v2 → v3 changes

---

## v2.0.0 (Original)

The baseline version before v3 development began. Features:
- Hieroglyph scanning with ONNX + AI ensemble
- Gardiner dictionary (1,000+ signs)
- Write in hieroglyphs
- 260+ Egyptian landmarks explorer
- Thoth AI chatbot (Gemini-powered)
- Quiz feature
- Black & gold Egyptian theme
