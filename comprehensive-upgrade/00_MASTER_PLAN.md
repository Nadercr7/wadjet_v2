# WADJET — COMPREHENSIVE UPGRADE MASTER PLAN

> Version: 1.0 | Date: 2026-03-30 | Status: PLANNING  
> Author: Nader Mohamed + AI Architecture Team

---

## Executive Summary

Wadjet v3-beta is being promoted to production as the official live version, replacing
the current v2 deployed on HuggingFace Spaces. Alongside promotion, 7 additional
requirements are being implemented: Google OAuth + Resend email, a new serpent-W
logo, animated loading screen, stories enrichment with real Egyptian history,
scan pipeline upgrade with TTS, comprehensive security audit, and technical debt fixes.

**Total scope**: 8 requirements across 8 phases.

---

## Requirements Summary

| ID | Requirement | Category | Size | Priority |
|----|------------|----------|------|----------|
| REQ-1 | Version Promotion (v3-beta → production) | Infrastructure | M | P1 — after auth+scan+stories |
| REQ-2 | Google OAuth + Resend Email Integration | Infrastructure | L | P0 — foundational |
| REQ-3 | New Logo (W-as-Serpent, big brand quality) | Design | M | P2 — post-promotion |
| REQ-4 | Animated Loading Screen (logo-driven) | Design | M | P2 — requires logo |
| REQ-5 | Stories Enrichment (real history + smart images) | Feature | L | P1 — pre-promotion |
| REQ-6 | Scan Pipeline Full Upgrade + TTS | Feature | L | P1 — core feature |
| REQ-7 | Security Comprehensive Check | Security | S | P0 — first |
| REQ-8 | Additional Recommendations & Fixes | Polish | S | P2 — final |

---

## Dependency Graph

```
Phase 1: Security Audit ──────────────────────────────────────────────┐
    │                                                                  │
    ▼                                                                  │
Phase 2: Google OAuth + Resend ────┐                                   │
    │                              │                                   │
    ▼                              ▼                                   │
Phase 3: Scan Pipeline        Phase 4: Stories Enrichment              │
    │  + TTS Audio                 │  + Smart Images                   │
    │                              │                                   │
    ├──────────────────────────────┤                                   │
    ▼                              ▼                                   │
Phase 5: Version Promotion ◄───────────────────────────────────────────┘
    │   (v3 → live on HF Space)
    │
    ▼
Phase 6: New Logo (W-as-Serpent)
    │
    ▼
Phase 7: Animated Loading Screen
    │
    ▼
Phase 8: Polish + Additional Fixes
```

### Hard Dependencies

| Dependency | Reason |
|-----------|--------|
| Security Audit → everything | Must understand attack surface before adding OAuth |
| OAuth → Promotion | Users will create accounts on live site |
| Scan fixes → Promotion | Core value proposition must work |
| Logo → Loading Animation | Animation uses the logo as its centerpiece |
| Promotion → Logo/Loading | Visual polish ships as post-launch update |

### Parallelizable

- Phase 3 (Scan) and Phase 4 (Stories) can run in parallel after Phase 2
- Phase 6 (Logo) design exploration can start during Phase 5

---

## Recommended Phase Sequence

| Order | Phase | REQ | Effort | Start Condition |
|-------|-------|-----|--------|----------------|
| 1 | Security Audit | REQ-7 | S (1 session) | All credentials verified |
| 2 | Google OAuth + Resend | REQ-2 | L (2-3 sessions) | GOOGLE_CLIENT_SECRET obtained |
| 3 | Scan Pipeline Upgrade | REQ-6 | L (2-3 sessions) | Phase 2 committed |
| 4 | Stories Enrichment | REQ-5 | L (2-3 sessions) | Phase 2 committed |
| 5 | Version Promotion | REQ-1 | M (1-2 sessions) | Phases 1-4 complete |
| 6 | New Logo | REQ-3 | M (1-2 sessions) | Phase 5 complete |
| 7 | Animated Loading | REQ-4 | M (1-2 sessions) | Phase 6 complete |
| 8 | Polish + Fixes | REQ-8 | S (1 session) | Phase 7 complete |

---

## Risk Register — Top 10

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|-----------|------------|
| 1 | `GOOGLE_CLIENT_SECRET` missing from `.env` | OAuth cannot function | Certain | User must retrieve from Google Cloud Console |
| 2 | SQLite ephemeral on HF Space (wiped on rebuild) | All user data lost | Certain | Option A: PostgreSQL (Supabase). Option B: Accept for MVP, add later |
| 3 | HF Space Dockerfile uses port 8000, HF expects 7860 | Deployment fails | High | Update Dockerfile EXPOSE + CMD |
| 4 | JWT_SECRET auto-generated on restart | Sessions invalidated per deploy | Certain | Set fixed value in HF Space env vars |
| 5 | v3-beta has NO git remotes | Cannot push to GitHub/HF | Certain | Add origin + hf remotes in Phase 5 |
| 6 | Old HF token embedded in old Wadjet `.git/config` | Token leak if repo goes public | Medium | Rotate token after promotion |
| 7 | No Resend sending domain verified | Emails go to spam or fail | High | Verify domain or use `onboarding@resend.dev` for testing |
| 8 | Google OAuth redirect URI mismatch | OAuth flow breaks | High | Configure exact URI in Google Cloud Console |
| 9 | User model has no OAuth columns | DB migration needed before OAuth | Certain | Create Alembic migration as first OAuth step |
| 10 | CORS/CSP blocks OAuth redirect | Invisible failure in production | Medium | Test locally first, adjust CSP headers |

---

## Blocked Items (Require User Input)

| Item | What's Needed | Blocking Phase |
|------|-------------|----------------|
| `GOOGLE_CLIENT_SECRET` | Value from Google Cloud Console | Phase 2 |
| Google Cloud redirect URI | Must add `https://nadercr7-wadjet-v2.hf.space/auth/google/callback` | Phase 2 |
| Resend sending domain | Verify which domain is configured in Resend dashboard | Phase 2 |
| Database decision | SQLite (ephemeral) vs PostgreSQL (Supabase free tier) for HF | Phase 5 |
| Logo design direction | Answers to 6 design questions (see `05_DESIGN_SYSTEM.md`) | Phase 6 |
| `JWT_SECRET` value | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` | Phase 1 |
| `CSRF_SECRET` value | Generate: same as above | Phase 1 |

---

## Git & Branch Strategy

```
Current state:
  Old Wadjet:    clean-main (default) → github:Nadercr7/wadjet_v2 + hf:nadercr7/wadjet-v2
  v3-beta:       master (local only, no remotes)

Target state:
  v3-beta → main branch of wadjet_v2 repo
  Old code archived as v2.0.0 tag
  v3 tagged as v3.0.0
  HF Space points to v3 code
```

### Phase-by-Phase Git Strategy

| Phase | Branch | Commit Convention | Tag |
|-------|--------|-------------------|-----|
| P1 Security | `master` | `security(audit): <description>` | — |
| P2 Auth | `master` | `feat(auth): <description>` | — |
| P3 Scan | `master` | `feat(scan): <description>` | — |
| P4 Stories | `master` | `feat(stories): <description>` | — |
| P5 Promotion | `master` → push | `chore(promote): v3 becomes production` | `v3.0.0` |
| P6 Logo | `master` | `feat(brand): <description>` | — |
| P7 Loading | `master` | `feat(loading): <description>` | — |
| P8 Polish | `master` | `fix/chore: <description>` | `v3.1.0` |

### Commit Rules for Entire Upgrade

- Every phase starts with a checkpoint commit: `chore(phase-N): checkpoint before <phase name>`
- Every phase ends with a phase commit: `chore(phase-N): complete <phase name>`
- No `--force` push. No `--no-verify`. No rewriting published history.
- `.env` never committed. `.env.example` updated on every new env var.

---

## File Index

| File | Purpose |
|------|---------|
| `00_MASTER_PLAN.md` | This file — executive overview |
| `01_PHASE_MAP.md` | Detailed phase definitions with DoD |
| `02_PHASE_PROMPTS.md` | Self-contained execution prompts per phase |
| `03_VERSION_PROMOTION_PLAN.md` | Dedicated v3 promotion + HF deployment plan |
| `04_AUTH_PLAN.md` | Google OAuth + Resend deep-dive |
| `05_DESIGN_SYSTEM.md` | Visual identity + logo + loading spec |
| `06_SCAN_PIPELINE_AUDIT.md` | Current pipeline audit + upgrade plan |
| `07_STORIES_ENRICHMENT_PLAN.md` | New stories + smart image generation |
| `08_TESTING_PLAN.md` | Test plan for all phases |
| `09_CREDENTIALS_AND_SETUP_CHECKLIST.md` | Credential verification + setup walkthrough |
| `10_QUALITY_GATES.md` | Definition of done + QA checklists |
