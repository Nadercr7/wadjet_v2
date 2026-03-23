# Wadjet v2 — Pre-Launch Checklist (Phase E Gate)

> Complete ALL items before considering the app ready for production deploy.
> Spec: `planning/rebuild/MASTER_PLAN.md`
> Issues fixed: `planning/rebuild/KNOWN_ISSUES.md`

---

## A. Model & ML

- [ ] CHK-A1 `hieroglyph_classifier_uint8.onnx` exists in `models/hieroglyph/classifier/`
- [ ] CHK-A2 `label_mapping.json` has 171 entries (all Gardiner codes 0–170)
- [ ] CHK-A3 `model_metadata.json` exists and documents `input_size=128, format=NCHW`
- [ ] CHK-A4 ONNX validation: `ort.InferenceSession` loads without error
- [ ] CHK-A5 ONNX output shape verified: `(1, 171)` for a `(1,3,128,128)` input
- [ ] CHK-A6 `glyph_detector_uint8.onnx` still in `models/hieroglyph/detection/` (unchanged)
- [ ] CHK-A7 Val top-1 accuracy ≥ 70% (recorded in training notebook)

---

## B. Backend

- [ ] CHK-B1 `hieroglyph_pipeline.py` — preprocessing is NCHW `[1,3,H,W]` (not NHWC)
- [ ] CHK-B2 `hieroglyph_pipeline.py` — model path points to `hieroglyph_classifier_uint8.onnx`
- [ ] CHK-B3 `hieroglyph_pipeline.py` — confidence threshold is 0.15 (not 0.25)
- [ ] CHK-B4 `gardiner.py` — all 171 sign codes are mapped (no blank entries)
- [ ] CHK-B5 `rag_translator.py` — `TRANSLATION_ENABLED` flag removed or set `True`
- [ ] CHK-B6 `scan.py` — `CONFIDENCE_THRESHOLD = 0.15`
- [ ] CHK-B7 `gemini_service.py` — `identify_landmark()` method exists and works
- [ ] CHK-B8 `POST /api/explore/identify` endpoint returns valid JSON
- [ ] CHK-B9 Old TF.js identify endpoint removed from `explore.py`
- [ ] CHK-B10 `curl -F file=@glyph.jpg POST /api/scan` returns glyphs with codes + translation
- [ ] CHK-B11 `curl -F file=@pyramids.jpg POST /api/explore/identify` returns `{"name": ..., "confidence": ..., "slug": ...}`
- [ ] CHK-B12 `GET /api/health` returns `{"status": "ok"}`

---

## C. Frontend

- [ ] CHK-C1 `hieroglyph-pipeline.js` — `classify()` uses NCHW planar loop + tensor `[1, 3, size, size]` (not `[1, size, size, 3]`)
- [ ] CHK-C1b `hieroglyph-pipeline.js` — `_warmup()` dummy classifier tensor is `[1, 3, s, s]` (not `[1, s, s, 3]`)
- [ ] CHK-C2 `hieroglyph-pipeline.js` — model URL = `/models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx`
- [ ] CHK-C3 `explore.html` — `tf.loadLayersModel()` code fully removed
- [ ] CHK-C4 `explore.html` — HTMX `hx-post="/api/explore/identify"` form present
- [ ] CHK-C5 `partials/identify_result.html` exists and renders correctly in browser
- [ ] CHK-C6 `sw.js` — `CACHE_VERSION = 'v15'` (bumped from v14)
- [ ] CHK-C7 `base.html` — `?v=15` on CSS and JS import links
- [ ] CHK-C8 `npm run build` ran successfully (minified CSS in `static/dist/styles.css`)

---

## D. Full E2E Manual Test (all 9 pages)

- [ ] CHK-D1 `/` — Landing page loads, both path cards visible, animations run
- [ ] CHK-D2 `/hieroglyphs` — Hub page loads, 3 feature cards visible
- [ ] CHK-D3 `/landmarks` — Hub page loads, 3 feature cards visible
- [ ] CHK-D4 `/scan` — Upload hieroglyph image → full pipeline: detect → classify → translit → translate
- [ ] CHK-D5 `/scan` — Camera mode opens (or shows permission error gracefully)
- [ ] CHK-D5b `/scan` — Camera mode: live detection boxes appear (gold outlines) on video feed in real-time
- [ ] CHK-D5c `/scan` — Camera mode: "Capture & Classify" captures a frame and produces Gardiner codes
- [ ] CHK-D6 `/dictionary` — 171 signs visible, search works, modal opens with full info
- [ ] CHK-D7 `/write` — Enter text → hieroglyphs appear, alpha + MdC modes work
- [ ] CHK-D8 `/explore` — 52 landmark cards visible, category/city filter works
- [ ] CHK-D9 `/explore` — Upload photo → identifies landmark → shows result with "View Details"
- [ ] CHK-D10 `/chat` — Thoth responds to a message, streaming works
- [ ] CHK-D11 `/quiz` — Quick quiz runs 5 questions, score displayed
- [ ] CHK-D12 Chrome DevTools → Console: zero JS errors on any page

---

## E. Performance & Security

- [ ] CHK-E1 No API keys hardcoded in any JS or HTML files (all in `.env`)
- [ ] CHK-E2 File upload validated by content (not just extension) before Gemini call
- [ ] CHK-E3 Max file size enforced: 10 MB for identify, 5 MB for scan
- [ ] CHK-E4 Gemini prompt does not leak internal system info or keys
- [ ] CHK-E5 ONNX Runtime session created ONCE at startup (not per-request)
- [ ] CHK-E6 `ruff check app/` passes with no errors
- [ ] CHK-E7 Lighthouse performance score ≥ 80 (run on `/`)
- [ ] CHK-E8 No `print()` debug statements left in production code
- [ ] CHK-E9 `gitleaks detect` passes — no API keys or secrets found (`D:\Personal attachements\Repos\18-Security\gitleaks\`)

---

## F. Deploy

- [ ] CHK-F1 `Dockerfile` builds successfully: `docker build -t wadjet .`
- [ ] CHK-F2 Docker container starts and responds at port 8000
- [ ] CHK-F3 `models/` folder included in Docker image (NOT gitignored in container)
- [ ] CHK-F4 Render env vars set: `GEMINI_API_KEYS`, `SECRET_KEY`
- [ ] CHK-F5 `render.yaml` points to correct start command
- [ ] CHK-F6 Production deploy responds at Render URL
- [ ] CHK-F7 All 9 routes return 200 on production URL
- [ ] CHK-F8 Scan and identify features work on production URL
