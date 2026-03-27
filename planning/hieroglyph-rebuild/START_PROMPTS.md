# Wadjet v2 — Hieroglyph Rebuild: Start Prompts

> Copy-paste these prompts to start each phase.
> Each prompt gives the AI full context to begin work immediately.

---

## Phase H-FIX: Start Prompt

```
I'm working on Wadjet v2, an Egyptian heritage web app. Read these files for full context:

1. CLAUDE.md (project instructions)
2. planning/hieroglyph-rebuild/PROBLEM_ANALYSIS.md (all bugs documented)
3. planning/hieroglyph-rebuild/REBUILD_TASKS.md (task list)
4. planning/hieroglyph-rebuild/CHECKLIST.md (quality gates FIX-G0A through FIX-G13)

We're starting Phase H-FIX — fixing all critical bugs in the hieroglyph pipeline WITHOUT changing architecture. 19 tasks total.

START WITH THE MOST CRITICAL — Classifier is completely broken (4 bugs):
- H-FIX-00A: Switch config from uint8 to FP32 classifier + git LFS track + .gitignore whitelist
- H-FIX-00B: Add BGR→RGB conversion before classifier (cv2.cvtColor)
- H-FIX-00C: Verify label_mapping.json path uses filesystem order (not alphabetical)
- H-FIX-00D: Update JS pipeline to use FP32 model URL + correct label map

THEN fix the remaining 15 tasks (H-FIX-01 through H-FIX-15).
H-FIX-11 (create /api/translate endpoint) must be done before H-FIX-13.

Key files to modify:
- app/config.py (classifier path: uint8 → FP32)
- app/core/hieroglyph_pipeline.py (BGR→RGB, label mapping)
- app/core/postprocess.py
- app/api/scan.py
- app/core/transliteration.py
- app/core/reading_order.py
- app/core/rag_translator.py
- app/core/gardiner.py
- app/dependencies.py
- app/static/js/hieroglyph-pipeline.js
- app/static/sw.js
- .gitignore
- NEW: app/api/translate.py

After completing all classifier fixes (00A-00D), push to GitHub + HF and verify the Space works.
After all 19 tasks, verify all CHECKLIST.md gates.
Update planning/hieroglyph-rebuild/PROGRESS.md after each task.
```

---

## Phase H-VISION: Start Prompt

```
I'm working on Wadjet v2, an Egyptian heritage web app. Read these files:

1. CLAUDE.md (project instructions)
2. planning/hieroglyph-rebuild/MASTER_PLAN.md (architecture overview)
3. planning/hieroglyph-rebuild/SYSTEM_DESIGN.md (detailed component design)
4. planning/hieroglyph-rebuild/API_STRATEGY.md (multi-API fallback strategy)
5. planning/hieroglyph-rebuild/REBUILD_TASKS.md (H-VISION tasks)
6. planning/hieroglyph-rebuild/CHECKLIST.md (gates VIS-G1 through VIS-G10)

Phase H-FIX is complete. Now starting Phase H-VISION — adding AI Vision as the PRIMARY hieroglyph reader.

This is the biggest quality improvement. Instead of relying on ONNX detect→classify (5-15% accuracy on real stone), we send the photo to Gemini Vision which can read inscriptions directly.

Start with H-VISION-01 (AIService base class with key rotation), then H-VISION-02 (AI reader with Gemini prompt).

Available API keys in .env:
- 17 Gemini keys (GEMINI_API_KEY_1 through _17)
- 8 Grok keys (GROK_API_KEY_1 through _8)
- Add GROQ_API_KEY (user will provide)

Key new files to create:
- app/core/ai_service.py (unified multi-provider service)
- app/core/ai_reader.py (hieroglyph vision reader)
- app/core/cross_validator.py (AI vs ONNX comparison)

Key files to modify:
- app/api/scan.py (add mode parameter, AI-first flow)
- app/config.py (add Groq/Cohere keys)
- app/dependencies.py (wire AI services)
- app/templates/scan.html (mode selector UI)
- app/static/js/hieroglyph-pipeline.js (AI mode support)

See SYSTEM_DESIGN.md for the Gemini Vision prompt (Egyptologist expert). Follow the fallback chain: Gemini → Groq → Grok → ONNX-only.

After each task, update PROGRESS.md.
```

---

## Phase H-TRANSLATE: Start Prompt

```
I'm working on Wadjet v2, an Egyptian heritage web app. Read these files:

1. CLAUDE.md
2. planning/hieroglyph-rebuild/SYSTEM_DESIGN.md (Component 3: Translation Engine)
3. planning/hieroglyph-rebuild/API_STRATEGY.md (embedding strategy)
4. planning/hieroglyph-rebuild/REBUILD_TASKS.md (H-TRANSLATE tasks)
5. planning/hieroglyph-rebuild/CHECKLIST.md (gates TRN-G1 through TRN-G8)

Phases H-FIX and H-VISION are complete. Now rebuilding the translation engine.

Current problems:
- all-MiniLM-L6-v2 produces meaningless embeddings for MdC hieroglyphic strings
- Translation calls Gemini twice (EN then AR) instead of once
- No caching, no fallback

Changes needed:
1. Replace embedding model with Gemini text-embedding-004 (768-dim, handles MdC better)
2. Rebuild FAISS index with new embeddings (15,604 corpus pairs in data/translation/corpus.jsonl)
3. New few-shot translation prompt with RAG examples
4. Add Groq fallback for translation
5. Add LRU cache for repeated sequences

Key file: app/core/rag_translator.py
Data files: data/translation/corpus.jsonl, data/embeddings/

After each task, update PROGRESS.md.
```

---

## Phase H-AUDIO: Start Prompt

```
I'm working on Wadjet v2, an Egyptian heritage web app. Read these files:

1. CLAUDE.md
2. planning/hieroglyph-rebuild/SYSTEM_DESIGN.md (Component 4: TTS)
3. planning/hieroglyph-rebuild/REBUILD_TASKS.md (H-AUDIO tasks)
4. planning/hieroglyph-rebuild/CHECKLIST.md (gates AUD-G1 through AUD-G9)

Adding voice features to the hieroglyph system.

Task 1: Port TTS from V1. The V1 project at D:\Personal attachements\Projects\Final_Horus\Wadjet\ has static/js/tts.js with a WadjetTTS object using Web Speech API. Port it to V2, modernize for Alpine.js integration.

Task 2-3: Add "Listen" buttons to scan results (app/templates/scan.html) and dictionary (app/templates/dictionary.html). Use Alpine.js x-data for play/pause state.

Task 4 (optional): Add Groq TTS endpoint. Groq offers playai-tts model (free tier). Create /api/tts endpoint that returns audio.

Task 5 (optional): Add Groq STT. Using whisper-large-v3-turbo on Groq free tier. "Speak" button for voice input.

The V2 design system is black & gold. TTS buttons should use btn-ghost class with a speaker icon (Lucide inline SVG).

After each task, update PROGRESS.md.
```

---

## Phase H-DETECTOR: Start Prompt

```
I'm working on Wadjet v2, an Egyptian heritage web app. Read these files:

1. CLAUDE.md  
2. planning/hieroglyph-rebuild/PROBLEM_ANALYSIS.md (detector quality section)
3. planning/hieroglyph-rebuild/REBUILD_TASKS.md (H-DETECTOR tasks)
4. planning/hieroglyph-rebuild/CHECKLIST.md (gates DET-G1 through DET-G7)
5. planning/detector-rebuild/ (existing detector rebuild plans if any)

Current model performance:
- Detector (YOLO26s): mAP50=0.71, recall=0.64 (both below quality gates)
- Classifier (MobileNetV3): 98% on test, 5-15% on real stone crops (domain gap)

Training data locations:
- Detection: data/detection/ (10,311 images, 84% from mohiey source — domain bias)
- Classification: data/hieroglyph_classification/ (16,638 images, 171 classes)
- Additional scraped: scripts/sites_data/ (438 images, NOT annotated)
- Kaggle datasets: 86,389 total detection images available

Plan:
1. Audit data: class distribution, source diversity, labeling quality
2. Auto-annotate unannotated images with GroundingDINO
3. Clean dataset with CLIP (remove mislabeled crops)
4. Retrain detector with cleaned + balanced data (target mAP50>0.85)
5. Retrain classifier with stone-texture augmentation (target >50% on real stone)
6. Export ONNX and test

Note: AI Vision (Phase H-VISION) already bypasses model quality issues for online users. This phase improves offline/fallback quality.

After each task, update PROGRESS.md.
```

---

## Quick Reference: Key File Locations

```
# Planning
planning/hieroglyph-rebuild/PROBLEM_ANALYSIS.md    — All 20+ bugs
planning/hieroglyph-rebuild/MASTER_PLAN.md          — Architecture overview
planning/hieroglyph-rebuild/SYSTEM_DESIGN.md        — Detailed component design
planning/hieroglyph-rebuild/REBUILD_TASKS.md        — 57 tasks, sized & ordered
planning/hieroglyph-rebuild/API_STRATEGY.md         — Multi-API fallback
planning/hieroglyph-rebuild/CHECKLIST.md            — Quality gates
planning/hieroglyph-rebuild/PROGRESS.md             — Live tracker

# Pipeline (Python)
app/api/scan.py                                     — Scan endpoint
app/core/postprocess.py                             — YOLO postprocessing
app/core/hieroglyph_pipeline.py                     — ONNX detect + classify
app/core/transliteration.py                         — MdC transliteration
app/core/reading_order.py                           — Direction detection
app/core/gardiner.py                                — 1,023 Gardiner signs
app/core/rag_translator.py                          — RAG translation
app/config.py                                       — Settings
app/dependencies.py                                 — DI wiring

# Pipeline (JavaScript)
app/static/js/hieroglyph-pipeline.js                — Client-side ONNX pipeline

# Templates
app/templates/scan.html                             — Scan page
app/templates/dictionary.html                       — Dictionary page
app/templates/write.html                            — Write page (~380 lines)
app/templates/explore.html                          — Explore page (~800 lines)

# Write Feature
app/api/write.py                                    — Write API (~290 lines, 3 modes)

# Landmarks Feature
app/api/explore.py                                  — Explore/Identify API (~950 lines)
app/core/ensemble.py                                — Multi-model vote/merge
app/core/gemini_service.py                          — Gemini identify + describe
app/core/grok_service.py                            — Grok identify

# Models
models/hieroglyph/glyph_detector_uint8.onnx         — YOLO detector
models/hieroglyph/hieroglyph_classifier.onnx         — MobileNetV3 FP32
models/hieroglyph/hieroglyph_classifier_uint8.onnx   — MobileNetV3 INT8 (broken)
models/hieroglyph/label_mapping.json                 — 171 class labels

# Data
data/translation/corpus.jsonl                        — 15,604 translation pairs
data/embeddings/                                     — FAISS index
data/hieroglyph_classification/                      — Classifier training data
data/detection/                                      — Detector training data

# V1 Reference
D:\Personal attachements\Projects\Final_Horus\Wadjet\  — V1 project (TTS, gardiner, pipeline)
```

---

## Phase W-WRITE: Start Prompt

```
I'm working on Wadjet v2, an Egyptian heritage web app. Read these files:

1. CLAUDE.md (project instructions)
2. planning/hieroglyph-rebuild/REBUILD_TASKS.md (W-WRITE tasks — look for "Phase W-WRITE")
3. planning/hieroglyph-rebuild/CHECKLIST.md (gates WRT-G1 through WRT-G12)
4. planning/hieroglyph-rebuild/API_STRATEGY.md (multi-API fallback strategy)
5. app/api/write.py (current write feature — MUST READ FULLY)
6. app/core/gardiner.py (Gardiner sign data — 1,023+ signs)
7. data/translation/corpus.jsonl (first 50 lines — existing MdC→EN pairs)

We're starting Phase W-WRITE — fixing the Write in Hieroglyphs feature so it actually works correctly.

CURRENT PROBLEMS:
- Smart mode prompt is weak: no few-shot examples, no grammar rules, no Egyptological context
- Gemini hallucinates non-existent Gardiner codes (e.g., "A100", "Z99")
- No fallback: if Gemini fails, falls straight to letter-by-letter (useless for phrases)
- MdC mode misses many valid transliterations (incomplete _TRANSLIT_TO_SIGN)
- No reverse corpus: existing corpus is MdC→EN only, smart mode needs EN→MdC examples
- No validation: AI output is trusted blindly, no check against known signs
- No tests: we can't verify if smart mode actually works

PHASE W-WRITE GOAL: Known Egyptian phrases produce correct hieroglyph sequences.

START WITH W-WRITE-01: Build reverse translation corpus
Create data/translation/write_corpus.jsonl with EN→MdC pairs. Extract from existing corpus.jsonl (reverse direction) + add 150+ curated entries for common phrases like:
- "An offering which the king gives" → "Htp di nsw"
- "Son of Ra" → "sA ra"
- "life" → "anx"
- "given life forever" → "Dj anx Dt"
- "words to be spoken" → "Dd mdw"

THEN W-WRITE-02: Rewrite the smart mode prompt in _ai_translate_to_hieroglyphs().

KEY RULES:
- ONLY use Gardiner codes that exist in GARDINER_TRANSLITERATION dict
- Test every change with known phrases from corpus
- Add Groq/Grok as fallback (same prompt format)
- Known phrase shortcuts should bypass AI entirely (instant, guaranteed correct)

Available APIs: 17 Gemini keys, 8 Grok keys, 1 Groq key (all in .env)

After each task, update planning/hieroglyph-rebuild/PROGRESS.md.
```

---

## Phase L-LANDMARKS: Start Prompt

```
I'm working on Wadjet v2, an Egyptian heritage web app. Read these files:

1. CLAUDE.md (project instructions)
2. planning/hieroglyph-rebuild/REBUILD_TASKS.md (L-LANDMARKS tasks — look for "Phase L-LANDMARKS")
3. planning/hieroglyph-rebuild/CHECKLIST.md (gates LM-G1 through LM-G7)
4. planning/hieroglyph-rebuild/API_STRATEGY.md (multi-API fallback strategy)
5. app/api/explore.py (current explore/identify feature — MUST READ FULLY, ~950 lines)
6. app/core/ensemble.py (merge/vote logic for multi-model identification)
7. app/core/gemini_service.py (identify_landmark + describe_landmark methods)
8. app/core/grok_service.py (identify_landmark method)
9. data/expanded_sites.json (161+ heritage sites — check for empty descriptions)

We're starting Phase L-LANDMARKS — improving landmarks/explore using the multi-API strategy.

CURRENT STATE:
- Landmarks browse + identify WORK but have gaps:
  - Many non-curated sites have EMPTY descriptions in the browse grid
  - Non-curated detail pages have empty highlights/visiting_tips/historical_significance
  - Identify fallback: if Gemini fails → ONNX only (52 classes, lower quality) — no vision AI backup
  - Grok tiebreaker exists but only for disagreements, not as a standalone fallback

WHAT WE HAVE (from API research):
- Groq: Llama 4 Scout 17B with vision — FREE, fast, good quality — SHOULD be identify fallback
- Cloudflare Workers AI: 10K neurons/day FREE forever — vision models available as emergency fallback
- TLA API: 90K Egyptian lemmas, free, no key — scholarly data for pharaonic landmarks

PHASE L-LANDMARKS GOAL: Zero empty descriptions, multi-layer identify fallback, richer detail pages.

START WITH L-LANDMARKS-01: Fill empty descriptions
Write a script that iterates expanded_sites.json, finds entries with empty/short descriptions, calls Gemini to generate 2-3 sentences for each, and saves them back. Then add lazy AI generation in the API for any remaining gaps.

THEN L-LANDMARKS-02: Add Groq Vision as identify fallback
Create GroqService.identify_landmark() using same prompt format as Gemini. Insert into the identify pipeline.

KEY RULES:
- DO NOT change the ensemble logic in ensemble.py — it works well
- DO NOT change the curated ATTRACTIONS data or templates
- Only ADD fallback layers and fill empty content
- Test with real landmark photos to verify fallback chain

Available APIs: 17 Gemini keys, 8 Grok keys, 1 Groq key, Cloudflare account (all in .env)

After each task, update planning/hieroglyph-rebuild/PROGRESS.md.
```
