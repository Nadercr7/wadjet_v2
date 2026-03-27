import json

# Read original landmark notebook
orig = json.load(open('planning/model-rebuild/notebooks/landmark_classifier.ipynb', encoding='utf-8'))
orig_build_cell = orig['cells'][12]
src = ''.join(orig_build_cell.get('source', []))
print("=== Original build_model cell (Cell 12) ===")
print(src)
print(f"\n--- Length: {len(src)} chars ---")
