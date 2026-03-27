import json, sys

path = 'planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb'
with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

checks = {
    'pytorch_lightning (not lightning)': False,
    'onnxscript pip install': False,
    'onnxruntime pip install': False,
    'precision="32-true"': False,
    'P1_EPOCHS = 8': False,
    'P2_EPOCHS = 40': False,
    'KeepAliveCallback': False,
    'enable_progress_bar=False': False,
    'dynamo=False': False,
    'opset_version=18': False,
    'labels=list(range': False,
    'class_to_idx remap': False,
    'DATA_ROOT auto-discover': False,
}

for cell in nb['cells']:
    src = ''.join(cell['source'])
    if 'pytorch_lightning' in src:
        checks['pytorch_lightning (not lightning)'] = True
    if 'onnxscript' in src:
        checks['onnxscript pip install'] = True
    if 'onnxruntime' in src and 'pip install' in src:
        checks['onnxruntime pip install'] = True
    if 'precision="32-true"' in src:
        checks['precision="32-true"'] = True
    if 'P1_EPOCHS = 8' in src:
        checks['P1_EPOCHS = 8'] = True
    if 'P2_EPOCHS = 40' in src:
        checks['P2_EPOCHS = 40'] = True
    if 'KeepAliveCallback' in src:
        checks['KeepAliveCallback'] = True
    if 'enable_progress_bar=False' in src:
        checks['enable_progress_bar=False'] = True
    if 'dynamo=False' in src:
        checks['dynamo=False'] = True
    if 'opset_version=18' in src:
        checks['opset_version=18'] = True
    if 'labels=list(range' in src:
        checks['labels=list(range'] = True
    if 'class_to_idx' in src and 'remap' in src.lower():
        checks['class_to_idx remap'] = True
    if 'os.walk' in src and 'train' in src:
        checks['DATA_ROOT auto-discover'] = True

print("=== CRITICAL FIX VERIFICATION ===")
all_pass = True
for check, passed in checks.items():
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    print(f"  [{status}] {check}")

print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
