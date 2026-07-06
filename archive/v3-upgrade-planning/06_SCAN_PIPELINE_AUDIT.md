# SCAN PIPELINE AUDIT — Current State + Upgrade Plan

> Covers: pipeline architecture, known issues, TTS integration, UX improvements.

---

## Current Architecture

```
User uploads image
        │
        ▼
  app/api/scan.py     ─── POST /api/scan
        │
        ▼
  HieroglyphPipeline.process_image()   ─── app/core/hieroglyph_pipeline.py
        │
        ├─► Detector (YOLOv8s ONNX)    ─── models/hieroglyph/detector/glyph_detector_uint8.onnx
        │     └─ Outputs: bounding boxes + confidence scores
        │
        ├─► Classifier (MobileNetV3)    ─── models/hieroglyph/classifier/hieroglyph_classifier.onnx
        │     └─ Outputs: Gardiner code per glyph (171 classes)
        │     └─ ⚠ Config default points to float32 model, not uint8
        │
        ├─► Transliteration             ─── app/core/transliteration.py
        │     └─ Gardiner code → phonetic transliteration
        │
        └─► RAG Translation             ─── app/core/rag_translator.py
              ├─ FAISS index             ─── data/embeddings/corpus.index
              ├─ Corpus IDs              ─── data/embeddings/corpus_ids.json
              └─ Gemini embeddings → AI verification (Gemini + Grok tiebreak)
```

---

## Known Issues

### Issue 1: Classifier Path Default (Config)

**File**: `app/config.py` line 65  
**Problem**: Default path is `hieroglyph_classifier.onnx` (float32, ~14MB) instead of `hieroglyph_classifier_uint8.onnx` (quantized, ~3.5MB).

**Current**:
```python
hieroglyph_classifier_path: str = "models/hieroglyph/classifier/hieroglyph_classifier.onnx"
```

**Fix**:
```python
hieroglyph_classifier_path: str = "models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx"
```

**Verify first**: Check if `hieroglyph_classifier_uint8.onnx` actually exists in the models directory.

---

### Issue 2: TTS Architecture Disconnect

**Problem**: The TTS service (`app/core/tts_service.py`) implements a 3-tier fallback chain:
1. Gemini 2.5 Flash TTS (Tier 1)
2. Groq PlayAI (Tier 2)  
3. Browser SpeechSynthesis (Tier 3, client-side)

But the `/api/tts` endpoint in `app/api/audio.py` **bypasses `tts_service.py`** and goes directly to Groq. Tier 1 (Gemini) is never used for TTS.

**Fix**: Refactor `/api/tts` to call `tts_service.synthesize()` instead of calling Groq directly.

---

### Issue 3: No Progress Feedback During Scan

**Problem**: User uploads an image and sees nothing until the entire pipeline completes (which can take 5-15 seconds with AI translation).

**Fix**: Add Server-Sent Events (SSE) or a polling mechanism to show progress:
- Step 1: "Detecting hieroglyphs..." (detector inference)
- Step 2: "Classifying N symbols..." (classifier inference)  
- Step 3: "Transliterating..." (fast, local)
- Step 4: "Translating inscription..." (AI call, slowest)
- Step 5: "Done! Found N hieroglyphs."

---

### Issue 4: No Image Preprocessing

**Problem**: Large camera photos (4000×3000+) are sent directly to ONNX inference, which can be slow or OOM. No HEIC/WebP handling.

**Fix**: Add preprocessing in `scan.py`:
```python
from PIL import Image
import io

MAX_DIM = 1024

async def preprocess_image(file_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(file_bytes))
    
    # Convert non-standard formats
    if img.format in ("HEIC", "HEIF"):
        # Requires pillow-heif
        img = img.convert("RGB")
    
    # Resize if too large
    w, h = img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    
    # Convert to RGB JPEG
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue()
```

---

### Issue 5: File Upload Validation

**Problem**: Only checks file extension, not magic bytes. A renamed `.exe` → `.jpg` would pass.

**Fix**: Add magic byte validation:
```python
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG': 'png',
    b'RIFF': 'webp',  # (first 4 bytes, then check for WEBP at offset 8)
    b'GIF8': 'gif',
}

def validate_image(data: bytes) -> bool:
    for magic, fmt in MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            return True
    return False
```

---

## Upgrade Plan

### Step 1: Fix TTS Service (Standalone)

1. Read current `app/core/tts_service.py` implementation
2. Read current `app/api/audio.py` implementation
3. Refactor `/api/tts` to call `tts_service.synthesize(text, lang, voice)`
4. Ensure 3-tier fallback works: Gemini → Groq → return `null` (client falls back to browser)
5. Test with curl: `POST /api/tts {"text": "hello", "lang": "en"}`

### Step 2: Fix Scan Pipeline Config

1. Verify uint8 classifier model exists
2. Update config.py default path
3. Verify pipeline still works with uint8 model

### Step 3: Add Image Preprocessing

1. Add `pillow-heif` to requirements.txt (for HEIC support)
2. Add preprocessing function in `scan.py`
3. Resize large images before inference
4. Convert WebP/HEIC to standard JPEG

### Step 4: Add Progress Feedback

Two options:

**Option A: SSE (Server-Sent Events)**
```python
@router.post("/api/scan/stream")
async def scan_with_progress(file: UploadFile):
    async def generate():
        yield f"data: {json.dumps({'step': 1, 'message': 'Detecting hieroglyphs...'})}\n\n"
        boxes = await pipeline.detect(image)
        yield f"data: {json.dumps({'step': 2, 'message': f'Classifying {len(boxes)} symbols...'})}\n\n"
        # ... etc
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Option B: Polling (Simpler)**
```python
# POST /api/scan → returns scan_id
# GET /api/scan/{scan_id}/status → returns current step
```

**Recommendation**: Use SSE (Option A) — it's simpler and HTMX has built-in SSE support.

### Step 5: Add TTS to Scan Results

1. After translation complete, add "Listen" button to results UI
2. Button calls `/api/tts` with the translation text
3. Use Egyptian Arabic voice for Arabic text, English voice for English
4. Cache audio response client-side (avoid re-synthesis)

### Step 6: Improve Error Handling

| Error Scenario | Current Behavior | Target Behavior |
|---------------|-----------------|----------------|
| No glyphs detected | Generic error | "No hieroglyphs found in this image. Try a clearer photo." |
| Low confidence | Shows all results | Flag low-confidence glyphs with ⚠ |
| AI translation fails | Error 500 | Fall back to transliteration only |
| Image too small | Stretched/blurry | "Image too small. Minimum 200×200px recommended." |
| Unsupported format | Error | "Unsupported format. Use JPEG, PNG, or WebP." |

---

## Model Files Inventory

```
models/hieroglyph/
├── detector/
│   └── glyph_detector_uint8.onnx     (~6MB, YOLOv8s quantized)
├── classifier/
│   ├── hieroglyph_classifier.onnx     (~14MB, MobileNetV3 float32)
│   ├── hieroglyph_classifier_uint8.onnx  (~3.5MB, quantized) — if exists
│   └── label_mapping.json              (171 Gardiner classes)
models/landmark/
├── landmark_classifier_uint8.onnx      (quantized)
└── landmark_label_mapping.json
```

---

## Test Plan for Scan Upgrades

| # | Test | Method | Expected |
|---|------|--------|----------|
| 1 | Upload valid JPEG with hieroglyphs | POST /api/scan | Boxes detected, classified, translated |
| 2 | Upload large image (4000×3000) | POST /api/scan | Auto-resized, processed normally |
| 3 | Upload WebP image | POST /api/scan | Converted to JPEG, processed |
| 4 | Upload image with no hieroglyphs | POST /api/scan | Friendly "no glyphs found" message |
| 5 | Upload non-image file | POST /api/scan | 400 "Invalid image format" |
| 6 | TTS on scan result | POST /api/tts | Audio stream returned |
| 7 | TTS with Gemini down | POST /api/tts | Falls back to Groq |
| 8 | Progress SSE stream | POST /api/scan/stream | Steps arrive in order |
