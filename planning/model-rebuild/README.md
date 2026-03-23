# Model Rebuild — PyTorch + Kaggle GPU Edition

> **Strategy**: Train on Kaggle GPU (T4/P100) using PyTorch + timm.
> `torch.onnx.export()` is built-in — no tf2onnx needed. Works perfectly.

## Active Notebooks (write locally → push to Kaggle)

```
pytorch/
  hieroglyph/
    kernel-metadata.json   ← Kaggle kernel config (dataset: wadjet-hieroglyph-classification)
    hieroglyph_classifier.ipynb  ← Phase B: create + push to Kaggle
  landmark/
    kernel-metadata.json   ← Kaggle kernel config (datasets: wadjet-landmark-classification + eg-landmarks-extra)
    landmark_classifier.ipynb    ← Phase B2: create + push to Kaggle
```

## Archive (old TFRecord / Keras approach — DO NOT USE)

```
notebooks/
  hieroglyph_classifier.ipynb   ← OLD: TFRecord parsing + Keras EfficientNetV2 — OBSOLETE
  landmark_classifier.ipynb     ← OLD: TFRecord parsing + Keras EfficientNetV2 — OBSOLETE
kaggle-archive/                 ← Old Kaggle TF/Keras configs — OBSOLETE
```

## Dataset Metadata (Kaggle upload — metadata files ready ✅)

```
data/hieroglyph_classification/dataset-metadata.json  ← wadjet-hieroglyph-classification
data/downloads/eg-landmarks/dataset-metadata.json     ← eg-landmarks-extra
D:\...\Wadjet\data\splits\dataset-metadata.json       ← wadjet-landmark-classification
```

## Plan
See `planning/rebuild/MASTER_PLAN.md` for full rebuild strategy.
See `planning/rebuild/REBUILD_TASKS.md` for phase-by-phase tasks.
See `planning/rebuild/START_PROMPTS.md` for ready-to-paste session prompts.
