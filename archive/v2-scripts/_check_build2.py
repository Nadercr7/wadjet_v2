import json
nb = json.load(open('planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb', encoding='utf-8'))
# The pre-download cell is 13, so build_model should be around cell 13-14 area
# But the original was cell 12 before we inserted. Let's check all cells
for i in [12, 13, 14]:
    c = nb['cells'][i]
    src = ''.join(c.get('source', []))
    print(f"\n=== Cell {i} ({len(src)} chars) ===")
    print(src[:400])
