import json

# === HIEROGLYPH NOTEBOOK ===
print("=== HIEROGLYPH NOTEBOOK ===")
with open('planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
all_code = []
for c in nb['cells']:
    if c['cell_type'] == 'code':
        all_code.extend(c['source'])
code = '\n'.join(all_code)

checks = {
    'INPUT_SIZE=128': 'INPUT_SIZE = 128' in code,
    'NUM_CLASSES=171': 'NUM_CLASSES = 171' in code,
    'mobilenetv3_small_100': 'mobilenetv3_small_100' in code,
    'FocalLoss': 'class FocalLoss' in code,
    'NO h-flip (no HorizontalFlip)': 'HorizontalFlip' not in code,
    'P1_EPOCHS=5': 'P1_EPOCHS = 5' in code,
    'P2_EPOCHS=30': 'P2_EPOCHS = 30' in code,
    'P1_LR=1e-3': 'P1_LR = 1e-3' in code,
    'P2_LR=1e-4': 'P2_LR = 1e-4' in code,
    'opset_version=17': 'opset_version=17' in code,
    'NCHW input': '1, 3, INPUT_SIZE, INPUT_SIZE' in code,
    'quantize_dynamic': 'quantize_dynamic' in code,
    'label_mapping.json': 'label_mapping.json' in code,
    'model_metadata.json': 'model_metadata.json' in code,
    'class_weights sqrt-inv': 'math.sqrt(total / (NUM_CLASSES * count))' in code,
    'EarlyStopping': 'EarlyStopping' in code,
    'ImageFolder': 'ImageFolder' in code,
    'albumentations': 'albumentations' in code,
    'lightning': 'lightning' in code,
    'Kaggle paths /kaggle/input': '/kaggle/input/wadjet-hieroglyph-classification' in code,
    'Output to /kaggle/working': '/kaggle/working' in code,
}
for k, v in checks.items():
    status = 'PASS' if v else 'FAIL'
    print(f"  [{status}] {k}")

# === LANDMARK NOTEBOOK ===
print("\n=== LANDMARK NOTEBOOK ===")
with open('planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
all_code = []
for c in nb['cells']:
    if c['cell_type'] == 'code':
        all_code.extend(c['source'])
code = '\n'.join(all_code)

checks2 = {
    'INPUT_SIZE=224': 'INPUT_SIZE = 224' in code,
    'NUM_CLASSES=52': 'NUM_CLASSES = 52' in code,
    'efficientnet_b0': 'efficientnet_b0' in code,
    'HorizontalFlip ALLOWED': 'HorizontalFlip' in code,
    'P1_EPOCHS=5': 'P1_EPOCHS = 5' in code,
    'P2_EPOCHS=30': 'P2_EPOCHS = 30' in code,
    'P1_LR=1e-3': 'P1_LR = 1e-3' in code,
    'P2_LR=5e-5': 'P2_LR = 5e-5' in code,
    'opset_version=17': 'opset_version=17' in code,
    'NCHW input': '1, 3, INPUT_SIZE, INPUT_SIZE' in code,
    'quantize_dynamic': 'quantize_dynamic' in code,
    'landmark_label_mapping.json': 'landmark_label_mapping.json' in code,
    'model_metadata.json': 'model_metadata.json' in code,
    'CrossEntropyLoss': 'CrossEntropyLoss' in code,
    'LABEL_SMOOTHING=0.1': 'LABEL_SMOOTHING = 0.1' in code,
    'class_weights sqrt-inv': 'math.sqrt(total / (NUM_CLASSES * count))' in code,
    'EarlyStopping': 'EarlyStopping' in code,
    'ImageFolder': 'ImageFolder' in code,
    'albumentations': 'albumentations' in code,
    'lightning': 'lightning' in code,
    'RandomShadow (real photos)': 'RandomShadow' in code,
    'unfreeze_top 50%': 'fraction=0.5' in code,
    'Kaggle paths /kaggle/input': '/kaggle/input/wadjet-landmark-classification' in code,
    'Output to /kaggle/working': '/kaggle/working' in code,
    'top3 accuracy': 'top_k_accuracy_score' in code and 'k=3' in code,
}
for k, v in checks2.items():
    status = 'PASS' if v else 'FAIL'
    print(f"  [{status}] {k}")

# === KERNEL METADATA ===
print("\n=== KERNEL METADATA ===")
for name, path in [('hieroglyph', 'planning/model-rebuild/pytorch/hieroglyph/kernel-metadata.json'),
                    ('landmark', 'planning/model-rebuild/pytorch/landmark/kernel-metadata.json')]:
    with open(path, encoding='utf-8') as f:
        meta = json.load(f)
    checks_meta = {
        'enable_gpu': meta.get('enable_gpu') == True,
        'is_private': meta.get('is_private') == True,
        'enable_internet=false': meta.get('enable_internet') == False,
        'code_file matches .ipynb': meta.get('code_file', '').endswith('.ipynb'),
        'has dataset_sources': len(meta.get('dataset_sources', [])) > 0,
    }
    print(f"  --- {name} ---")
    for k, v in checks_meta.items():
        status = 'PASS' if v else 'FAIL'
        print(f"    [{status}] {k}")
