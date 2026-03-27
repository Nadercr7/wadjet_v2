# Hieroglyph Detector v2 — Training Results

**Kernel**: `nadermohamedcr7/wadjet-hieroglyph-detector`
**Architecture**: YOLO26s, single-class, NMS-free end-to-end
**Training**: 148 effective epochs (resumed from v1 epoch 88), Kaggle T4 GPU
**Dataset**: 10,311 images (7,655 train / 2,051 val / 605 test)

## Results

### Validation Set
| Metric | Value |
|--------|-------|
| mAP50 | 0.710 |
| Precision | 0.717 |
| Recall | 0.642 |

### Test Set
| Metric | Value |
|--------|-------|
| mAP50 | 0.7515 |
| Precision | 0.721 |
| Recall | 0.692 |
| AI Fallback Rate | 2.1% |

## Exported Model
- `glyph_detector_uint8.onnx` — quantized, 9.9 MB
- Output shape: [1,300,6] (NMS-free, up to 300 detections)
- Format per detection: [x_center, y_center, width, height, confidence, class]

## Data Sources
- mohiey: 8,650 images (84%)
- synthetic: 951 images (9%)
- signs_seg: 289 images (3%)
- v1_raw: 229 images (2%)
- hla: 192 images (2%)
