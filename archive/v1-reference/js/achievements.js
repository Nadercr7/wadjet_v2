/**
 * Wadjet AI - Phase 7.10: Achievement / Badge System
 *
 * Global module loaded on every page.  Checks badge conditions
 * against localStorage data and awards new badges automatically.
 *
 * Usage from other scripts:
 *   WadjetAchievements.check();          // re-evaluate all badges
 *   WadjetAchievements.award('id');      // force-award a badge
 *   WadjetAchievements.getAll();         // [{id, name, icon, ...}]
 *   WadjetAchievements.getEarned();      // earned-only subset
 */

/* eslint-disable no-var */
var WadjetAchievements = (function () {
    'use strict';

    var STORAGE_KEY = 'wadjet_achievements';

    // ── Category constants for the 52 classes ────────────────
    var PYRAMIDS = [
        'Great Pyramids of Giza', 'Pyramid of Djoser',
        'Bent Pyramid', 'Red Pyramid'
    ];
    var TEMPLES = [
        'Abu Simbel', 'Abydos Temple', 'Dendera Temple',
        'Edfu Temple', 'Karnak Temple', 'Kom Ombo Temple',
        'Luxor Temple', 'Philae Temple', 'Temple of Hatshepsut'
    ];
    var MOSQUES = [
        'Al-Azhar Mosque', 'Ibn Tulun Mosque',
        'Muhammad Ali Mosque', 'Sultan Hassan Mosque'
    ];

    // ── Badge definitions ────────────────────────────────────
    var BADGES = [
        {
            id: 'first_discovery',
            name: 'First Discovery',
            icon: '\uD83D\uDD0D',
            description: 'Identify your first Egyptian landmark',
            category: 'discovery',
            check: function () { return uniqueDiscoveries() >= 1; }
        },
        {
            id: 'explorer',
            name: 'Explorer',
            icon: '\uD83E\uDDED',
            description: 'Identify 5 different landmarks',
            category: 'discovery',
            check: function () { return uniqueDiscoveries() >= 5; }
        },
        {
            id: 'archaeologist',
            name: 'Archaeologist',
            icon: '\uD83D\uDDFA\uFE0F',
            description: 'Identify 15 different landmarks',
            category: 'discovery',
            check: function () { return uniqueDiscoveries() >= 15; }
        },
        {
            id: 'egyptologist',
            name: 'Egyptologist',
            icon: '\uD83C\uDFDB\uFE0F',
            description: 'Identify 30 different landmarks',
            category: 'discovery',
            check: function () { return uniqueDiscoveries() >= 30; }
        },
        {
            id: 'pyramid_hunter',
            name: 'Pyramid Hunter',
            icon: '\uD83D\uDD3A',
            description: 'Identify all 4 pyramids of Egypt',
            category: 'discovery',
            check: function () { return hasAllOf(PYRAMIDS); }
        },
        {
            id: 'temple_seeker',
            name: 'Temple Seeker',
            icon: '\u26E9\uFE0F',
            description: 'Identify all 9 ancient temples',
            category: 'discovery',
            check: function () { return hasAllOf(TEMPLES); }
        },
        {
            id: 'mosque_explorer',
            name: 'Mosque Explorer',
            icon: '\uD83D\uDD4C',
            description: 'Identify all 4 historic mosques',
            category: 'discovery',
            check: function () { return hasAllOf(MOSQUES); }
        },
        {
            id: 'quiz_apprentice',
            name: 'Quiz Apprentice',
            icon: '\uD83D\uDCDD',
            description: 'Complete your first quiz',
            category: 'knowledge',
            check: function () { return quizCount() >= 1; }
        },
        {
            id: 'quiz_master',
            name: 'Quiz Master',
            icon: '\uD83C\uDF93',
            description: 'Score 80%+ on 3 different quizzes',
            category: 'knowledge',
            check: function () { return quizHighScores() >= 3; }
        },
        {
            id: 'history_buff',
            name: 'History Buff',
            icon: '\uD83D\uDCDC',
            description: 'Explore the Timeline page',
            category: 'knowledge',
            check: function () {
                return !!localStorage.getItem('wadjet_timeline_visited');
            }
        },
        {
            id: 'linguist',
            name: 'Linguist',
            icon: '\uD80C\uDC80',
            description: 'Translate 5 texts to hieroglyphs',
            category: 'knowledge',
            check: function () {
                return getCounter('wadjet_translations') >= 5;
            }
        },
        {
            id: 'collector',
            name: 'Collector',
            icon: '\u2B50',
            description: 'Add 10 landmarks to favorites',
            category: 'collection',
            check: function () {
                try {
                    var f = JSON.parse(localStorage.getItem('wadjet_favorites') || '[]');
                    return f.length >= 10;
                } catch (_) { return false; }
            }
        },
        {
            id: 'night_owl',
            name: 'Night Explorer',
            icon: '\uD83C\uDF19',
            description: 'Switch to dark mode',
            category: 'collection',
            check: function () {
                return localStorage.getItem('wadjet-theme') === 'dark';
            }
        },
        {
            id: 'polyglot',
            name: 'Polyglot',
            icon: '\uD83C\uDF0D',
            description: 'Try a non-English language',
            category: 'collection',
            check: function () {
                var lang = localStorage.getItem('wadjet-lang');
                return lang && lang !== 'en';
            }
        },
        {
            id: 'sharpshooter',
            name: 'Sharpshooter',
            icon: '\uD83C\uDFAF',
            description: 'Get a 90%+ confidence identification',
            category: 'discovery',
            check: function () {
                try {
                    var h = JSON.parse(localStorage.getItem('wadjet_history') || '[]');
                    return h.some(function (e) { return e.confidence >= 0.9; });
                } catch (_) { return false; }
            }
        }
    ];

    // ── Helpers ──────────────────────────────────────────────

    function uniqueDiscoveries() {
        try {
            var h = JSON.parse(localStorage.getItem('wadjet_history') || '[]');
            var names = {};
            h.forEach(function (e) { if (e.class_name) names[e.class_name] = 1; });
            return Object.keys(names).length;
        } catch (_) { return 0; }
    }

    function hasAllOf(list) {
        try {
            var h = JSON.parse(localStorage.getItem('wadjet_history') || '[]');
            var names = {};
            h.forEach(function (e) { if (e.class_name) names[e.class_name] = 1; });
            return list.every(function (n) { return !!names[n]; });
        } catch (_) { return false; }
    }

    function quizCount() {
        return getCounter('wadjet_quiz_completed');
    }

    function quizHighScores() {
        return getCounter('wadjet_quiz_high_scores');
    }

    function getCounter(key) {
        try { return parseInt(localStorage.getItem(key) || '0', 10) || 0; }
        catch (_) { return 0; }
    }

    // ── Storage ─────────────────────────────────────────────

    function loadEarned() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        } catch (_) { return {}; }
    }

    function saveEarned(earned) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(earned)); }
        catch (_) { /* quota */ }
    }

    // ── Toast notification ──────────────────────────────────

    function showToast(badge) {
        var existing = document.getElementById('ach-toast');
        if (existing) existing.remove();

        var toast = document.createElement('div');
        toast.id = 'ach-toast';
        toast.className = 'ach-toast';
        toast.setAttribute('role', 'alert');
        toast.innerHTML =
            '<span class="ach-toast-icon">' + badge.icon + '</span>' +
            '<span class="ach-toast-text">' +
                '<strong>Badge Earned!</strong> ' + badge.name +
            '</span>';
        document.body.appendChild(toast);

        // Trigger CSS transition
        requestAnimationFrame(function () {
            toast.classList.add('ach-toast-visible');
        });

        setTimeout(function () {
            toast.classList.remove('ach-toast-visible');
            setTimeout(function () { toast.remove(); }, 400);
        }, 4000);
    }

    // ── Core ────────────────────────────────────────────────

    function check() {
        var earned = loadEarned();
        var newlyEarned = [];

        BADGES.forEach(function (b) {
            if (earned[b.id]) return;  // already earned
            try {
                if (b.check()) {
                    earned[b.id] = {
                        date: new Date().toISOString(),
                        ts: Date.now()
                    };
                    newlyEarned.push(b);
                }
            } catch (_) { /* skip */ }
        });

        if (newlyEarned.length > 0) {
            saveEarned(earned);

            // Show toasts sequentially
            newlyEarned.forEach(function (b, i) {
                setTimeout(function () { showToast(b); }, i * 4500);
            });

            // Dispatch event for other components
            newlyEarned.forEach(function (b) {
                document.dispatchEvent(new CustomEvent('wadjet:badge-earned', {
                    detail: { badge: b }
                }));
            });
        }

        return newlyEarned;
    }

    function award(id) {
        var earned = loadEarned();
        if (earned[id]) return false;

        var badge = BADGES.find(function (b) { return b.id === id; });
        if (!badge) return false;

        earned[id] = { date: new Date().toISOString(), ts: Date.now() };
        saveEarned(earned);
        showToast(badge);
        document.dispatchEvent(new CustomEvent('wadjet:badge-earned', {
            detail: { badge: badge }
        }));
        return true;
    }

    function getAll() {
        var earned = loadEarned();
        return BADGES.map(function (b) {
            var e = earned[b.id];
            return {
                id: b.id,
                name: b.name,
                icon: b.icon,
                description: b.description,
                category: b.category,
                earned: !!e,
                date: e ? e.date : null
            };
        });
    }

    function getEarned() {
        return getAll().filter(function (b) { return b.earned; });
    }

    function getProgress() {
        var earned = loadEarned();
        var total = BADGES.length;
        var count = Object.keys(earned).length;
        return { earned: count, total: total, pct: Math.round((count / total) * 100) };
    }

    // ── Auto-check on page load ─────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            setTimeout(check, 1500);  // delay so other page JS runs first
        });
    } else {
        setTimeout(check, 1500);
    }

    // ── Track Timeline visit ────────────────────────────────
    if (window.location.pathname === '/timeline') {
        localStorage.setItem('wadjet_timeline_visited', '1');
    }

    console.log('[Wadjet Achievements] Phase 7.10 - module loaded');

    return {
        check: check,
        award: award,
        getAll: getAll,
        getEarned: getEarned,
        getProgress: getProgress,
        BADGES: BADGES
    };
})();
