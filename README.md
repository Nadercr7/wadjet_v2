<div align="center">

<!-- Header Banner -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0A0A0A,50:D4AF37,100:0A0A0A&height=220&section=header&text=𓂀%20WADJET&fontSize=72&fontColor=D4AF37&fontAlignY=35&desc=AI-Powered%20Egyptian%20Heritage%20Platform&descSize=18&descColor=C4A265&descAlignY=55&animation=fadeIn" width="100%" />

<!-- Badges -->
<p>
<img src="https://img.shields.io/badge/Python-3.13-D4AF37?style=for-the-badge&logo=python&logoColor=0A0A0A&labelColor=141414" />
<img src="https://img.shields.io/badge/FastAPI-0.115-D4AF37?style=for-the-badge&logo=fastapi&logoColor=0A0A0A&labelColor=141414" />
<img src="https://img.shields.io/badge/TailwindCSS-v4-D4AF37?style=for-the-badge&logo=tailwindcss&logoColor=0A0A0A&labelColor=141414" />
<img src="https://img.shields.io/badge/ONNX-Runtime-D4AF37?style=for-the-badge&logo=onnx&logoColor=0A0A0A&labelColor=141414" />
<img src="https://img.shields.io/badge/HTMX-2.0-D4AF37?style=for-the-badge&logo=htmx&logoColor=0A0A0A&labelColor=141414" />
</p>

<p>
<strong>Scan hieroglyphs · Translate inscriptions · Explore 260+ landmarks · Learn from Thoth</strong>
</p>

<!-- Buttons -->
<a href="https://nadercr7-wadjet-v2.hf.space">
<img src="https://img.shields.io/badge/🚀%20Live%20Demo-HuggingFace%20Spaces-D4AF37?style=for-the-badge&labelColor=141414" />
</a>
&nbsp;
<a href="https://github.com/Nadercr7/wadjet_v2">
<img src="https://img.shields.io/badge/📦%20Source-GitHub-D4AF37?style=for-the-badge&logo=github&logoColor=D4AF37&labelColor=141414" />
</a>

<br/><br/>

<code>𓁹 𓂋 𓏏 𓅱 𓆓 𓊹 𓋴 𓂧 𓏲 𓎼 𓃭 𓆣 𓇋 𓈖 𓊃 𓄿</code>

</div>

<br/>

---

<br/>

<div align="center">

## ✦ What It Does

</div>

<table align="center">
<tr>
<td align="center" width="19%">
<h3>𓂀</h3>
<strong>Scan</strong><br/>
<sub>Upload hieroglyphic inscriptions → detect every glyph → classify → transliterate → translate to English</sub>
</td>
<td align="center" width="19%">
<h3>𓏛</h3>
<strong>Dictionary</strong><br/>
<sub>Browse 1,000+ Gardiner signs across all 26 categories with phonetic values and meanings</sub>
</td>
<td align="center" width="19%">
<h3>𓆣</h3>
<strong>Write</strong><br/>
<sub>Type English or transliteration and see it rendered in authentic hieroglyphic sequences</sub>
</td>
<td align="center" width="19%">
<h3>🏛️</h3>
<strong>Explore</strong><br/>
<sub>260+ Egyptian landmarks — temples, tombs, pyramids — with rich descriptions and details</sub>
</td>
<td align="center" width="19%">
<h3>𓅃</h3>
<strong>Thoth</strong><br/>
<sub>Ask anything about Ancient Egypt. Thoth answers with the depth of a master Egyptologist</sub>
</td>
</tr>
</table>

<br/>

---

<br/>

## 𓊹 Architecture

```
                          ┌──────────────────────────┐
                          │     Landing Page  (/)     │
                          └─────────┬────────────────┘
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │  𓂀 Hieroglyphs    │           │  🏛️ Landmarks     │
        │     Path          │           │     Path          │
        └───────┬───────────┘           └───────┬───────────┘
                │                               │
    ┌───────────┼───────────┐       ┌───────────┼───────────┐
    │           │           │       │           │           │
    ▼           ▼           ▼       ▼           ▼           │
 /scan     /dictionary   /write  /explore   /identify      │
                                                            │
                    ┌───────────────────────────────────────┘
                    ▼
              𓅃  /chat  (Thoth — shared by both paths)
```

**Scan Pipeline** — Two-stage on-device inference:

```
Image → YOLO Detector (find glyph regions) → ONNX Classifier (171 Gardiner classes)
      → FAISS-indexed RAG (transliteration → English)
      → Gemini Vision fallback (when local confidence is low)
```

All inference runs **on-device** — no images leave the browser for ML processing.

<br/>

---

<br/>

## 𓏏 Tech Stack

<table>
<tr><td><strong>Layer</strong></td><td><strong>Technology</strong></td></tr>
<tr><td>Backend</td><td>Python 3.13 · FastAPI 0.115 · Uvicorn</td></tr>
<tr><td>Templates</td><td>Jinja2 (server-side rendering, layout inheritance)</td></tr>
<tr><td>CSS</td><td>TailwindCSS v4 (CLI build, custom design system)</td></tr>
<tr><td>Interactivity</td><td>Alpine.js 3.14 · HTMX 2.0</td></tr>
<tr><td>ML — Browser</td><td>ONNX Runtime Web · TensorFlow.js</td></tr>
<tr><td>ML — Server</td><td>ONNX Runtime · FAISS vector search</td></tr>
<tr><td>AI Providers</td><td>Gemini · Groq · Grok (multi-provider fallback chain)</td></tr>
<tr><td>Fonts</td><td>Playfair Display · Inter · Noto Sans Egyptian Hieroglyphs</td></tr>
<tr><td>Deploy</td><td>Docker · HuggingFace Spaces · Render</td></tr>
</table>

<br/>

---

<br/>

## 𓃭 Models

<table>
<tr>
<td><strong>Model</strong></td>
<td><strong>Architecture</strong></td>
<td><strong>Task</strong></td>
<td><strong>Accuracy</strong></td>
</tr>
<tr>
<td>Hieroglyph Detector</td>
<td>YOLOv26s · ONNX uint8</td>
<td>Localize glyphs in photos</td>
<td><strong>mAP50 = 0.75</strong></td>
</tr>
<tr>
<td>Hieroglyph Classifier</td>
<td>MobileNetV3-Small · ONNX uint8</td>
<td>Identify 171 Gardiner signs</td>
<td><strong>98.2% top-1</strong></td>
</tr>
<tr>
<td>Landmark Classifier</td>
<td>EfficientNet-B0 · ONNX uint8</td>
<td>Identify 52 Egyptian sites</td>
<td><strong>93.8% top-1</strong></td>
</tr>
</table>

> All models are quantized to uint8 for minimal size and fast on-device inference. No images are sent to external servers.

<br/>

---

<br/>

## 🎨 Design System

<table>
<tr><td colspan="4" align="center"><strong>Black & Gold Egyptian Theme</strong></td></tr>
<tr>
<td align="center">
<img src="https://img.shields.io/badge/●-0A0A0A?style=flat-square&labelColor=0A0A0A" /> <br/><sub><code>#0A0A0A</code><br/>Night</sub>
</td>
<td align="center">
<img src="https://img.shields.io/badge/●-141414?style=flat-square&labelColor=141414" /> <br/><sub><code>#141414</code><br/>Surface</sub>
</td>
<td align="center">
<img src="https://img.shields.io/badge/●-D4AF37?style=flat-square&labelColor=D4AF37" /> <br/><sub><code>#D4AF37</code><br/>Gold</sub>
</td>
<td align="center">
<img src="https://img.shields.io/badge/●-F5F0E8?style=flat-square&labelColor=F5F0E8" /> <br/><sub><code>#F5F0E8</code><br/>Ivory</sub>
</td>
</tr>
</table>

- **Typography:** Playfair Display (headings) · Inter (body) · Noto Sans Egyptian Hieroglyphs (glyphs)
- **Fully dark UI** — no light mode, no white backgrounds, no blue links
- **Custom animations:** shimmer, pulse-gold, gradient-sweep, border-beam, meteor effects
- **Responsive:** Mobile-first layout, touch-optimized interactions

<br/>

---

<br/>

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/Nadercr7/wadjet_v2.git
cd wadjet_v2

# Environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# Build CSS
npm install && npm run build

# Configure — add your Gemini API key(s)
cp .env.example .env

# Launch
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000**

> 📌 Scan and Dictionary work fully offline. Translation, Chat, and Explore enrichment require a Gemini API key (free tier works).

<br/>

---

<br/>

## 🐳 Docker

```bash
docker build -t wadjet .
docker run -p 8000:8000 --env-file .env wadjet
```

Or with docker-compose:

```bash
docker-compose up
```

<br/>

---

<br/>

## 📂 Project Structure

```
wadjet/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # Pydantic Settings
│   ├── api/                 # Route handlers (pages + API)
│   ├── core/                # Business logic (classifiers, translation, quiz)
│   ├── static/              # CSS, JS, fonts, images
│   └── templates/           # Jinja2 templates (base + pages + partials)
├── models/                  # ONNX models (hieroglyph + landmark)
├── data/                    # Gardiner data, landmark data, embeddings
├── scripts/                 # Build & utility scripts
├── Dockerfile               # Multi-stage production build
└── docker-compose.yml       # Local container setup
```

<br/>

---

<br/>

## 𓂋 Routes

| Route | Description |
|---|---|
| `/` | Landing page — choose Hieroglyphs or Landmarks path |
| `/hieroglyphs` | Hieroglyphs hub — scan, dictionary, write |
| `/landmarks` | Landmarks hub — explore and identify |
| `/scan` | Upload photo → detect + classify + translate hieroglyphs |
| `/dictionary` | Browse 1,023 Gardiner signs with search & filtering |
| `/write` | Convert text to hieroglyphic sequences |
| `/explore` | Browse 260+ Egyptian heritage sites |
| `/chat` | Thoth — Egyptology chatbot |
| `/quiz` | Test your Ancient Egypt knowledge |
| `/api/health` | Health check endpoint |

<br/>

---

<br/>

<div align="center">

## 𓁹 The Journey

This project evolved through multiple stages — from a graduation project called **Horus AI** (Flask + single Keras classifier) to **Wadjet v1** (FastAPI + TF.js + 52 landmarks) and finally to **Wadjet v2**: a complete rebuild with custom-trained models, a dual-path architecture, and a fully dark Egyptian design system.

Three custom models were trained on Kaggle T4/P100 GPUs across multiple iterations. The hieroglyph classifier reached **98.2% accuracy** across 171 Gardiner sign classes. The detector was trained on **10,311 annotated images** combining museum photographs with synthetic stone-texture composites.

The full story is in [`JOURNEY.md`](JOURNEY.md).

</div>

<br/>

---

<br/>

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0A0A0A,50:D4AF37,100:0A0A0A&height=120&section=footer" width="100%" />

<br/>

<sub><strong>Built by Mr Robot</strong></sub>

<br/><br/>

<code>𓂀 𓊹 𓅃 𓆣 𓏛 𓃭</code>

</div>
