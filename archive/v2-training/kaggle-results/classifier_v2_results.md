# Hieroglyph Classifier v2 — Training Results

**Kernel**: `naderelakany/wadjet-hieroglyph-classifier-v2`
**Architecture**: MobileNetV3-Small (timm), with stone-texture augmentation
**Training**: PyTorch Lightning, float32, /255 normalization, Kaggle T4 GPU
**Dataset**: 16,638 train images + stone texture augmentation, 171 Gardiner sign classes

## Results

| Metric | Value |
|--------|-------|
| Top-1 Accuracy | 97.31% |
| Top-5 Accuracy | 99.91% |
| Stone-Texture Accuracy | 55.63% |

## Notes
- Slight drop in top-1 vs v1 (97.31% vs 98.18%) due to stone-texture training
- Stone-texture accuracy target was 50% — achieved 55.63%
- Exported to `hieroglyph_classifier_uint8_v2.onnx`
