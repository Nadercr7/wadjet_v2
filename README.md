---
title: Wadjet v2
emoji: 🏛️
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: true
---

# Wadjet v2

> **AI-powered Egyptian heritage app** — scan hieroglyphs, translate inscriptions, explore landmarks, and learn from Thoth.

## Architecture

Wadjet v2 uses a **dual-path** design. The landing page presents two equal choices:

- **Hieroglyphs Path** (`/hieroglyphs`) — Scan & identify, Gardiner dictionary, write in hieroglyphs
- **Landmarks Path** (`/landmarks`) — Explore 52 Egyptian sites, identify from photos
- **Shared** — Thoth AI chatbot, 2 ML models, offline support

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Build TailwindCSS
npx @tailwindcss/cli@4 -i app/static/css/input.css -o app/static/dist/styles.css --watch

# 4. Copy .env
copy .env.example .env
# Edit .env with your Gemini API keys

# 5. Run dev server
uvicorn app.main:app --reload --port 8000
```

Visit [http://localhost:8000](http://localhost:8000)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python 3.13 |
| Templates | Jinja2 |
| CSS | TailwindCSS v4 |
| Interactivity | Alpine.js + HTMX |
| ML (browser) | ONNX Runtime Web + TF.js |
| ML (server) | ONNX Runtime + TensorFlow |
| AI | Gemini API (translation, chat) |
| Translation | FAISS RAG + Gemini |

## Features

- **Scan** — Upload/camera → detect hieroglyphs → classify → transliterate → translate
- **Dictionary** — Browse 700+ Gardiner signs by category
- **Write** — Convert text to hieroglyphs
- **Explore** — 52 Egyptian landmarks with AI descriptions
- **Ask Thoth** — AI chatbot for Egyptology questions

## Design

Black & Gold theme with Playfair Display headings and Inter body text.
Egyptian-themed, professional SaaS-quality UI.

## Project Structure

See [planning/PLAN.md](planning/PLAN.md) for full architecture documentation.
