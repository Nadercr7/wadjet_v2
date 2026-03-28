/**
 * Wadjet v3 — App JS
 * Global Alpine.js components, HTMX config, Atropos, GSAP, Lenis
 */

// ── CSRF token helper (reads starlette-csrf cookie) ──
function _getCsrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : '';
}

// Patch global fetch to auto-include CSRF token on mutating requests
const _originalFetch = window.fetch;
window.fetch = function(input, init) {
    init = init || {};
    const method = (init.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
        init.headers = init.headers || {};
        // Support both Headers object and plain object
        if (init.headers instanceof Headers) {
            if (!init.headers.has('x-csrftoken')) {
                init.headers.set('x-csrftoken', _getCsrfToken());
            }
        } else {
            if (!init.headers['x-csrftoken']) {
                init.headers['x-csrftoken'] = _getCsrfToken();
            }
        }
    }
    return _originalFetch.call(this, input, init);
};

// HTMX: include CSRF token on every request
document.addEventListener('htmx:configRequest', function(e) {
    e.detail.headers['x-csrftoken'] = _getCsrfToken();
});

// ── Service Worker registration ──
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js', { scope: '/' })
            .catch(() => { /* SW registration failed — non-critical */ });
    });
}

// ── Page loading progress bar ──
const _loader = {
    el: null,
    _get() { return this.el || (this.el = document.getElementById('page-loader')); },
    start() { const e = this._get(); if (e) { e.style.width = '0%'; e.offsetWidth; e.style.width = '70%'; } },
    finish() { const e = this._get(); if (e) { e.style.width = '100%'; setTimeout(() => { e.style.width = '0%'; }, 300); } },
};

// HTMX: add loading indicator class on requests
document.addEventListener('htmx:beforeRequest', function () {
    document.body.classList.add('htmx-loading');
    _loader.start();
});
document.addEventListener('htmx:afterRequest', function () {
    document.body.classList.remove('htmx-loading');
    _loader.finish();
});

// Page transition: loading bar on regular navigation
document.addEventListener('click', function (e) {
    const a = e.target.closest('a[href]');
    if (!a || a.target === '_blank' || a.href.startsWith('#') || a.href.startsWith('javascript:')
        || a.hasAttribute('download') || e.metaKey || e.ctrlKey) return;
    const url = new URL(a.href, location.origin);
    if (url.origin === location.origin && url.pathname !== location.pathname) {
        _loader.start();
    }
});
window.addEventListener('pageshow', function () { _loader.finish(); });

// Lenis smooth scroll
document.addEventListener('DOMContentLoaded', function () {
    if (typeof Lenis !== 'undefined') {
        const lenis = new Lenis({ duration: 1.2, easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)) });
        function raf(time) { lenis.raf(time); requestAnimationFrame(raf); }
        requestAnimationFrame(raf);

        // Sync Lenis with GSAP ScrollTrigger
        if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
            gsap.registerPlugin(ScrollTrigger);
            lenis.on('scroll', ScrollTrigger.update);
            gsap.ticker.add((time) => lenis.raf(time * 1000));
            gsap.ticker.lagSmoothing(0);
        }
    }

    // Atropos: auto-init all [data-atropos] elements
    if (typeof Atropos !== 'undefined') {
        document.querySelectorAll('[data-atropos]').forEach(function (el) {
            Atropos({
                el: el,
                rotateXMax: 10,
                rotateYMax: 10,
                shadow: true,
                highlight: true,
                duration: 400,
            });
        });
    }

    // GSAP: auto-animate all [data-animate] elements on scroll
    if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
        gsap.utils.toArray('[data-animate]').forEach(function (el) {
            gsap.from(el, {
                y: 40,
                opacity: 0,
                duration: 0.8,
                ease: 'power2.out',
                scrollTrigger: {
                    trigger: el,
                    start: 'top 85%',
                    toggleActions: 'play none none none',
                },
            });
        });
    }
});

// ── WadjetHistory: localStorage history manager ──
const WadjetHistory = {
    MAX_ITEMS: 20,
    MAX_THUMB_PX: 120,

    _get(key) {
        try { return JSON.parse(localStorage.getItem(key)) || []; }
        catch { return []; }
    },
    _set(key, items) {
        try { localStorage.setItem(key, JSON.stringify(items.slice(0, this.MAX_ITEMS))); }
        catch { /* quota exceeded — silently fail */ }
    },
    _push(key, entry) {
        const items = this._get(key);
        items.unshift({ ...entry, timestamp: Date.now() });
        this._set(key, items);
    },
    _remove(key, timestamp) {
        this._set(key, this._get(key).filter(i => i.timestamp !== timestamp));
    },
    _clear(key) { localStorage.removeItem(key); },

    // Resize image to small thumbnail data URL
    fileToThumb(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    const s = Math.min(this.MAX_THUMB_PX / Math.max(img.width, img.height), 1);
                    const c = document.createElement('canvas');
                    c.width = img.width * s; c.height = img.height * s;
                    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
                    resolve(c.toDataURL('image/jpeg', 0.6));
                };
                img.onerror = () => resolve(null);
                img.src = e.target.result;
            };
            reader.onerror = () => resolve(null);
            reader.readAsDataURL(file);
        });
    },

    // Scan history
    getScanHistory()  { return this._get('wadjet_scan_history'); },
    clearScanHistory() { this._clear('wadjet_scan_history'); },
    removeScanItem(ts) { this._remove('wadjet_scan_history', ts); },
    async addScan(file, result) {
        const thumb = file ? await this.fileToThumb(file) : null;
        this._push('wadjet_scan_history', {
            thumb,
            numGlyphs: result.num_detections || 0,
            transliteration: result.transliteration || '',
            gardiner: result.gardiner_sequence || '',
            glyphs: (result.glyphs || []).slice(0, 6).map(g => ({
                code: g.gardiner_code, conf: Math.round((g.class_confidence || 0) * 100)
            })),
        });
    },

    // Write history
    getWriteHistory()  { return this._get('wadjet_write_history'); },
    clearWriteHistory() { this._clear('wadjet_write_history'); },
    removeWriteItem(ts) { this._remove('wadjet_write_history', ts); },
    addWrite(inputText, mode, result) {
        this._push('wadjet_write_history', {
            input: inputText.slice(0, 200),
            mode,
            hieroglyphs: result.hieroglyphs || '',
            numGlyphs: (result.glyphs || []).length,
        });
    },

    // Chat history (saves conversations)
    getChatHistory()  { return this._get('wadjet_chat_history'); },
    clearChatHistory() { this._clear('wadjet_chat_history'); },
    removeChatItem(ts) { this._remove('wadjet_chat_history', ts); },
    addChat(messages) {
        if (!messages || messages.length < 2) return;
        const first = messages.find(m => m.role === 'user');
        this._push('wadjet_chat_history', {
            preview: first ? first.content.slice(0, 100) : 'Conversation',
            messageCount: messages.length,
            messages: messages.slice(0, 20), // cap stored messages
        });
    },
};

// Simple toast notification system
document.addEventListener('alpine:init', () => {
    Alpine.store('toast', {
        message: '',
        type: 'info', // info | success | error
        visible: false,

        show(message, type = 'info', duration = 3000) {
            this.message = message;
            this.type = type;
            this.visible = true;
            setTimeout(() => { this.visible = false; }, duration);
        }
    });

    // ── Auth store ──
    Alpine.store('auth', {
        user: null,
        token: null,
        showLogin: false,
        showSignup: false,
        loading: false,
        error: '',

        init() {
            // Restore from localStorage on page load
            const stored = localStorage.getItem('wadjet_auth');
            if (stored) {
                try {
                    const data = JSON.parse(stored);
                    this.user = data.user;
                    this.token = data.token;
                } catch { /* corrupt data */ }
            }
        },

        _save() {
            if (this.user && this.token) {
                localStorage.setItem('wadjet_auth', JSON.stringify({ user: this.user, token: this.token }));
            } else {
                localStorage.removeItem('wadjet_auth');
            }
        },

        async register(email, password, displayName) {
            this.loading = true;
            this.error = '';
            try {
                const r = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, display_name: displayName || null }),
                });
                const data = await r.json();
                if (!r.ok) { this.error = data.detail || 'Registration failed'; return false; }
                this.user = data.user;
                this.token = data.access_token;
                this._save();
                this.showSignup = false;
                Alpine.store('toast').show('Welcome to Wadjet!', 'success');
                // Redirect to dashboard if on landing, otherwise reload to refresh auth-gated content
                if (window.location.pathname === '/') {
                    window.location.href = '/dashboard';
                } else {
                    window.location.reload();
                }
                return true;
            } catch { this.error = 'Network error'; return false; }
            finally { this.loading = false; }
        },

        async login(email, password) {
            this.loading = true;
            this.error = '';
            try {
                const r = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password }),
                });
                const data = await r.json();
                if (!r.ok) { this.error = data.detail || 'Login failed'; return false; }
                this.user = data.user;
                this.token = data.access_token;
                this._save();
                this.showLogin = false;
                Alpine.store('toast').show('Welcome back!', 'success');
                // Redirect to dashboard if on landing, otherwise reload to refresh auth-gated content
                if (window.location.pathname === '/') {
                    window.location.href = '/dashboard';
                } else {
                    window.location.reload();
                }
                return true;
            } catch { this.error = 'Network error'; return false; }
            finally { this.loading = false; }
        },

        async logout() {
            try { await fetch('/api/auth/logout', { method: 'POST' }); } catch { /* best-effort */ }
            this.user = null;
            this.token = null;
            this._save();
            Alpine.store('toast').show('Signed out', 'info');
        },

        async refreshToken() {
            try {
                const r = await fetch('/api/auth/refresh', { method: 'POST' });
                if (!r.ok) { this.logout(); return; }
                const data = await r.json();
                this.token = data.access_token;
                this._save();
            } catch { this.logout(); }
        },
    });
});

// ── TTS for hieroglyphic pronunciation ──
// Delegates to WadjetTTS module (tts.js), with server audio fallback for dictionary.
const _ttsAudioCache = {};
let _ttsCurrentAudio = null;

function speakSign(text) {
    if (!text) return;
    // Stop any playing audio
    if (_ttsCurrentAudio) {
        _ttsCurrentAudio.pause();
        _ttsCurrentAudio = null;
    }
    if (typeof WadjetTTS !== 'undefined') WadjetTTS.stop();

    // Try server TTS (Gemini natural voice) for dictionary pronunciation
    const cacheKey = text.trim().toLowerCase();
    if (_ttsAudioCache[cacheKey]) {
        _playAudio(_ttsAudioCache[cacheKey], text);
        return;
    }

    const url = '/api/dictionary/speak?text=' + encodeURIComponent(text);
    fetch(url).then(r => {
        if (!r.ok) throw new Error('TTS unavailable');
        return r.blob();
    }).then(blob => {
        const audioUrl = URL.createObjectURL(blob);
        _ttsAudioCache[cacheKey] = audioUrl;
        _playAudio(audioUrl, text);
    }).catch(() => {
        // Fallback: WadjetTTS module (Web Speech API)
        if (typeof WadjetTTS !== 'undefined' && WadjetTTS.isSupported()) {
            WadjetTTS.speak(text, { lang: 'en', rate: 0.75 });
        }
    });
}

function _playAudio(url, fallbackText) {
    const audio = new Audio(url);
    audio.volume = 1.0;
    _ttsCurrentAudio = audio;
    audio.play().catch(() => {
        if (fallbackText && typeof WadjetTTS !== 'undefined' && WadjetTTS.isSupported()) {
            WadjetTTS.speak(fallbackText, { lang: 'en', rate: 0.75 });
        }
    });
}
