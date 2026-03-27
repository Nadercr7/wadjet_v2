# Wadjet v2 — Rebuild Start Prompts

> Ready-to-paste prompts for each rebuild phase.
> **Order**: Phase A → B → C → D → E
> **Tasks reference**: `planning/rebuild/REBUILD_TASKS.md`
> **Full plan**: `planning/rebuild/MASTER_PLAN.md`
> **Feature specs**: `planning/rebuild/specs/` (hieroglyph-classifier-spec.md, landmark-identify-spec.md)
> **Known issues**: `planning/rebuild/KNOWN_ISSUES.md`
> **Pre-launch gate**: `planning/rebuild/CHECKLIST.md`

---

## PHASE A — Environment & Verification

> Send this prompt to start Phase A.

```
We're working on Wadjet v2 — an AI-powered Egyptian heritage web app.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST (in order):
1. CLAUDE.md
2. planning/CONSTITUTION.md
3. planning/rebuild/MASTER_PLAN.md  ← full rebuild plan
4. planning/rebuild/REBUILD_TASKS.md  ← task tracker, start at Phase A
5. planning/rebuild/KNOWN_ISSUES.md  ← WHY things are broken + what exact fix is needed

CONTEXT:
- Frontend (P0–P6) is 100% COMPLETE. Do NOT touch any templates or CSS.
- We are rebuilding the ML backend from scratch using PyTorch (not Keras/TF).
- Old models had _FusedConv2D crash in ONNX Runtime — scrapping them entirely.
- Training will happen on KAGGLE GPU (T4/P100) — PyTorch + timm + onnx are pre-installed there.
- Previous Kaggle failure was due to tf2onnx pip install — NOT an issue now (torch.onnx.export is built-in).

PHASE A GOAL: Prepare the Kaggle training environment and get ALL datasets uploaded (hieroglyph + landmark).

DATA STATUS:
- Hieroglyph dataset: ✅ PREPARED at data/hieroglyph_classification/ (16,638 train, 171 classes, augmented)
- Landmark dataset: ✅ PREPARED at data/landmark_classification/ (25,710 train, 52 classes, merged from v1 splits + eg-landmarks + augmented, min=300)

Tasks:
- A.1: Verify Kaggle account has GPU quota enabled (phone verification if needed)
    Kaggle account: nadermohamedcr7
    Credentials: C:\Users\Nader\.kaggle\kaggle.json ✅ already in place
    CLI: .venv\Scripts\kaggle.exe (install via `pip install kaggle` — already done ✅)
- A.2: Upload the hieroglyph dataset to Kaggle:
    Command: kaggle datasets create -p "data\hieroglyph_classification" --dir-mode zip
    ✅ dataset-metadata.json already at data/hieroglyph_classification/dataset-metadata.json
- A.2b: Upload the landmark dataset to Kaggle:
    Command: kaggle datasets create -p "data\landmark_classification" --dir-mode zip
    ✅ dataset-metadata.json already at data/landmark_classification/dataset-metadata.json
    This dataset includes: v1 splits + eg-landmarks extra + augmentation (25,710 train, 52 classes, min=300)
- A.3: Copy ONNX detector to correct project path:
    From: D:\Personal attachements\Projects\Final_Horus\Wadjet\hieroglyph_model\models\detection\glyph_detector_uint8.onnx
    To:   models/hieroglyph/detection/glyph_detector_uint8.onnx
- A.4: Create skeleton training notebooks:
    ✅ kernel-metadata.json files ALREADY CREATED at:
       planning/model-rebuild/pytorch/hieroglyph/kernel-metadata.json
       planning/model-rebuild/pytorch/landmark/kernel-metadata.json
    Still needed: create minimal notebook files in same folders so kaggle kernels push works
- A.5: Confirm planning/model-rebuild/pytorch/ folder structure exists ✅

Resources to check:
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\ml-engineer\SKILL.md
- D:\Personal attachements\Repos\AGENTS.md (repo inventory)
- D:\Personal attachements\Repos\kaggle-api\  ← Kaggle CLI: dataset upload + kernel push + output download

Kaggle CLI key commands:
  kaggle datasets create -p <dir> --dir-mode zip   ← upload dataset
  kaggle kernels push -p planning/model-rebuild/pytorch/hieroglyph/  ← push hieroglyph notebook
  kaggle kernels push -p planning/model-rebuild/pytorch/landmark/    ← push landmark notebook
  kaggle kernels status nadermohamedcr7/hieroglyph-classifier  ← check if training finished
  kaggle kernels status nadermohamedcr7/landmark-classifier    ← check if landmark training finished
  kaggle kernels output nadermohamedcr7/hieroglyph-classifier -p models/hieroglyph/classifier/
  kaggle kernels output nadermohamedcr7/landmark-classifier -p models/landmark/classifier/

Gate: Kaggle GPU active, both datasets uploaded, detector copied, both notebook skeletons + kernel-metadata.json ready.
Update REBUILD_TASKS.md checkboxes as each task completes.
```

---

## PHASE B — Hieroglyph Classifier Training

> Send this prompt AFTER Phase A gate passes.

```
We're working on Wadjet v2 — Phase A (environment) is complete.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST:
1. planning/rebuild/MASTER_PLAN.md  (Sections 2.1, Phase B, Section 6 critical rules)
2. planning/rebuild/REBUILD_TASKS.md  (Phase B tasks)
3. planning/rebuild/specs/hieroglyph-classifier-spec.md  ← full spec with acceptance criteria

PHASE B GOAL: Build the training notebook, run it on Kaggle GPU, export the classifier as ONNX.

TRAINING PLATFORM: Kaggle GPU (T4 or P100)
- torch, torchvision, timm, onnx, onnxruntime, albumentations, kornia, mlflow are PRE-INSTALLED
- Only need: !pip install -q lightning  (one line at top of notebook)
- Dataset attached from Kaggle private dataset: /kaggle/input/wadjet-hieroglyph-classification/
- Outputs saved to /kaggle/working/ → download via kaggle-api after run

Push notebook to run:   kaggle kernels push -p planning/model-rebuild/pytorch/
Monitor:                kaggle kernels status nadermohamedcr7/hieroglyph-classifier
Download outputs:       kaggle kernels output nadermohamedcr7/hieroglyph-classifier -p models/hieroglyph/classifier/

Load these skills:
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\ml-engineer\SKILL.md
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\computer-vision-expert\SKILL.md

Key repos to reference (for patterns — all pre-installed on Kaggle):
- D:\Personal attachements\Repos\kaggle-api\  ← push kernel + download outputs CLI
- D:\Personal attachements\Repos\pytorch-image-models\  (timm — pretrained MobileNetV3)
- D:\Personal attachements\Repos\pytorch-lightning\  (training loop — LightningModule + Trainer)
- D:\Personal attachements\Repos\albumentations\  (augmentation pipeline)
- D:\Personal attachements\Repos\mlflow\  (experiment tracking — log metrics/artifacts)
- D:\Personal attachements\Repos\optuna\  (optional: hyperparameter search if accuracy < 70%)

Data (on Kaggle after dataset is attached):
  Train: /kaggle/input/wadjet-hieroglyph-classification/train
  Val:   /kaggle/input/wadjet-hieroglyph-classification/val
  Test:  /kaggle/input/wadjet-hieroglyph-classification/test
  Classes: 171, Images: ~15,017 train

CRITICAL RULES:
- NO horizontal flip augmentation (hieroglyphs are direction-sensitive!)
- Export format: NCHW [1, 3, 128, 128] float32 — NOT NHWC
- Use torch.onnx.export(), opset_version=17
- Use float32 ONLY (no mixed precision — causes fused ops that break ONNX)
- After export: quantize_dynamic to uint8

Tasks: B.0 (optional fiftyone inspect) → B.1 (create notebook) → B.2–B.13 (train → export → copy)

Output files to produce:
  models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx
  models/hieroglyph/classifier/label_mapping.json  (0→"A1", 1→"A55", ...)
  models/hieroglyph/classifier/model_metadata.json

Gate: val accuracy > 70%, ONNX output shape [1, 171] confirmed.
Update REBUILD_TASKS.md as tasks complete.
```

---

## PHASE B2 — Landmark Classifier Training

> Send this prompt AFTER Phase A gate passes (landmark datasets are uploaded to Kaggle).
> Can run in PARALLEL with Phase B (both are independent Kaggle notebooks).

```
We're working on Wadjet v2 — Phase A (environment) is complete and landmark datasets are uploaded.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST:
1. planning/rebuild/MASTER_PLAN.md  (Sections 2.2 EfficientNet-B0 spec, 2.3 hybrid endpoint, Phase B2, Section 6 critical rules)
2. planning/rebuild/REBUILD_TASKS.md  (Phase B2 tasks)
3. planning/rebuild/specs/landmark-identify-spec.md  ← if it exists; check planning/rebuild/specs/

PHASE B2 GOAL: Build the landmark training notebook, run it on Kaggle GPU, export EfficientNet-B0 as ONNX uint8.

TRAINING PLATFORM: Kaggle GPU (T4 or P100)
- torch, torchvision, timm, onnx, onnxruntime, albumentations are PRE-INSTALLED
- Only need: !pip install -q lightning
- Dataset attached on Kaggle:
    /kaggle/input/wadjet-landmark-classification/   ← merged dataset (train/val/test, 52 classes, 25,710 train, min=300)
    NOTE: Data is already merged + augmented locally. NO merge needed in notebook!
- Outputs saved to /kaggle/working/ → download via kaggle-api after run

Push notebook to run:   kaggle kernels push -p planning/model-rebuild/pytorch/landmark/
Monitor:                kaggle kernels status nadermohamedcr7/landmark-classifier
Download outputs:       kaggle kernels output nadermohamedcr7/landmark-classifier -p models/landmark/classifier/

Load these skills:
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\ml-engineer\SKILL.md
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\computer-vision-expert\SKILL.md

Key repos to reference:
- D:\Personal attachements\Repos\pytorch-image-models\  (timm — pretrained EfficientNet-B0)
- D:\Personal attachements\Repos\pytorch-lightning\  (training loop)
- D:\Personal attachements\Repos\albumentations\  (augmentation)
- D:\Personal attachements\Repos\kornia\  (optional GPU augmentation)

Architecture:
  Model: timm.create_model('efficientnet_b0', pretrained=True, num_classes=52)
  Input: [1, 3, 224, 224] float32 NCHW
  Output: [1, 52] softmax probabilities
  Export: opset_version=17, dynamic_axes on batch dim

EG_TO_V1 mapping (NOT needed in notebook — merge was done locally):
  All data is already merged in the uploaded dataset. No folder renaming needed.
  The training notebook just uses ImageFolder on /kaggle/input/wadjet-landmark-classification/train/

Data strategy:
  Dataset is ALREADY PREPARED — 25,710 train / 4,506 val / 4,497 test
  All 52 classes have min=300 images (augmentation done locally)
  NO merge/augmentation needed in the notebook — just train directly!

CRITICAL RULES:
- HorizontalFlip IS ALLOWED (landmarks are real-world photos, not direction-sensitive)
- Export format: NCHW [1, 3, 224, 224] float32 (NOT NHWC!)
- Use torch.onnx.export(), opset_version=17
- Use float32 ONLY (no mixed precision)
- After export: quantize_dynamic to uint8

Tasks: B2.1 (create notebook) → B2.2 (EG_TO_V1 merge) → B2.3–B2.15 (train → export → copy)

Output files to produce:
  models/landmark/classifier/landmark_classifier_uint8.onnx   (~15-20 MB)
  models/landmark/classifier/landmark_label_mapping.json      (0→"abu_simbel", ..., 51→"white_desert")
  models/landmark/classifier/model_metadata.json

Gate: val accuracy > 75%, ONNX output shape [1, 52] confirmed.
Update REBUILD_TASKS.md as tasks complete.
```

---

## PHASE C — Backend Integration

> Send this prompt AFTER BOTH Phase B AND Phase B2 gate passes (both ONNX models exported).

```
We're working on Wadjet v2 — Phases B and B2 (training) are complete. Both ONNX models ready.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST:
1. planning/rebuild/MASTER_PLAN.md  (Section 2 architecture, Section 4 File Map, Phase C, Section 6 critical rules)
2. planning/rebuild/REBUILD_TASKS.md  (Phase C tasks)
3. planning/rebuild/KNOWN_ISSUES.md  (Issues 3, 4, 5 — the exact backend problems)
4. planning/rebuild/specs/hieroglyph-classifier-spec.md
5. planning/rebuild/specs/landmark-identify-spec.md  ← hybrid ONNX+Gemini endpoint spec (UPDATED)
6. app/core/hieroglyph_pipeline.py  ← needs NCHW fix
7. app/core/gardiner.py  ← only 71/171 signs mapped
8. app/api/explore.py  ← needs new hybrid endpoint

Load these skills:
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\fastapi-pro\SKILL.md
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\fastapi-router-py\SKILL.md
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\gemini-api-dev\SKILL.md
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\prompt-engineering-patterns\SKILL.md

Key repos to reference:
- D:\Personal attachements\Repos\sentence-transformers\  ← rag_translator.py uses bge-m3 embeddings
- D:\Personal attachements\Repos\faiss\  ← rag_translator.py uses FAISS index (debug if search fails)
- D:\Personal attachements\Repos\05-LangChain\langchain\  ← LangChain patterns if rag_translator.py uses chains
- D:\Personal attachements\Repos\01-Google-AI\  ← Gemini Vision multimodal examples
- D:\Personal attachements\Repos\Prompt-Engineering-Guide\  ← Gemini JSON prompt patterns

PHASE C GOAL: Wire the new ONNX classifiers into the backend, complete Gardiner mapping, add hybrid landmark identify endpoint.

Tasks:
- C.1–C.4: Fix hieroglyph_pipeline.py (NCHW input, correct path, lower threshold 0.25→0.15)
- C.5: Complete gardiner.py — map ALL 171 signs from label_mapping.json
- C.6: Re-enable translation — remove disabled flag in rag_translator.py
- C.7: Create app/core/landmark_pipeline.py (ONNX inference wrapper for landmark classifier)
- C.8: Add identify_landmark() (Gemini Vision fallback) + describe_landmark() to gemini_service.py
- C.9: Add POST /api/explore/identify hybrid endpoint:
    1. Run local ONNX model → get class + confidence
    2. If confidence >= 0.5 → return model result + Gemini description (enrichment only)
    3. If confidence < 0.5 → also call Gemini Vision to identify (double-check)
    4. If ONNX fails → fallback to Gemini Vision only
- C.10: Remove old TF.js explore endpoint
- C.11–C.12: Manual curl tests for both APIs

GEMINI_API_KEYS: 17 keys in .env, comma-separated — already wired in gemini_service.py rotation.

Gate: curl /api/scan returns glyphs, curl /api/explore/identify returns landmark JSON {name, slug, confidence, source, description, top3}.
Update REBUILD_TASKS.md as tasks complete.
```

---

## PHASE D — Frontend Updates

> Send this prompt AFTER Phase C gate passes (all API endpoints work).

```
We're working on Wadjet v2 — Phase C (backend) is complete.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST:
1. planning/rebuild/MASTER_PLAN.md  (Phase D)
2. planning/rebuild/REBUILD_TASKS.md  (Phase D tasks)
3. app/static/js/hieroglyph-pipeline.js  ← needs NCHW fix
4. app/templates/explore.html  ← needs TF.js removal + Gemini HTMX form
5. app/static/sw.js  ← cache version bump
6. app/templates/base.html  ← cache buster bump

Load this skill:
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\tailwind-patterns\SKILL.md

PHASE D GOAL: Fix the browser-side classifier preprocessing and replace TF.js landmark identify with HTMX → Gemini endpoint.

Tasks:
- D.1–D.3: Fix hieroglyph-pipeline.js — TWO places need NCHW fix:
    (a) `_warmup()` dummy tensor: change from [1, s, s, 3] → [1, 3, s, s]
    (b) `classify()` pixel loop: change from NHWC interleaved to NCHW planar + tensor [1, 3, size, size]
    (c) Update model URL to hieroglyph_classifier_uint8.onnx
    See KNOWN_ISSUES.md Issue 5 for exact before/after code snippets.
- D.4–D.5: explore.html — remove all tf.loadLayersModel() code, add HTMX form hx-post="/api/explore/identify"
- D.6: Create app/templates/partials/identify_result.html partial
- D.7: Bump sw.js CACHE_VERSION to 'v15'
- D.8: Bump base.html ?v= cache busters to v=15
- D.9: npm run build (production CSS)
- D.10: Browser smoke test — Chrome DevTools, no console errors

CRITICAL: Do NOT redesign any page. Only fix the broken JS/HTMX wiring.

Gate: Full browser test — scan works + landmark identify works, no console errors.
Update REBUILD_TASKS.md as tasks complete.
```

---

## PHASE E — Integration Testing & Deploy

> Send this prompt AFTER Phase D gate passes (browser test passes).

```
We're working on Wadjet v2 — Phases A–D are complete. Ready to deploy.
Project path: D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\

READ THESE FILES FIRST:
1. planning/rebuild/MASTER_PLAN.md  (Phase E)
2. planning/rebuild/REBUILD_TASKS.md  (Phase E tasks)
3. planning/rebuild/CHECKLIST.md  ← all gate criteria must pass before calling deploy done
3. Dockerfile
4. render.yaml
5. docker-compose.yml

Load these skills:
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\deployment-engineer\SKILL.md
- D:\Personal attachements\Repos\antigravity-awesome-skills\skills\docker-expert\SKILL.md

Security + Deploy references:
- D:\Personal attachements\Repos\18-Security\gitleaks\  ← run before deploy: `gitleaks detect` scans for API keys in code
- D:\Personal attachements\Repos\18-Security\Top10\  ← OWASP review: file upload validation, injection, access control
- D:\Personal attachements\Repos\BentoML\  ← model packaging alternative if raw Dockerfile gets complex

PHASE E GOAL: Full E2E test, production build, Docker, deploy to Render.

Tasks:
- E.1: Full E2E test locally (uvicorn, all 9 routes, all features)
- E.2: Fix Dockerfile — ensure models/ folder is included (it's git-ignored, needs special handling)
- E.3: Test Docker build locally (docker build && docker run)
- E.4: Configure Render env vars (GEMINI_API_KEYS, SECRET_KEY, etc.)
- E.5: Deploy to Render (git push / render.yaml)
- E.6: Smoke test on production URL

NOTE: models/ is git-ignored. For Render deploy, options:
  a) Commit models/ with a .dockerignore exception
  b) Use Render Disk mount
  c) Download models on container startup from cloud storage

Gate: Production URL responds. All 9 pages load. Scan works. Landmark identify works.
Update REBUILD_TASKS.md as tasks complete. Update PROGRESS.md P7+P8 to all ✅.
```

---

## AFTER EACH PHASE — Handoff Prompt

> After a phase completes and you want to save state before starting the next one.

```
Phase [X] is complete for Wadjet v2.

Please:
1. Update planning/rebuild/REBUILD_TASKS.md — mark all Phase [X] tasks as ✅
2. Update planning/rebuild/PROGRESS.md — mark Phase P8.[X] tasks as ✅
3. Write a brief summary of what changed (files modified, any issues encountered)
4. Confirm the gate condition passes
5. Tell me which file to send next (use planning/START_PROMPTS.md — Phase [X+1])
```
