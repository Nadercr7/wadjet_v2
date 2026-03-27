# Wadjet v2 — Hieroglyph Rebuild: Task List

> Every task, sized, ordered, with dependencies.
> Each task should take 1-4 hours max (if bigger, split).

---

## Phase H-FIX: Critical Bug Fixes (Week 1)
> Fix everything broken without changing architecture.
> Goal: Current pipeline works correctly, albeit low quality.

### H-FIX-00A: Switch classifier to FP32 model [CRITICAL]
- **File**: `app/config.py`, `.gitignore`
- **What**: 
  1. Change `hieroglyph_classifier_path` from `hieroglyph_classifier_uint8.onnx` to `hieroglyph_classifier.onnx`
  2. Add `!models/hieroglyph/classifier/hieroglyph_classifier.onnx` to `.gitignore`
  3. Track FP32 model with git LFS (`git lfs track`)
  4. Verify FP32 model exists locally at `models/hieroglyph/classifier/hieroglyph_classifier.onnx`
- **Why**: INT8 model gives 0% accuracy. FP32 gives 97% on test.
- **Deps**: None
- **Size**: S (30 min)

### H-FIX-00B: Add BGR→RGB conversion in classifier [CRITICAL]
- **File**: `app/core/hieroglyph_pipeline.py`
- **What**: Add `cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)` before classifier preprocessing. OpenCV loads BGR but model was trained on RGB.
- **Why**: Without this, color channels are swapped → predictions are garbage on color-sensitive signs
- **Deps**: None
- **Size**: XS (15 min)

### H-FIX-00C: Fix label_mapping.json path [CRITICAL]
- **File**: `app/core/hieroglyph_pipeline.py`
- **What**: Ensure label_mapping.json loads from `models/hieroglyph/classifier/label_mapping.json` (filesystem order, 171 classes). Verify mapping matches training order, NOT alphabetical sort.
- **Why**: Wrong mapping shifts 110/171 class labels → most predictions are wrong even when model is confident
- **Deps**: None
- **Size**: XS (15 min)

### H-FIX-00D: Update JS pipeline for FP32 + correct label map [HIGH]
- **File**: `app/static/js/hieroglyph-pipeline.js`, `app/static/sw.js`
- **What**: Update JS classifier URL to point to FP32 model. Ensure label mapping URL is correct. Update SW cache list.
- **Why**: JS client-side pipeline has same INT8/label issues as Python
- **Deps**: H-FIX-00A
- **Size**: S (30 min)

### H-FIX-01: Fix asyncio deprecation [CRITICAL]
- **File**: `app/api/scan.py`
- **What**: Replace `asyncio.get_event_loop().run_in_executor()` with `asyncio.get_running_loop().run_in_executor()` or `asyncio.to_thread()`
- **Why**: Python 3.13 will crash on `get_event_loop()` in async context
- **Deps**: None
- **Size**: XS (15 min)

### H-FIX-02: Wire config threshold to pipeline [HIGH]
- **File**: `app/dependencies.py`, `app/config.py`
- **What**: Actually pass `settings.detection_confidence_threshold` to postprocess module instead of hardcoded 0.10
- **Why**: Config value (0.15) is ignored — detector uses hardcoded 0.10 from postprocess.py
- **Deps**: None
- **Size**: S (30 min)

### H-FIX-03: Fix postprocess return type [MEDIUM]
- **File**: `app/core/postprocess.py`
- **What**: Return type says tuple of 4, actually returns 5 (includes label index). Fix type hint. Rename `class_id`/`score` clarity.
- **Why**: Misleading, causes confusion
- **Deps**: None
- **Size**: XS (15 min)

### H-FIX-04: Fix transliteration unknown sign handling [MEDIUM]
- **File**: `app/core/transliteration.py`
- **What**: Signs not in MdC map should produce `[?]` not crash or produce empty string. Handle multi-glyph quadrats.
- **Deps**: None
- **Size**: S (30 min)

### H-FIX-05: Fix reading order (always RTL bug) [HIGH]
- **File**: `app/core/reading_order.py`
- **What**: `detect_reading_direction()` always returns RTL because `facing_direction()` is never called. Add basic heuristic: if bird/person Gardiner codes present, check their facing.
- **Deps**: None
- **Size**: M (1 hr)

### H-FIX-06: Fix Grok vision tiebreaker [HIGH]
- **File**: `app/api/scan.py`
- **What**: Grok likely fails silently on large base64 data URIs. Either: (a) upload image to temp URL, or (b) compress image before base64.
- **Why**: Grok tiebreaker never actually works → always fallback
- **Deps**: None
- **Size**: M (1 hr)

### H-FIX-07: Skip unnecessary Gemini verify [HIGH]
- **File**: `app/api/scan.py`
- **What**: Add confidence threshold check: if avg glyph confidence > 0.6, skip full-sequence Gemini verification. Save API calls.
- **Deps**: None
- **Size**: S (30 min)

### H-FIX-08: Fix bilingual translation (2 calls → 1) [HIGH]
- **File**: `app/core/rag_translator.py`
- **What**: `translate_bilingual()` calls `translate_single()` twice sequentially. Merge into one Gemini call returning both EN + AR.
- **Deps**: None
- **Size**: S (45 min)

### H-FIX-09: Move debug function out of production [LOW]
- **File**: `app/core/postprocess.py`
- **What**: Move `evaluate_conf_threshold()` to `scripts/` directory
- **Deps**: None
- **Size**: XS (15 min)

### H-FIX-10: Fix gardiner.py logogram/determinative overlap [MEDIUM]
- **File**: `app/core/gardiner.py`
- **What**: Some signs are classified as both logogram and determinative. Add `usage` field that's a list.
- **Deps**: None
- **Size**: S (30 min)

### H-FIX-11: Create /api/translate endpoint [CRITICAL]
- **File**: NEW `app/api/translate.py`, modify `app/main.py`
- **What**: JS pipeline's `translate()` sends JSON to file-upload `/api/scan` → always 422. Create proper `/api/translate` endpoint accepting `{transliteration, gardiner_sequence}`.
- **Deps**: None
- **Size**: M (1 hr)

### H-FIX-12: Fix JS Gardiner map completeness [HIGH]
- **File**: `app/static/js/hieroglyph-pipeline.js`
- **What**: JS `GARDINER_MAP` has ~125 entries but model outputs 171 classes. Fill missing 46 entries using `label_mapping.json` + `gardiner.py`.
- **Deps**: None
- **Size**: M (1 hr)

### H-FIX-13: Fix JS translate() to use new endpoint [CRITICAL]
- **File**: `app/static/js/hieroglyph-pipeline.js`
- **What**: Update `translate()` to POST JSON to `/api/translate` instead of sending multipart FormData to `/api/scan`.
- **Deps**: H-FIX-11
- **Size**: S (30 min)

### H-FIX-14: Batch JS classification [MEDIUM]
- **File**: `app/static/js/hieroglyph-pipeline.js`
- **What**: Currently classifies glyphs one-by-one (N ONNX sessions). Batch into single tensor for one inference call.
- **Deps**: None
- **Size**: M (1-2 hrs)

### H-FIX-15: Fix camera loop CPU burn [MEDIUM]
- **File**: `app/static/js/hieroglyph-pipeline.js`
- **What**: Camera detection loop calls `requestAnimationFrame` with no delay → 60fps inference. Add min 100ms delay or frame skip.
- **Deps**: None
- **Size**: S (30 min)

**Phase H-FIX Total: 19 tasks, ~13-16 hours**

---

## Phase H-VISION: AI Vision Reader (Week 2)
> Add Gemini/Groq/Grok vision as the PRIMARY hieroglyph reader.
> This is the single biggest quality improvement.

### H-VISION-01: Create AIService base class
- **File**: NEW `app/core/ai_service.py`
- **What**: Create unified multi-provider AI service with:
  - Key rotation (round-robin across 17 Gemini keys, 8 Grok keys)
  - Automatic fallback (Gemini → Groq → Grok)
  - Rate limit tracking per key
  - Error handling and retry logic
- **Deps**: None
- **Size**: L (2-3 hrs)

### H-VISION-02: Create AI Hieroglyph Reader
- **File**: NEW `app/core/ai_reader.py`
- **What**: Implement `AIHieroglyphReader` using structured Gemini Vision prompt:
  - Send photo → get full reading (glyphs, MdC, translation, direction)
  - Parse and validate JSON response
  - Handle partial failures gracefully
- **Deps**: H-VISION-01
- **Size**: L (2-3 hrs)

### H-VISION-03: Add Groq Vision fallback
- **File**: `app/core/ai_reader.py`, `app/config.py`
- **What**: Add Groq (Llama 4 Scout 17B) as vision fallback. Configure API key in .env.
- **Deps**: H-VISION-01, H-VISION-02
- **Size**: M (1-2 hrs)

### H-VISION-04: Integrate AI reader into scan pipeline
- **File**: `app/api/scan.py`
- **What**: Add `mode` parameter ("auto", "ai", "onnx"). For "auto": run ONNX detect + AI read concurrently, merge results.
- **Deps**: H-VISION-02
- **Size**: L (2-3 hrs)

### H-VISION-05: Create cross-validator
- **File**: NEW `app/core/cross_validator.py`
- **What**: When both AI and ONNX results available, compare and merge. Match by bbox overlap. Flag disagreements. Output confidence.
- **Deps**: H-VISION-04
- **Size**: M (1-2 hrs)

### H-VISION-06: Create /api/read endpoint
- **File**: `app/api/translate.py` or NEW `app/api/read.py`
- **What**: Lightweight AI-only reading endpoint (no ONNX). For client-side pipeline to get AI reading after local detection.
- **Deps**: H-VISION-02
- **Size**: S (45 min)

### H-VISION-07: Add mode selector to scan UI
- **File**: `app/templates/scan.html`
- **What**: Add toggle: "AI-Powered (Recommended)" / "Fast Local" / "Auto". Default to AI-Powered. Show which mode was used in results.
- **Deps**: H-VISION-04
- **Size**: M (1 hr)

### H-VISION-08: Update JS pipeline for AI mode
- **File**: `app/static/js/hieroglyph-pipeline.js`
- **What**: When AI mode selected, send image to `/api/read` instead of running local ONNX classify. Still use local ONNX detect for bbox visualization.
- **Deps**: H-VISION-06, H-FIX-13
- **Size**: M (1-2 hrs)

**Phase H-VISION Total: 8 tasks, ~12-17 hours**

---

## Phase H-TRANSLATE: Translation Engine (Week 3)
> Rebuild RAG with proper embeddings, improve translation quality.

### H-TRANSLATE-01: Replace embedding model
- **File**: `app/core/rag_translator.py`
- **What**: Replace all-MiniLM-L6-v2 (meaningless for MdC) with Gemini `text-embedding-004` or Cohere `embed-multilingual-v3.0`. Rebuild FAISS index.
- **Deps**: H-VISION-01 (for AIService)
- **Size**: L (2-3 hrs)

### H-TRANSLATE-02: Rebuild FAISS index
- **File**: Script + `data/embeddings/`
- **What**: Create script to re-embed all 15,604 corpus pairs using new embedding model. Save new FAISS index.
- **Deps**: H-TRANSLATE-01
- **Size**: M (1-2 hrs)

### H-TRANSLATE-03: Few-shot translation prompt
- **File**: `app/core/rag_translator.py`
- **What**: New translation prompt: retrieve top-5 RAG examples as few-shot, ask Gemini to translate MdC → EN + AR in one call. Include inscription type context.
- **Deps**: H-TRANSLATE-01
- **Size**: M (1-2 hrs)

### H-TRANSLATE-04: Add Groq translation fallback
- **File**: `app/core/rag_translator.py`
- **What**: If Gemini rate-limited, fall back to Groq (Llama 3.3 70B) for translation. Same prompt format.
- **Deps**: H-TRANSLATE-03, H-VISION-01
- **Size**: S (45 min)

### H-TRANSLATE-05: Translation caching
- **File**: `app/core/rag_translator.py`
- **What**: Cache translated MdC sequences (LRU cache or Redis). Same MdC → return cached translation. Saves API calls.
- **Deps**: H-TRANSLATE-03
- **Size**: S (45 min)

### H-TRANSLATE-06: Translation quality evaluation
- **File**: Script in `scripts/`
- **What**: Create eval script: take 50 known inscriptions (from Rosetta Stone project, standard Egyptology texts), compare AI translation vs ground truth. Track BLEU score.
- **Deps**: H-TRANSLATE-03
- **Size**: M (1-2 hrs)

**Phase H-TRANSLATE Total: 6 tasks, ~7-11 hours**

---

## Phase H-AUDIO: Voice Features (Week 3-4)
> Add TTS and optional STT.

### H-AUDIO-01: Port V1 TTS to V2
- **File**: NEW `app/static/js/tts.js`
- **What**: Port `WadjetTTS` from V1 (`Wadjet/static/js/tts.js`). Web Speech API, language selection, play/pause/stop. Modernize for Alpine.js integration.
- **Deps**: None
- **Size**: M (1-2 hrs)

### H-AUDIO-02: Add TTS buttons to scan results
- **File**: `app/templates/scan.html`
- **What**: Add "Listen" button next to transliteration and translation text. Language selector (EN/AR). Alpine.js state management.
- **Deps**: H-AUDIO-01
- **Size**: M (1 hr)

### H-AUDIO-03: Add TTS to dictionary page
- **File**: `app/templates/dictionary.html`
- **What**: Each glyph card gets pronunciation button. Read phonetic value.
- **Deps**: H-AUDIO-01
- **Size**: S (45 min)

### H-AUDIO-04: Optional Groq TTS (server-side)
- **File**: NEW `app/api/audio.py`
- **What**: `/api/tts` endpoint using Groq's PlayAI TTS model for higher quality Arabic pronunciation. Falls back to client Web Speech API.
- **Deps**: H-VISION-01 (AIService), H-AUDIO-01
- **Size**: M (1-2 hrs)

### H-AUDIO-05: Optional Groq STT (speech input)
- **File**: `app/api/audio.py`, scan.html
- **What**: "Speak to describe" feature: user speaks, Groq Whisper transcribes, text sent as context to AI reader. For accessibility.
- **Deps**: H-VISION-01
- **Size**: M (1-2 hrs)

**Phase H-AUDIO Total: 5 tasks, ~5-8 hours**

---

## Phase H-DETECTOR: Model Improvement (Week 4+)
> Only if we want better ONNX-only performance.
> AI Vision already bypasses detector quality issues.

### H-DETECTOR-01: Audit training data distribution
- **File**: Script in `scripts/`
- **What**: Analyze class balance across all 86K+ detection images. Identify underrepresented sign categories. Check for systematic labeling errors.
- **Deps**: None
- **Size**: M (1-2 hrs)

### H-DETECTOR-02: Add GroundingDINO zero-shot annotations
- **File**: Script in `scripts/`
- **What**: Run GroundingDINO on unannotated images (438 scraped museum images). Auto-annotate with "hieroglyph" prompt. Manual verification.
- **Deps**: None
- **Size**: L (3-4 hrs)

### H-DETECTOR-03: CLIP-based data cleaning
- **File**: Script in `scripts/`
- **What**: Run CLIP on all training crops. Filter out mislabeled images (crops that don't match their class text description). Log flagged images.
- **Deps**: None
- **Size**: L (2-3 hrs)

### H-DETECTOR-04: Retrain detector with cleaned data
- **File**: Kaggle notebook
- **What**: Retrain YOLO detector on cleaned, balanced dataset. Target: mAP50 > 0.85, recall > 0.80.
- **Deps**: H-DETECTOR-01/02/03
- **Size**: XL (4-6 hrs + training time)

### H-DETECTOR-05: Retrain classifier with stone-crop augmentation
- **File**: Kaggle notebook
- **What**: Add aggressive augmentation mimicking real stone: noise, blur, lighting variation, stone texture background. Fine-tune MobileNetV3 on augmented set.
- **Deps**: H-DETECTOR-03
- **Size**: XL (4-6 hrs + training time)

### H-DETECTOR-06: Export and test new models
- **File**: Scripts
- **What**: Export new ONNX models. Test on benchmark set. Compare before/after metrics.
- **Deps**: H-DETECTOR-04, H-DETECTOR-05
- **Size**: M (1-2 hrs)

**Phase H-DETECTOR Total: 6 tasks, ~16-23 hours**

---

## Summary

See **Updated Summary** after Phase L-LANDMARKS below.

---

## Dependency Graph

```
H-FIX-00A ── → H-FIX-00D     (FP32 model must exist before JS updates)
H-FIX-00B ──────────────────── (no deps, do first alongside 00A)
H-FIX-00C ──────────────────── (no deps)
H-FIX-01 ──────────────────── (no deps, do first)
H-FIX-02 ──────────────────── (no deps)
H-FIX-03..10 ─────────────── (no deps, parallel)
H-FIX-11 ──── → H-FIX-13     (/api/translate must exist before JS uses it)

H-VISION-01 ── → H-VISION-02 ── → H-VISION-04 ── → H-VISION-05
                               └─→ H-VISION-03
                               └─→ H-VISION-06 ── → H-VISION-08
                                   H-VISION-07

H-TRANSLATE-01 → H-TRANSLATE-02
               → H-TRANSLATE-03 → H-TRANSLATE-04
                               → H-TRANSLATE-05
                               → H-TRANSLATE-06

H-AUDIO-01 ── → H-AUDIO-02
              → H-AUDIO-03
H-AUDIO-04 (needs H-VISION-01)
H-AUDIO-05 (needs H-VISION-01)

H-DETECTOR-01..03 (parallel) → H-DETECTOR-04 → H-DETECTOR-06
                              → H-DETECTOR-05 → H-DETECTOR-06
```

---

## Execution Order (Recommended)

```
Week 1: H-FIX-00A/B/C/D FIRST (classifier fix — most critical)
         Then H-FIX-01..15 (parallel where possible)
Week 2: H-VISION-01 → 02 → 03 → 04 → 05 → 06 → 07 → 08
Week 3: H-TRANSLATE-01 → 02/03 → 04/05 → 06
         H-AUDIO-01 → 02/03 (parallel with translate)
Week 4: H-AUDIO-04/05
         W-WRITE-01 → 02 → 03 → 04 → 05 → 06 → 07
         L-LANDMARKS-01 → 02 → 03 → 04 → 05 → 06
Week 5+: H-DETECTOR-01/02/03 (background)
         H-DETECTOR-04/05/06 (if needed)
```

---

## Phase W-WRITE: Write Feature Quality (NEW)
> Fix "Write in Hieroglyphs" so it actually produces correct output.
> Goal: Smart mode gives scholarly-accurate translations; MdC mode covers all signs.

### W-WRITE-01: Build reverse translation corpus [HIGH]
- **File**: NEW `data/translation/write_corpus.jsonl`
- **What**: Create EN→MdC parallel corpus from existing `corpus.jsonl` (reverse direction). Add 50+ curated entries for common phrases:
  - Offering formula: "An offering which the king gives" → `Htp di nsw`
  - Royal titles: "Son of Ra" → `sA ra`, "Lord of the Two Lands" → `nb tAwj`
  - Common words: "life" → `anx`, "health" → `snb`, "dominion" → `wAs`
  - God names: "Amun" → `jmn`, "Ra" → `ra`, "Osiris" → `wsjr`
  - Greeting formulae: "given life forever" → `Dj anx Dt`
- **Why**: Smart mode has NO examples to learn from. The existing corpus is MdC→EN only.
- **Deps**: None
- **Size**: M (1-2 hrs)

### W-WRITE-02: Rewrite smart mode AI prompt [CRITICAL]
- **File**: `app/api/write.py` → `_ai_translate_to_hieroglyphs()`
- **What**: Replace weak prompt with proper Egyptologist prompt:
  - Add system persona: "You are a professional Egyptologist specializing in Middle Egyptian hieroglyphic writing"
  - Add few-shot examples from `write_corpus.jsonl` (retrieve top-5 similar via keyword match)
  - Add explicit grammar rules: reading direction, determinatives, phonetic complements
  - Add validation: only return Gardiner codes that exist in our `GARDINER_TRANSLITERATION` dict
  - Add fallback logic: if input is already MdC (detected by pattern), parse it directly instead of AI
  - Require the AI to provide `gardiner_sequence` (dash-separated) AND `explanation` of each choice
- **Why**: Current prompt is "translate to hieroglyphs" with no examples — Gemini hallucinates codes
- **Deps**: W-WRITE-01
- **Size**: L (2-3 hrs)

### W-WRITE-03: Add Groq/Grok fallback for smart mode [HIGH]
- **File**: `app/api/write.py`
- **What**: If Gemini fails/rate-limited in smart mode:
  1. Try Groq (Llama 3.3 70B) with same prompt
  2. Try Grok with same prompt
  3. Fall back to MdC mode if input looks like transliteration, else alpha mode
- **Why**: Currently falls straight to alpha mode (letter-by-letter) which is useless for phrases
- **Deps**: W-WRITE-02
- **Size**: M (1 hr)

### W-WRITE-04: Validate AI output against known signs [HIGH]
- **File**: `app/api/write.py`
- **What**: After AI returns glyphs, validate each Gardiner code:
  - Check code exists in `GARDINER_TRANSLITERATION`
  - Check unicode_char is not empty (renderable)
  - Flag codes the AI made up (not in our dict) with a warning
  - Strip determinatives from the display output (they're meaning markers, not rendered sounds)
  - Add `"verified": true/false` field per glyph
- **Why**: Gemini sometimes returns non-existent Gardiner codes (e.g. "A100", "Z99")
- **Deps**: W-WRITE-02
- **Size**: S (45 min)

### W-WRITE-05: Add known phrase shortcuts [MEDIUM]
- **File**: `app/api/write.py`
- **What**: Pre-computed lookup for the most common phrases:
  - `"life, prosperity, health"` → `anx-wDA-snb` (the classic ꜥnḫ-wḏꜣ-snb)
  - `"an offering which the king gives"` → `Htp-di-nsw`
  - `"given life forever"` → `Dj-anx-Dt`
  - 20-30 more common phrases
  - Check input against shortcuts BEFORE calling AI (instant, guaranteed correct)
- **Why**: Eliminates AI errors for the most commonly requested translations
- **Deps**: None
- **Size**: M (1 hr)

### W-WRITE-06: Improve MdC mode coverage [MEDIUM]
- **File**: `app/api/write.py`, `app/core/gardiner.py`
- **What**: 
  - Audit `_TRANSLIT_TO_SIGN` coverage: which MdC strings from corpus are NOT matched?
  - Add missing mappings (biliteral/triliteral signs not in current dict)
  - Handle common MdC conventions: `.f` (suffix pronoun), `=f` (alt suffix), `(j)` (optional)
  - Add MdC syntax helpers: `*` (tight group), `:` (vertical stack), `-` (separator)
- **Why**: MdC mode misses many valid transliterations because `_TRANSLIT_TO_SIGN` is incomplete
- **Deps**: None
- **Size**: M (1-2 hrs)

### W-WRITE-07: Test with known translations [CRITICAL]
- **File**: Script `scripts/test_write.py`
- **What**: Automated test script that:
  1. Sends 20+ known EN→hieroglyph pairs to `/api/write` (smart mode)
  2. Compares output Gardiner sequence to expected sequence
  3. Reports accuracy per phrase
  4. Tests MdC mode with 20+ known transliterations
  5. Tests alpha mode with full alphabet
  6. Fails if accuracy < 70% on smart mode (known phrases)
- **Test phrases** (ground truth from corpus):
  - "life" → must include `anx` (G1-N35-Aa1 or equivalent)
  - "son of ra" → `sA ra` (G39-D21-N5)
  - "an offering which the king gives" → `Htp di nsw` (R4-X8-N5-S40-M23-X1)
  - "words to be spoken" → `Dd mdw` (I10-D46-S43-G43)
  - "given life forever" → `Dj anx Dt` (similar codes)
- **Why**: Without tests, we can't verify smart mode actually works
- **Deps**: W-WRITE-02
- **Size**: M (1-2 hrs)

**Phase W-WRITE Total: 7 tasks, ~8-12 hours**

---

## Phase L-LANDMARKS: Landmarks Enhancement (NEW)
> Improve explore/identify features using the multi-API strategy.
> Goal: Richer descriptions, better identification fallbacks, zero empty fields.

### L-LANDMARKS-01: Fill empty descriptions with AI [HIGH]
- **File**: `app/api/explore.py`, NEW script `scripts/generate_descriptions.py`
- **What**: 
  - Script: iterate all 161+ sites from `expanded_sites.json`, find those with empty/short descriptions
  - Call Gemini to generate 2-3 sentence descriptions for each
  - Save to `expanded_sites.json` (or a companion `descriptions_cache.json`)
  - API: at browse/detail time, if description still empty, call `gemini.describe_landmark()` lazily and cache
- **Why**: Many non-curated sites show empty description cards in the browse grid
- **Deps**: None
- **Size**: L (2-3 hrs)

### L-LANDMARKS-02: Add Groq Vision as identify fallback [HIGH]
- **File**: `app/api/explore.py`, NEW or extend `app/core/groq_service.py`
- **What**: 
  - Create `GroqService.identify_landmark()` using Llama 4 Scout vision (same prompt format as Gemini)
  - Insert Groq into the identify pipeline: ONNX + Gemini in parallel → if Gemini fails → try Groq before Grok tiebreaker
  - Fallback chain becomes: ONNX + Gemini → Groq → Grok → ONNX-only
- **Why**: If Gemini is rate-limited, identify currently falls to ONNX-only (52 classes, lower quality). Groq provides free vision backup.
- **Deps**: None
- **Size**: M (1-2 hrs)

### L-LANDMARKS-03: Add Cloudflare Workers AI as emergency identify [MEDIUM]
- **File**: NEW `app/core/cloudflare_service.py`, `app/api/explore.py`
- **What**: 
  - Cloudflare Workers AI offers vision models (Llama-3.2-11B-Vision, Gemma 3 12B) with 10K neurons/day FREE forever
  - Create lightweight CloudflareService with `identify_landmark()` method
  - Add as last-resort vision fallback before ONNX-only
  - Fallback chain: ONNX + Gemini → Groq → Grok → Cloudflare → ONNX-only
- **Why**: Five-layer AI redundancy means identify virtually never falls to ONNX-only
- **Deps**: L-LANDMARKS-02
- **Size**: M (1-2 hrs)

### L-LANDMARKS-04: Enrich detail pages with AI context [MEDIUM]
- **File**: `app/api/explore.py` → `get_landmark()` endpoint
- **What**:
  - For non-curated sites (no `highlights`, `visiting_tips`, `historical_significance`), call Gemini to generate these fields on first access
  - Cache generated fields in memory (LRU) or in a companion JSON file
  - Prompt: "You are an Egyptian history expert. For [landmark name] in [city], provide: highlights (3-5 bullet points), visiting tips (2-3 tips), historical significance (1-2 sentences)."
  - Don't overwrite curated data — only fill empty fields
- **Why**: Non-curated detail pages are sparse; AI can fill gaps with quality historical info
- **Deps**: L-LANDMARKS-01
- **Size**: M (1-2 hrs)

### L-LANDMARKS-05: Add TLA API integration for Egyptological grounding [LOW]
- **File**: NEW `app/core/tla_service.py`, optionally integrate into explore detail
- **What**:
  - TLA (Thesaurus Linguae Aegyptiae) API at `https://api.thesaurus-linguae-aegyptiae.de/` is free, no key needed
  - 90,000 ancient Egyptian lemmas with transliteration, translation, attestations
  - For pharaonic landmarks: look up known ancient Egyptian names and add to detail page
  - For Thoth chatbot: ground answers in scholarly TLA data
- **Why**: Adds scholarly credibility and unique data that AI models can't fabricate
- **Deps**: None
- **Size**: L (2-3 hrs)

### L-LANDMARKS-06: Test identify fallback chain [HIGH]
- **File**: Script `scripts/test_identify.py` (update existing)
- **What**:
  - Test with 5+ known landmark photos
  - Verify each fallback layer works: block Gemini → Groq handles it → block Groq → Grok handles it
  - Verify ensemble merge logic produces correct result
  - Verify not-Egyptian detection works
  - Verify empty descriptions get AI-generated content
- **Deps**: L-LANDMARKS-02
- **Size**: S (45 min)

**Phase L-LANDMARKS Total: 6 tasks, ~9-13 hours**

---

## Updated Summary

| Phase | Tasks | Hours | Priority |
|-------|-------|-------|----------|
| H-FIX | 19 | 13-16 | NOW — everything broken |
| H-VISION | 8 | 12-17 | HIGH — biggest quality jump |
| H-TRANSLATE | 6 | 7-11 | HIGH — enables proper translations |
| H-AUDIO | 5 | 5-8 | MEDIUM — nice-to-have feature |
| **W-WRITE** | **7** | **8-12** | **HIGH — write feature currently unreliable** |
| **L-LANDMARKS** | **6** | **9-13** | **MEDIUM — works but can be much better** |
| H-DETECTOR | 6 | 16-23 | LOW — AI Vision handles this |
| **TOTAL** | **57** | **70-100** | — |

