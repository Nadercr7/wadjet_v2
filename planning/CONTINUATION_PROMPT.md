# Wadjet v2 — Continuation Prompt (Post-Kaggle Training)

> Paste this entire file into a new chat session after Kaggle notebooks finish.
> Attach CLAUDE.md as the project instructions file.

---

## Context

You are continuing work on **Wadjet v2**, an Egyptian heritage web app. The previous session completed **52/57 tasks**. Two Kaggle notebooks were left training on T4 GPUs. Those should now be done.

**Git state**: Branch `clean-main`, HEAD `ff0d282`, synced to `origin` (GitHub) + `hf` (HuggingFace).

**What's left** (5 tasks, then checklist + final commit):

| Task | Phase | Priority | Description |
|------|-------|----------|-------------|
| H-DETECTOR-05 | H-DETECTOR | HIGH | Download trained models from Kaggle, verify quality gates |
| H-DETECTOR-06 | H-DETECTOR | HIGH | Deploy models to `models/`, test in both pipelines |
| L-LANDMARKS-03 | L-LANDMARKS | MEDIUM | Cloudflare Workers AI as emergency vision fallback |
| L-LANDMARKS-05 | L-LANDMARKS | LOW | TLA (Thesaurus Linguae Aegyptiae) API integration |
| L-LANDMARKS-06 | L-LANDMARKS | HIGH | Test identify fallback chain script |

After the 5 tasks: tick all 43 unchecked gates in `planning/hieroglyph-rebuild/CHECKLIST.md`, update `planning/hieroglyph-rebuild/PROGRESS.md` to 57/57, commit, and push to both remotes.

---

## TASK 1: H-DETECTOR-05 — Download & Verify Kaggle Models

### 1a. Check Kaggle Kernel Status

```bash
# Ensure kaggle CLI is configured
# Creds: C:\Users\Nader\Downloads\kaggle.json → ~/.kaggle/kaggle.json

kaggle kernels status naderelakany/wadjet-hieroglyph-detector-v3
kaggle kernels status naderelakany/wadjet-hieroglyph-classifier-v2
```

Both should show `complete`. If either shows `running`, wait. If `error`, pull logs:

```bash
kaggle kernels output naderelakany/wadjet-hieroglyph-detector-v3 -p tmp_kaggle_output/detector_v3
kaggle kernels output naderelakany/wadjet-hieroglyph-classifier-v2 -p tmp_kaggle_output/classifier_v2
```

### 1b. Download Outputs

```bash
kaggle kernels output naderelakany/wadjet-hieroglyph-detector-v3 -p tmp_kaggle_output/detector_v3
kaggle kernels output naderelakany/wadjet-hieroglyph-classifier-v2 -p tmp_kaggle_output/classifier_v2
```

### 1c. Verify Quality Gates

**Detector v3** (YOLO26s NMS-free):
- Check training log for: `mAP50 ≥ 0.85` and `recall ≥ 0.80`
- Output format must be `[1, 300, 6]` (NMS-free)
- Expected files: `best.pt`, possibly ONNX export, training metrics

**Classifier v2** (MobileNetV3-Small with stone-texture augmentation):
- Check training log for: `top-1 accuracy ≥ 98%` and `stone accuracy ≥ 50%`
- Previous run hit 97.31% top-1 (crashed before stone eval — now fixed)
- Expected files: `hieroglyph_classifier.onnx` (fp32), `hieroglyph_classifier_uint8.onnx`, `label_mapping.json`, `model_metadata.json`

**If quality gates fail**: Note the metrics. We may still deploy if they're close (e.g., mAP50=0.83 is acceptable, 0.60 is not). Use judgment.

### 1d. Export Detector ONNX (if not already exported by notebook)

If the detector notebook only produced `best.pt` without ONNX:
```python
from ultralytics import YOLO
model = YOLO("tmp_kaggle_output/detector_v3/best.pt")
model.export(format="onnx", opset=17, simplify=True, imgsz=640)
# Then quantize to uint8 with onnxruntime
```

---

## TASK 2: H-DETECTOR-06 — Deploy & Test Models

### 2a. Deploy to models/

```bash
# Detector
cp tmp_kaggle_output/detector_v3/glyph_detector.onnx models/hieroglyph/detection/glyph_detector.onnx
cp tmp_kaggle_output/detector_v3/glyph_detector_uint8.onnx models/hieroglyph/detection/glyph_detector_uint8.onnx

# Classifier  
cp tmp_kaggle_output/classifier_v2/hieroglyph_classifier.onnx models/hieroglyph/classifier/hieroglyph_classifier.onnx
cp tmp_kaggle_output/classifier_v2/hieroglyph_classifier_uint8.onnx models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx
cp tmp_kaggle_output/classifier_v2/label_mapping.json models/hieroglyph/classifier/label_mapping.json
cp tmp_kaggle_output/classifier_v2/model_metadata.json models/hieroglyph/classifier/model_metadata.json
```

Adjust filenames to match what the notebooks actually output — the above are the expected names.

### 2b. CRITICAL: No Pipeline Code Changes Needed

**Both JS and Python pipelines already handle the new detector format:**
- **JS** (`app/static/js/hieroglyph-pipeline.js` line ~190): Already parses `[1, 300, 6]` NMS-free output format
- **Python** (`app/core/postprocess.py` line ~118-124): Already parses `[1, 300, 6]` format

Do NOT modify these files unless the actual output shape is different from `[1, 300, 6]`.

### 2c. Verify label_mapping.json

Confirm `label_mapping.json` has 171 entries (indices 0-170, all Gardiner codes). Compare against existing file if it differs.

### 2d. Test Both Pipelines

```bash
# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test Python pipeline (scan endpoint)
curl -X POST -F "file=@test_image.jpg" http://localhost:8000/api/scan

# Test JS pipeline: open http://localhost:8000/scan in browser, upload image
```

Also run existing test scripts:
```bash
python scripts/quick_scan_test.py    # if it exists
python scripts/_validate_all.py       # full 42-check validation
```

### 2e. Before/After Comparison

Test on real stone images to validate improvement. The detector should find more glyphs with higher confidence than the v1 model. The classifier should correctly identify stone-crop glyphs that v1 missed.

---

## TASK 3: L-LANDMARKS-03 — Cloudflare Workers AI Emergency Fallback

### What
Add Cloudflare Workers AI as the #4 vision fallback in the identify chain, after Grok and before ONNX-only.

### Current Identify Fallback Chain (in `app/api/explore.py`)
```
ONNX + Gemini (parallel) → Groq (if Gemini failed) → Grok (tiebreaker) → ONNX-only
```

### Target Identify Fallback Chain
```
ONNX + Gemini (parallel) → Groq (if Gemini failed) → Grok (tiebreaker/fallback) → Cloudflare (emergency) → ONNX-only
```

### Implementation

**3a. Add config** (`app/config.py`):
```python
cloudflare_account_id: str = ""
cloudflare_api_token: str = ""
```

**Credentials already in `.env`:**
```
CLOUDFLARE_ACCOUNT_ID=b3edf0e44c706e4437265904e67a24e2
CLOUDFLARE_API_TOKEN=cfut_9qA4tVFEou2UIaWdtEU95pE2DagBFrooF4xAoSlB0e2d9c7c
```
Token verified working (Read All Resources scope). Account: naderelakany@gmail.com.

**3b. Create `app/core/cloudflare_service.py`**:
- REST endpoint: `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}`
- Vision models: `@cf/meta/llama-3.2-11b-vision-instruct` (primary), `@cf/google/gemma-3-12b-it` (backup)
- Method: `identify_landmark(image_bytes: bytes, filename: str) -> dict` → returns `{"name": ..., "confidence": ..., "description": ...}`
- Use `httpx.AsyncClient` (consistent with other services)
- Budget: 10,000 neurons/day free (≈500 identify calls/day)
- Handle: missing config (skip gracefully), rate limits, timeouts

**3c. Wire into `app/api/explore.py`**:
- After Grok fails (or as additional fallback layer), try Cloudflare
- If Cloudflare produces a result, merge it with ONNX via ensemble
- Keep ONNX-only as absolute last resort

**3d. Add to `.env.example`**:
```
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
```

> Note: Real credentials are already in `.env`. Just wire `config.py` to read them.

---

## TASK 4: L-LANDMARKS-05 — TLA API Integration

### What
Integrate the Thesaurus Linguae Aegyptiae (TLA) API for Egyptological grounding.

### TLA API Details
- **Base URL**: `https://api.thesaurus-linguae-aegyptiae.de/`
- **Auth**: None required (free, public)
- **Content**: 90,000+ ancient Egyptian lemmas with transliteration, translation, attestations
- **Format**: REST JSON

### Implementation

**4a. Create `app/core/tla_service.py`**:
- `search_lemma(term: str) -> list[dict]` — search for Egyptian terms
- `get_lemma(id: str) -> dict` — get full lemma details
- Cache results (LRU or disk cache) — TLA data is static
- Timeout: 5 seconds, graceful failure (not critical path)

**4b. Integration points** (optional, low priority):
- **Explore detail** (`app/api/explore.py`): For pharaonic landmarks, look up known ancient Egyptian names and add to detail response
- **Thoth chat** (`app/core/thoth_chat.py`): When user asks about Egyptian terms, ground Thoth's answer in TLA scholarly data
- Keep integration light — this is enrichment, not core functionality

---

## TASK 5: L-LANDMARKS-06 — Test Identify Fallback Chain

### What
Create/update `scripts/test_identify.py` to verify the entire identify pipeline.

### Test Cases

```python
# 1. Happy path: upload known landmark → correct identification
# 2. Gemini blocked: set GEMINI_API_KEYS="" → Groq handles it
# 3. Gemini + Groq blocked: → Grok handles it  
# 4. All AI blocked: → ONNX-only result returned
# 5. Not-Egyptian image: upload cat/car photo → "not an Egyptian landmark"
# 6. Empty description: identified landmark missing description → AI generates one
# 7. (If Cloudflare added) Gemini+Groq+Grok blocked → Cloudflare handles it
```

### Implementation
- Use `httpx` to call `POST /api/explore/identify` with test images
- For "blocked" tests: temporarily override env vars or mock service failures
- Print clear PASS/FAIL for each test case
- Include at least 3 different known landmark images (pyramids, sphinx, karnak, etc.)

---

## TASK 6: Tick All Checklist Gates

After tasks 1-5 are complete, update `planning/hieroglyph-rebuild/CHECKLIST.md`:

### Already checked (leave as-is):
- TRN-G1 through TRN-G8 (all ✅)
- AUD-G1 through AUD-G9 (all ✅)
- WRT-G1 through WRT-G8, WRT-G10 through WRT-G12 (all ✅)
- LM-G1, LM-G2, LM-G3, LM-G6 (all ✅)

### Need to check (change `[ ]` → `[x]`):

**H-FIX gates** (FIX-G0A through FIX-G13) — All 14 are implemented but unchecked. Verify each is truly working and tick them.

**H-VISION gates** (VIS-G1 through VIS-G10) — All 10 are implemented but unchecked. Verify and tick.

**H-DETECTOR gates** (DET-G1 through DET-G7) — Tick after deploying new models and confirming metrics.

**W-WRITE** (WRT-G9) — "Smart mode fallback: block Gemini → Groq handles request". This IS working (Gemini→Groq→Grok chain is wired). Test and tick.

**L-LANDMARKS** (LM-G4, LM-G5, LM-G7):
- LM-G4: "Identify works when Gemini + Groq blocked → Grok provides result" — test and tick
- LM-G5: "Not-Egyptian detection still works with new fallback chain" — test and tick
- LM-G7: "`scripts/test_identify.py` passes all tests" — tick after Task 5

**LAUNCH gates** (LAUNCH-G1 through LAUNCH-G10) — All 10 depend on prior gates passing. Tick after confirming all phases pass.

---

## TASK 7: Update Progress & Commit

### 7a. Update PROGRESS.md
Set `planning/hieroglyph-rebuild/PROGRESS.md` to **57/57** — mark H-DETECTOR-05, H-DETECTOR-06, L-LANDMARKS-03, L-LANDMARKS-05, L-LANDMARKS-06 as complete with dates and notes.

### 7b. Run Full Validation
```bash
python scripts/_validate_all.py
```
All 42+ checks should pass.

### 7c. Build CSS
```bash
npm run build
```

### 7d. Commit & Push
```bash
git add -A
git commit -m "feat: complete all 57/57 tasks — new models, Cloudflare fallback, TLA API, tests"
git push origin clean-main
git push hf clean-main:main
```

---

## Key File Locations

| File | Purpose |
|------|---------|
| `app/api/explore.py` | Identify endpoint + landmark routes (~1080 lines) |
| `app/core/ai_service.py` | GeminiService, GroqService, GrokService |
| `app/core/ensemble.py` | merge_landmark() for multi-source results |
| `app/core/landmark_pipeline.py` | ONNX landmark inference |
| `app/core/postprocess.py` | Detector output parsing (already handles [1,300,6]) |
| `app/static/js/hieroglyph-pipeline.js` | JS ML pipeline (already handles [1,300,6]) |
| `app/core/thoth_chat.py` | Thoth chatbot with 3-provider fallback |
| `app/config.py` | Pydantic Settings (add Cloudflare vars here) |
| `models/hieroglyph/detection/` | Detector ONNX files |
| `models/hieroglyph/classifier/` | Classifier ONNX + label_mapping + metadata |
| `planning/hieroglyph-rebuild/CHECKLIST.md` | 43 unchecked quality gates |
| `planning/hieroglyph-rebuild/PROGRESS.md` | 52/57 → update to 57/57 |
| `scripts/_validate_all.py` | 42-check validation suite |
| `scripts/test_identify.py` | Landmark identify tests (create/update in Task 5) |

---

## Kaggle Account Details

| Field | Value |
|-------|-------|
| Training account | `naderelakany` |
| Dataset account | `nadermohamedcr7` (shared as editor) |
| Detector kernel | `naderelakany/wadjet-hieroglyph-detector-v3` |
| Classifier kernel | `naderelakany/wadjet-hieroglyph-classifier-v2` |
| Creds location | `C:\Users\Nader\Downloads\kaggle.json` |
| GPU | T4 (specified via `--accelerator NvidiaTeslaT4`) |

---

## Quality Gate Thresholds Summary

| Metric | Target | Fail-safe |
|--------|--------|-----------|
| Detector mAP50 | ≥ 0.85 | Accept ≥ 0.80 |
| Detector recall | ≥ 0.80 | Accept ≥ 0.75 |
| Classifier top-1 | ≥ 98% | Accept ≥ 95% |
| Classifier stone accuracy | ≥ 50% | Accept ≥ 30% (was 5-15%) |
| Dataset mislabel rate | < 5% | — |
| Identify fallback chain | 5 layers work | All tested |
| Full scan latency | < 10 seconds | With AI |

---

## Planning Files Reference

All planning docs live under `planning/`. Read these if you need deeper context on any area.

### Top-Level Planning
| File | Purpose |
|------|---------|
| `planning/CONSTITUTION.md` | Project constitution — identity, values, non-negotiables |
| `planning/EXPANSION_PLAN.md` | Future expansion ideas (post-launch) |
| `planning/CONTINUATION_PROMPT.md` | THIS FILE — the continuation prompt |
| `planning/templates/` | Spec/task/checklist templates |

### Hieroglyph Rebuild (Active — where our 5 remaining tasks live)
| File | Purpose | Key Info |
|------|---------|----------|
| `planning/hieroglyph-rebuild/MASTER_PLAN.md` | Full rebuild plan, quality gates table, file structure | Quality gate targets (mAP50≥0.85, top-1≥98%, stone≥50%, etc.) |
| `planning/hieroglyph-rebuild/PROBLEM_ANALYSIS.md` | Root cause analysis — why v1 models failed | Detector mAP50=0.71 (gate 0.85), classifier stone accuracy 5-15% |
| `planning/hieroglyph-rebuild/SYSTEM_DESIGN.md` | Architecture: dual pipeline, fallback chains, data flow | Scan flow, identify flow, Thoth chat flow |
| `planning/hieroglyph-rebuild/REBUILD_TASKS.md` | All 57 tasks with descriptions, deps, sizes | H-DETECTOR-05/06, L-LANDMARKS-03/05/06 details |
| `planning/hieroglyph-rebuild/CHECKLIST.md` | 43 quality gates — **ALL UNCHECKED** (need ticking) | FIX-G0A→G13, VIS-G1→G10, DET-G1→G7, WRT-G9, LM-G4/5/7, LAUNCH-G1→G10 |
| `planning/hieroglyph-rebuild/PROGRESS.md` | Task completion tracker — **currently 52/57** | Update to 57/57 when done |
| `planning/hieroglyph-rebuild/API_STRATEGY.md` | All API providers: Gemini, Groq, Grok, Cloudflare, Deepgram, TLA | Cloudflare config, endpoint format, neuron budget |
| `planning/hieroglyph-rebuild/START_PROMPTS.md` | Session start prompts for each phase | Historical reference only |

### Original App Build (Complete — 86/86)
| File | Purpose |
|------|---------|
| `planning/rebuild/MASTER_PLAN.md` | Original P0-P7 build plan (all complete) |
| `planning/rebuild/PROGRESS.md` | 86/86 = 100% |
| `planning/rebuild/CHECKLIST.md` | Original build checklist (separate from hieroglyph rebuild) |
| `planning/rebuild/REBUILD_TASKS.md` | Original build tasks |
| `planning/rebuild/KNOWN_ISSUES.md` | Historical known issues |

### Detector Rebuild (Historical — folded into H-DETECTOR)
| File | Purpose |
|------|---------|
| `planning/detector-rebuild/MASTER_PLAN.md` | Detector-specific rebuild plan |
| `planning/detector-rebuild/DETECTOR_REBUILD_LOG.md` | Training log: v1 88 epochs mAP50=0.71, v2 attempts |
| `planning/detector-rebuild/PROGRESS.md` | Detector rebuild progress |
| `planning/detector-rebuild/CHECKLIST.md` | Detector-specific quality gates |

### Model Notebooks (Kaggle sources)
| File | Purpose |
|------|---------|
| `planning/model-rebuild/pytorch/detector/hieroglyph_detector_v3.ipynb` | Detector v3 notebook (pushed to Kaggle) |
| `planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier_v2.ipynb` | Classifier v2 notebook (pushed to Kaggle) |
| `planning/model-rebuild/pytorch/detector/kernel-metadata.json` | Detector kernel config: `naderelakany/wadjet-hieroglyph-detector-v3` |
| `planning/model-rebuild/pytorch/hieroglyph/kernel-metadata.json` | Classifier kernel config: `naderelakany/wadjet-hieroglyph-classifier-v2` |

---

## Current Project Status Snapshot

> This snapshot is accurate as of commit `ff0d282` on `clean-main` (March 27, 2026).
> If VS Code crashes, this is your ground truth.

### Completed Phases (52/57)

| Phase | Tasks | Status | Summary |
|-------|-------|--------|---------|
| H-FIX | 19/19 | ✅ | FP32 classifier, BGR→RGB, label_mapping fixed (110/171 were wrong), asyncio fix, config threshold wired, reading direction, Grok vision, bilingual translation, JS pipeline fixes, camera CPU fix |
| H-VISION | 8/8 | ✅ | AIService + GroqService, AI reader (Gemini→Groq→Grok), scan mode selector (AI/ONNX/Auto), cross-validator, /api/read endpoint |
| H-TRANSLATE | 6/6 | ✅ | Gemini embeddings (768-dim), FAISS index (15,604 vectors), few-shot bilingual translation, Groq fallback, cache (512 LRU), BLEU=0.594 |
| H-AUDIO | 5/5 | ✅ | WadjetTTS (Web Speech), TTS in scan+dictionary+chat, Groq PlayAI TTS (/api/tts), Groq Whisper STT (/api/stt), MediaRecorder UI |
| H-DETECTOR | 4/6 | 🔄 | Data audited, balanced dataset (4,771 train), detector v3 notebook, classifier v2 notebook. **05/06 remaining** |
| W-WRITE | 7/7 | ✅ | 14,593 EN→MdC corpus, 60+ shortcut phrases, Egyptologist AI prompt, j↔i/z→s aliases, test_write.py 100% |
| L-LANDMARKS | 3/6 | 🔄 | 260+ sites with descriptions, AI enrichment cached, Groq Llama 4 Scout fallback. **03/05/06 remaining** |

### Fallback Chains (Current State)

| Feature | Chain |
|---------|-------|
| Scan (AI read) | Gemini → Groq (Llama 4 Scout vision) → Grok (grok-4 vision) |
| Scan (translate) | Gemini → Groq (Llama 3.3 70B) → Grok fallback |
| Identify (landmark) | ONNX + Gemini (parallel) → Groq → Grok (tiebreaker) → ONNX-only |
| Write (smart mode) | Gemini → Groq → Grok via AIService.text_json() |
| Thoth Chat | Gemini → Groq (generate_text) → Grok |
| TTS | Groq PlayAI → Web Speech API |
| STT | Groq Whisper (whisper-large-v3-turbo) |

### API Keys in .env

| Provider | Config Key | Count |
|----------|-----------|-------|
| Gemini | `GEMINI_API_KEYS` | 17-key rotation |
| Groq | `GROQ_API_KEYS` | 8-key rotation |
| Grok (xAI) | `GROK_API_KEY` | 1 key |
| Cloudflare | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | 1 account (already in .env) |

### Git State

```
Branch: clean-main
HEAD:   ff0d282 "feat: Groq fallback for Thoth chat"
Remotes:
  origin → GitHub (synced)
  hf     → HuggingFace Spaces (synced, pushes clean-main:main)
```

### Recent Commits (newest first)

| Hash | Message |
|------|---------|
| `ff0d282` | feat: Groq fallback for Thoth chat |
| `93463e6` | feat: TTS + STT in chat page |
| `f07a889` | fix: update stale landmark/sign counts across all templates |
| (earlier) | Various H-FIX, H-VISION, H-TRANSLATE, H-AUDIO, W-WRITE, L-LANDMARKS commits |

### Data Files

| File | Content |
|------|---------|
| `data/expanded_sites.json` | 260+ Egyptian sites with descriptions, coordinates, categories |
| `data/landmark_enrichment_cache.json` | Disk LRU cache (300 entries) for AI-generated highlights/tips |
| `data/translation/faiss_index.bin` | 15,604 vectors, 768-dim, IndexFlatIP |
| `data/translation/corpus_texts.json` | Translation corpus for RAG |
| `data/reference/gardiner_data.json` | 1,000+ Gardiner signs |
| `data/reference/en_to_mdc_corpus.json` | 14,593 EN→MdC entries for write feature |
| `data/reference/known_phrases.json` | 60+ shortcut phrases |
| `models/hieroglyph/detection/` | glyph_detector.onnx + uint8 (v1 — will be replaced) |
| `models/hieroglyph/classifier/` | hieroglyph_classifier.onnx + uint8, label_mapping.json, model_metadata.json (v1 — will be replaced) |
| `models/landmark/` | Landmark ONNX model + classes |

---

## DO NOT

- **Do NOT modify** `hieroglyph-pipeline.js` detect/classify parsing unless the actual output shape differs from expected
- **Do NOT modify** `postprocess.py` unless the actual output shape differs
- **Do NOT change** the existing Gemini→Groq→Grok fallback chain — only ADD Cloudflare after Grok
- **Do NOT over-engineer** the TLA integration — keep it lightweight and optional
- **Do NOT skip** running `_validate_all.py` before the final commit
