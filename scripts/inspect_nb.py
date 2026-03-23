import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else 'planning/model-rebuild/pytorch/landmark/landmark_classifier.ipynb'
with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

print(f"Total cells: {len(nb['cells'])}")
for i, cell in enumerate(nb['cells']):
    ct = cell['cell_type']
    src = ''.join(cell['source'])[:150].replace('\n', ' | ')
    print(f"  Cell {i}: [{ct}] {src}")
