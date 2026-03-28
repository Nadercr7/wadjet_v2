# Wadjet v1 Reference

These are key files from Wadjet v1 — the first full rewrite of the Horus AI project. V1 introduced:

- FastAPI + Jinja2 server-side rendering (replacing Flask)
- Dual-path architecture: Hieroglyphs + Landmarks
- TailwindCSS design system
- TF.js browser-side ML inference
- YOLOv8 hieroglyph detection (261 auto-labeled images)
- 52 landmark classes, 171 Gardiner sign classes
- HuggingFace Spaces deployment

## Contents

- `core/` — Python business logic modules (pipeline, gardiner mapping, translation, attractions data, etc.)
- `js/` — Client-side JavaScript (hieroglyph pipeline, camera, classifier, detection, TTS)
- `templates/` — Original scan.html and explore.html for comparison with v2

V2 rebuilt everything from scratch with better architecture, more data, and AI-first design.
