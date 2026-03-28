# Phase 4 — UX, Accessibility & TTS Service

## Goal
Fix all navigation, usability, and accessibility issues. **Build the server-side TTS service** with Gemini TTS as primary provider (FREE, 30 voices, Arabic support, style-controllable). After this phase, every feature is reachable, content is correct, the app passes WCAG AA, and all audio uses the smart TTS fallback chain.

## Bugs Fixed
- **C4**: Chat TTS hardcoded to English (`lang='en'`)
- **H1**: `/write` page missing from navigation
- **H2**: Chat uses browser TTS instead of server TTS
- **H4**: Was Scepter coded as R11, should be S42
- **H5**: `text-dim` color fails WCAG AA contrast (4.5:1)
- **H7**: "Glyph of the Day" only has 7 entries
- **M10**: Search inputs lack `<label>` elements
- **M13**: Noto Sans Egyptian Hieroglyphs font declared but never loaded
- **M15**: Favicon MIME type mismatch (`.svg` file with `type="image/svg+xml"` but `href="/favicon.ico"`)
- **M17**: No confidence threshold shown to user in scan results

## Files Modified
- `app/templates/partials/nav.html` — add /write link
- `app/templates/chat.html` — language-aware TTS, prefer server TTS
- `app/templates/landing.html` — fix R11→S42, expand daily glyph pool
- `app/templates/base.html` — fix favicon href, add font-face, add narration button partial
- `app/templates/scan.html` — show confidence percentage
- `app/templates/dictionary.html` — add labels
- `app/templates/explore.html` — add labels
- `app/static/css/input.css` — fix text-dim contrast

## Files Created
- `app/core/tts_service.py` — TTS smart fallback chain (Gemini → Groq → Browser)
- `app/api/media.py` — `/api/audio/speak` endpoint
- `app/templates/partials/narration_button.html` — reusable floating narration control
- `app/static/cache/audio/` — directory for cached TTS audio

## Implementation Steps

### Step 1: Fix H1 — Add /write to navigation
In `partials/nav.html`, add Write link in both desktop and mobile:

**Desktop** (after Explore, before Quiz):
```html
<a href="/write" class="px-4 py-2 rounded-lg text-sm text-text-muted hover:text-text hover:bg-surface-alt transition-all duration-200">Write</a>
```

**Mobile** (add between Explore and Quiz):
```html
<a href="/write" class="px-4 py-3 rounded-lg text-sm text-text-muted hover:text-text hover:bg-surface-alt transition-all pl-8">↳ Write</a>
```

### Step 2: Fix C4 + H2 — Language-aware TTS with Gemini TTS Service
Build `app/core/tts_service.py` — the centralized TTS service used by ALL pages:

```python
# app/core/tts_service.py
# Smart fallback: Gemini 2.5 Flash TTS → Groq Orpheus → returns None (browser fallback)
# See constitution.md for voice presets and full architecture.
# Key voice presets:
#   - "thoth_chat": Orus (Firm) — authoritative ancient deity
#   - "landing": Charon (Informative) — warm guide
#   - "dictionary": Rasalgethi (Informative) — academic
#   - "story_narration": Aoede (Breezy) — used in Phase 8
# Requires: pip install google-genai
# Uses existing Gemini API keys (already have 17!)
```

Create `app/api/media.py`:
```python
from fastapi import APIRouter, Request
from fastapi.responses import Response
from app.core.tts_service import speak

router = APIRouter(prefix="/api/audio", tags=["audio"])

@router.post("/speak")
async def tts_speak(request: Request):
    body = await request.json()
    text = body.get("text", "")[:5000]  # Limit length
    lang = body.get("lang", "en")
    context = body.get("context", "default")

    audio_path = await speak(text, lang=lang, context=context)
    if audio_path:
        return FileResponse(audio_path, media_type="audio/wav")
    return Response(status_code=204)  # No audio — frontend uses browser TTS
```

In `chat.html`, replace hardcoded `lang: 'en'`:
```javascript
// Detect language from user preference or page lang
const chatLang = document.documentElement.lang || 'en';

// Use server TTS when online (now Gemini-powered!), browser TTS fallback offline
async speakMessage(text, messageId) {
    if (navigator.onLine) {
        try {
            const resp = await fetch('/api/audio/speak', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text, lang: chatLang, context: 'thoth_chat'})
            });
            if (resp.ok) {
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const audio = new Audio(url);
                audio.play();
                return;
            }
        } catch (e) { /* fall through to browser TTS */ }
    }
    // Offline fallback: browser TTS
    WadjetTTS.speakToggle(text, messageId, {lang: chatLang, rate: 0.95});
}
```

Add narration button on ALL content pages (landing, explore, dictionary, scan results):
```html
<!-- app/templates/partials/narration_button.html -->
<div class="fixed bottom-6 right-6 z-50" x-data="narration" x-show="hasContent">
    <button @click="toggle()" class="w-14 h-14 rounded-full bg-gold/20 border border-gold/50 backdrop-blur-xl flex items-center justify-center shadow-lg hover:bg-gold/30 transition" :aria-label="playing ? 'Pause narration' : 'Play narration'">
        <span x-show="!playing" class="text-2xl" aria-hidden="true">🔊</span>
        <span x-show="playing" class="text-2xl" aria-hidden="true">⏸️</span>
    </button>
</div>
```

### Step 3: Fix H4 — Was Scepter code
In `landing.html`, find the glyph array and change:
```javascript
// BEFORE:
{ glyph: '𓊹', label: 'Was Scepter', code: 'R11', meaning: 'Power & dominion' }
// AFTER:
{ glyph: '𓌀', label: 'Was Scepter', code: 'S42', meaning: 'Power & dominion' }
```
Note: The unicode glyph should also be verified against S42 in gardiner_data.

### Step 4: Fix H5 — WCAG contrast for text-dim
In `input.css`, find the `text-dim` color definition and increase brightness:
```css
/* BEFORE: likely something like #666 or rgba(255,255,255,0.4) */
/* AFTER: ensure 4.5:1 ratio against #0A0A0A background */
--color-text-dim: #9CA3AF;  /* gray-400 = 4.6:1 ratio on #0A0A0A */
```

### Step 5: Fix H7 — Expand Glyph of the Day
Replace the 7-item hardcoded array with a comprehensive set generated from gardiner_data. Create a script or use the existing 1,023 signs:

```javascript
// Generate from gardiner sign categories
const allGlyphs = [
    // A — Man and his activities (60+ signs)
    { glyph: '𓀀', label: 'Seated Man', code: 'A1', meaning: 'Man, person' },
    // ... hundreds more from gardiner_data
];

// Daily selection: hash-based for determinism
const today = new Date();
const dayIndex = Math.floor(today.getTime() / 86400000);
const dailyGlyph = allGlyphs[dayIndex % allGlyphs.length];
```

Or better: generate a `daily-glyphs.json` from the Python gardiner_data using a build script.

### Step 6: Fix M10 — Add labels to search inputs
In `dictionary.html` and `explore.html`:
```html
<!-- BEFORE: -->
<input type="text" placeholder="Search..." ...>

<!-- AFTER: -->
<label for="dict-search" class="sr-only">Search hieroglyphs</label>
<input id="dict-search" type="text" placeholder="Search hieroglyphs..." ...>
```

### Step 7: Fix M13 — Load Noto Sans Egyptian Hieroglyphs
In `base.html` or `input.css`, add proper font-face:
```css
@font-face {
    font-family: 'Noto Sans Egyptian Hieroglyphs';
    src: url('/static/fonts/NotoSansEgyptianHieroglyphs-Regular.ttf') format('truetype');
    font-display: swap;
}
```

### Step 8: Fix M15 — Favicon
In `base.html`:
```html
<!-- BEFORE: -->
<link rel="icon" href="/favicon.ico" type="image/svg+xml">
<!-- AFTER: -->
<link rel="icon" href="/static/images/favicon.svg" type="image/svg+xml">
```

### Step 9: Fix M17 — Show confidence in scan results
In `scan.html`, add confidence display:
```html
<span class="text-xs" :class="glyph.confidence > 0.7 ? 'text-success' : glyph.confidence > 0.4 ? 'text-gold' : 'text-error'">
    <span x-text="Math.round(glyph.confidence * 100)"></span>% confidence
</span>
```

## Testing Checklist
- [ ] /write appears in desktop nav (between Explore and Quiz)
- [ ] /write appears in mobile nav
- [ ] Click Write in nav → navigates to /write page
- [ ] Chat TTS: speaks in English when page is English
- [ ] Chat TTS: speaks in Arabic when page is Arabic (after Phase 6)
- [ ] **Chat TTS: Gemini TTS voice sounds authoritative (Orus voice)**
- [ ] Chat TTS: uses server TTS when online (check Network tab for `/api/audio/speak`)
- [ ] Chat TTS: falls back to browser TTS when offline
- [ ] **Narration button (🔊) visible on landing, explore, dictionary pages**
- [ ] **Click narration → page content read aloud via Gemini TTS**
- [ ] **TTS returns audio within 3-5 seconds**
- [ ] **Audio cached — second play of same text loads instantly**
- [ ] Landing page: Was Scepter shows code S42 (not R11)
- [ ] All text-dim elements: contrast ≥ 4.5:1 (use browser DevTools or axe)
- [ ] Glyph of Day: shows different glyph each day for 30+ days
- [ ] Dictionary search input: has associated label (check with screen reader)
- [ ] Explore search input: has associated label
- [ ] Egyptian hieroglyph characters render correctly (Noto Sans loaded)
- [ ] Favicon shows in browser tab (SVG icon)
- [ ] Scan results: each glyph shows confidence percentage
- [ ] Low-confidence glyphs (<40%) show in orange/red
- [ ] Run axe accessibility checker → 0 critical/serious violations

## Git Commit
```
[Phase 4] UX, accessibility & TTS service — nav fix, Gemini TTS, WCAG contrast, labels, narration
```
