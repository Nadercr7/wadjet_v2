# Phase 10 — v3 Beta Finalization

## Goal
Add the beta badge, bump all versions, run a full audit, and create the changelog. After this phase, Wadjet v3 Beta is ready.

## Tasks
1. Beta badge next to logo in nav
2. Version bump everywhere (pyproject.toml, SW cache, package.json)
3. Update CLAUDE.md and README.md
4. Create CHANGELOG.md (v2 → v3 beta)
5. Full Lighthouse audit (Performance, Accessibility, SEO, Best Practices)
6. End-to-end smoke test on all pages
7. Offline mode full test
8. Mobile responsive test
9. Arabic RTL full test
10. Final git tag: `v3.0.0-beta`
11. **Version replacement option** — script to swap v3-beta as the main version

## Files Modified
- `app/templates/partials/nav.html` — beta badge
- `pyproject.toml` — version 3.0.0-beta
- `app/static/sw.js` — cache version bump
- `package.json` — version bump
- `README.md` — updated docs
- `CLAUDE.md` — updated project instructions

## Files Created
- `CHANGELOG.md` — all changes documented

## Implementation Steps

### Step 1: Beta badge in nav
```html
<!-- In nav.html, logo area: -->
<a href="/" class="flex items-center gap-2.5 group" aria-label="Wadjet home">
    <span class="text-2xl" aria-hidden="true">𓂀</span>
    <span class="font-display font-bold text-lg text-gold-gradient">Wadjet</span>
    <span class="text-[10px] font-semibold tracking-wider uppercase border border-gold/50 text-gold px-1.5 py-0.5 rounded-full leading-none">BETA</span>
</a>
```

### Step 2: Version bumps
```toml
# pyproject.toml
[project]
name = "wadjet"
version = "3.0.0-beta"
```

```javascript
// sw.js
const CACHE_VERSION = 'wadjet-v30-beta';
```

```json
// package.json
{ "version": "3.0.0-beta" }
```

### Step 3: CHANGELOG.md
```markdown
# Changelog

## v3.0.0-beta (2026-03-xx)

### 🔒 Security
- Magic byte validation for image uploads (not just content-type)
- CSRF protection on all POST endpoints (starlette-csrf)
- Rate limiting on all API endpoints (slowapi)
- Quiz answers no longer exposed in client-side JavaScript
- Error messages sanitized (generic to user, detailed in logs)
- JWT-based authentication system

### 🌐 Offline & Performance
- All 6 CDN scripts self-hosted in /static/vendor/
- Service worker completely rewritten — full offline support
- ML models use cache-first strategy (no unnecessary re-downloads)
- Lazy loading for below-fold images
- Explore page: infinite scroll pagination (20 cards at a time)

### 🎨 UX & Accessibility
- /write page added to navigation
- Was Scepter corrected from R11 to S42
- WCAG AA contrast compliance (text-dim fixed)
- All form inputs have proper labels
- Confidence percentage shown in scan results
- Glyph of the Day expanded from 7 to 1,023 entries
- Favicon path and MIME type fixed
- Noto Sans Egyptian Hieroglyphs font properly loaded

### 🌍 Arabic & i18n
- Full Arabic language support with language toggle
- RTL layout via Tailwind CSS
- Arabic landmark and glyph names rendered
- Bilingual UI strings (en.json + ar.json)
- Cairo font for Arabic text
- Write page: Arabic examples added

### 📊 SEO
- Open Graph + Twitter Card meta tags on all pages
- JSON-LD structured data
- robots.txt + dynamic sitemap.xml
- Canonical URLs

### 📖 Stories of the Nile (NEW — replaces Quiz)
- 5 interactive Egyptian mythology stories
- 4 learning interaction types
- Progress tracking per story
- Bilingual content (English + Arabic)
- Offline-capable

### 🏗️ SaaS Foundation (NEW)
- SQLite database (PostgreSQL-ready via SQLAlchemy)
- User registration and JWT authentication
- User dashboard with stats, history, progress
- Scan history saved per user
- Story progress tracking
- Favorites system (landmarks, glyphs)
- Free tier with soft limits

### 🤖 AI Media Services (NEW)
- **Gemini 2.5 Flash TTS** across all pages — 30 voices, Arabic support, style-controllable
- Smart TTS fallback chain: Gemini → Groq Orpheus → Browser SpeechSynthesis
- Floating narration button (🔊) on all content pages
- **Cloudflare FLUX.1** AI-generated story illustrations
- Ken Burns cinematic animations on story images
- Generated media cached for instant replay
- No user-facing provider selection — system picks best available

### 🏷️ Meta
- Version bumped to v3.0.0-beta
- Beta badge added next to logo
- Comprehensive planning documentation
```

### Step 4: Full audit checklist

#### Lighthouse Targets
| Category | Target | Notes |
|----------|--------|-------|
| Performance | > 85 | Lazy loading, cache-first, pagination |
| Accessibility | > 95 | Labels, ARIA, contrast, skip-to-content |
| Best Practices | > 90 | No mixed content, SRI on externals |
| SEO | > 90 | OG tags, sitemap, robots.txt, canonical |

#### Smoke Test (Every Page)
- [ ] Landing page loads, daily glyph shows, CTA works
- [ ] /hieroglyphs — hub page navigable
- [ ] /scan — upload image works, results display with confidence
- [ ] /dictionary — search works, hieroglyphs render
- [ ] /write — text to hieroglyph works, Arabic examples present
- [ ] /landmarks — page loads
- [ ] /explore — cards load, infinite scroll works, favorites work
- [ ] /chat — messages send, TTS works in correct language
- [ ] /stories — story list shows, reader works, all 4 interactions work
- [ ] /dashboard — stats, history, progress, favorites (logged in)
- [ ] /settings — profile update works

#### Offline Test
- [ ] Disconnect network
- [ ] Landing page loads from cache
- [ ] Scan page loads, client-side ONNX works
- [ ] Dictionary works from cache
- [ ] Stories load from cache
- [ ] All vendor scripts (Alpine, HTMX, GSAP, etc.) work offline
- [ ] TTS falls back to browser speech synthesis

#### Mobile Test
- [ ] Nav hamburger menu works
- [ ] All pages render correctly on 375px width
- [ ] Touch interactions smooth (stories, scan upload, cards)
- [ ] No horizontal scroll overflow

#### Arabic Test
- [ ] Toggle to Arabic → full RTL layout
- [ ] All UI strings in Arabic
- [ ] Arabic landmark/glyph names shown
- [ ] Stories display in Arabic
- [ ] Dashboard in Arabic
- [ ] Toggle back → LTR restored

### Step 5: Final git commit + tag
```bash
git add -A
git commit -m "[Phase 10] v3.0.0-beta — finalization, beta badge, changelog, full audit"
git tag -a v3.0.0-beta -m "Wadjet v3.0.0 Beta Release"
```

### Step 6: Version Replacement Option
After the beta is stable and tested, the user can choose to make it the production version.

**PowerShell script** (`wadjet-v3-planning/scripts/replace-version.ps1`):
```powershell
# Run ONLY when user explicitly decides to replace the original
# This archives v2 and promotes v3-beta to the main folder

$originalPath = "D:\Personal attachements\Projects\Wadjet"
$betaPath = "D:\Personal attachements\Projects\Wadjet-v3-beta"
$archivePath = "D:\Personal attachements\Projects\Wadjet-v2-archive"

Write-Host "=== Wadjet Version Replacement ===" -ForegroundColor Gold
Write-Host "This will:" -ForegroundColor Yellow
Write-Host "  1. Archive current Wadjet/ -> Wadjet-v2-archive/"
Write-Host "  2. Copy Wadjet-v3-beta/ -> Wadjet/"
Write-Host ""

$confirm = Read-Host "Are you sure? (type 'yes' to confirm)"
if ($confirm -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Red
    exit
}

# Archive original
if (Test-Path $originalPath) {
    Write-Host "Archiving v2..." -ForegroundColor Cyan
    Rename-Item $originalPath $archivePath
}

# Copy v3-beta as main
Write-Host "Promoting v3-beta to main..." -ForegroundColor Cyan
Copy-Item $betaPath $originalPath -Recurse -Exclude @('.venv', 'node_modules', '__pycache__', 'wadjet-v3-planning')

Write-Host "Done! Wadjet v3 is now the main version." -ForegroundColor Green
Write-Host "Original v2 archived at: $archivePath" -ForegroundColor DarkGray
```

## Testing Checklist
- [ ] Beta badge visible next to "Wadjet" text in nav
- [ ] Badge shows on both desktop and mobile
- [ ] Badge does not break nav layout
- [ ] Version is 3.0.0-beta in pyproject.toml
- [ ] SW cache version is wadjet-v30-beta
- [ ] CHANGELOG.md is comprehensive and accurate
- [ ] README.md reflects v3 features
- [ ] All Lighthouse scores meet targets
- [ ] All smoke tests pass
- [ ] All offline tests pass
- [ ] All mobile tests pass
- [ ] All Arabic tests pass
- [ ] Git tag v3.0.0-beta exists
- [ ] **Version replacement script exists and runs without error in dry-run mode**

## Git Commit
```
[Phase 10] v3.0.0-beta — beta badge, version bump, changelog, full audit, version replacement script
```
