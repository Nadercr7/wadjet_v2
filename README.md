---
title: Wadjet v2
emoji: 🏛️
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: true
---

<div align="center">

<img src="https://img.shields.io/badge/Python-3.13-D4AF37?style=for-the-badge&logo=python&logoColor=0A0A0A&labelColor=141414" />
<img src="https://img.shields.io/badge/FastAPI-0.115-D4AF37?style=for-the-badge&logo=fastapi&logoColor=0A0A0A&labelColor=141414" />
<img src="https://img.shields.io/badge/TailwindCSS-v4-D4AF37?style=for-the-badge&logo=tailwindcss&logoColor=0A0A0A&labelColor=141414" />
<img src="https://img.shields.io/badge/ONNX-Runtime-D4AF37?style=for-the-badge&logo=onnx&logoColor=0A0A0A&labelColor=141414" />

<br/><br/>

<h1>
  <img src="https://img.shields.io/badge/𓂀_WADJET-v2-D4AF37?style=flat-square&labelColor=0A0A0A&color=D4AF37&logoColor=D4AF37" height="40"/>
</h1>

<p><strong>AI-powered Egyptian heritage platform</strong><br/>
Scan hieroglyphs · Translate inscriptions · Explore 260+ landmarks · Ask Thoth</p>

<a href="https://huggingface.co/spaces/nadercr7/wadjet-v2">
  <img src="https://img.shields.io/badge/🚀_Live_Demo-HuggingFace-D4AF37?style=for-the-badge&labelColor=141414" />
</a>

</div>

---

<div align="center">
<table>
<tr>
<td align="center" width="20%">
<h3>𓂀</h3>
<strong>Scan</strong><br/>
<sub>Upload or photograph hieroglyphic inscriptions. Detect, classify, and transliterate every sign.</sub>
</td>
<td align="center" width="20%">
<h3>𓏏</h3>
<strong>Dictionary</strong><br/>
<sub>Browse 1,000+ Gardiner signs across all 26 categories with full phonetic and semantic data.</sub>
</td>
<td align="center" width="20%">
<h3>𓆣</h3>
<strong>Write</strong><br/>
<sub>Convert English or transliteration into authentic hieroglyphic sequences.</sub>
</td>
<td align="center" width="20%">
<h3>🏛️</h3>
<strong>Explore</strong><br/>
<sub>260+ Egyptian landmarks — temples, tombs, pyramids — with AI-enriched descriptions.</sub>
</td>
<td align="center" width="20%">
<h3>𓅃</h3>
<strong>Thoth</strong><br/>
<sub>Ask anything about Ancient Egypt. Thoth answers with the wisdom of a master Egyptologist.</sub>
</td>
</tr>
</table>
</div>

---

## How It Works

Wadjet is built around a **dual-path architecture** — every feature belongs to either the Hieroglyphs path or the Landmarks path, both equally accessible from the landing page.

```
Landing Page (/)
├── 𓂀 Hieroglyphs Path
│   ├── /scan        — Upload image → detect glyphs → classify → translate
│   ├── /dictionary  — Browse 1,023 Gardiner signs
│   └── /write       — Text → hieroglyphs (alpha or transliteration mode)
│
└── 🏛️ Landmarks Path
    ├── /explore     — 260+ heritage sites, search & filter
    └── /identify    — Upload photo → identify the landmark (via /explore)
        
    𓅃 /chat  — Thoth AI chatbot (shared by both paths)
```

The hieroglyph scanner uses a two-stage pipeline: a custom YOLO-based detector finds glyph regions, then an ONNX classifier identifies each sign from 171 Gardiner classes. A FAISS-indexed RAG system handles translation. When the local pipeline confidence is low, Gemini Vision steps in as a fallback reader.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13 · FastAPI 0.115 · Uvicorn |
| Templates | Jinja2 · Server-side rendering |
| CSS | TailwindCSS v4 (CLI build) |
| Interactivity | Alpine.js 3.14 · HTMX 2.0 |
| ML — browser | ONNX Runtime Web · TF.js |
| ML — server | ONNX Runtime · FAISS |
| AI | Gemini · Groq · Grok (multi-provider fallback chain) |
| Deploy | Docker · HuggingFace Spaces · Render |

---

## Running Locally

```bash
# Clone
git clone https://github.com/Nadercr7/wadjet_v2.git
cd wadjet_v2

# Environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# CSS
npm install
npm run build

# Config — add your Gemini API key(s)
cp .env.example .env

# Start
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000**

> Scan and Dictionary work offline. Translation, Chat, and Landmark AI require a Gemini API key (free tier).

---

## Models

| Model | Architecture | Classes | Accuracy |
|---|---|---|---|
| Hieroglyph Detector | YOLOv26s · ONNX uint8 | 1 (glyph) | mAP50 = 0.75 |
| Hieroglyph Classifier | MobileNetV3-Small · ONNX uint8 | 171 Gardiner | 98.2% top-1 |
| Landmark Classifier | EfficientNet-B0 · ONNX uint8 | 52 sites | 93.8% top-1 |

All models run fully **on-device** — no images are sent to external servers for inference.

---

## Design

The entire UI uses a custom **Black & Gold Egyptian** design system:

- Background `#0A0A0A` · Surfaces `#141414` / `#1E1E1E`
- Gold accent `#D4AF37` — all CTAs, highlights, and active states
- Typography: **Playfair Display** (headings) · **Inter** (body) · **Noto Sans Egyptian Hieroglyphs** (glyphs)
- No light mode. No blue links. No white backgrounds.

---

<div align="center">
<sub>Built by Mr Robot</sub>
</div>
