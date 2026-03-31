/**
 * Wadjet v3 — Service Worker
 * Caches static assets and ML models for offline scanning.
 */

const CACHE_VERSION = 'wadjet-v32-beta';
const STATIC_CACHE = CACHE_VERSION + '-static';
const MODEL_CACHE = 'wadjet-models';  // version-independent: models persist across updates

// Static assets to pre-cache on install
const STATIC_ASSETS = [
    '/',
    '/hieroglyphs',
    '/landmarks',
    '/scan',
    '/dictionary',
    '/write',
    '/explore',
    '/chat',
    '/stories',
    '/stories/akhenatens-revolution',
    '/stories/cleopatras-last-stand',
    '/stories/contendings-horus-set',
    '/stories/creation-from-nun',
    '/stories/eye-of-ra',
    '/stories/osiris-myth',
    '/stories/the-book-of-thoth',
    '/stories/the-eye-of-horus',
    '/stories/the-great-pyramid',
    '/stories/the-journey-of-ra',
    '/stories/the-tears-of-isis',
    '/stories/the-weighing-of-the-heart',
    '/static/dist/styles.css',
    '/static/css/atropos.css',
    '/static/js/app.js',
    '/static/js/tts.js',
    '/static/js/hieroglyph-pipeline.js',
    '/static/vendor/alpine.min.js',
    '/static/vendor/alpine-intersect.min.js',
    '/static/vendor/htmx.min.js',
    '/static/vendor/gsap.min.js',
    '/static/vendor/scrolltrigger.min.js',
    '/static/vendor/lenis.min.js',
    '/static/vendor/atropos.min.js',
];

// ML models are cached on first use via cacheFirst() — too large to pre-cache

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== STATIC_CACHE && k !== MODEL_CACHE)
                    .map(k => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

// Fetch strategy
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Skip external requests (CDN scripts load from their own cache)
    if (url.origin !== self.location.origin) return;

    // API endpoints: network-only (except health)
    if (url.pathname.startsWith('/api/')) return;

    // ML models: cache-first (they only change on version bump)
    const isModel = url.pathname.startsWith('/models/');
    if (isModel) {
        event.respondWith(cacheFirst(event.request, MODEL_CACHE));
        return;
    }

    // Static assets: stale-while-revalidate (strip ?v= for cache matching)
    if (url.pathname.startsWith('/static/')) {
        const cacheUrl = new Request(url.origin + url.pathname);
        event.respondWith(staleWhileRevalidate(event.request, cacheUrl, STATIC_CACHE));
        return;
    }

    // HTML pages: network-first with cache fallback
    event.respondWith(networkFirst(event.request, STATIC_CACHE));
});

// ── Caching strategies ──

async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return new Response('Offline — model not cached', { status: 503 });
    }
}

async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            try {
                const cache = await caches.open(cacheName);
                cache.put(request, response.clone());
            } catch (e) {
                // Cache storage full or clone failed — not fatal
                console.warn('[SW] Cache put failed:', e.message);
            }
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;
        // Return branded offline page for navigation requests
        if (request.mode === 'navigate') return offlinePage();
        return new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain' } });
    }
}

function offlinePage() {
    const html = `<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offline — Wadjet</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{min-height:100vh;display:flex;align-items:center;justify-content:center;flex-direction:column;background:#0A0A0A;color:#F5F0E8;font-family:Inter,system-ui,sans-serif;text-align:center;padding:2rem}
        .logo{font-size:4rem;margin-bottom:1rem;opacity:.2;font-family:serif}
        h1{font-family:'Playfair Display',Georgia,serif;font-size:2rem;color:#D4AF37;margin-bottom:.5rem}
        p{color:#A89070;margin-bottom:1.5rem;max-width:24rem}
        .btn{display:inline-flex;align-items:center;gap:.5rem;padding:.75rem 1.5rem;border-radius:.5rem;font-size:.875rem;font-weight:500;text-decoration:none;transition:all .2s;background:#D4AF37;color:#0A0A0A;border:none;cursor:pointer}
        .btn:hover{background:#E5C76B}
        .divider{width:8rem;height:1px;background:linear-gradient(to right,transparent,#2A2A2A,transparent);margin:2rem auto}
        .sub{font-size:.75rem;color:#A89070}
    </style>
</head>
<body>
    <div class="logo">𓂀</div>
    <h1>You're Offline</h1>
    <p>The connection to the ancient archives has been lost. Please check your internet and try again.</p>
    <button class="btn" onclick="location.reload()">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
        Try Again
    </button>
    <div class="divider"></div>
    <p class="sub">Wadjet — Egyptian Heritage Explorer</p>
</body>
</html>`;
    return new Response(html, { status: 503, headers: { 'Content-Type': 'text/html; charset=UTF-8' } });
}

async function staleWhileRevalidate(request, cacheKey, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(cacheKey);
    const fetchPromise = fetch(request).then(response => {
        if (response.ok) cache.put(cacheKey, response.clone());
        return response;
    }).catch(() => cached || offlinePage());
    return cached || fetchPromise;
}
