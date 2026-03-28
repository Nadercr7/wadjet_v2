# Wadjet v3 Beta — Progress Tracker

## Phase Status

| Phase | Status | Started | Completed | Git Tag | Notes |
|-------|--------|---------|-----------|---------|-------|
| 0 | ✅ DONE | 2026-03-28 | 2026-03-28 | v2-baseline | Copy + git init |
| 1 | ✅ DONE | 2026-03-28 | 2026-03-28 | — | Security hardening |
| 2 | ⬜ TODO | — | — | — | CDN self-host + offline |
| 3 | ⬜ TODO | — | — | — | Database & auth |
| 4 | ⬜ TODO | — | — | — | UX & accessibility |
| 5 | ⬜ TODO | — | — | — | Performance |
| 6 | ⬜ TODO | — | — | — | Arabic i18n |
| 7 | ⬜ TODO | — | — | — | SEO & social |
| 8 | ⬜ TODO | — | — | — | Stories of the Nile |
| 9 | ⬜ TODO | — | — | — | SaaS dashboard |
| 10 | ⬜ TODO | — | — | — | Beta finalize |

## Bug Tracker

### Critical (6)
- [ ] C1: CDN scripts not cached (Phase 2)
- [x] C2: Content-Type bypass (Phase 1)
- [x] C3: Quiz answers client-side (Phase 1)
- [ ] C4: Chat TTS English-only (Phase 4)
- [x] C5: Error message leakage (Phase 1)
- [x] C6: No CSRF protection (Phase 1)

### High (8)
- [ ] H1: /write missing from nav (Phase 4)
- [ ] H2: Browser TTS instead of server TTS (Phase 4)
- [x] H3: Quiz dedup infinite loop (Phase 1)
- [ ] H4: Was Scepter R11→S42 (Phase 4)
- [ ] H5: text-dim WCAG contrast (Phase 4)
- [x] H6: No rate limiting (Phase 1)
- [ ] H7: Glyph of Day only 7 entries (Phase 4)
- [ ] H8: Model cache network-first (Phase 5)

### Medium (18)
- [ ] M1: Zero RTL CSS (Phase 6)
- [ ] M2: Arabic names not rendered (Phase 6)
- [ ] M3: Write English-only examples (Phase 6)
- [ ] M4: No Arabic translations (Phase 6)
- [ ] M5: No OG/Twitter tags (Phase 7)
- [ ] M6: No robots.txt/sitemap (Phase 7)
- [ ] M7: No lazy loading (Phase 5)
- [ ] M8: HTMX no defer (Phase 2)
- [ ] M9: 260 cards load at once (Phase 5)
- [ ] M10: Missing form labels (Phase 4)
- [ ] M11: No SRI on CDN (Phase 2)
- [ ] M12: tts.js not in SW cache (Phase 2)
- [ ] M13: Noto Sans font declared not loaded (Phase 4)
- [x] M14: Deterministic quiz seed (Phase 1)
- [ ] M15: Favicon MIME mismatch (Phase 4)
- [ ] M16: In-memory sessions (Phase 3)
- [ ] M17: No confidence shown (Phase 4)
- [ ] M18: Cache wipes everything (Phase 2)
