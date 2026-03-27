# Wadjet v2 — Hieroglyph System: Detailed System Design

> Technical architecture for the AI-first hieroglyph reading system.
> Every component, every API flow, every data structure.

---

## System Overview

```
                            ┌─────────────────────────────┐
                            │     User uploads photo       │
                            └──────────────┬──────────────┘
                                           │
                     ┌─────────────────────┼─────────────────────┐
                     │                     │                     │
              ┌──────▼──────┐     ┌────────▼────────┐    ┌──────▼──────┐
              │ Server Mode │     │  Client Mode     │    │  AI Mode    │
              │  POST /api/ │     │  ONNX in Browser │    │  (default)  │
              │   scan      │     │  + /api/translate │    │             │
              └──────┬──────┘     └────────┬────────┘    └──────┬──────┘
                     │                     │                     │
                     ▼                     ▼                     ▼
              ┌──────────────────────────────────────────────────────┐
              │              UNIFIED RESULT FORMAT                    │
              │  glyphs[], gardiner_sequence, transliteration,       │
              │  translation_en, translation_ar, direction,          │
              │  timing, confidence, source ("onnx"|"gemini"|"groq") │
              └──────────────────────────────────────────────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │  TTS Output  │
                                    │ Web Speech   │
                                    └─────────────┘
```

---

## Processing Modes

### Mode 1: AI-First (Default, recommended, requires internet)
```
Photo → Gemini Vision (full reading) ─── ┐
Photo → ONNX Detect (bboxes for UI) ──── ┤
                                          ▼
                              Merge & Cross-Validate
                                          │
                     ┌────────────────────┤
                     │ If Gemini fails:   │
                     ▼                    ▼
              Groq Vision fallback   ONNX classify + translit
                     │                    │
                     ▼                    ▼
              Final Result ←──── Best available reading
```

### Mode 2: Server ONNX (fallback, lower quality, faster)
```
Photo → ONNX Detect → ONNX Classify → Translit → Gemini Translate
                                                       │
                                              (if offline: skip translate)
```

### Mode 3: Client ONNX (fully offline, lowest quality)
```
Photo → ONNX Detect (WASM) → ONNX Classify (WASM) → JS Translit
                                                         │
                                                  /api/translate (if online)
```

---

## Component 1: AI Vision Reader

### New file: `app/core/ai_reader.py`

```python
class AIHieroglyphReader:
    """Reads hieroglyphic inscriptions using vision AI models.
    
    Fallback chain: Gemini → Groq → Grok → None
    """
    
    async def read_inscription(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> InscriptionReading | None:
        """Read full inscription from image.
        
        Returns structured reading with:
        - glyphs: list of {gardiner_code, bbox_pct, confidence, description}
        - gardiner_sequence: "G1-D21-M17-N35"
        - transliteration: MdC string
        - translation_en: English translation
        - translation_ar: Arabic translation
        - direction: "right-to-left" | "left-to-right"
        - notes: scholarly context
        """
```

### Gemini Vision Prompt (Egyptologist Expert)
```
You are a world-class Egyptologist with complete mastery of the Gardiner 
Sign List (700+ hieroglyphs). You can read ancient Egyptian hieroglyphic 
inscriptions from photographs with near-perfect accuracy.

TASK: Read the hieroglyphs in this photograph.

For EACH hieroglyph visible:
1. Identify its Gardiner code (e.g., G1, D21, M17)
2. Estimate its bounding box as percentages [x1%, y1%, x2%, y2%]
3. Note if it's a phonogram, logogram, or determinative
4. Provide its phonetic value

Then:
5. Determine reading direction (look at which way birds/people face)
6. Read the inscription in correct order
7. Provide MdC (Manuel de Codage) transliteration
8. Provide literal word-for-word English translation
9. Provide Arabic translation
10. Add brief scholarly notes (e.g., "royal titulary", "offering formula")

Return ONLY valid JSON in this exact format:
{
  "glyphs": [
    {
      "gardiner_code": "G1",
      "bbox_pct": [10.0, 20.0, 25.0, 45.0],
      "confidence": 0.95,
      "type": "uniliteral",
      "phonetic": "A",
      "description": "Egyptian vulture"
    }
  ],
  "direction": "right-to-left",
  "gardiner_sequence": "G1-D21-M17-N35",
  "transliteration": "A-r-i-n",
  "translation_en": "the son of Ra",
  "translation_ar": "ابن رع",
  "notes": "Royal titulary formula from the New Kingdom period"
}
```

### Groq Vision Fallback
- Model: `meta-llama/llama-4-scout-17b-16e-instruct` (vision capable)
- Same prompt structure, adapted format
- Free tier: 1000 req/day, 30 req/min
- Endpoint: `https://api.groq.com/openai/v1/chat/completions`

### Grok Vision Fallback  
- Model: `grok-4-latest` (vision capable)
- 8 API keys available
- Fix: Upload image to temp URL instead of base64 data URI

---

## Component 2: Improved Scan Pipeline

### Modified: `app/api/scan.py`

```python
@router.post("/scan")
async def scan_image(request, file, translate=True, mode="auto"):
    """
    Modes:
    - "auto" (default): AI-first with ONNX assist
    - "onnx": ONNX pipeline only (faster, offline compatible)
    - "ai": AI vision only (best quality, requires internet)
    
    Flow for "auto":
    1. Start ONNX detection in background (for bounding boxes)
    2. Send image to AI Vision Reader (primary reading)
    3. If AI succeeds:
       - Use AI reading for glyphs, translation, direction
       - Use ONNX bboxes for visualization (if available)
       - Cross-validate: compare AI codes vs ONNX codes
    4. If AI fails:
       - Fall back to ONNX pipeline
       - Attempt Gemini text-only translation
    5. Return unified result
    """
```

### New: `/api/translate` endpoint
```python
@router.post("/translate")
async def translate_text(request, body: TranslateRequest):
    """Translate MdC transliteration to English + Arabic.
    
    Input: {"transliteration": "sA-ra-nb-pt", "gardiner_sequence": "G39-D21-V30-N1"}
    Output: {"translation_en": "...", "translation_ar": "...", "source": "gemini"}
    """
```

### New: `/api/read` endpoint (AI-only reading)
```python
@router.post("/read")
async def read_inscription(request, file):
    """AI Vision reads inscription directly.
    
    Lighter than /scan — no ONNX, no cross-validation.
    Used by client-side pipeline for translation step.
    """
```

---

## Component 3: Translation Engine Rebuild

### Modified: `app/core/rag_translator.py`

**Changes:**
1. Replace `all-MiniLM-L6-v2` with Gemini `text-embedding-004` (768-dim, handles MdC better)
2. Bilingual in one call (EN + AR together, not sequential)
3. Better prompt with scholarly corpus examples
4. Fallback: Groq Llama for translation if Gemini is rate-limited

### New embedding strategy:
```python
# Option A: Voyage AI voyage-4-large ⭐ BEST
# 200M free tokens LIFETIME, OpenAI-compatible API
# High quality multilingual embeddings
# voyage-multimodal-3.5: embed hieroglyph images + MdC text in SAME vector space
# rerank-2.5: 200M free tokens for reranking RAG results

# Option B: Gemini text-embedding-004
# 768 dimensions, free, unlimited calls
# Already have API keys

# Option C: Cohere embed-multilingual-v3.0
# 1024 dimensions, 100+ languages
# Free tier: 1000 API calls/month — limited

# Option D: Cloudflare bge-m3
# Free 10K neurons/day, multilingual

# Decision: Use Voyage AI (200M tokens = ~2M documents, highest quality)
# Backup: Gemini embedding (unlimited, already have keys)
# Rebuild FAISS index with Voyage voyage-4-large embeddings
```

### Bilingual translation prompt:
```
You are an expert Egyptologist. Translate this Ancient Egyptian inscription.

REFERENCE EXAMPLES from a scholarly corpus:
{top_5_examples}

INPUT: {mdc_transliteration}
GARDINER: {gardiner_sequence}

Provide:
1. Literal English translation (word-for-word, scholarly)
2. Arabic translation (فصحى)
3. Brief context note (what type of inscription: offering formula, royal titulary, etc.)

Return JSON:
{
  "translation_en": "...",
  "translation_ar": "...",
  "context": "..."
}
```

---

## Component 4: TTS (Text-to-Speech)

### New file: `app/static/js/tts.js` (port from V1)

```javascript
var WadjetTTS = {
    speak: function(text, opts) { /* Web Speech API */ },
    pause: function() {},
    resume: function() {},
    stop: function() {},
    isSupported: function() { return 'speechSynthesis' in window; },
    attachButton: function(btn, textFn, opts) { /* toggle on/off */ },
    pickVoice: function(lang) { /* prefer non-Google voices */ },
};
```

### UI Integration (scan.html):
- "Listen" button next to translation text
- Language selector (EN/AR/FR/DE)
- Auto-read option in settings
- Read both transliteration (phonetic) and translation

### Optional: Groq TTS
- Endpoint: `POST https://api.groq.com/openai/v1/audio/speech`
- Model: `playai-tts` or `playai-tts-arabic`
- Higher quality than Web Speech API, but requires internet
- Free tier available

### Optional: Groq STT (Speech-to-Text)
- Model: `whisper-large-v3-turbo` (Groq free tier)
- User speaks a question about hieroglyphs → transcribed → sent to Thoth chatbot
- Or: Describe what you see → AI helps identify

---

## Component 5: Cross-Validation Engine

### New file: `app/core/cross_validator.py`

```python
class CrossValidator:
    """Compare AI reading vs ONNX classification results.
    
    Resolves disagreements, calculates confidence, flags uncertainties.
    """
    
    def validate(
        self,
        ai_reading: InscriptionReading,
        onnx_glyphs: list[GlyphResult],
    ) -> ValidatedResult:
        """
        For each AI-detected glyph:
        1. Find matching ONNX detection (by bbox overlap)
        2. Compare Gardiner codes
        3. If they agree → high confidence
        4. If they disagree → use the more confident source
        5. If only AI detected it → trust AI (ONNX missed it)
        6. If only ONNX detected it → trust ONNX (AI missed it)
        """
```

---

## Component 6: Multi-API Service

### New file: `app/core/ai_service.py`

```python
class AIService:
    """Unified AI service with automatic fallback across providers.
    
    Providers (in priority order):
    1. Gemini (17 keys, primary for vision + translation + embedding)
    2. Groq (free tier, fast inference, vision via Llama 4 Scout)
    3. Grok (8 keys, tiebreaker)
    4. Cohere (free tier, embedding + rerank for RAG)
    5. OpenRouter (29+ free models, emergency fallback)
    """
    
    async def vision_read(self, image_bytes, mime) -> dict:
        """Try vision providers in order until one succeeds."""
        
    async def translate(self, mdc, gardiner_seq) -> dict:
        """Try translation providers in order."""
        
    async def embed(self, texts) -> np.ndarray:
        """Get embeddings for RAG."""
        
    async def tts(self, text, lang) -> bytes | None:
        """Optional server-side TTS via Groq."""
```

### Config additions (`app/config.py`):
```python
# Groq
groq_api_key: str = ""

# Cohere
cohere_api_key: str = ""

# OpenRouter
openrouter_api_key: str = ""
```

---

## Data Flow: Complete Scan (AI-First Mode)

```
1. User uploads photo
2. Frontend sends POST /api/scan?mode=auto

3. Server receives image
   ├── Async Task A: ONNX detect (500ms)
   │   └── Returns: bounding boxes for visualization
   │
   └── Async Task B: AI Vision read (1-3s)
       └── Gemini reads full inscription
       └── If Gemini fails → try Groq → try Grok
       └── Returns: glyphs, MdC, translation EN+AR, direction

4. If Task B succeeded:
   ├── Use AI reading for text results
   ├── Use Task A bboxes for visualization (if available)
   ├── Cross-validate AI codes vs ONNX codes (optional, when both available)
   └── Return merged result

5. If Task B failed (all APIs down):
   ├── Use Task A (ONNX detect + classify)
   ├── Run transliteration
   ├── Skip translation (no API available)
   └── Return ONNX-only result with note

6. Frontend renders results
   ├── Detection image with bounding boxes
   ├── Glyph cards with Unicode, Gardiner code, confidence
   ├── Transliteration + direction
   ├── Translation EN + AR
   └── TTS buttons (Web Speech API)
```

---

## Client-Side Flow (Offline Capable)

```
1. User uploads photo (client mode selected)
2. JS pipeline:
   ├── ONNX detect (WASM, 500ms)
   ├── ONNX classify (WASM, per-glyph 50ms → batch to single call)
   ├── JS transliteration (instant)
   └── Result displayed

3. If online: POST /api/translate with MdC string
   └── Server translates via Gemini/Groq
   └── Returns EN + AR translation

4. If offline: Show transliteration only, no translation
   └── "Translation requires internet connection"

5. TTS: Web Speech API (works offline for built-in voices)
```

---

## Bug Fixes Required (Phase H-FIX)

### Python Backend:
| ID | Fix | File |
|----|-----|------|
| C3 | `asyncio.get_event_loop()` → `asyncio.get_running_loop()` | scan.py |
| H1 | Wire `detection_confidence_threshold` from config to pipeline | dependencies.py |
| H2 | Implement basic direction detection (use facing sign analysis from AI reading) | reading_order.py |
| H5 | Add confidence check before full-sequence verify (skip if avg > 0.6) | scan.py |
| H6 | Bilingual in one call | rag_translator.py |
| H7 | Fix Grok vision: upload image properly instead of base64 data URI | scan.py |
| M1 | Fix return type hint | postprocess.py |
| M4 | Handle unknown signs in quadrat notation | transliteration.py |
| M5 | Separate logogram vs determinative classification | gardiner.py |
| M6 | Rename variables for clarity | postprocess.py |
| L3 | Move `evaluate_conf_threshold()` to scripts/ | postprocess.py |

### JavaScript Frontend:
| ID | Fix | File |
|----|-----|------|
| C2 | Create `/api/translate` endpoint + update JS to use it | scan.py + pipeline.js |
| H3 | Fix line clustering to use full line extent | pipeline.js |
| H4 | Complete Gardiner map for all 171 model classes | pipeline.js |
| M2 | Batch ONNX classification (single tensor) | pipeline.js |
| M3 | Camera loop: min 100ms delay or requestAnimationFrame | pipeline.js |

---

## New Files to Create

| File | Purpose |
|------|---------|
| `app/core/ai_reader.py` | AI Vision inscription reader (Gemini/Groq/Grok) |
| `app/core/ai_service.py` | Unified multi-API service with fallback |
| `app/core/cross_validator.py` | Cross-validate AI vs ONNX results |
| `app/static/js/tts.js` | Text-to-speech (Web Speech API) |
| `app/api/translate.py` | `/api/translate` and `/api/read` endpoints |

## Files to Modify

| File | Changes |
|------|---------|
| `app/api/scan.py` | Add AI-first mode, fix bugs C3/H5/H7 |
| `app/core/rag_translator.py` | New embeddings, bilingual single-call |
| `app/core/reading_order.py` | Direction detection using AI or facing signs |
| `app/core/transliteration.py` | Fix quadrat notation, determinative handling |
| `app/core/gardiner.py` | Fix logogram/determinative overlap |
| `app/core/hieroglyph_pipeline.py` | Add AI-first mode support |
| `app/static/js/hieroglyph-pipeline.js` | Fix all JS bugs, add translate endpoint, complete Gardiner map |
| `app/templates/scan.html` | Add TTS buttons, mode selector, AI indicator |
| `app/config.py` | Add Groq/Cohere/OpenRouter keys |
| `app/dependencies.py` | Wire config to pipeline, add AI services |
| `app/main.py` | Register new API routers |
