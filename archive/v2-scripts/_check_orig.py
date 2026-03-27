import json

# Check the ORIGINAL landmark notebook (not the one in the subfolder)
nb = json.load(open('planning/model-rebuild/notebooks/landmark_classifier.ipynb', encoding='utf-8'))
print(f"ORIGINAL notebook: {len(nb['cells'])} cells")
for i, c in enumerate(nb['cells']):
    src = ''.join(c.get('source', []))
    title = ""
    for ln in src.split('\n'):
        ln = ln.strip()
        if ln and not ln.startswith('# ==='):
            title = ln[:80]
            break
    print(f"  Cell {i:2d}: {title}")
    if 'build_model' in src or ('backbone' in src and 'def ' in src):
        print(f"         *** CONTAINS build_model ***")
