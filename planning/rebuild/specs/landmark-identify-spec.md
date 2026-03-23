# Feature Specification: Landmark Identification (Hybrid: ONNX + Gemini Vision)

**Created**: 2026-03-20
**Updated**: 2026-03-21 — Strategy changed from Gemini-only to hybrid local model + Gemini
**Status**: Ready for implementation (after Phase B2 model is trained)
**Phase**: P8-B2 (train EfficientNet-B0) → P8-C (backend integration) → P8-D (frontend)

---

## Context

The old TF.js EfficientNetV2-S landmark classifier crashes with `_FusedConv2D`
errors. It is being replaced with a **hybrid approach**:

1. **Primary**: Local EfficientNet-B0 ONNX model (`landmark_classifier_uint8.onnx`)
   — fast, free, offline-capable, 52 Egyptian landmark classes.
2. **Enrichment**: Gemini Vision adds description + interesting facts for confirmed results.
3. **Fallback**: If ONNX confidence < 0.5, Gemini Vision also identifies (double-check).
4. **Emergency fallback**: If ONNX fails entirely, Gemini Vision only.

The 52-landmark **browsing** feature (cards, detail modal, JSON data) is **UNCHANGED**.
Only the "Upload photo → identify" feature is being rebuilt.

---

## User Stories

### Story 1 — Identify a landmark from a photo (P1 — Core)

**Scenario**: A user takes or uploads a photo of an Egyptian site. The app runs
the local ONNX model first, then Gemini enriches or confirms the result.

**Acceptance Scenarios**:

1. **Given** a clear photo of the Pyramids of Giza, **When** the user uploads it
   and clicks "Identify", **Then** the ONNX model returns `"slug": "great_pyramids_of_giza"`
   with `confidence ≥ 0.85`, Gemini provides a description, and a "View Details" link appears.

2. **Given** a photo where the ONNX model returns `confidence < 0.5` (ambiguous photo),
   **When** identified, **Then** Gemini Vision also identifies the landmark, the combined
   result shows top-3 alternatives, and the UI shows "Not certain — could be one of these:".

3. **Given** a completely non-Egyptian photo (a random street or animal),
   **When** identified, **Then** `confidence = 0.0` from both sources and the UI
   shows "Could not identify an Egyptian landmark in this photo."

4. **Given** the ONNX model fails to load (missing file), **When** identify is called,
   **Then** the endpoint gracefully falls back to Gemini Vision only (no 500 crash).

5. **Given** both ONNX and Gemini fail (all 17 keys exhausted),
   **When** identify is called, **Then** a user-friendly 503 error is returned.

**Edge Cases**:
- File > 10 MB → reject 413 before any inference
- Non-image file → reject 422 before any inference
- Gemini returns malformed JSON → parse defensively, return ONNX result only
- All 17 keys exhausted → return 503 with "Service temporarily unavailable"
- ONNX model not yet deployed → graceful fallback to Gemini

---

### Story 2 — Smooth UI flow from identify → detail (P2 — UX)

**Acceptance Scenarios**:

1. **Given** `slug = "karnak_temple"` from identify response, **When** result shows,
   **Then** a "View Details" button opens the same modal as clicking the landmark card.

2. **Given** the HTMX response in `#identify-result`, **When** user scrolls,
   **Then** result stays visible until dismissed or new photo uploaded.

---

## Requirements

### API Design
```
POST /api/explore/identify
  Content-Type: multipart/form-data
  Body: file (image/jpeg or image/png, max 10 MB)

Response 200 (high confidence, local model wins):
{
  "name": "Abu Simbel Temples",
  "confidence": 0.94,
  "slug": "abu_simbel",
  "source": "local_model",
  "description": "Twin rock temples built by Ramesses II circa 1264 BC",
  "top3": [
    {"name": "Abu Simbel Temples", "slug": "abu_simbel", "confidence": 0.94},
    {"name": "Philae Temple",       "slug": "philae_temple", "confidence": 0.03},
    {"name": "Edfu Temple",         "slug": "edfu_temple",   "confidence": 0.02}
  ]
}

Response 200 (low confidence, hybrid result):
{
  "name": "Karnak Temple",
  "confidence": 0.42,
  "slug": "karnak_temple",
  "source": "hybrid",
  "description": "...",
  "top3": [...]
}

Response 422: {"detail": "File is not a valid image"}
Response 413: {"detail": "File too large (max 10MB)"}
Response 503: {"detail": "Landmark identification temporarily unavailable"}
```

### Inference Flow
```
1. Validate file (type, size)
2. Run landmark_classifier_uint8.onnx → predicted class + confidence + top3
3. If confidence >= 0.5:
     source = "local_model"
     Call Gemini: describe_landmark(slug) → description text only
4. If confidence < 0.5:
     Also call Gemini Vision: identify_landmark(image_bytes) → {name, slug, confidence, description}
     source = "hybrid"
     If Gemini confidence > ONNX confidence → use Gemini's class
5. If ONNX fails (exception):
     Fall back to Gemini identify_landmark() only, source = "gemini"
6. If both fail:
     Return 503
```

### ONNX Model Details
```
File:    models/landmark/classifier/landmark_classifier_uint8.onnx
Input:   [1, 3, 224, 224] float32 NCHW — normalize to [0,1]
Output:  [1, 52] logits (apply softmax to get probabilities)
Labels:  models/landmark/classifier/landmark_label_mapping.json
         {0: "abu_simbel", 1: "akhenaten", ..., 51: "white_desert"}
Wrapper: app/core/landmark_pipeline.py  (new file to create in Phase C)
```

### Gemini Integration
- **Model**: `gemini-2.5-flash` (multimodal, vision-capable)
- **SDK**: `google-genai` (already installed — uses `genai.Client`)
- **Key rotation**: Use existing `GeminiService` rotation logic (17 keys)
- **Two methods to add**:
  - `identify_landmark(image_bytes)` → full vision identification (low-conf fallback)
  - `describe_landmark(slug)` → text-only enrichment (high-conf case, no image needed)
- **Response parsing**: Strict JSON parse with fallback on malformed response

### Backend Files
| File | Change |
|------|--------|
| `app/core/landmark_pipeline.py` | **NEW** — ONNX inference wrapper (load model, NCHW, predict, top3) |
| `app/core/gemini_service.py` | Add `identify_landmark(image_bytes)` + `describe_landmark(slug)` |
| `app/api/explore.py` | Add `POST /api/explore/identify` hybrid endpoint, remove old TF.js |

### Frontend Files
| File | Change |
|------|--------|
| `app/templates/explore.html` | Remove `tf.loadLayersModel()` code; add HTMX upload form |
| `app/templates/partials/identify_result.html` | **NEW** partial rendered by HTMX response |

### Partial Template (`identify_result.html`)
Must render:
- Landmark name (large, gold)
- Confidence as percentage + color bar (green ≥ 0.7, amber 0.5–0.7, red < 0.5)
- Brief description (from Gemini)
- `source` badge (Local Model / AI-Assisted / AI-Only)
- "View Details" button → opens landmark modal
- top3 alternatives (if confidence < 0.8)
- "Try again" link

---

## Non-Functional Requirements

- ONNX inference: ≤ 200ms (uint8 model, CPU)
- Gemini call: ≤ 5s under normal conditions
- Privacy: ONNX runs locally (no data leaves the server). Gemini only receives
  the image in the low-confidence fallback case.
- Security: Validate file type by magic bytes (not just MIME header)
- Cost: Gemini only called for enrichment + low-confidence cases — minimal token usage

---

## Context

The old TF.js EfficientNetV2-S landmark classifier crashes with `_FusedConv2D`
errors. It is being replaced with a direct call to Gemini Vision API
(`gemini-2.5-flash` multimodal) — no training required, no model file, one API call.

The 52-landmark **browsing** feature (cards, detail modal, JSON data) is **UNCHANGED**
and working. Only the "Upload photo → identify" feature is being rebuilt.

---

## User Stories

### Story 1 — Identify a landmark from a photo (P1 — Core)

**Scenario**: A user takes or uploads a photo of an Egyptian site. The app calls
Gemini Vision and returns which landmark it is, with a confidence score, brief
description, and a link to the landmark's detail page.

**Why P1**: This replaces the broken TF.js classifier. Without it the "Identify"
button on the Explore page is non-functional.

**Acceptance Scenarios**:

1. **Given** a clear photo of the Pyramids of Giza, **When** the user uploads it
   and clicks "Identify", **Then** the response shows `"name": "Pyramids of Giza"`,
   `"confidence" ≥ 0.85`, and a link to the `/explore?landmark=pyramids_of_giza` detail.

2. **Given** a photo of Abu Simbel, **When** identified, **Then** the slug
   `"abu_simbel"` is returned and the detail modal can be opened from the result.

3. **Given** an ambiguous or partial photo (e.g., just a column), **When**
   confidence < 0.6, **Then** the top 3 alternatives are shown with their scores
   and the UI shows "Not certain — could be one of these:" instead of a definitive answer.

4. **Given** a photo of a non-Egyptian scene (a dog, a park), **When** identified,
   **Then** confidence = 0.0 and the UI shows "Could not identify an Egyptian landmark
   in this photo."

5. **Given** a Gemini API failure (rate limit, network error), **When** the call
   fails, **Then** a user-friendly error message is shown (not a 500 crash) and
   the next API key is tried automatically (17 keys available in rotation).

**Edge Cases**:
- File > 10 MB → reject with 413 before calling Gemini
- Non-image file (PDF, etc.) → reject with 422 before calling Gemini
- Gemini returns malformed JSON → parse defensively, return partial result + log error
- All 17 keys exhausted (daily quota) → return 503 with message "Service temporarily unavailable"

---

### Story 2 — Smooth UI flow from identify → detail (P2 — UX)

**Scenario**: After identification, the user can go directly to the full landmark
detail modal without re-searching.

**Acceptance Scenarios**:

1. **Given** a successful identification with `slug = "karnak_temple"`,
   **When** the result is shown, **Then** a "View Details" button is present
   that opens the same modal as clicking the karnak_temple card in the grid.

2. **Given** the HTMX response loads into `#identify-result`,
   **When** the user scrolls, **Then** the result stays visible until they
   dismiss it or upload a new photo (no auto-clear).

---

## Requirements

### API Design
```
POST /api/explore/identify
  Content-Type: multipart/form-data
  Body: file (image/jpeg or image/png, max 10 MB)

Response 200:
{
  "name": "Abu Simbel Temples",
  "confidence": 0.95,
  "slug": "abu_simbel",
  "description": "Twin rock temples built by Ramesses II circa 1264 BC",
  "alternatives": [
    {"name": "Nefertari Temple", "confidence": 0.03, "slug": "abu_simbel"}
  ]
}

Response 422: {"detail": "File is not a valid image"}
Response 413: {"detail": "File too large (max 10MB)"}
Response 503: {"detail": "Landmark identification temporarily unavailable"}
```

### Gemini Integration
- **Model**: `gemini-2.5-flash` (multimodal, vision-capable)
- **Key rotation**: Use `GeminiService` existing rotation logic (17 keys)
- **Prompt**: See `planning/rebuild/MASTER_PLAN.md` Section 7 for full prompt
- **Response parsing**: Strict JSON parse with fallback on malformed response
- **Retry**: On 429/quota, rotate to next key before failing

### Backend Files
| File | Change |
|------|--------|
| `app/core/gemini_service.py` | Add `identify_landmark(image_bytes) -> dict` method |
| `app/api/explore.py` | Add `POST /api/explore/identify` endpoint, remove old TF.js endpoint |

### Frontend Files
| File | Change |
|------|--------|
| `app/templates/explore.html` | Remove `tf.loadLayersModel()` code; add HTMX upload form |
| `app/templates/partials/identify_result.html` | New partial rendered by HTMX response |

### Partial Template (`identify_result.html`)
Must render:
- Landmark name (large)
- Confidence as percentage + color bar
- Brief description
- "View Details" button (links to `/explore?modal=<slug>` or triggers modal)
- Alternatives list (if confidence < 0.8)
- "Try again" link

---

## Non-Functional Requirements

- Response time: ≤ 5s for Gemini call under normal conditions
- Cost: `gemini-2.5-flash` is cheap — well within free tier for expected usage
- Privacy: Image bytes are sent to Gemini API. Do NOT log or store the image.
- Security: Validate file type by content (magic bytes), not just MIME header
