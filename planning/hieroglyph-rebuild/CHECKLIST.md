# Wadjet v2 — Hieroglyph Rebuild: Quality Checklist

> Pass ALL gates before declaring a phase complete.
> Each gate has specific, measurable criteria.

---

## Phase H-FIX: Critical Bug Fixes

### Gate: "Pipeline Works Correctly"

- [ ] **FIX-G0A**: Config points to FP32 classifier (`hieroglyph_classifier.onnx`) not uint8
- [ ] **FIX-G0B**: FP32 model tracked via git LFS and whitelisted in .gitignore
- [ ] **FIX-G0C**: Classifier on test images returns top-1 confidence > 50% (not 0.6%)
- [ ] **FIX-G0D**: JS pipeline also uses FP32 model URL
- [ ] **FIX-G1**: Python scan runs without any exceptions on 10 test images
- [ ] **FIX-G2**: `asyncio` warning gone — no deprecation warnings in log
- [ ] **FIX-G3**: Config `detection_confidence_threshold` change actually affects detection count
- [ ] **FIX-G4**: `/api/translate` endpoint returns 200 with valid JSON for valid MdC input
- [ ] **FIX-G5**: JS pipeline's `translate()` successfully calls `/api/translate` and displays result
- [ ] **FIX-G6**: JS Gardiner map covers all 171 model classes (0 "Unknown" labels)
- [ ] **FIX-G7**: Unknown signs produce `[?]` not crash or empty string
- [ ] **FIX-G8**: Reading direction returns "left-to-right" on at least one test image (not always RTL)
- [ ] **FIX-G9**: Grok tiebreaker actually returns a response (not silent failure)
- [ ] **FIX-G10**: Bilingual translation returns both EN + AR in single call
- [ ] **FIX-G11**: Camera mode doesn't exceed 10 FPS inference rate
- [ ] **FIX-G12**: No `evaluate_conf_threshold()` in production code
- [ ] **FIX-G13**: HuggingFace Space deploys and scans successfully

---

## Phase H-VISION: AI Vision Reader

### Gate: "AI Reads Inscriptions Accurately"

- [ ] **VIS-G1**: Gemini Vision reads Rosetta Stone fragment → produces valid Gardiner sequence with ≥10 correctly identified signs
- [ ] **VIS-G2**: AI reader returns structured JSON with all required fields (glyphs, transliteration, translation_en, direction)
- [ ] **VIS-G3**: Fallback chain works: block Gemini → Groq handles request → block Groq → Grok handles request
- [ ] **VIS-G4**: Key rotation demonstrates: consecutive requests use different API keys
- [ ] **VIS-G5**: Mode selector in UI switches between AI/ONNX/Auto and shows result source
- [ ] **VIS-G6**: Auto mode: ONNX bboxes displayed on image + AI reading shown as text
- [ ] **VIS-G7**: Cross-validator produces merged result when both AI and ONNX available
- [ ] **VIS-G8**: Full scan (AI mode) completes in < 8 seconds average
- [ ] **VIS-G9**: When all APIs down, ONNX-only result returned with "offline" indicator
- [ ] **VIS-G10**: `/api/read` endpoint returns valid JSON within 5 seconds

### Benchmark: Compare AI vs ONNX on 10 Test Images
| Image | ONNX Signs Found | AI Signs Found | ONNX Correct% | AI Correct% |
|-------|-----------------|---------------|---------------|-------------|
| rosetta_fragment.jpg | ? | ? | ? | ? |
| karnak_pillar.jpg | ? | ? | ? | ? |
| tutankhamun_tomb.jpg | ? | ? | ? | ? |
| ... | | | | |

**Target**: AI correct% > 70% on average (vs ONNX ~5-15%)

---

## Phase H-TRANSLATE: Translation Engine

### Gate: "Translations Are Meaningful"

- [x] **TRN-G1**: New embedding model produces different vectors for different MdC strings (cosine sim 0.57-0.72 for dissimilar pairs)
- [x] **TRN-G2**: RAG retrieves relevant corpus examples (0.87-0.96 similarity, verified 5 queries)
- [x] **TRN-G3**: Translation of `Htp di nsw` returns "an offering the king makes" / "A royal offering"
- [x] **TRN-G4**: Arabic translation present and grammatically correct for 5/5 test cases
- [x] **TRN-G5**: Translation cache works: second identical request returns in 0.0ms (< 100ms)
- [x] **TRN-G6**: Groq fallback translation works when Gemini is blocked (provider=groq)
- [x] **TRN-G7**: BLEU score on 20 known inscriptions = 0.594 (> 0.3 threshold), 70% pass rate
- [x] **TRN-G8**: Single API call for bilingual (EN + AR + context in one JSON response)

---

## Phase H-AUDIO: Voice Features

### Gate: "User Can Listen to Results"

- [x] **AUD-G1**: TTS "Listen" button appears next to transliteration, English, and Arabic translation in scan results
- [x] **AUD-G2**: Clicking "Listen" speaks the English translation via WadjetTTS.speakToggle (en voice)
- [x] **AUD-G3**: Arabic "Listen" button speaks Arabic text with lang='ar' voice selection
- [x] **AUD-G4**: Play/Pause toggle via WadjetTTS.speakToggle + Alpine.js state poller (250ms)
- [x] **AUD-G5**: Dictionary page: speakSign() plays pronunciation for each phonetic sign (server TTS → Web Speech fallback)
- [x] **AUD-G6**: TTS works offline via Web Speech API (WadjetTTS module, no server needed)
- [x] **AUD-G7**: Groq TTS endpoint POST /api/tts — PlayAI model, returns audio/wav, with server fallback in tts.js
- [x] **AUD-G8**: STT: "Speak" button in scan.html → MediaRecorder → POST /api/stt (Groq Whisper) → voiceText
- [x] **AUD-G9**: No TTS errors — WadjetTTS checks isSupported() before rendering buttons, clean stop on reset/destroy

---

## Phase H-DETECTOR: Model Improvement

### Gate: "Models Meet Quality Thresholds"

- [ ] **DET-G1**: Detection mAP50 ≥ 0.85 (current: 0.71)
- [ ] **DET-G2**: Detection recall ≥ 0.80 (current: 0.64)
- [ ] **DET-G3**: Classifier test accuracy ≥ 98% (maintained)
- [ ] **DET-G4**: Classifier real-stone accuracy ≥ 50% (current: 5-15%)
- [ ] **DET-G5**: Cleaned dataset has < 5% mislabeled images
- [ ] **DET-G6**: New ONNX models exported and work in both Python and JS pipelines
- [ ] **DET-G7**: Before/after comparison on 10 real stone images shows improvement

---

## Phase W-WRITE: Write Feature Quality

### Gate: "Write Feature Produces Correct Output"

- [ ] **WRT-G1**: Smart mode: "life" → output contains `anx` (Gardiner A1 or equivalent ankh sign)
- [ ] **WRT-G2**: Smart mode: "son of ra" → output contains `sA` + `ra` signs
- [ ] **WRT-G3**: Smart mode: "an offering which the king gives" → output contains `Htp di nsw` signs
- [ ] **WRT-G4**: Smart mode: "words to be spoken" → output contains `Dd mdw` signs
- [ ] **WRT-G5**: Smart mode: "given life forever" → output contains `Dj anx Dt` signs
- [ ] **WRT-G6**: Smart mode returns NO non-existent Gardiner codes on 10 test phrases
- [ ] **WRT-G7**: MdC mode: `Htp-di-nsw` produces correct signs (R4, X8, S40, M23, X1, or close)
- [ ] **WRT-G8**: MdC mode: all 26 uniliteral signs parse correctly
- [ ] **WRT-G9**: Smart mode fallback: block Gemini → Groq handles request → output still reasonable
- [ ] **WRT-G10**: Alpha mode: all 26 English letters produce a glyph (no unknown)
- [ ] **WRT-G11**: Known phrase shortcuts return correct output in < 50ms (no AI call)
- [ ] **WRT-G12**: `scripts/test_write.py` passes with ≥ 70% accuracy on smart mode

---

## Phase L-LANDMARKS: Landmarks Enhancement

### Gate: "Landmarks Feature Is Comprehensive and Reliable"

- [ ] **LM-G1**: Zero landmarks with empty description in `/api/landmarks` response
- [ ] **LM-G2**: Non-curated detail pages show highlights + visiting_tips (AI-generated)
- [ ] **LM-G3**: Identify works when Gemini blocked → Groq provides result
- [ ] **LM-G4**: Identify works when Gemini + Groq blocked → Grok provides result
- [ ] **LM-G5**: Not-Egyptian detection still works with new fallback chain
- [ ] **LM-G6**: AI-generated descriptions are cached (second request is instant)
- [ ] **LM-G7**: `scripts/test_identify.py` passes all landmark identification tests

---

## Overall Launch Gate

### Gate: "Hieroglyph System is Production Ready"

- [ ] **LAUNCH-G1**: All Phase H-FIX gates pass
- [ ] **LAUNCH-G2**: All Phase H-VISION gates pass
- [ ] **LAUNCH-G3**: All Phase H-TRANSLATE gates pass
- [ ] **LAUNCH-G4**: All Phase H-AUDIO mandatory gates pass (G1-G6)
- [ ] **LAUNCH-G5**: HuggingFace Space: scan works end-to-end (upload → bboxes → reading → translation → TTS)
- [ ] **LAUNCH-G6**: Local dev: all 3 modes work (AI, ONNX, Auto)
- [ ] **LAUNCH-G7**: No console errors or Python exceptions on happy path
- [ ] **LAUNCH-G8**: Response time < 10 seconds for full AI scan
- [ ] **LAUNCH-G9**: Fallback to ONNX-only works when offline
- [ ] **LAUNCH-G10**: README updated with new architecture description
