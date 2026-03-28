import json
nb = json.load(open('planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb', encoding='utf-8'))
for i, c in enumerate(nb['cells']):
    src = ''.join(c.get('source', []))
    if 'build_model' in src or 'EfficientNetV2' in src or "weights='imagenet'" in src:
        print(f"Cell {i}: (first 200 chars)")
        print(src[:200])
        print("---")
