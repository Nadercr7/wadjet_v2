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
// and auto-refresh auth token on 401 responses
const _originalFetch = window.fetch;
let _refreshingToken = null;
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
    return _originalFetch.call(this, input, init).then(function(response) {
        // Auto-refresh token on 401 (except for auth endpoints themselves)
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        if (response.status === 401 && !url.includes('/api/auth/')) {
            // Single refresh request shared across all concurrent 401s
            if (!_refreshingToken) {
                _refreshingToken = _originalFetch.call(window, '/api/auth/refresh', { method: 'POST' })
                    .then(function(r) {
                        if (r.ok) return r.json();
                        throw new Error('refresh failed');
                    })
                    .then(function(data) {
                        if (typeof Alpine !== 'undefined' && Alpine.store('auth')) {
                            Alpine.store('auth').token = data.access_token;
                            Alpine.store('auth')._save();
                        }
                    })
                    .catch(function() {
                        if (typeof Alpine !== 'undefined' && Alpine.store('auth')) {
                            Alpine.store('auth').logout();
                        }
                        throw new Error('refresh failed');
                    })
                    .finally(function() {
                        _refreshingToken = null;
                    });
            }
            // Each caller waits for refresh, then retries its own request
            return _refreshingToken.then(function() {
                return _originalFetch.call(window, input, init);
            }).catch(function() {
                return response;
            });
        }
        return response;
    });
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
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.querySelectorAll('[data-animate]').forEach(el => el.style.opacity = '1');
        } else {
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
        showForgotPassword: false,
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

        _getNextUrl() {
            const params = new URLSearchParams(window.location.search);
            const next = params.get('next') || '';
            if (next && next.startsWith('/')
                && !next.startsWith('//')
                && !next.startsWith('/\\')
                && !next.includes('@')
                && !next.includes('\n')
                && !next.includes('\r')
                && !next.includes('%0a')
                && !next.includes('%0d')
                && !next.includes('%0A')
                && !next.includes('%0D')) {
                return next;
            }
            return '/';
        },

        async logout() {
            try { await fetch('/api/auth/logout', { method: 'POST' }); } catch { /* best-effort */ }
            this.user = null;
            this.token = null;
            this._save();
            document.cookie = 'wadjet_session=;path=/;max-age=0';
            Alpine.store('toast').show((window.__i18n && window.__i18n.auth_signed_out) || 'Signed out', 'info');
            window.location.href = '/welcome';
        },

        async refreshToken() {
            try {
                const r = await fetch('/api/auth/refresh', { method: 'POST' });
                if (!r.ok) { this.logout(); return null; }
                const data = await r.json();
                this.token = data.access_token;
                this._save();
                return this.token;
            } catch { this.logout(); return null; }
        },

        async _authFetch(url, options) {
            const headers = { ...(options?.headers || {}), 'Authorization': 'Bearer ' + this.token };
            let res = await fetch(url, { ...options, headers });
            if (res.status === 401) {
                const newToken = await this.refreshToken();
                if (newToken) {
                    headers['Authorization'] = 'Bearer ' + newToken;
                    res = await fetch(url, { ...options, headers });
                }
            }
            return res;
        },

        async googleSignIn() {
            if (typeof google === 'undefined' || !google.accounts) {
                this.error = 'Google Sign-In not available';
                return;
            }
            const self = this;
            google.accounts.id.initialize({
                client_id: document.querySelector('meta[name="google-client-id"]')?.content || '',
                callback: function(response) {
                    self._handleGoogleCredential(response.credential);
                },
            });
            google.accounts.id.prompt();
        },

        async _handleGoogleCredential(credential) {
            this.loading = true;
            this.error = '';
            try {
                const r = await fetch('/api/auth/google', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ credential }),
                });
                const data = await r.json();
                if (!r.ok) {
                    this.error = data.detail || 'Google sign-in failed';
                    return;
                }
                this.user = data.user;
                this.token = data.access_token;
                this._save();
                document.cookie = 'wadjet_session=1;path=/;SameSite=Lax;max-age=' + (60*60*24*30) + (location.protocol === 'https:' ? ';Secure' : '');
                this.showLogin = false;
                this.showSignup = false;
                Alpine.store('toast').show((window.__i18n && window.__i18n.auth_welcome_back) || 'Welcome!', 'success');
                window.location.href = this._getNextUrl();
            } catch { this.error = (window.__i18n && window.__i18n.auth_network) || 'Network error'; }
            finally { this.loading = false; }
        },

    });
});

// ── TTS for hieroglyphic pronunciation ──
// Uses the smart TTS chain: Gemini (multi-key, disk cache) → Groq → browser.
const _ttsAudioCache = {};
const _ttsCacheKeys = []; // track insertion order for eviction
const _TTS_CACHE_MAX = 50;
let _ttsCurrentAudio = null;

function speakSign(text, btnEl) {
    if (!text) return;
    // Stop any playing audio
    if (_ttsCurrentAudio) {
        _ttsCurrentAudio.pause();
        _ttsCurrentAudio = null;
    }
    if (typeof WadjetTTS !== 'undefined') WadjetTTS.stop();

    // Show loading state on the clicked button
    if (btnEl) { btnEl.classList.add('animate-pulse', 'opacity-50'); btnEl.disabled = true; }
    const _done = () => { if (btnEl) { btnEl.classList.remove('animate-pulse', 'opacity-50'); btnEl.disabled = false; } };

    // Try in-memory JS cache first (instant replay)
    const cacheKey = text.trim().toLowerCase();
    if (_ttsAudioCache[cacheKey]) {
        _playAudio(_ttsAudioCache[cacheKey], text);
        _done();
        return;
    }

    // Smart TTS chain: Gemini (multi-key pool, disk cached) → Groq → 204
    fetch('/api/audio/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, lang: 'en', context: 'pronunciation' })
    }).then(r => {
        if (!r.ok || r.status === 204) throw new Error('TTS unavailable');
        return r.blob();
    }).then(blob => {
        const audioUrl = URL.createObjectURL(blob);
        // Evict oldest blob URLs when cache exceeds limit
        if (_ttsCacheKeys.length >= _TTS_CACHE_MAX) {
            const oldest = _ttsCacheKeys.shift();
            if (_ttsAudioCache[oldest]) {
                URL.revokeObjectURL(_ttsAudioCache[oldest]);
                delete _ttsAudioCache[oldest];
            }
        }
        _ttsAudioCache[cacheKey] = audioUrl;
        _ttsCacheKeys.push(cacheKey);
        _playAudio(audioUrl, text);
        _done();
    }).catch(() => {
        // Last resort: browser SpeechSynthesis (voice-selected, slow for clarity)
        if (typeof WadjetTTS !== 'undefined' && WadjetTTS.isSupported()) {
            WadjetTTS.speak(text, { lang: 'en', rate: 0.75 });
        }
        _done();
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

// ── Focus Trap Utility (WCAG 2.1 AA) ──
window.createFocusTrap = function(container) {
    const FOCUSABLE = 'a[href], button:not(:disabled), input, select, textarea, [tabindex]:not([tabindex="-1"])';
    let _handler = null;

    function _getFocusable() {
        return Array.from(container.querySelectorAll(FOCUSABLE)).filter(el => el.offsetParent !== null);
    }

    function _onKeydown(e) {
        if (e.key !== 'Tab') return;
        const focusable = _getFocusable();
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
            if (document.activeElement === first) { e.preventDefault(); last.focus(); }
        } else {
            if (document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
    }

    return {
        activate() { _handler = _onKeydown; container.addEventListener('keydown', _handler); },
        deactivate() { if (_handler) { container.removeEventListener('keydown', _handler); _handler = null; } }
    };
};
