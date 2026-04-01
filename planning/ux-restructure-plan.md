# Wadjet v3 — UX Restructure Plan

> Goal: Simplify navigation, reduce redundant pages, fix UI bugs — zero breaking changes.
> All existing routes stay alive (SEO safe). Only nav links and page internals change.
> Respects project identity: **dual-path architecture** (Hieroglyphs path + Landmarks path).

---

## Project Identity Constraints

From CLAUDE.md — these are NON-NEGOTIABLE and must be preserved:

- **Dual-path architecture**: Landing page (/) splits into Hieroglyphs path + Landmarks path
- **Design system**: Black & Gold (#0A0A0A + #D4AF37), Playfair Display headings, Inter body
- **Tech stack locked**: FastAPI + Jinja2 + Alpine.js + HTMX + TailwindCSS v4
- **Footer**: "Built by Mr Robot" — never change
- **Bilingual**: EN + AR with `t('key', lang)` i18n helper throughout
- **Auth**: Google OAuth (primary), JWT tokens, `wadjet_session` cookie
- **Narration**: TTS on landing, explore, story pages — `data-narration-context` attribute

---

## Current State

### Routes (17 templates, 14 unique routes)
```
/                    → landing.html        (app hub, dual-path cards → /hieroglyphs, /landmarks)
/welcome             → welcome.html        (marketing/onboarding — first visit only, no nav)
/hieroglyphs         → hieroglyphs.html    (hub: 3 cards → scan/dict/write)
/landmarks           → landmarks.html      (hub: 2 cards → explore, explore?identify)
/scan                → scan.html           (hieroglyph scanner — upload → detect → translate)
/dictionary          → dictionary.html     (browse + learn tabs, sign detail modal)
/dictionary/lesson/N → lesson_page.html    (5 progressive lessons, same sign detail modal)
/write               → write.html          (text → hieroglyphs + glyph palette)
/explore             → explore.html        (landmarks browse + identify + detail modal)
/chat                → chat.html           (Thoth AI chatbot, streaming + STT + TTS)
/stories             → stories.html        (story listing, difficulty filter, progress)
/stories/:id         → story_reader.html   (interactive reader, 4 interaction types)
/dashboard           → dashboard.html      (user stats, auth-gated)
/settings            → settings.html       (account settings, auth-gated)
/feedback            → feedback_admin.html  (admin only)
/quiz                → 301 → /stories      (dead redirect)
/error               → error.html          (error page)
```

### Auth Model
```
First visit (no cookie)  → /welcome   (marketing, Google Sign-In CTA)
After login (has cookie)  → /         (app hub, dual-path)
All feature pages         → _require_session() gate → redirect to /welcome?next=...
Hard-gated               → /dashboard, /settings (in-page auth wall)
Admin-only               → /feedback (403 if not admin email)
```

### Nav Structure (8 desktop links + 8 mobile links with grouping)
```
Desktop: Hieroglyphs | Scan | Dictionary | Landmarks | Explore | Write | Stories | Thoth
Mobile:  Hieroglyphs
           ↳ Scan
           ↳ Dictionary
         Landmarks
           ↳ Explore
           ↳ Write
         Stories
         Thoth
```
Logged-in desktop also shows: `[Scan] btn-gold` + user avatar dropdown → Dashboard, Settings, Feedback, Sign Out.

### Footer (4-column)
```
Brand + tagline | Hieroglyphs col (Overview, Scan, Dict, Write) | Landmarks col (Overview, Explore, Thoth, API Status)
                                                                  Bottom: "Built by Mr Robot"
```

### User Journey Analysis
```
New user:  Google → /welcome → Sign In → / (landing) → choose path
                                                      ↓           ↓
                                              /hieroglyphs    /landmarks
                                              ↓    ↓    ↓         ↓
                                           /scan /dict /write  /explore
                                                  ↓
                                            /dictionary/lesson/N

Returning: / (landing) → nav links → any feature page
```

**Problem**: The hub pages (/hieroglyphs, /landmarks) are a 3rd click between landing and features.
Landing already describes what each path contains. The hubs repeat the same info with clickable cards.
Users from nav skip hubs entirely. Hub value = zero for nav users, marginal for landing users.

### Known Issues
1. **Nav has 8 items** — too many for desktop (cognitive load), worse on mobile (long scroll)
2. **Hub pages = extra click** — both /hieroglyphs and /landmarks are static card pages
3. **Mobile nav grouping misleading** — "Write" is under Landmarks (should be under Hieroglyphs if anything)
4. **quiz.html = dead code** — 300 lines of template + Alpine component, route is 301 → /stories
5. **Sign detail modal duplicated** — dictionary.html + lesson_page.html (~120 lines identical)
6. **Dashboard story titles** — shows raw slug `sp.story_id.replace(/-/g, ' ')` not actual title
7. **Dashboard favorite names** — shows `f.item_id.replace(/-/g, ' ')` not landmark display name
8. **Settings password form** — shown to Google OAuth users who have no password to change
   - `UserResponse.auth_provider` field exists ("google" vs "email") — can use client-side
9. **scan.html ARIA orphan** — `role="tabpanel"` remains but camera tab button was removed
10. **write.html zombie state** — `mode: 'smart'` in Alpine data but no UI toggle
11. **Footer misgroups** — Stories and Chat not in footer; Write under Hieroglyphs; API Status prominent but unnecessary
12. **Landing dual-path cards** → link to hubs, not directly to features (extra click)
13. **Favorites 401 in explore** — already fixed (previous commit), but dashboard has same pattern without token guard

---

## Plan

### Task 1 — Simplify Nav (8 → 5 items)

**What changes:**
- Desktop nav: `Scan | Dictionary | Explore | Stories | Thoth`
- Mobile nav: flat list of same 5 items (no parent → child indentation needed)
- Remove from nav: Hieroglyphs hub, Landmarks hub, Write
- Logged-in CTA button stays: `[Scan] btn-gold`

**Files:**
- `app/templates/partials/nav.html` — remove 3 desktop links + 3 mobile links, flatten mobile structure
- `app/i18n/en.json` + `app/i18n/ar.json` — remove `sub_scan`, `sub_dictionary`, `sub_explore`, `sub_write` keys (no longer needed)

**What stays unchanged:**
- Routes `/hieroglyphs`, `/landmarks`, `/write` all stay alive (SEO, bookmarks, sitemap, landing links)
- Hub pages still reachable from landing page dual-path cards
- Write still reachable from Dictionary (Task 2), footer, and direct URL
- Footer keeps all links (footer = comprehensive sitemap, nav = quick access)

**Why 5 is the right number:**
- Scan = primary feature (hero CTA)
- Dictionary = learning hub (Browse + Learn + Write after Task 2)
- Explore = landmarks (browse + identify in one page)
- Stories = engagement/narrative
- Thoth = AI companion (always accessible)
- These 5 cover every feature. The hubs add no value in nav since users already know where they're going.

---

### Task 2 — Merge Write into Dictionary (3rd tab)

**What changes:**
- Dictionary tabs go from `Browse | Learn` → `Browse | Learn | Write`
- Write tab content = current write.html Alpine component + UI
- `/write` route changes to 302 redirect → `/dictionary?tab=write`

**Files:**
- `app/templates/dictionary.html` — add Write tab button + write panel (inline the writeApp Alpine component)
- `app/api/pages.py` — change `/write` handler to `RedirectResponse("/dictionary?tab=write", 302)`
- `app/api/write.py` — no changes (API endpoints stay at `/api/write/*`)

**Tab activation logic:**
```js
// In dictionaryApp() init:
const urlTab = new URLSearchParams(location.search).get('tab');
this.tab = ['browse', 'learn', 'write'].includes(urlTab) ? urlTab : 'browse';
```

**Implementation approach:**
- Inline the write UI directly in dictionary.html under a new tabpanel
- The write Alpine component (`writeApp`) merges into `dictionaryApp()` — add its state vars + methods
- Keep `/api/write/*` endpoints untouched
- `write.html` template stays in repo as fallback (dead but no harm)

**Why this makes sense:**
- Dictionary = "learn hieroglyphs" hub — Browse (reference), Learn (lessons), Write (practice)
- Natural progression: see signs → learn signs → use signs
- Reduces nav items and page count without losing functionality

**Size concern:**
- dictionary.html is ~600 lines, write.html is ~400 lines
- Combined = ~900–1000 lines — acceptable for a tabbed SPA-like page
- Each tab panel only renders when active (Alpine `x-show`), so no perf impact

---

### Task 3 — Extract Sign Detail Modal to Partial

**What changes:**
- New file: `app/templates/partials/sign_detail_modal.html` — the shared modal (~120 lines)
- Both dictionary.html and lesson_page.html use `{% include "partials/sign_detail_modal.html" %}`

**Files:**
- Create: `app/templates/partials/sign_detail_modal.html`
- Edit: `app/templates/dictionary.html` — replace inline modal with `{% include %}`
- Edit: `app/templates/lesson_page.html` — replace inline modal with `{% include %}`

**Prerequisite check:**
- Both modals use `detailSign` as the Alpine data variable name — confirmed identical
- Both have the same type-conditional rendering (phonetic/logogram/determinative)
- Both use `speakSign()` and TTS button — same API

**Why:** Eliminates ~120 lines of duplicated HTML. Single source of truth means any modal fix applies everywhere.

---

### Task 4 — Fix Dashboard Display Names

**4a — Story titles:**
- Dashboard currently: `sp.story_id.replace(/-/g, ' ')` → "osiris and the nile"
- Should show: bilingual story title from `/api/stories`

**Implementation:**
```js
// In dashboardApp() init — fetch stories alongside other data:
const storiesRes = await fetch('/api/stories');
const storiesData = await storiesRes.json();
this.storyTitleMap = {};
for (const s of storiesData.stories) {
    const title = typeof s.title === 'object' ? (s.title[lang] || s.title.en) : s.title;
    this.storyTitleMap[s.id] = title;
}
```
Then in template: `x-text="storyTitleMap[sp.story_id] || sp.story_id.replace(/-/g, ' ')"`

**4b — Favorite landmark names:**
- Dashboard currently: `f.item_id.replace(/-/g, ' ')` (line 219)
- Should show: landmark display name

**Implementation:**
- For landmark favorites: fetch `/api/landmarks?limit=999` on init, build `landmarkNameMap`
- OR: include `display_name` in the favorites API response (cleaner but needs API change)
- **Recommendation:** Client-side map for now (no API change). The stories API and landmarks browse API already have this data.

**Files:**
- `app/templates/dashboard.html` — add title/name maps, update display expressions

---

### Task 5 — Hide Password Form for OAuth Users

**Current state:**
- `settings.html` shows password change form to ALL users
- Google OAuth users have no password — form submission will fail with confusing error
- `UserResponse` schema already includes `auth_provider: str` (value: "google" or "email")
- `$store.auth.user` has this field from login response

**Implementation:**
```html
<!-- Password Section — only for email-based accounts -->
<div x-show="$store.auth.user && $store.auth.user.auth_provider !== 'google'" x-cloak>
    <!-- existing password form -->
</div>
```

**Files:**
- `app/templates/settings.html` — wrap password section in `x-show` conditional

**No API change needed** — `auth_provider` already served in `UserResponse`.

---

### Task 6 — Clean Up Dead Code & ARIA Fixes

**6a — Delete quiz.html:**
- `app/templates/quiz.html` — 300 lines of dead code
- Route `/quiz` is a 301 → `/stories` (in `pages.py`)
- Template never rendered. Safe to delete.

**6b — Fix scan.html ARIA orphan:**
- Upload panel still has `role="tabpanel"` and `id="scan-panel-upload"` from when camera tab existed
- Remove these ARIA attributes since there's no tablist anymore (upload is the only mode)

**6c — Clean write.html zombie state (if not merged into dictionary):**
- `mode: 'smart'` in Alpine data — no UI toggle, no other mode
- Remove the state variable and any `mode ===` conditionals
- NOTE: If Task 2 (merge) is done, this is moot — write.html becomes a redirect

**6d — Fix explore.html camera cleanup:**
- Camera JS functions (`startIdentifyCamera`, `captureIdentifyPhoto`, `stopIdentifyCamera`) still in script block
- Camera state vars (`identifyCameraActive`, `identifyStream`) still in Alpine data
- Remove dead camera code from both scan.html and explore.html script blocks

**Files:**
- Delete: `app/templates/quiz.html`
- Edit: `app/templates/scan.html` — remove ARIA tabpanel attrs + dead camera JS
- Edit: `app/templates/explore.html` — remove dead camera JS + state vars
- Edit: `app/templates/write.html` — remove zombie `mode` state (if not doing Task 2)

---

### Task 7 — Update Footer Structure

**Current footer (4-col):**
```
Brand | Hieroglyphs col | Landmarks col
```
**Issues:**
- Stories and Chat not represented in footer
- "API Status" link is developer-facing, not user-facing
- Structure dates from when navigation was path-based

**Proposed footer (3-col or 4-col):**
```
Brand (col-span-2) | Features | Resources
                      Scan        Stories
                      Dictionary  Thoth Chat
                      Explore     Dashboard
                      Write       API Health
```

**Files:**
- `app/templates/partials/footer.html` — restructure columns
- `app/i18n/en.json` + `app/i18n/ar.json` — add/update footer translation keys

**Why:** Footer should be a comprehensive sitemap with logical grouping. Current grouping by "path" makes less sense once nav is simplified.

---

### Task 8 — Update Landing Page Direct Links (Optional)

**Current:** Landing page dual-path cards link to hub pages:
- Hieroglyphs card → `/hieroglyphs`
- Landmarks card → `/landmarks`

**Consideration:** Since hubs are now de-emphasized (removed from nav), should the landing cards link directly to the primary feature?
- Hieroglyphs card → `/scan` (primary action) with secondary links to `/dictionary`, `/write`
- Landmarks card → `/explore` (primary action)

**Recommendation:** Keep as-is for now. The landing page dual-path cards are a "choose your journey" moment — the hubs serve as a gentle introduction. Hubs are still useful as intermediary pages for first-time users who need to understand what tools are available. This is different from nav (where users already know).

**Decision: SKIP THIS TASK** — landing page flow is fine. Hubs are valuable for first-time path commitment.

---

## Execution Order (dependency-aware)

```
1. Task 6 — Clean dead code           (clean slate — no dependencies)
2. Task 3 — Extract sign modal partial (prerequisite for Task 2)
3. Task 1 — Simplify nav 8→5          (high-impact, no code deps)
4. Task 7 — Update footer              (pairs with nav change)
5. Task 2 — Merge Write into Dict      (depends on Task 3 partial, needs clean dictionary.html)
6. Task 4 — Fix dashboard titles       (independent bug fix)
7. Task 5 — Hide password for OAuth    (independent bug fix)
```

Task 8 (landing direct links) is SKIPPED — landing flow is fine as-is.

**Commit strategy:** One commit per task for clean git history + easy revert.

---

## Risk Assessment

| Task | Risk | Mitigation |
|------|------|-----------|
| Task 1 (nav) | Users expect "Write" in nav | Footer keeps Write link; Dictionary tab provides access |
| Task 2 (merge) | dictionary.html gets large (~1000 lines) | Alpine `x-show` means only active tab renders; can split to partial later |
| Task 2 (merge) | Write API calls go to `/api/write/*` from inside `/dictionary` page | API is path-independent, just fetches — works fine |
| Task 3 (partial) | Sign modal uses Alpine vars from parent component | Both parents use `detailSign` — same variable name, no conflict |
| Task 4 (titles) | Extra fetch on dashboard load | `/api/stories` is tiny (5 stories, ~1KB), cached on server |
| Task 6 (delete quiz) | Someone bookmarked /quiz | Route still exists as 301 → /stories, template deletion has no effect |
| Task 7 (footer) | i18n keys need AR translation | Must update both en.json and ar.json simultaneously |

---

## What Does NOT Change

- All existing routes stay alive and working (no broken bookmarks, no broken SEO)
- No API endpoint changes (all `/api/*` routes untouched)
- No database schema changes
- No auth flow changes
- No CSS/design system changes (Black & Gold preserved)
- Landing page dual-path hub stays as-is (still links to /hieroglyphs, /landmarks)
- Hub pages (/hieroglyphs, /landmarks) stay as SEO landing pages
- Sitemap.xml keeps all URLs
- Welcome page flow unchanged (first visit → /welcome, returning → /)
- "Built by Mr Robot" footer attribution unchanged
- Narration system unchanged (data-narration-context on landing, explore, stories)
- TTS/STT systems unchanged
- ONNX model loading unchanged

---

## Final State After All Tasks

### Nav
```
Desktop:  Scan | Dictionary | Explore | Stories | Thoth     [5 items]
Mobile:   Scan | Dictionary | Explore | Stories | Thoth     [5 items, flat list]
```

### Footer
```
Brand + tagline  |  Features           |  Resources
                    Scan & Identify        Stories
                    Dictionary & Learn     Thoth Chat
                    Explore Sites          Dashboard
                    Write Hieroglyphs      API Health
```

### Route → Template Map

```
/                    → landing.html        (unchanged — links to /hieroglyphs, /landmarks)
/welcome             → welcome.html        (unchanged — marketing/onboarding)
/hieroglyphs         → hieroglyphs.html    (unchanged — removed from nav but still accessible)
/landmarks           → landmarks.html      (unchanged — removed from nav but still accessible)
/scan                → scan.html           (cleanup: remove ARIA orphans + dead camera JS)
/dictionary          → dictionary.html     (3 tabs: Browse | Learn | Write, + sign modal partial)
/dictionary?tab=write → dictionary.html    (Write tab auto-selected)
/dictionary/lesson/N → lesson_page.html    (+ sign modal partial include)
/write               → 302 → /dictionary?tab=write
/explore             → explore.html        (cleanup: remove dead camera JS)
/chat                → chat.html           (unchanged)
/stories             → stories.html        (unchanged)
/stories/:id         → story_reader.html   (unchanged)
/dashboard           → dashboard.html      (fix: story titles + fav names with real display names)
/settings            → settings.html       (fix: hide password for Google OAuth users)
/feedback            → feedback_admin.html  (unchanged)
/quiz                → 301 → /stories      (unchanged — template deleted, redirect stays)
```

### File Changes Summary

| Action | File | Task |
|--------|------|------|
| **DELETE** | `app/templates/quiz.html` | 6 |
| **CREATE** | `app/templates/partials/sign_detail_modal.html` | 3 |
| **EDIT** | `app/templates/partials/nav.html` | 1 |
| **EDIT** | `app/templates/partials/footer.html` | 7 |
| **EDIT** | `app/templates/dictionary.html` | 2, 3 |
| **EDIT** | `app/templates/lesson_page.html` | 3 |
| **EDIT** | `app/templates/scan.html` | 6 |
| **EDIT** | `app/templates/explore.html` | 6 |
| **EDIT** | `app/templates/write.html` | 6 (if not superseded by Task 2) |
| **EDIT** | `app/templates/dashboard.html` | 4 |
| **EDIT** | `app/templates/settings.html` | 5 |
| **EDIT** | `app/api/pages.py` | 2 |
| **EDIT** | `app/i18n/en.json` | 1, 7 |
| **EDIT** | `app/i18n/ar.json` | 1, 7 |

**Net template count:** 17 → 16 (quiz.html deleted, sign_detail_modal.html created as partial)
**Net route count:** unchanged (all routes preserved)
