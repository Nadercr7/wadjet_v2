# Wadjet v3 Beta — Work Log

> Append-only log of all changes made during development.

---

## 2026-03-28 — Phase 0: Setup

- Copied `Wadjet/` → `Wadjet-v3-beta/` (excluding .venv, node_modules, .git, __pycache__)
- Initialized git repo with baseline commit (528 files, tag: v2-baseline)
- Created `wadjet-v3-planning/` folder with constitution, spec, plan, progress, work-log
- Created prompt files for all 11 phases (0-10)

---

## 2026-03-28 — Phase 0: AI Media Enhancement Planning

**API Research Completed:**
- Fetched Cloudflare Workers AI docs → found FREE image gen models (FLUX.1 schnell, SDXL, DreamShaper, etc.)
- Fetched Gemini API TTS docs → found FREE TTS (gemini-2.5-flash-preview-tts, 30 voices, 73+ langs including Arabic!)
- Fetched Gemini Veo docs → Veo 3.1 video gen is PAID ONLY ($0.15-$0.60/video) — skipped
- Fetched Groq TTS docs → found FREE Orpheus (English + Arabic Saudi, expressive)
- Confirmed Imagen 4 is PAID ONLY ($0.02-$0.06/image) — use Cloudflare FLUX instead
- Confirmed Lyria 3 music is PAID ONLY ($0.04-$0.08/song) — skipped

**Files Updated:**
- `constitution.md`: Added "AI Generation Services (Smart Defaults)" section, voice presets, fallback chains, Rule 11, new pip deps (google-genai, httpx), updated Out of Scope
- `spec.md`: Added section 3.10 (AI Media Generation Service), updated 3.6 (Thoth Chat TTS upgrade), updated 3.7 (Stories with AI illustrations + narrative voice), renumbered 3.11 (Dashboard)
- `plan.md`: Updated phase names, added AI Provider Stack table, added Bonus Improvements table (10 items), added Version Replacement section
- `phase-4-ux.md`: Renamed to "UX, Accessibility & TTS Service", added Gemini TTS service creation, narration button on all pages, media API endpoint, expanded testing checklist
- `phase-8-stories.md`: Added AI image gen (Cloudflare FLUX), narrative TTS (Gemini), Ken Burns CSS animation, image_service.py and tts_service.py code, scene_image_prompt + tts_voice in story JSON schema, expanded testing checklist
- `phase-10-finalize.md`: Added version replacement script (PowerShell), AI Media Services changelog section, expanded testing checklist

**Key Decisions:**
- ✅ Gemini 2.5 Flash TTS as primary TTS (FREE, best quality, Arabic)
- ✅ Cloudflare FLUX.1 schnell as primary image gen (FREE, fast)
- ✅ No video generation (no free API) → Ken Burns animations instead
- ✅ Smart defaults: system picks best provider, no user selector
- ✅ Version replacement via PowerShell script in Phase 10
