# Wadjet v3 Beta — Master Plan

## Phase Overview

| Phase | Name | Bugs Fixed | New Features | Priority |
|-------|------|-----------|--------------|----------|
| **0** | Setup | — | Copy, git, planning | ✅ DONE |
| **1** | Security Hardening | C2,C3,C5,C6,H3,H6,M14 | slowapi, starlette-csrf, magic bytes | CRITICAL |
| **2** | Self-Host CDN + Offline | C1,M8,M11,M12,M18 | vendor/ folder, SW rewrite | CRITICAL |
| **3** | Database & Auth | M16 | SQLite, SQLAlchemy, JWT, user model | HIGH |
| **4** | UX, Accessibility & TTS | C4,H1,H2,H4,H5,H7,M10,M13,M15,M17 | Nav fixes, WCAG, confidence display, **Gemini TTS service**, smart audio fallbacks | HIGH |
| **5** | Performance | H8,M7,M9 | Cache-first models, lazy load, pagination | MEDIUM |
| **6** | Arabic i18n | M1,M2,M3,M4 | RTL, translations, language toggle | MEDIUM |
| **7** | SEO & Social | M5,M6 | OG tags, sitemap, robots.txt, JSON-LD | MEDIUM |
| **8** | Stories of the Nile | — | Quiz replacement, 5 stories, 4 interaction types, **AI-generated illustrations**, **narrative voice** | HIGH |
| **9** | SaaS Dashboard | — | User dashboard, history, progress, favorites | HIGH |
| **10** | v3 Beta Finalize | — | Beta badge, version bump, changelog, full audit, **version replacement option** | FINAL |

**Total**: 32 bugs fixed + 6 major features added + SaaS foundation + AI media services (TTS + image gen)

## AI Provider Stack (All FREE)

| Service | Primary Provider | Fallback | Offline |
|---------|-----------------|----------|---------|
| **TTS (all pages)** | Gemini 2.5 Flash TTS (30 voices, Arabic) | Groq Orpheus (en + ar) | Browser SpeechSynthesis |
| **Image gen (stories)** | Cloudflare FLUX.1 schnell | Cloudflare SDXL | Static placeholders |
| **Chat AI** | Gemini 2.5 Flash | Grok → Groq → Cloudflare | Cached responses |
| **Video** | CSS/Canvas animations on images | — | Same (all client-side) |

> **Smart Defaults**: System auto-selects best available provider. No user-facing choice. See constitution.md for details.

## Dependency Graph

```
Phase 0 (Setup) ──→ Phase 1 (Security) ──→ Phase 2 (Offline)
                                                    │
                                                    ├──→ Phase 3 (DB & Auth) ──→ Phase 9 (Dashboard)
                                                    │                                    │
                                                    ├──→ Phase 4 (UX)                    │
                                                    │                                    │
                                                    ├──→ Phase 5 (Performance)           │
                                                    │                                    │
                                                    ├──→ Phase 6 (Arabic)                │
                                                    │                                    │
                                                    ├──→ Phase 7 (SEO)                   │
                                                    │                                    │
                                                    └──→ Phase 8 (Stories) ──────────────┘
                                                                                         │
                                                                                         ▼
                                                                              Phase 10 (Finalize)
```

Phases 4-8 can run in parallel after Phase 2. Phase 9 depends on Phase 3 (DB) and Phase 8 (Stories). Phase 10 is always last.

## Resources from Repos

| Resource | Path | Usage |
|----------|------|-------|
| FastAPI+SQLAlchemy patterns | `Repos/12-SaaS-Boilerplates/minimal-fastapi-postgres-template/` | DB layer, auth, JWT |
| Atropos source | `Repos/21-Frontend/atropos/` | Self-host latest version |
| Tailwind landing patterns | `Repos/21-Frontend/tailwind-landing-page-template/` | Landing page reference |
| spec-kit format | `Repos/spec-kit/` | Planning structure inspiration |
| ONNX reference | `Repos/onnx/` | Model optimization reference |

## Bonus Improvements (Can Be Added During Any Phase)

These are additional improvements beyond the original analysis. They are not required for beta but significantly elevate the product:

| Improvement | Phase to Add | Effort | Impact |
|-------------|-------------|--------|--------|
| **PWA install prompt** (manifest.json + install banner) | Phase 2 (Offline) | Low | High — mobile users can install |
| **Web Share API** — share scan results, stories, glyphs | Phase 7 (SEO) | Low | Medium — viral growth |
| **Skeleton loading screens** — instead of spinners | Phase 5 (Perf) | Low | High — perceived speed |
| **Content preloading** — preload next story chapter | Phase 8 (Stories) | Low | Medium — seamless reading |
| **Keyboard shortcuts** — Ctrl+K search, Space toggle TTS | Phase 4 (UX) | Low | Medium — power users |
| **Auto-save drafts** — Write page drafts in localStorage | Phase 4 (UX) | Low | Medium — users don't lose work |
| **Gamification badges** — "Decoded 100 glyphs" etc. | Phase 9 (Dashboard) | Medium | High — retention |
| **Print stylesheet** — dictionary and scan results | Phase 4 (UX) | Low | Low — niche but professional |
| **Haptic feedback** — vibration on story interactions | Phase 8 (Stories) | Low | Low — mobile polish |
| **Ambient audio** — Egyptian background music for stories | Phase 8 (Stories) | Low | Medium — immersion |

## Git Strategy

- Each phase = 1 commit minimum, tagged `phase-N`
- Commit message format: `[Phase N] Brief description`
- Branch: `main` (single developer, no PRs needed for beta)
- Baseline tag: `v2-baseline` (already committed)

## Version Replacement (Post-Completion)

After all phases complete and v3 beta is stable:
1. Archive original `Wadjet/` → `Wadjet-v2-archive/`
2. Copy `Wadjet-v3-beta/` → `Wadjet/` (or rename)
3. Update HuggingFace Spaces deployment
4. Update GitHub repo
5. This is optional — user chooses when/if to replace
