# WADJET v3 — MASTER PLAN

> Generated: 2026-03-29
> Status: **IN PROGRESS**
> Source: Full-spectrum audit (137 findings) + cross-reference verification

---

## Executive Summary

Wadjet v3 Beta has **strong fundamentals** (impressive ML models, solid design system, complete bilingual support, resilient AI fallback architecture) but is **not launch-ready** due to critical security gaps, zero test coverage, and several runtime bugs.

This plan addresses **127 verified issues** across 10 phases. The audit originally reported 137, but verification found **1 false positive** (CSS duplication), **2 partially true** (FK indexes 3/4 not 4/4, asyncio.run is inefficient not crashing), and **1 severity adjustment** (path traversal mitigated at HTTP layer, downgraded from CRITICAL to HIGH). Additionally, **1 new critical finding** was discovered: CSRF protection is completely inoperative across ALL API routes, not just `/api/user/`.

---

## Issue Count by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Security | 5 | 16 | 10 | 6 | **37** |
| Bugs | 5 | 5 | 5 | 0 | **15** |
| Architecture / Code Quality | 0 | 0 | 8 | 8 | **16** |
| Performance | 0 | 0 | 10 | 3 | **13** |
| UX / Frontend | 0 | 0 | 5 | 5 | **10** |
| Testing | 1 | 0 | 0 | 0 | **1** |
| DevOps / Deployment | 1 | 5 | 4 | 3 | **13** |
| Documentation | 0 | 1 | 1 | 3 | **5** |
| **Total** | **12** | **27** | **43** | **28** | **110** |

*Note: Count differs from audit's 137 because we merged duplicates, removed false positives, and consolidated related items.*

---

## Phase Overview

| Phase | Name | Effort | Issues Resolved | Status |
|-------|------|--------|-----------------|--------|
| 0 | Project Setup & Foundation | S | 3 | ✅ Done |
| 1 | Security — Critical Fixes | L | 8 | ⬜ Not Started |
| 2 | Security — High Priority | L | 12 | ⬜ Not Started |
| 3 | Critical Bug Fixes | M | 8 | ⬜ Not Started |
| 4 | Database & Migrations | M | 6 | ⬜ Not Started |
| 5 | Architecture Cleanup | L | 12 | ⬜ Not Started |
| 6 | Input Validation & Prompt Hardening | M | 10 | ⬜ Not Started |
| 7 | Frontend & UX Fixes | M | 10 | ⬜ Not Started |
| 8 | Performance Optimization | M | 10 | ⬜ Not Started |
| 9 | Test Coverage | XL | 1 (but massive scope) | ⬜ Not Started |
| 10 | DevOps, Docs & Final Polish | M | 20 | ⬜ Not Started |

---

## Phase Dependency Map

```
Phase 0 ─────────────────────────────────────────────────┐
    │                                                     │
    ├──→ Phase 1 (Security Critical) ──→ Phase 2 (Security High)
    │         │                                │
    │         ├──→ Phase 5 (Architecture) ──→ Phase 8 (Performance)
    │         │
    │         └──→ Phase 6 (Validation) 
    │         │
    │         └──→ Phase 7 (Frontend/UX)
    │
    ├──→ Phase 3 (Critical Bugs) ──→ Phase 4 (Database)
    │                                    │
    │                                    └──→ Phase 10 (DevOps/Docs)
    │
    └──→ Phase 9 (Tests) — runs in parallel with Phases 2-8,
         tests written alongside or immediately after each fix
```

**Strict ordering**:
- Phase 0 before everything
- Phase 1 before Phases 2, 5, 6, 7
- Phase 3 before Phase 4
- Phase 4 before Phase 10
- Phase 5 before Phase 8

**Parallel-safe**:
- Phase 3 can run alongside Phase 1
- Phase 9 (tests) runs continuously alongside all other phases

---

## Risk Map

| Change | What Could Break | Severity | Mitigation |
|--------|-----------------|----------|------------|
| CSRF reconfiguration | Legitimate POST/PUT/DELETE requests rejected with 403 | HIGH | Map every client→server call pattern before changing. Test every page. |
| Settings singleton unification | Routes using `Depends(get_settings)` may break if signature changes | MEDIUM | Grep all usages first. The fix is compatible (same return type). |
| Rate limit key function | Behind reverse proxy, `get_remote_address` returns proxy IP (shared) | HIGH | Make trusted proxy depth configurable via env var. |
| Chat stream GET→POST | SSE `EventSource` only supports GET. Frontend rewrite needed. | HIGH | Switch to `fetch()` + `ReadableStream` or use `hx-ext="sse"` with POST. |
| FK migration in SQLite | SQLite can't ALTER FK constraints. Need table recreation. | MEDIUM | Use Alembic `batch_alter_table`. Test on DB copy first. |
| CSP header | Inline `<script>` / `<style>` blocks may violate CSP and break functionality | MEDIUM | Audit all inline scripts first. Use `'unsafe-inline'` initially, tighten later. |

---

## Verified Audit Corrections

| Original Audit Finding | Verification Result | Action |
|------------------------|--------------------:|--------|
| SEC-03: Path traversal CRITICAL | `pages.py` has regex `^[a-z0-9\-]{1,50}$` on `story_id` → HTTP layer blocks traversal | Downgrade to HIGH. Still add defense-in-depth in `stories_engine.py`. |
| CSS `input.css` duplication | `@layer base` and `@layer components` each appear exactly once | **FALSE POSITIVE.** Skip fix. |
| BUG-05: asyncio.run crashes | Guard correctly routes `asyncio.run` to spawned thread (no running loop). Wasteful, not crashing. | Downgrade from CRITICAL to MEDIUM (performance issue). |
| Missing FK indexes on 4/4 columns | `ScanHistory.user_id` already has `index=True`. 3/4 missing. | Fix only 3 columns. |
| CSRF: `/api/user/` too broad | **EVERY** `/api/*` route is CSRF-exempt. Middleware is completely inoperative. | **UPGRADE** from HIGH to CRITICAL. New #1 priority. |
| SEC-06: Chat clear no auth | Confirmed. No `get_current_user` imported anywhere in `chat.py`. | Confirmed as-is. |

---

## Completion Criteria

The project is considered **launch-ready** when:

1. ✅ All 12 CRITICAL issues resolved
2. ✅ All 27 HIGH issues resolved
3. ✅ CSRF protection actually protects state-mutating endpoints
4. ✅ Rate limiting cannot be bypassed by header spoofing
5. ✅ JWT secrets are mandatory env vars, not auto-generated
6. ✅ Zero runtime crashes on any authenticated user flow
7. ✅ Docker deployment works end-to-end
8. ✅ Test suite exists with >70% coverage on auth, security, and CRUD paths
9. ✅ All MEDIUM issues resolved or documented as accepted risk
10. ✅ Security scorecard ≥ 7/10 (currently 4.6/10)
