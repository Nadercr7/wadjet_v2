# Wadjet v3 Beta — Progress Tracker

## Phase Status

| Phase | Status | Started | Completed | Git Tag | Notes |
|-------|--------|---------|-----------|---------|-------|
| 0 | ✅ DONE | 2026-03-28 | 2026-03-28 | v2-baseline | Copy + git init |
| 1 | ✅ DONE | 2026-03-28 | 2026-03-28 | — | Security hardening |
| 2 | ✅ DONE | 2026-03-28 | 2026-03-28 | — | CDN self-host + offline |
| 3 | ✅ DONE | 2026-03-28 | 2026-03-28 | — | Database & auth |
| 4 | ✅ DONE | 2026-03-28 | 2026-03-28 | — | UX, accessibility & TTS |
| 5 | ✅ DONE | 2026-03-28 | 2026-03-28 | — | Performance |
| 6 | ✅ DONE | 2026-03-28 | 2026-03-28 | — | Arabic i18n |
| 7 | ✅ DONE | 2026-03-28 | 2026-03-28 | — | SEO & social + cross-phase audit |
| 8 | ✅ DONE | 2026-03-28 | 2026-03-28 | 46a7376 | Stories of the Nile — 5 stories, AI images, TTS narration, Ken Burns |
| 9 | ⬜ TODO | — | — | — | SaaS dashboard |
| 10 | ⬜ TODO | — | — | — | Beta finalize |

## Bug Tracker

### Critical (6)
- [x] C1: CDN scripts not cached (Phase 2)
- [x] C2: Content-Type bypass (Phase 1)
- [x] C3: Quiz answers client-side (Phase 1)
- [x] C4: Chat TTS English-only (Phase 4)
- [x] C5: Error message leakage (Phase 1)
- [x] C6: No CSRF protection (Phase 1)

### High (8)
- [x] H1: /write missing from nav (Phase 4)
- [x] H2: Browser TTS instead of server TTS (Phase 4)
- [x] H3: Quiz dedup infinite loop (Phase 1)
- [x] H4: Was Scepter R11→S42 (Phase 4)
- [x] H5: text-dim WCAG contrast (Phase 4)
- [x] H6: No rate limiting (Phase 1)
- [x] H7: Glyph of Day only 7 entries (Phase 4)
- [x] H8: Model cache network-first (Phase 5) ✅

### Medium (18)
- [x] M1: Zero RTL CSS (Phase 6) ✅
- [x] M2: Arabic names not rendered (Phase 6) ✅
- [x] M3: Write English-only examples (Phase 6) ✅
- [x] M4: No Arabic translations (Phase 6) ✅
- [x] M5: No OG/Twitter tags (Phase 7) ✅
- [x] M6: No robots.txt/sitemap (Phase 7) ✅
- [x] M7: No lazy loading (Phase 5)
- [x] M8: HTMX no defer (Phase 2)
- [x] M9: 260 cards load at once (Phase 5)
- [x] M10: Missing form labels (Phase 4)
- [x] M11: No SRI on CDN (Phase 2)
- [x] M12: tts.js not in SW cache (Phase 2)
- [x] M13: Noto Sans font declared not loaded (Phase 4)
- [x] M14: Deterministic quiz seed (Phase 1)
- [x] M15: Favicon MIME mismatch (Phase 4)
- [x] M16: In-memory sessions (Phase 3)
- [x] M17: No confidence shown (Phase 4)
- [x] M18: Cache wipes everything (Phase 2)
