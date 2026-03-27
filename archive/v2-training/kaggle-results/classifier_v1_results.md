# Hieroglyph Classifier v1 — Training Results

**Kernel**: `nadermohamedcr7/wadjet-hieroglyph-classifier`
**Architecture**: MobileNetV3-Small (timm)
**Training**: PyTorch Lightning, float32, /255 normalization, Kaggle T4 GPU
**Dataset**: 16,638 train images, 171 Gardiner sign classes

## Results

| Metric | Value |
|--------|-------|
| Top-1 Accuracy | 98.18% |
| Top-5 Accuracy | 99.91% |

## Exported Models
- `hieroglyph_classifier.onnx` — float32, ~6.5 MB
- `hieroglyph_classifier_uint8.onnx` — quantized, ~1.8 MB
- `model.json` + shards — TF.js browser model, ~20 MB
