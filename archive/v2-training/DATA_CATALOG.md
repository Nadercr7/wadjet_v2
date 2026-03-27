# Wadjet v2 — Data Catalog

All training datasets live on Kaggle. They are NOT included in this repository.

## Kaggle Datasets

| Dataset | Kaggle Slug | Size | Classes | Notes |
|---------|-------------|------|---------|-------|
| Hieroglyph Classification | `nadermohamedcr7/wadjet-hieroglyph-classification` | ~1 GB | 171 Gardiner signs | 16,638 train images, min 80/class (67 augmented, no h-flip) |
| Landmark Classification | `nadermohamedcr7/wadjet-landmark-classification` | ~15 GB | 52 Egyptian landmarks | 25,710 train images, min 300/class (merged v1 + eg-landmarks + augmented) |
| Detection v3 (Balanced) | `nadermohamedcr7/wadjet-hieroglyph-detection-v3` | 831 MB | 1 (hieroglyph) | 10,311 images: train 7,655 / val 2,051 / test 605 |
| Stone Textures | `nadermohamedcr7/wadjet-stone-textures` | 61 MB | — | Synthetic stone backgrounds for classifier hardening |

## Kaggle Kernels (Training Notebooks)

| Kernel | Slug | Owner | Result |
|--------|------|-------|--------|
| Hieroglyph Classifier v1 | `nadermohamedcr7/wadjet-hieroglyph-classifier` | nadermohamedcr7 | 98.18% top-1, 99.91% top-5 |
| Hieroglyph Classifier v2 | `naderelakany/wadjet-hieroglyph-classifier-v2` | naderelakany | 97.31% top-1, 55.63% stone-texture |
| Landmark Classifier | `nadermohamedcr7/wadjet-landmark-classifier` | nadermohamedcr7 | 93.80% top-1, 97.40% top-3 |
| Hieroglyph Detector v2 | `nadermohamedcr7/wadjet-hieroglyph-detector` | nadermohamedcr7 | mAP50=0.710, P=0.717, R=0.642 |
| Hieroglyph Detector v3 | `naderelakany/wadjet-hieroglyph-detector-v3` | naderelakany | In progress |

## Data Sources

### Detection Dataset (10,311 images)
- **mohiey**: 8,650 images (84%) — Kaggle dataset, hieroglyph annotations
- **synthetic**: 951 images (9%) — Generated via `create_stone_textures.py` + `generate_synthetic_composites.py`
- **signs_seg**: 289 images (3%) — Segmented sign images
- **v1_raw**: 229 images (2%) — Original v1 auto-labeled images
- **hla**: 192 images (2%) — COCO polygon/bbox → YOLO format
- **Dedup pipeline**: 21,974 raw → 10,654 after pHash dedup → 10,311 after CLIP cleaning

### Scraped (not included in final dataset)
- Met Museum API: 338 images (not annotated — CPU GroundingDINO too slow)
- Wikimedia Commons: 121 images (not annotated)

## How to Re-Download

```bash
pip install kaggle
cp ~/Downloads/kaggle.json ~/.kaggle/
kaggle datasets download nadermohamedcr7/wadjet-hieroglyph-classification -p data/
kaggle datasets download nadermohamedcr7/wadjet-hieroglyph-detection-v3 -p data/
kaggle datasets download nadermohamedcr7/wadjet-landmark-classification -p data/
kaggle datasets download nadermohamedcr7/wadjet-stone-textures -p data/
```

## Model Architecture

| Model | Architecture | Input | Output | Size (uint8) |
|-------|-------------|-------|--------|-------------|
| Hieroglyph Classifier | MobileNetV3-Small | [1,3,128,128] float32 | [1,171] | 1.8 MB |
| Landmark Classifier | EfficientNet-B0 | [1,3,224,224] float32 | [1,52] | 4.2 MB |
| Hieroglyph Detector | YOLO26s (NMS-free) | [1,3,640,640] float32 | [1,300,6] | 9.9 MB |
| TF.js Browser Classifier | MobileNetV3-Small | [1,128,128,3] float32 | [1,171] | ~20 MB |

All models use `/255` normalization only (no ImageNet mean/std).
