# Phase 2 — Self-Host CDN Scripts + Offline Fix

## Goal
Eliminate all external runtime dependencies by downloading CDN scripts locally. Fix the service worker so the app works fully offline. This is the #1 critical bug — offline mode is completely broken.

## Bugs Fixed
- **C1**: 6 CDN scripts not cached → offline mode completely broken
- **M8**: HTMX script lacks `defer` attribute
- **M11**: No Subresource Integrity on CDN scripts (solved by self-hosting)
- **M12**: `tts.js` not in service worker pre-cache list
- **M18**: Cache invalidation wipes entire cache on version bump

## Files Modified
- `app/static/vendor/` — NEW folder with 6 self-hosted scripts
- `app/templates/base.html` — switch CDN → local paths, add defer
- `app/static/sw.js` — add vendor scripts to pre-cache, fix cache strategy

## Implementation Steps

### Step 1: Download CDN scripts to vendor/
Create `app/static/vendor/` and download:

```powershell
$vendor = "D:\Personal attachements\Projects\Wadjet-v3-beta\app\static\vendor"
New-Item -ItemType Directory -Path $vendor -Force

# Alpine.js 3.14.8
Invoke-WebRequest "https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js" -OutFile "$vendor\alpine.min.js"

# HTMX 2.0.4
Invoke-WebRequest "https://unpkg.com/htmx.org@2.0.4" -OutFile "$vendor\htmx.min.js"

# GSAP 3 + ScrollTrigger
Invoke-WebRequest "https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js" -OutFile "$vendor\gsap.min.js"
Invoke-WebRequest "https://cdn.jsdelivr.net/npm/gsap@3/dist/ScrollTrigger.min.js" -OutFile "$vendor\scrolltrigger.min.js"

# Lenis smooth scroll
Invoke-WebRequest "https://cdn.jsdelivr.net/npm/lenis@1/dist/lenis.min.js" -OutFile "$vendor\lenis.min.js"

# Atropos 3D (copy from Repos if available, otherwise CDN)
Invoke-WebRequest "https://cdn.jsdelivr.net/npm/atropos@2/atropos.min.js" -OutFile "$vendor\atropos.min.js"
```

### Step 2: Update base.html
Replace CDN script tags with local paths:

```html
<!-- BEFORE (CDN — breaks offline): -->
<script src="https://cdn.jsdelivr.net/npm/atropos@2/atropos.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/ScrollTrigger.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/lenis@1/dist/lenis.min.js" defer></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js"></script>
<script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-..." crossorigin="anonymous"></script>

<!-- AFTER (local — works offline): -->
<script src="/static/vendor/atropos.min.js" defer></script>
<script src="/static/vendor/gsap.min.js" defer></script>
<script src="/static/vendor/scrolltrigger.min.js" defer></script>
<script src="/static/vendor/lenis.min.js" defer></script>
<script src="/static/vendor/alpine.min.js" defer></script>
<script src="/static/vendor/htmx.min.js" defer></script>
```

Note: All scripts now have `defer` (M8 fixed). No SRI needed since files are local (M11 solved).

### Step 3: Update service worker
Add vendor scripts and tts.js to STATIC_ASSETS:

```javascript
const CACHE_VERSION = 'wadjet-v20';  // bump version
const STATIC_ASSETS = [
    '/',
    '/hieroglyphs',
    '/landmarks',
    '/scan',
    '/dictionary',
    '/write',
    '/explore',
    '/chat',
    '/static/dist/styles.css',
    '/static/css/atropos.css',
    '/static/js/app.js',
    '/static/js/tts.js',                    // M12 fix
    '/static/js/hieroglyph-pipeline.js',
    '/static/vendor/alpine.min.js',          // C1 fix
    '/static/vendor/htmx.min.js',            // C1 fix
    '/static/vendor/gsap.min.js',            // C1 fix
    '/static/vendor/scrolltrigger.min.js',   // C1 fix
    '/static/vendor/lenis.min.js',           // C1 fix
    '/static/vendor/atropos.min.js',         // C1 fix
];
```

### Step 4: Fix M18 — Smart cache invalidation
Instead of wiping everything on version bump, use per-resource versioning:

```javascript
// On activate, only delete caches with OLD version prefix
self.addEventListener('activate', (event) => {
    const currentCaches = [STATIC_CACHE, MODEL_CACHE];
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => !currentCaches.includes(k))
                    .map(k => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});
```

### Step 5: Fix model caching strategy
Change models from network-first to cache-first (H8):

```javascript
// Models: cache-first (they don't change unless we bump the version)
if (isModel) {
    event.respondWith(cacheFirst(event.request, MODEL_CACHE));
    return;
}
```

### Step 6: Remove DNS prefetch for CDN
Remove these lines from base.html since we no longer use CDN:
```html
<!-- REMOVE: -->
<link rel="dns-prefetch" href="https://cdn.jsdelivr.net">
<link rel="dns-prefetch" href="https://unpkg.com">
```
Keep Google Fonts prefetch (still using CDN for fonts — OK, fonts are optional).

## Testing Checklist
- [ ] All pages load correctly with local scripts (no CDN requests in Network tab)
- [ ] Disconnect network → app loads fully offline
- [ ] Alpine.js reactivity works (mobile menu, toasts, quiz interactions)
- [ ] HTMX partial loading works (explore, dictionary)
- [ ] GSAP scroll animations run (landing page, section reveals)
- [ ] Lenis smooth scrolling active
- [ ] Atropos 3D card effects work on landing
- [ ] TTS works offline (tts.js cached)
- [ ] `navigator.serviceWorker.ready` → cache contents include all vendor scripts
- [ ] Models NOT re-downloaded when online (cache-first)
- [ ] Update SW version → old static cache deleted, model cache preserved
- [ ] No console errors on any page

## Git Commit
```
[Phase 2] Self-host CDN scripts, fix service worker offline caching, cache-first models
```
