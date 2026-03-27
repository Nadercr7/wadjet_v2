# Detector Rebuild — Work Log

## 2026-03-24 — Research & Planning

### Research Completed
- [x] Analyzed current detector: YOLOv8s, 261 imgs, auto-labels, fails on stone
- [x] Explored repos: ultralytics, mmdetection, GroundingDINO, SAM2, supervision
- [x] Read computer-vision-expert skill (YOLO26 NMS-free, SAM3, deployment patterns)
- [x] Researched YOLO26 docs: NMS-free, ProgLoss+STAL small objects, MuSGD, ONNX export
- [x] Researched YOLO11 docs: solid predecessor, NMS required
- [x] Searched Roboflow: found Hieroglyph Dataset (40 imgs, 86 classes, CC BY 4.0)
- [x] Searched HuggingFace:
  - HLA Dataset (897 imgs, Line+Cartouche, museum photos, CVAT annotated)
  - Signs Segmentation (300 imgs, individual sign polygons with orientation)
  - Arasoul/hieroglyph-yolo-dataset (163 downloads, YOLO format)
  - HamdiJr/Egyptian_hieroglyphs (4K+ classification images)
- [x] Inventoried V1 data:
  - 496 raw detection images
  - V1 config: yolov8n/s, 640, 100 epochs, batch 16, 1 class, NO hflip
  - V1 labels: auto-generated (OpenCV), NOT hand-annotated
  - V1 datasets: GlyphNet, GlyphReader, HLA, segmentation_dataset
- [x] Created comprehensive rebuild plan

### Architecture Decision
- **YOLO26s** (single-class detection)
- End-to-end NMS-free output: [1, 300, 6]
- Transfer learning from COCO weights
- Target: **5,000+** properly annotated images from 7+ sources, 10+ museums

### Available Tools (Repos/)
- **Scrapling** — Spider scraping framework with StealthyFetcher, rate limiting, proxy rotation, pause/resume
- **browser-use** — AI browser agent (Playwright + LLM) for JS-heavy museum sites
- **GroundingDINO** — via `transformers` library (CPU-compatible), zero-shot detection for auto-annotation
- **CLIP / open_clip** — Text-image similarity for relevance filtering
- **supervision** — Dataset format conversion (COCO↔YOLO), merging, splitting
- **label-studio** — Web annotation UI for human verification
- **celery** — Distributed task queue for parallel scraping

### Next Steps
- [ ] Phase D1: Set up GroundingDINO (via transformers, already in dataprep-env) for semi-auto annotation of V1 images
- [ ] Phase D2: Download & convert HLA dataset
- [ ] Phase D3: Scrape 10+ museum collections (2,500-3,000 images via Scrapling)
- [ ] Phase D4: Search existing Kaggle/HF datasets
- [ ] Phase D5: Generate 1,000 synthetic composites
- [ ] Phase D6: Download Roboflow dataset
- [ ] Phase D7: CLIP-filtered web images (300-500)
- [ ] Phase D8: Merge all data, split, validate, upload to Kaggle
- [ ] Phase T1: Create training notebook
- [ ] Phase T2: Train on Kaggle
- [ ] Phase I1: Update postprocess.py
- [ ] Phase I2: Deploy & test
