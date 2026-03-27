# Wadjet v2 — Hieroglyph Pipeline: Complete Problem Analysis

> Every bug, gap, and weakness — documented with severity, root cause, and evidence.
> This analysis covers ALL 4 pipeline stages + the frontend + APIs.

---

## Severity Legend

| Level | Meaning |
|-------|---------|
| **CRITICAL** | Causes total feature failure or wrong results |
| **HIGH** | Significantly degrades quality or user experience |
| **MEDIUM** | Noticeable quality issue, workaround exists |
| **LOW** | Cosmetic or future-proofing concern |

---

## STAGE 1: DETECTION (postprocess.py + glyph_detector_uint8.onnx)

### C1 — Detector Failed ALL Quality Gates ⛔ CRITICAL

**Evidence:** `models/hieroglyph/detector/model_metadata.json`
```
val_mAP50:      0.710  (gate ≥ 0.85 → FAILED by 0.14)
val_precision:  0.717  (gate ≥ 0.80 → FAILED)
val_recall:     0.642  (gate ≥ 0.80 → FAILED by 0.16)
```

**Impact:** With 64% recall, the model misses ~36% of glyphs even under ideal conditions. On real stone photos (out-of-distribution), it drops to detecting only 3-5 glyphs from inscriptions containing 20+.

**Root cause:** Training data was 84% from one source (`mohiey` dataset = 8,650/10,311 images). Museum-scraped images (438 total from Met + Wikimedia) were collected but NOT annotated/included because CPU-based GroundingDINO was too slow. The model overfits to mohiey's visual style.

**What was tried:** 
- v1: 88 epochs, mAP50=0.710
- v2: Kaggle kernel failed (kernelspec error)
- Confidence threshold at 0.10 in postprocess.py, config says 0.15 but not wired

---

### H1 — `detection_confidence_threshold` Config Never Wired Up — HIGH

**File:** `app/config.py` line 35 → `app/dependencies.py` line 20-29

The config var exists (`detection_confidence_threshold: float = 0.15`) but `get_pipeline()` in dependencies.py never passes it to the pipeline. The detector always uses the hardcoded `CONF_THRESHOLD = 0.10` from `postprocess.py`. Changing the env var does nothing.

---

### M1 — `preprocess()` Return Type Hint Wrong — MEDIUM

**File:** `app/core/postprocess.py` line 96

Returns 5 values `(blob, (orig_h, orig_w), scale, pad_x, pad_y)` but type hint declares 4 elements: `tuple[np.ndarray, tuple[int, int], float, float]`.

---

### M6 — `_suppress_containers` Variable Naming Inverted — MEDIUM

**File:** `app/core/postprocess.py` line 167

Variables named `big`/`small` imply size ordering, but list is sorted by confidence descending. Logic works but naming is misleading and fragile.

---

### L3 — Debug Function in Production Code — LOW

`evaluate_conf_threshold()` (lines 248-320) is a grid-search utility that does disk I/O. Should live in `scripts/`, not `app/core/`.

---

## STAGE 2: CLASSIFICATION (hieroglyph_pipeline.py + hieroglyph_classifier.onnx)

### Domain Gap: 98% Test Accuracy But 3-15% Real-World Confidence — HIGH

**Evidence:** Classifier achieves 98.18% top-1 accuracy on the test set (drawn from same distribution as training: clean lab images). But on real stone photos cropped by the detector:
- Average confidence: 3-15%
- Many crops classified as D34, L1, O49 (signs with simple shapes that match noise)

**Root cause:** The classifier was trained on clean, isolated glyph images. Real detector crops contain: stone texture noise, erosion, uneven lighting, partial occlusions, surrounding glyphs bleeding in. The softmax distribution becomes very flat (uncertain) on out-of-distribution inputs.

**Compounding factor:** The detector produces imprecise bounding boxes that include surrounding context, making crops even less clean.

---

### C4 — INT8 Quantization Destroyed Classifier Weights — CRITICAL

The uint8 quantized model (`hieroglyph_classifier_uint8.onnx`) gives 0% accuracy. FP32 model (6.8MB, `hieroglyph_classifier.onnx`) gives 97% on test. **Currently deployed with the BROKEN uint8 model** — needs switching to FP32.

Additionally:
- **BGR→RGB missing**: OpenCV loads BGR, but ONNX model expects RGB. Need `cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)` in classify step.
- **Wrong label_mapping.json path**: Previous attempt pointed to wrong file. Must use `models/hieroglyph/classifier/label_mapping.json` (171 classes, filesystem order not alphabetical).
- **FP32 .onnx not in git**: The `.gitignore` doesn't whitelist the FP32 model. Must add `!models/hieroglyph/classifier/hieroglyph_classifier.onnx` to .gitignore and track via git LFS.

These 4 issues together mean the classifier currently returns ~0% correct predictions on deployed code.

---

## STAGE 3: TRANSLITERATION (transliteration.py + reading_order.py + gardiner.py)

### H2 — Reading Direction Always Returns RTL — HIGH

**File:** `app/core/reading_order.py` line 232-240

```python
def detect_reading_direction(boxes, layout=None) -> Direction:
    # Without image-level orientation analysis, we default to RTL.
    return Direction.RIGHT_TO_LEFT  # ← ALWAYS
```

~20% of inscriptions read left-to-right (Late Period, many temple inscriptions). These all get reversed. The function exists, `FACING_SIGNS` is defined (100+ signs), but pixel-level orientation analysis is marked TODO.

---

### L2 — `_init_model_facing_signs()` Never Called — LOW

Defined at `reading_order.py` line 150-154 but never invoked. `FACING_SIGNS_IN_MODEL` stays empty. Dead code from an unfinished direction detection feature.

---

### M4 — Unknown Signs Break MdC Quadrat Notation — MEDIUM

**File:** `app/core/transliteration.py` line 185-193

When a quadrat contains known + unknown signs, output becomes `"nTr:[D5]:s"`. The `[D5]` bracket syntax breaks MdC's colon-separated stacking rules.

---

### M5 — Logograms Treated as Determinatives — MEDIUM

**File:** `app/core/gardiner.py` line 204-209

`is_determinative()` returns `True` for any sign with a `determinative_class` set, even logograms like G7 (Horus), N5 (Ra). These get wrapped in `<...>` in transliteration, suppressing their phonetic readings.

---

## STAGE 4: TRANSLATION (rag_translator.py)

### H8 — RAG Embeddings Are Meaningless for MdC Strings — HIGH

**File:** `app/core/rag_translator.py` line 54

```python
self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")
```

`all-MiniLM-L6-v2` is trained on natural English sentences. MdC strings like `"wDA-s-nTr-aA-nb-pt"` are completely foreign. Embeddings are near-random, making FAISS retrieval essentially random too. The "few-shot examples" fed to Gemini have no semantic relevance to the input.

**Available fix:** Cohere's `embed-multilingual-v3.0` (1024-dim) would handle MdC better as a "language," or we could use Gemini's `text-embedding-004` model. Alternatively, skip RAG entirely and let Gemini translate directly with a rich system prompt.

---

### H6 — `translate_bilingual()` Makes 2 Sequential Gemini Calls — HIGH

**File:** `app/core/rag_translator.py` line 245-260

English and Arabic translations run sequentially. Best case: 2 network round trips. Worst case with retries: 50 seconds. Should batch into one prompt or use `asyncio.gather`.

---

### L4 — Key Rotation Not Thread-Safe — LOW

`self._idx += 1` is unsynchronized. Under concurrent access, two callers could get the same key. Low risk in single-worker uvicorn but technically a race condition.

---

## API LAYER (scan.py)

### C2 — JS `translate()` Sends JSON to File-Upload Endpoint — CRITICAL

**File:** `app/static/js/hieroglyph-pipeline.js` line 455-461

```javascript
this._translationApi = '/api/scan';
// ...
fetch(this._translationApi, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transliteration: mdc })
});
```

But `/api/scan` expects `multipart/form-data` with a file upload. **Every JS `translate()` call returns 422.** There is NO `/api/translate` endpoint. Client-side translation is completely broken — users never see translations.

---

### C3 — `asyncio.get_event_loop()` Deprecated in Python 3.13 — CRITICAL

**File:** `app/api/scan.py` lines 541, 667

Should be `asyncio.get_running_loop()`. Current code emits DeprecationWarning and will break in future Python releases.

---

### H5 — Full-Sequence Gemini Verify Runs on EVERY Scan — HIGH

**File:** `app/api/scan.py` line 651-670

No confidence check — even if ONNX classification is 99% confident, Gemini Vision is still called. This adds 1-3 seconds latency and burns API quota unnecessarily. Should only fire when avg confidence < 0.6.

---

### H7 — Grok Tiebreaker Sends base64 Data URIs — HIGH

**File:** `app/api/scan.py` line 480-496

Grok Vision API may not support inline `data:` URIs. When it fails, the `except` block silently returns `{}` — Grok tiebreaker never actually works.

---

## FRONTEND JS (hieroglyph-pipeline.js)

### H3 — JS Line Clustering Compares Last Glyph Only — HIGH

**File:** `app/static/js/hieroglyph-pipeline.js` line 420-440

```javascript
var lastGlyph = lastLine[lastLine.length - 1];
```

Should compare against full line's vertical extent (min y1, max y2 of all glyphs in line), not just the last glyph. Causes incorrect line assignments when glyph heights vary.

---

### H4 — JS Gardiner Map Missing ~46/171 Model Classes — HIGH

**File:** `app/static/js/hieroglyph-pipeline.js` line 602-698

Static map covers ~125 of 171 classes. Missing: all C-category (deity signs), most P signs (ships), many common determinatives. Unrecognized codes show as `'[CODE]'` in output.

---

### M2 — JS Classifies Crops Sequentially — MEDIUM

Each glyph runs a separate ONNX inference. For 15 glyphs at ~50ms each = 750ms. Should batch into one `[N, 3, 128, 128]` tensor.

---

### M3 — Camera Loop `setTimeout(0)` Burns CPU — MEDIUM

When detection finds nothing, the loop runs at maximum speed. Should use `requestAnimationFrame` or minimum 100ms delay.

---

## MISSING FEATURES

| Feature | Status | Impact |
|---------|--------|--------|
| TTS (text-to-speech) | V1 had it (Web Speech API), V2 missing | Users can't hear translations |
| `/api/translate` endpoint | Does not exist | Client-side translation impossible |
| Reading direction detection | Stub returns RTL always | 20% of inscriptions read wrong |
| Audio input (speak to scan) | Never existed | Would be nice for accessibility |
| Facing sign analysis | `FACING_SIGNS` defined but never used | Can't detect reading direction |

---

## The Fundamental Problem

The current pipeline treats each stage independently:
1. A mediocre detector finds 3-5 boxes
2. A classifier (trained on clean images) can't identify noisy crops
3. Rule-based transliteration makes mistakes on wrong classifications
4. RAG with wrong embeddings gives random examples to Gemini

**Meanwhile, Gemini Vision can read full inscriptions directly in one call with high accuracy.** The pipeline is a chain of weak links where each stage amplifies the previous stage's errors.

**The solution isn't to fix each stage individually — it's to redesign the system to use AI vision as the primary reader, with ONNX models as a fast fallback for offline/quick scanning.**
