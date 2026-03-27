"""Show the build_model cell and Pre-load backbone cell in the modified landmark notebook."""
import json

nb = json.load(open('planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb', encoding='utf-8'))

# Cell 13 - Pre-load backbone
print("=== Cell 13: Pre-load backbone ===")
print(''.join(nb['cells'][13]['source']))

print("\n\n=== Cell 14: Model Architecture ===")
print(''.join(nb['cells'][14]['source']))

print("\n\n=== Cell 15: Phase 1 Training (first 30 lines) ===")
src = ''.join(nb['cells'][15]['source'])
for i, line in enumerate(src.split('\n')[:30]):
    print(f"  {i:3d}: {line}")
