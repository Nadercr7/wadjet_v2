import json
nb = json.load(open('planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb', encoding='utf-8'))
# Show full Cell 14 (Phase 1) to see if model is defined there
c = nb['cells'][14]
src = ''.join(c.get('source', []))
print(f"=== Cell 14 ({len(src)} chars) ===")
print(src)
