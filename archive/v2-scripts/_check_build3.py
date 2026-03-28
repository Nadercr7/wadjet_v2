import json
nb = json.load(open('planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb', encoding='utf-8'))
# Search ALL cells for model definition
for i, c in enumerate(nb['cells']):
    src = ''.join(c.get('source', []))
    if 'def build_model' in src or 'backbone' in src.lower() or 'model.compile' in src:
        print(f"Cell {i}: {src.split(chr(10))[0][:80]}")
        # Show lines with backbone/model mentions
        for j, line in enumerate(src.split('\n')):
            if 'backbone' in line.lower() or 'build_model' in line or 'model.compile' in line or 'EfficientNet' in line:
                print(f"  L{j}: {line.strip()[:100]}")
        print()
