/**
 * Wadjet AI — Audio Guide Module (Phase 7.6)
 * Browser Web Speech API (SpeechSynthesis) — free, offline-capable.
 *
 * Usage:
 *   WadjetTTS.speak(text, { lang: 'en', rate: 1.0, onStart, onEnd, onError })
 *   WadjetTTS.pause()  /  WadjetTTS.resume()  /  WadjetTTS.stop()
 *   WadjetTTS.isSupported()  /  WadjetTTS.isSpeaking()
 *   WadjetTTS.attachButton(btnEl, textFn, opts)
 */
(function (root) {
  'use strict';

  /* ── Language → BCP-47 voice mapping ───────────────── */
  var LANG_MAP = {
    en: ['en-US', 'en-GB', 'en'],
    ar: ['ar-SA', 'ar-EG', 'ar'],
    fr: ['fr-FR', 'fr'],
    de: ['de-DE', 'de']
  };

  var synth = window.speechSynthesis || null;
  var currentUtterance = null;
  var activeBtn = null;

  /* ── Public API ────────────────────────────────────── */
  var TTS = {};

  /** Check if browser supports Web Speech API */
  TTS.isSupported = function () {
    return !!(synth && typeof SpeechSynthesisUtterance !== 'undefined');
  };

  /** Whether TTS is currently speaking or paused */
  TTS.isSpeaking = function () {
    return synth && (synth.speaking || synth.paused);
  };

  TTS.isPaused = function () {
    return synth && synth.paused;
  };

  /** Get current playback progress (0-1) — approximate */
  TTS.getState = function () {
    if (!synth) return 'idle';
    if (synth.paused) return 'paused';
    if (synth.speaking) return 'playing';
    return 'idle';
  };

  /**
   * Pick the best matching voice for a given language code.
   */
  TTS.pickVoice = function (lang) {
    if (!synth) return null;
    var voices = synth.getVoices();
    if (!voices.length) return null;

    var candidates = LANG_MAP[lang] || LANG_MAP.en;
    // Exact match first (prefer non-Google for naturalness, but any will do)
    for (var c = 0; c < candidates.length; c++) {
      for (var v = 0; v < voices.length; v++) {
        if (voices[v].lang === candidates[c]) return voices[v];
      }
    }
    // Prefix match
    var prefix = (candidates[0] || 'en').split('-')[0];
    for (var i = 0; i < voices.length; i++) {
      if (voices[i].lang.startsWith(prefix)) return voices[i];
    }
    // Fallback to default
    return voices[0] || null;
  };

  /**
   * Speak text aloud.
   * @param {string} text  — plain text to read
   * @param {object} opts  — { lang, rate, pitch, volume, onStart, onEnd, onError }
   */
  TTS.speak = function (text, opts) {
    if (!TTS.isSupported()) {
      if (opts && opts.onError) opts.onError(new Error('TTS not supported'));
      return;
    }
    opts = opts || {};

    // Stop any current speech
    TTS.stop();

    // Clean text: strip markdown-ish, emoji, extra whitespace
    var clean = text
      .replace(/[#*_~`>]/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // [text](url) → text
      .replace(/\s+/g, ' ')
      .trim();

    if (!clean) return;

    var utterance = new SpeechSynthesisUtterance(clean);
    var lang = opts.lang || _getCurrentLang();
    var voice = TTS.pickVoice(lang);
    if (voice) utterance.voice = voice;
    utterance.lang = (voice && voice.lang) || lang;
    utterance.rate = opts.rate || _getSavedRate();
    utterance.pitch = opts.pitch || 1.0;
    utterance.volume = opts.volume || 1.0;

    utterance.onstart = function () {
      if (opts.onStart) opts.onStart();
    };
    utterance.onend = function () {
      currentUtterance = null;
      _setButtonState(activeBtn, 'idle');
      activeBtn = null;
      if (opts.onEnd) opts.onEnd();
    };
    utterance.onerror = function (e) {
      currentUtterance = null;
      _setButtonState(activeBtn, 'idle');
      activeBtn = null;
      if (opts.onError) opts.onError(e);
    };

    currentUtterance = utterance;
    synth.speak(utterance);
  };

  /** Pause speech */
  TTS.pause = function () {
    if (synth && synth.speaking && !synth.paused) {
      synth.pause();
      _setButtonState(activeBtn, 'paused');
    }
  };

  /** Resume speech */
  TTS.resume = function () {
    if (synth && synth.paused) {
      synth.resume();
      _setButtonState(activeBtn, 'playing');
    }
  };

  /** Stop speech */
  TTS.stop = function () {
    if (synth) {
      synth.cancel();
      currentUtterance = null;
      _setButtonState(activeBtn, 'idle');
      activeBtn = null;
    }
  };

  /** Set speech rate (0.5 – 2.0) and persist */
  TTS.setRate = function (rate) {
    rate = Math.max(0.5, Math.min(2.0, parseFloat(rate) || 1.0));
    try { localStorage.setItem('wadjet-tts-rate', rate); } catch (e) { /* */ }
    return rate;
  };

  /**
   * Attach audio-guide behavior to a button element.
   * @param {HTMLElement} btn      — the button element
   * @param {Function}    textFn   — returns the text to speak (called on click)
   * @param {object}      opts     — { lang, rate, onStart, onEnd }
   */
  TTS.attachButton = function (btn, textFn, opts) {
    if (!btn || !TTS.isSupported()) return;
    opts = opts || {};

    btn.addEventListener('click', function () {
      var state = TTS.getState();

      // If this button is currently active
      if (activeBtn === btn) {
        if (state === 'playing') {
          TTS.pause();
          return;
        } else if (state === 'paused') {
          TTS.resume();
          return;
        }
      }

      // Speak new text
      var text = typeof textFn === 'function' ? textFn() : textFn;
      if (!text) return;

      activeBtn = btn;
      _setButtonState(btn, 'playing');

      TTS.speak(text, {
        lang: opts.lang || _getCurrentLang(),
        rate: opts.rate,
        onStart: function () {
          _setButtonState(btn, 'playing');
          if (opts.onStart) opts.onStart();
        },
        onEnd: function () {
          _setButtonState(btn, 'idle');
          if (opts.onEnd) opts.onEnd();
        },
        onError: function () {
          _setButtonState(btn, 'idle');
        }
      });
    });

    // Mark as TTS-enabled
    btn.classList.add('tts-btn');
    btn.setAttribute('aria-label', 'Listen to description');
  };

  /* ── Internals ─────────────────────────────────────── */

  function _getCurrentLang() {
    try { return localStorage.getItem('wadjet-lang') || 'en'; }
    catch (e) { return 'en'; }
  }

  function _getSavedRate() {
    try { return parseFloat(localStorage.getItem('wadjet-tts-rate')) || 1.0; }
    catch (e) { return 1.0; }
  }

  /** Update button icon/class to reflect TTS state */
  function _setButtonState(btn, state) {
    if (!btn) return;
    btn.classList.remove('tts-playing', 'tts-paused');
    var icon = btn.querySelector('.tts-icon');
    if (!icon) return;

    if (state === 'playing') {
      btn.classList.add('tts-playing');
      btn.setAttribute('aria-label', 'Pause audio');
      icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"/>';
    } else if (state === 'paused') {
      btn.classList.add('tts-paused');
      btn.setAttribute('aria-label', 'Resume audio');
      icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>';
    } else {
      btn.setAttribute('aria-label', 'Listen to description');
      icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>';
    }
  }

  /* ── Voice Loading ─────────────────────────────────── */
  // Chrome loads voices async; retry after voiceschanged
  if (synth && synth.onvoiceschanged !== undefined) {
    synth.onvoiceschanged = function () { /* voices now available */ };
  }

  // Chromium bug: long utterances get cut off after ~15s.
  // Workaround: resume every 14s while speaking.
  if (synth) {
    setInterval(function () {
      if (synth.speaking && !synth.paused) {
        synth.pause();
        synth.resume();
      }
    }, 14000);
  }

  /* ── Export ────────────────────────────────────────── */
  root.WadjetTTS = TTS;

})(window);
