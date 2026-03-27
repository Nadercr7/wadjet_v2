# Wadjet v2 — Hieroglyph System: Master Plan

> Complete rebuild plan for a production-quality hieroglyph reading system.
> Goal: Upload a photo → get accurate glyph identification + scholarly translation + audio.

---

## The Core Insight

When a vision API looks at a hieroglyph photo, it can read it correctly.
When our ONNX pipeline does it, it fails — 3-5 blurry detections, random classifications, garbage transliteration.

**The solution: Make AI vision the PRIMARY reader, not the fallback.**

Current architecture (broken chain):
```
Photo → ONNX Detect → ONNX Classify → Rule-Based Translit → RAG+Gemini Translate
         ↓ fails         ↓ fails          ↓ fails              ↓ random
       3 boxes        wrong codes       wrong MdC           wrong translation
```

New architecture (AI-first, ONNX-assisted):
```
Photo ──┬──→ Gemini Vision (PRIMARY) ──→ Full Reading + Translation
        │     Gardiner codes, MdC, direction, translation
        │
        └──→ ONNX Pipeline (SECONDARY, parallel)
              Detect → Classify → Translit
              
        ──→ Cross-Validate & Merge ──→ Final Result + Confidence Score
        ──→ TTS (Browser Web Speech API) ──→ Audio playback
```

---

## Design Principles

1. **AI-First**: Gemini/Groq Vision reads the inscription — this is our strongest capability
2. **ONNX-Assisted**: ONNX provides fast bounding boxes for visualization + offline capability
3. **Multi-Model Verification**: Cross-validate AI reading vs ONNX classification
4. **Graceful Degradation**: Works offline (ONNX-only), better online (AI-enhanced)
5. **Multi-API Redundancy**: Gemini → Groq → Cohere → offline ONNX (never stuck)
6. **Fix Every Bug**: Every issue from PROBLEM_ANALYSIS.md gets resolved

---

## Architecture Components

### Component 1: AI Vision Reader (NEW — Primary)
- **What**: Gemini 2.5 Flash reads the full inscription in one call
- **Input**: Original photo (full resolution JPEG)
- **Output**: Structured JSON with glyphs, Gardiner codes, bounding box estimates, MdC, translation
- **Fallback chain**: Gemini → Groq (Llama 4 Scout with vision) → Grok → ONNX-only
- **Why**: AI vision models are already excellent at reading hieroglyphs. We tested this — Gemini correctly identifies inscriptions that our ONNX pipeline completely fails on.

### Component 2: ONNX Detection (IMPROVED — Secondary)
- **What**: YOLO26s detector finds glyph bounding boxes
- **Purpose**: Visual annotation (draw boxes on image), offline fallback, crop extraction for verification
- **Improvements needed**:
  - Retrain with more diverse data (annotate the 438 scraped museum images)
  - If possible, train on Kaggle with more epochs and the full diverse dataset
  - Lower priority since AI Vision is primary

### Component 3: ONNX Classification (IMPROVED — Verification)
- **What**: MobileNetV3 classifies individual glyph crops
- **Purpose**: Cross-validate AI reading, provide individual glyph confidence
- **Improvements needed**:
  - Augment training data with stone texture overlays (bridge domain gap)
  - Add test-time augmentation (TTA) for better confidence calibration
  - Temperature scaling for calibrated confidence scores

### Component 4: Smart Transliteration (FIXED)
- **What**: Convert Gardiner codes → MdC notation
- **Improvements needed**:
  - Fix reading direction detection (use AI + facing sign analysis)
  - Fix quadrat notation for unknown signs
  - Fix logogram/determinative classification
  - Port V1's complete GardinerSign mappings (phonetic values for all 171 model classes)

### Component 5: Translation Engine (REBUILT)
- **What**: Translate MdC → English + Arabic
- **Current issue**: RAG embeddings are meaningless for MdC strings
- **New approach**: 
  - **Primary**: Gemini already provides translation in the vision response
  - **Enhancement**: Use Gemini text model with curated scholarly prompt + top corpus examples
  - **Better RAG**: Replace `all-MiniLM-L6-v2` with Voyage AI `voyage-4-large` (200M free tokens, highest quality) or `voyage-multimodal-3.5` (embed images + text in same vector space)
  - **Bilingual in one call**: Single prompt for EN + AR instead of 2 sequential calls

### Component 6: TTS (NEW)
- **What**: Read aloud the translation and transliteration
- **Implementation**: Browser Web Speech API (proven in V1, zero cost, offline)
- **Languages**: English, Arabic, French, German
- **Interface**: Toggle button on results, auto-play option

### Component 7: `/api/translate` Endpoint (NEW)
- **What**: Standalone translation endpoint for client-side pipeline
- **Input**: MdC transliteration string (JSON body)
- **Output**: English + Arabic translation
- **Fixes**: C2 bug (JS translate() currently broken)

### Component 8: Multi-API Strategy (NEW — 11 providers, all free)
- **Gemini** (17 keys): Primary vision reader + translation + chat
- **Groq** (free tier): Fast Llama inference, Whisper STT, PlayAI TTS
- **Grok** (8 keys): Tiebreaker for disagreements
- **Cloudflare Workers AI** (10K neurons/day free forever): Vision (Llama-3.2-V, Mistral Small 3.1), STT, TTS (MeloTTS), embeddings (bge-m3)
- **Voyage AI** (200M tokens lifetime free): Best embeddings for RAG, multimodal (images+text), reranking
- **Cohere** (free trial): embed-multilingual-v3.0, Rerank for corpus search
- **OpenRouter** (free tier): 29+ free models as emergency fallback
- **Google Cloud TTS** (4M chars/month free): Arabic Neural voices for translation readback
- **ElevenLabs** (10K credits/month): Premium TTS for narrations
- **Deepgram** ($200 credit): Nova-3 STT (Arabic + English, 430 hrs)
- **TLA API** (free, no key): 90,000 ancient Egyptian lemmas for dictionary/Thoth grounding

---

## Phases

### Phase H-FIX: Bug Fixes (Fix Everything That's Broken)
Fix all C/H/M bugs from PROBLEM_ANALYSIS.md without changing architecture.
- ~2-3 sessions
- No model retraining needed
- Immediate quality improvement

### Phase H-VISION: AI Vision Primary Reader
Build the AI-first reading pipeline.
- ~2-3 sessions
- Gemini Vision integration as primary
- Groq/Grok fallback chain
- Cross-validation with ONNX

### Phase H-TRANSLATE: Translation Rebuild
Fix RAG, rebuild translation engine, add bilingual single-call.
- ~1-2 sessions
- Better embeddings (Gemini/Cohere)
- New `/api/translate` endpoint
- Bilingual in one prompt

### Phase H-AUDIO: TTS + Audio Features
Add voice output and optionally voice input.
- ~1 session
- Web Speech API TTS (from V1)
- Groq Whisper STT (optional)

### Phase H-DETECTOR: Detector v3 Training (Optional)
Retrain YOLO26s with more diverse data.
- ~2-3 sessions
- Annotate 438 scraped museum images
- Scrape more data if needed
- Target: mAP50 ≥ 0.85

### Phase W-WRITE: Write Feature Quality (NEW)
Fix the "Write in Hieroglyphs" feature so it actually produces correct translations.
- ~1-2 sessions
- Smart mode prompt rewrite with few-shot examples from corpus
- Groq/Grok fallback chain for AI mode
- Verification: known phrases must produce correct Gardiner sequences
- MdC mode improvements for complete coverage

### Phase L-LANDMARKS: Landmarks Enhancement (NEW)
Use the multi-API strategy to improve the landmarks/explore features.
- ~1-2 sessions
- AI-generated descriptions for all 161+ sites (fill empty descriptions)
- Groq/Cloudflare as fallback for identify when Gemini is rate-limited
- Richer detail pages with AI-enhanced historical context
- Better slug resolution and error handling

---

## Quality Gates (End State)

| Metric | Target | How to Test |
|--------|--------|-------------|
| Glyph identification accuracy | ≥ 85% on 20 real stone photos | Human evaluation: AI reads inscription, compare to known reading |
| Translation quality | Scholarly-quality for common formulae | Compare to Fayrose corpus ground truth |
| HF Space works | No crashes, no 422s, no missing files | Test all 3 modes: server, client, AI-first |
| Client-side translation | Actually works | Test JS pipeline translate() → /api/translate |
| Reading direction | Correct for RTL and LTR inscriptions | Test with known LTR examples |
| TTS playback | Works in Chrome/Safari/Firefox | Play translations in EN and AR |
| Offline mode | Detection + classification work without internet | Disable network, test client mode |
| API latency | Full pipeline < 5 seconds with AI | Time full scan including translation |
| Error rate | Zero crashes on valid images | Upload 100 varied images |
| Write: smart mode accuracy | Known phrases produce correct glyphs | Test 10 known phrases (offering formula, titles, etc.) |
| Write: no garbage output | Only valid Gardiner codes in output | No empty unicode chars or [?] for known MdC |
| Landmarks: zero empty descriptions | All 161+ sites have descriptions | Check /api/landmarks response |
| Landmarks: identify fallback | Works when Gemini is down | Block Gemini, test Groq/Grok fallback |

---

## File Structure

```
planning/hieroglyph-rebuild/
├── MASTER_PLAN.md          ← this file
├── PROBLEM_ANALYSIS.md     ← all bugs documented
├── SYSTEM_DESIGN.md        ← detailed architecture + API flows
├── REBUILD_TASKS.md        ← every task, every phase
├── API_STRATEGY.md         ← multi-API setup (Gemini/Groq/Cohere/Grok)
├── CHECKLIST.md            ← pre-launch quality gates
├── PROGRESS.md             ← session-by-session progress
└── START_PROMPTS.md        ← ready-to-paste prompts per phase
```

---

## Key Decision: Why AI-First?

**Evidence**: When I analyzed the current pipeline:
- ONNX detector: 3 glyphs found (should be 20+)
- ONNX classifier: 7-16% confidence (should be >80%)
- Transliteration: garbled output from wrong codes
- Translation: fails at multiple levels

**Meanwhile**: Gemini Vision, when asked to read the SAME image:
- Identifies 15+ glyphs correctly
- Provides Gardiner codes with explanations
- Reads in correct direction
- Translates with scholarly accuracy

The gap is enormous. Fixing the ONNX pipeline to match AI vision quality would require:
1. 5x more training data (diverse stone photos, all annotated)
2. Multiple training iterations on Kaggle
3. Domain adaptation for the classifier
4. Building image-level orientation analysis from scratch

**OR** we make one Gemini API call and get all of that for free.

The ONNX pipeline still has value:
- Offline capability (no internet needed)
- Speed (faster than API call for detection visualization)
- Visual annotation (drawing boxes on images)
- Cross-validation (catch AI hallucinations by comparing to ONNX)

So we keep both, but invert the priority. AI is primary, ONNX is secondary.
