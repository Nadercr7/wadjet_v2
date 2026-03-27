# Landmark Classifier — Training Results

**Kernel**: `nadermohamedcr7/wadjet-landmark-classifier`
**Architecture**: EfficientNet-B0 (timm)
**Training**: PyTorch Lightning, float32, /255 normalization, Kaggle T4 GPU
**Dataset**: 25,710 train images, 52 Egyptian landmark classes

## Results

| Metric | Value |
|--------|-------|
| Top-1 Accuracy | 93.80% |
| Top-3 Accuracy | 97.40% |

## Exported Models
- `landmark_classifier.onnx` — float32, ~15.5 MB
- `landmark_classifier_uint8.onnx` — quantized, ~4.2 MB
