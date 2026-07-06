# Wadjet v3 Beta — Specification

## 1. Product Vision

Wadjet v3 transforms from a technical demo into a **SaaS product** for Egyptian heritage education. Users create accounts, track learning progress, scan hieroglyphs, explore landmarks, and engage with interactive stories — all with full Arabic support and offline capability.

## 2. User Personas

### 2.1 Tourist (Free Tier)
- Visits Egyptian sites, wants to understand what they see
- Scans hieroglyphs, reads landmark info, uses Thoth chat
- Needs: offline mode, Arabic UI, quick results
- Limits: 10 scans/day, 5 chat messages/day, 3 stories

### 2.2 Student (Pro Tier — future)
- Studies Egyptology, ancient languages, or history
- Uses dictionary extensively, writes hieroglyphs, completes all stories
- Needs: unlimited access, progress tracking, export capabilities
- Limits: unlimited scans, full story library, API access

### 2.3 Museum/Institution (Enterprise — future)
- White-labels Wadjet for in-museum kiosks or educational apps
- Needs: custom branding, bulk API, content management
- Limits: SLA, dedicated support, custom models

## 3. Feature Specification

### 3.1 Authentication System (NEW)
- **Sign up**: Email + password (bcrypt hashed)
- **Login**: Returns JWT access token (30min) + refresh token (7 days, httpOnly cookie)
- **Guest mode**: Full functionality but no progress saving
- **Profile**: Name, email, preferred language (en/ar), avatar (Gravatar)
- **DB models**: `users`, `scan_history`, `story_progress`, `user_preferences`

### 3.2 Scan (Enhanced)
- **Existing**: Upload image → detect + classify hieroglyphs → translate
- **Fix C2**: Magic byte validation (JPEG `FF D8 FF`, PNG `89 50 4E 47`, WebP `52 49 46 46`)
- **Fix C5**: Generic error messages, detailed server logs
- **Fix M17**: Show confidence percentage per glyph
- **New**: Save scan to user history (if logged in)

### 3.3 Dictionary (Enhanced)
- **Existing**: Browse 1,023 Gardiner signs
- **Fix M2**: Show Arabic names (`name_ar` from gardiner_data)
- **Fix M10**: Add `<label>` elements to search
- **New**: Mark signs as "learned" (saved to user profile)

### 3.4 Write (Enhanced)
- **Existing**: Type text → generate hieroglyphs
- **Fix H1**: Add to navigation (desktop + mobile)
- **Fix M3**: Add Arabic examples alongside English
- **New**: Export as image (html2canvas), save to history

### 3.5 Explore (Enhanced)
- **Existing**: Browse 260 landmarks
- **Fix M2**: Show Arabic landmark names
- **Fix M9**: Paginate — 20 cards initially, infinite scroll via HTMX
- **Fix M10**: Label on search input
- **New**: Favorite landmarks (saved to user profile)

### 3.6 Thoth Chat (Enhanced)
- **Fix C4**: Language-aware TTS (`lang` from user preference or page lang)
- **Fix H2**: Server TTS when online, browser TTS fallback offline
- **TTS Upgrade**: Gemini 2.5 Flash TTS as primary (30 voices, Arabic support, style-controllable)
- **Thoth Voice**: Deep, authoritative voice using Gemini TTS `Orus` (Firm) voice with director's notes: *"Ancient Egyptian deity narrating with gravitas and wisdom"*
- **Fallback chain**: Gemini TTS → Groq Orpheus → Browser SpeechSynthesis
- **New**: Chat history saved per user session

### 3.7 Stories of the Nile (REPLACES Quiz)
- **13 Egyptian stories** (all public domain, see plan Phase 8)
- **4 interaction types**: Glyph Discovery, Choose the Glyph, Write the Word, Story Decision
- **AI-Generated Illustrations**: Each story chapter gets AI-generated scene images via Cloudflare FLUX.1 (free)
- **Narrative Voice**: Full audio narration per chapter using Gemini TTS with `Aoede` (Breezy) voice for myths
- **Cinematic animations**: Ken Burns effect on chapter images (zoom + pan) for a video-like experience
- **Progress tracking**: chapters completed, glyphs learned, score
- **Offline**: story content + generated images cached in SW
- **Design**: full-page reading mode, gold glyph highlights, smooth transitions, ambient narration

### 3.8 Arabic i18n (NEW)
- **Language toggle** in nav (🌐 icon)
- **RTL layout** via Tailwind `rtl:` prefix
- **Cairo font** from Google Fonts (self-hosted)
- **Translation files**: `i18n/en.json` + `i18n/ar.json`
- **Jinja2 macro**: `{{ t('key') }}` resolves from current language
- **Routes**: same URLs, language stored in cookie/localStorage

### 3.9 SEO (NEW)
- **Open Graph + Twitter Card** meta tags per page
- **JSON-LD** structured data (WebApplication + Organization)
- **robots.txt** + **sitemap.xml**
- **Canonical URLs**
- **Semantic HTML** (already mostly done)

### 3.10 AI Media Generation Service (NEW)
- **TTS Engine** (`app/core/tts_service.py`):
  - Smart fallback: Gemini TTS → Groq Orpheus → Browser SpeechSynthesis
  - Server-side audio generation, returns WAV/MP3
  - Per-page voice presets (Thoth = authoritative, Stories = narrative, Landing = welcoming)
  - Language auto-detection from page context
  - Audio caching (generated audio stored in `/static/cache/audio/` to reduce API calls)
- **Image Generation** (`app/core/image_service.py`):
  - Cloudflare Workers AI FLUX.1 schnell (primary) → SDXL (fallback) → static placeholders
  - Egyptian-themed prompt templates ("Ancient Egyptian scene of {description}, golden sand, hieroglyphs, dramatic lighting")
  - Generated images cached in `/static/cache/images/`
  - Used in: Stories (chapter illustrations), Landing (rotating hero images)
- **No user-facing provider selection** — system always picks the best available
- **Endpoints**:
  - `POST /api/audio/speak` — TTS with auto-provider selection
  - `POST /api/media/generate-image` — image gen with caching

### 3.11 User Dashboard (NEW)
- **Overview**: total scans, stories completed, glyphs learned
- **Scan History**: thumbnails + results, click to revisit
- **Story Progress**: per-story completion %, glyphs learned per story
- **Favorites**: saved landmarks, learned dictionary signs
- **Settings**: language, notification preferences, password change

## 4. Database Schema (SQLite → PostgreSQL ready)

```sql
-- Users
CREATE TABLE users (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    preferred_lang TEXT DEFAULT 'en',
    tier TEXT DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scan History
CREATE TABLE scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT REFERENCES users(id),
    image_thumbnail BLOB,
    results_json TEXT,
    confidence_avg REAL,
    glyph_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Story Progress
CREATE TABLE story_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT REFERENCES users(id),
    story_id TEXT NOT NULL,
    chapter_index INTEGER DEFAULT 0,
    glyphs_learned TEXT DEFAULT '[]',
    score INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, story_id)
);

-- User Favorites
CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT REFERENCES users(id),
    item_type TEXT NOT NULL,  -- 'landmark', 'glyph', 'story'
    item_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_type, item_id)
);

-- Sessions (for refresh tokens)
CREATE TABLE refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT REFERENCES users(id),
    token_hash TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5. API Additions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/auth/register | No | Create account |
| POST | /api/auth/login | No | Get JWT tokens |
| POST | /api/auth/refresh | Cookie | Refresh access token |
| POST | /api/auth/logout | Yes | Invalidate refresh token |
| GET | /api/user/profile | Yes | Get user profile |
| PATCH | /api/user/profile | Yes | Update profile |
| GET | /api/user/history | Yes | Scan history (paginated) |
| GET | /api/user/progress | Yes | Story progress |
| POST | /api/user/favorites | Yes | Add favorite |
| DELETE | /api/user/favorites/:id | Yes | Remove favorite |
| GET | /api/stories | No | List all stories |
| GET | /api/stories/:id | No | Get story + chapters |
| POST | /api/stories/:id/interact | Optional | Submit interaction answer |
| GET | /api/stories/:id/progress | Yes | User progress for story |
| GET | /sitemap.xml | No | Dynamic sitemap |
| GET | /robots.txt | No | Robots file |

## 6. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Offline capability | Full scan + stories + dictionary work offline |
| Page load (LCP) | < 2.5s on 3G |
| Lighthouse Performance | > 85 |
| Lighthouse Accessibility | > 95 |
| Lighthouse SEO | > 90 |
| WCAG level | AA (4.5:1 contrast, labels, ARIA) |
| Max bundle size | < 500KB JS (excluding ONNX) |
| API response time | < 500ms (non-AI endpoints) |
| Uptime | 99% (free tier hosting) |
