/**
 * Wadjet v2 — Service Worker
 * Caches static assets and ML models for offline scanning.
 */

const CACHE_VERSION = 'wadjet-v20';
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
    '/static/dist/styles.css',
    '/static/css/atropos.css',
    '/static/js/app.js',
    '/static/js/tts.js',
    '/static/js/hieroglyph-pipeline.js',
    '/static/vendor/alpine.min.js',
    '/static/vendor/htmx.min.js',
    '/static/vendor/gsap.min.js',
    '/static/vendor/scrolltrigger.min.js',
    '/static/vendor/lenis.min.js',
    '/static/vendor/atropos.min.js',
];

// ML model files — cached on first use (too large to pre-cache)
const MODEL_PATHS = [
    '/models/hieroglyph/detector/glyph_detector_uint8.onnx',
    '/models/hieroglyph/classifier/hieroglyph_classifier.onnx',
    '/models/hieroglyph/classifier/label_mapping.json',
    '/models/landmark/landmark_classifier_uint8.onnx',
    '/models/landmark/model_metadata.json',
];

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
        return cached || new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain' } });
    }
}

async function staleWhileRevalidate(request, cacheKey, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(cacheKey);
    const fetchPromise = fetch(request).then(response => {
        if (response.ok) cache.put(cacheKey, response.clone());
        return response;
    }).catch(() => cached || new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain' } }));
    return cached || fetchPromise;
}
