# Wadjet v2 — Pre-Flight Checklist

> Run through this checklist before starting any new phase.
> Each section must pass before proceeding.

---

## 1. Environment Setup

- [ ] Python 3.13 installed: `python --version`
- [ ] Virtual env exists: `.venv/` directory present
- [ ] Activate venv: `.venv\Scripts\activate` (Windows)
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] TailwindCSS v4 CLI available: `npx @tailwindcss/cli --help`
- [ ] Node modules installed: `npm install` (for Tailwind + dependencies)
- [ ] `.env` file exists (copy from `.env.example` if not)

## 2. Asset Copying (run once)

- [ ] Dry-run copy script: `python scripts/copy_assets.py --dry-run`
- [ ] Execute copy: `python scripts/copy_assets.py --execute`
- [ ] Verify models directory: `models/hieroglyph/` has detector + classifier
- [ ] Verify landmark model: `models/landmark/tfjs/model.json` exists
- [ ] Verify data directory: `data/translation/corpus.jsonl` exists
- [ ] Verify fonts: `app/static/fonts/NotoSansEgyptianHieroglyphs-Regular.ttf`

## 3. CSS Build

- [ ] Build CSS: `npx @tailwindcss/cli -i app/static/css/input.css -o app/static/dist/styles.css`
- [ ] Output file exists: `app/static/dist/styles.css`
- [ ] Cache bust: update `?v=N` in `base.html` `<link>` tag after changes

## 4. Server Test

- [ ] Start server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] Health check: `curl http://localhost:8000/api/health` returns `{"status":"ok"}`

## 5. Route Verification

- [ ] `/` — Landing page loads (dual-path choice)
- [ ] `/hieroglyphs` — Hieroglyphs hub loads
- [ ] `/landmarks` — Landmarks hub loads
- [ ] `/scan` — Scan page loads
- [ ] `/dictionary` — Dictionary page loads
- [ ] `/write` — Write page loads
- [ ] `/explore` — Explore page loads
- [ ] `/chat` — Chat page loads

## 6. Design System Check

- [ ] Background color is `#0A0A0A` (not white or gray)
- [ ] Gold accents are `#D4AF37`
- [ ] Playfair Display font loads for headings
- [ ] Inter font loads for body text
- [ ] Footer shows "Built by Mr Robot"
- [ ] Navigation breadcrumbs work on sub-pages
- [ ] Mobile responsive (test at 375px width)

## 7. Planning Files

- [ ] `planning/CONSTITUTION.md` — exists and is current
- [ ] `planning/PLAN.md` — exists and is current
- [ ] `planning/PROGRESS.md` — exists, tasks updated
- [ ] `planning/SESSION_LOG.md` — exists, last session documented
- [ ] `planning/PROMPTS.md` — exists, references CONSTITUTION.md

## 8. Phase-Specific Gates

### Before P2 (Scan Feature)
- [ ] ONNX detector model copied to `models/hieroglyph/detector/`
- [ ] Keras classifier copied to `models/hieroglyph/classifier_keras/`
- [ ] TF.js classifier copied to `models/hieroglyph/classifier_tfjs/`
- [ ] Label mapping JSON in place
- [ ] v1 `pipeline.py` reviewed for port

### Before P3 (Dictionary & Write)
- [ ] `gardiner_mapping.py` copied from v1
- [ ] All 700+ glyphs verified in mapping

### Before P4 (Explore)
- [ ] `attractions_data.py` copied from v1
- [ ] Landmark metadata JSONs in `data/metadata/`
- [ ] Landmark text descriptions in `data/text/`
- [ ] Landmark TF.js model in `models/landmark/tfjs/`

### Before P5 (AI Features)
- [ ] Gemini API key(s) in `.env`
- [ ] Key rotation logic tested

### Before P7 (Deploy)
- [ ] `Dockerfile` builds successfully: `docker build -t wadjet .`
- [ ] `docker-compose up` starts without errors
- [ ] `render.yaml` reviewed for current settings
