/**
 * Wadjet v3 — TTS Module
 * Browser Web Speech API (SpeechSynthesis) — free, offline-capable.
 * Fallback for server TTS (Gemini → Groq). Used by Alpine.js integration.
 *
 * Usage:
 *   WadjetTTS.speak(text, { lang: 'en', rate: 1.0, onEnd })
 *   WadjetTTS.pause()  /  WadjetTTS.resume()  /  WadjetTTS.stop()
 *   WadjetTTS.isSupported()  /  WadjetTTS.getState()
 *   WadjetTTS.speakToggle(text, opts) — toggle play/pause for Alpine buttons
 */
(function (root) {
    'use strict';

    /* ── Language → BCP-47 voice mapping ───────────────── */
    const LANG_MAP = {
        en: ['en-US', 'en-GB', 'en'],
        ar: ['ar-SA', 'ar-EG', 'ar'],
        fr: ['fr-FR', 'fr'],
        de: ['de-DE', 'de'],
    };

    const synth = window.speechSynthesis || null;
    let currentUtterance = null;
    let activeId = null; // tracks which Alpine button is active

    const TTS = {};

    /* ── State queries ───────────────────────────────── */

    TTS.isSupported = function () {
        return !!(synth && typeof SpeechSynthesisUtterance !== 'undefined');
    };

    TTS.isSpeaking = function () {
        return synth && (synth.speaking || synth.paused);
    };

    TTS.isPaused = function () {
        return synth && synth.paused;
    };

    /** 'idle' | 'playing' | 'paused' */
    TTS.getState = function () {
        if (!synth) return 'idle';
        if (synth.paused) return 'paused';
        if (synth.speaking) return 'playing';
        return 'idle';
    };

    /** ID of the currently active Alpine button (for multi-button pages) */
    TTS.getActiveId = function () {
        return activeId;
    };

    /* ── Voice selection ─────────────────────────────── */

    TTS.pickVoice = function (lang) {
        if (!synth) return null;
        const voices = synth.getVoices();
        if (!voices.length) return null;

        const candidates = LANG_MAP[lang] || LANG_MAP.en;

        // Prefer high-quality voices (Google, Neural, Natural, Premium)
        for (const tag of candidates) {
            const premium = voices.find(
                (v) => v.lang === tag && /google|neural|natural|premium/i.test(v.name)
            );
            if (premium) return premium;
        }
        // Exact match
        for (const tag of candidates) {
            const match = voices.find((v) => v.lang === tag);
            if (match) return match;
        }
        // Prefix match
        const prefix = (candidates[0] || 'en').split('-')[0];
        const prefixMatch = voices.find((v) => v.lang.startsWith(prefix));
        if (prefixMatch) return prefixMatch;

        return voices[0] || null;
    };

    /* ── Core speak / control ────────────────────────── */

    /**
     * Speak text aloud.
     * @param {string} text
     * @param {object} opts — { lang, rate, pitch, volume, id, onStart, onEnd, onError }
     */
    TTS.speak = function (text, opts) {
        if (!TTS.isSupported()) {
            if (opts && opts.onError) opts.onError(new Error('TTS not supported'));
            return;
        }
        opts = opts || {};
        TTS.stop();

        // Clean text: strip markdown, emoji, extra whitespace
        const clean = text
            .replace(/[#*_~`>]/g, '')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
            .replace(/\s+/g, ' ')
            .trim();
        if (!clean) return;

        const utterance = new SpeechSynthesisUtterance(clean);
        const lang = opts.lang || _getCurrentLang();
        const voice = TTS.pickVoice(lang);
        if (voice) utterance.voice = voice;
        utterance.lang = (voice && voice.lang) || lang;
        utterance.rate = opts.rate || _getSavedRate();
        utterance.pitch = opts.pitch || 1.0;
        utterance.volume = opts.volume || 1.0;

        activeId = opts.id || null;

        utterance.onstart = function () {
            if (opts.onStart) opts.onStart();
        };
        utterance.onend = function () {
            currentUtterance = null;
            activeId = null;
            if (opts.onEnd) opts.onEnd();
        };
        utterance.onerror = function (e) {
            currentUtterance = null;
            activeId = null;
            if (opts.onError) opts.onError(e);
        };

        currentUtterance = utterance;
        synth.speak(utterance);
    };

    TTS.pause = function () {
        if (_serverAudio && !_serverAudio.paused) {
            _serverAudio.pause();
        } else if (synth && synth.speaking && !synth.paused) {
            synth.pause();
        }
    };

    TTS.resume = function () {
        if (_serverAudio && _serverAudio.paused) {
            _serverAudio.play().catch(function () {});
        } else if (synth && synth.paused) {
            synth.resume();
        }
    };

    TTS.stop = function () {
        if (synth) {
            synth.cancel();
            currentUtterance = null;
            activeId = null;
        }
        if (_serverAudio) {
            _serverAudio.pause();
            _serverAudio = null;
        }
    };

    /* ── Server TTS (Groq PlayAI) ───────────────────── */

    /** Audio element for server TTS playback */
    let _serverAudio = null;

    /**
     * Try server TTS first (higher quality), fall back to Web Speech API.
     * @param {string} text
     * @param {object} opts — { lang, rate, id, onEnd }
     */
    TTS.speakWithServer = function (text, opts) {
        opts = opts || {};
        TTS.stop();

        if (!text || !text.trim()) return;
        activeId = opts.id || null;

        var lang = opts.lang || _getCurrentLang();

        fetch('/api/audio/speak', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text.trim(), lang: lang, context: 'narration' })
        })
            .then(function (r) {
                if (!r.ok) throw new Error('Server TTS unavailable');
                return r.blob();
            })
            .then(function (blob) {
                var blobUrl = URL.createObjectURL(blob);
                _serverAudio = new Audio(blobUrl);
                _serverAudio.volume = 1.0;
                _serverAudio.onended = function () {
                    URL.revokeObjectURL(blobUrl);
                    _serverAudio = null;
                    activeId = null;
                    if (opts.onEnd) opts.onEnd();
                };
                _serverAudio.onerror = function () {
                    URL.revokeObjectURL(blobUrl);
                    _serverAudio = null;
                    activeId = null;
                };
                _serverAudio.play().catch(function () {
                    URL.revokeObjectURL(blobUrl);
                    // Audio play failed — fall back to Web Speech
                    TTS.speak(text, opts);
                });
            })
            .catch(function () {
                // Server unavailable — fall back to Web Speech API
                TTS.speak(text, opts);
            });
    };

    /* ── Alpine-friendly toggle ──────────────────────── */

    /**
     * Toggle play/pause for a given text+id combo (Alpine button integration).
     * Returns new state: 'playing' | 'paused' | 'idle'
     * @param {string} text
     * @param {object} opts — { lang, rate, id }
     */
    TTS.speakToggle = function (text, opts) {
        opts = opts || {};
        const state = TTS.getState();

        // If same button is active — toggle pause/resume
        if (activeId && opts.id && activeId === opts.id) {
            if (state === 'playing') {
                TTS.pause();
                return 'paused';
            }
            if (state === 'paused') {
                TTS.resume();
                return 'playing';
            }
        }

        // New speech
        if (!text) return 'idle';
        TTS.speak(text, opts);
        return 'playing';
    };

    /* ── Rate persistence ────────────────────────────── */

    TTS.setRate = function (rate) {
        rate = Math.max(0.5, Math.min(2.0, parseFloat(rate) || 1.0));
        try { localStorage.setItem('wadjet-tts-rate', String(rate)); } catch (e) { /* */ }
        return rate;
    };

    TTS.getRate = function () {
        return _getSavedRate();
    };

    /* ── Internals ───────────────────────────────────── */

    function _getCurrentLang() {
        // Read from wadjet_lang cookie (set by nav.html toggleLang)
        try {
            var m = document.cookie.match(/(?:^|;\s*)wadjet_lang=([^;]*)/);
            return m ? decodeURIComponent(m[1]) : (document.documentElement.lang || 'en');
        } catch (e) { return 'en'; }
    }

    function _getSavedRate() {
        try { return parseFloat(localStorage.getItem('wadjet-tts-rate')) || 1.0; } catch (e) { return 1.0; }
    }

    /* ── Voice loading (Chrome loads async) ──────────── */
    if (synth && synth.onvoiceschanged !== undefined) {
        synth.onvoiceschanged = function () { /* voices now available */ };
    }

    /* ── Chromium workaround: long utterances cut off after ~15s ── */
    if (synth) {
        setInterval(function () {
            if (synth.speaking && !synth.paused) {
                synth.pause();
                synth.resume();
            }
        }, 14000);
    }

    /* ── Export ───────────────────────────────────────── */
    root.WadjetTTS = TTS;

})(window);
