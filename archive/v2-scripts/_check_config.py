"""Show config and auto-detect cells for both notebooks."""
import json

for name, path in [
    ("HIEROGLYPH", "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"),
    ("LANDMARK", "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb"),
]:
    nb = json.load(open(path, encoding='utf-8'))
    print(f"\n{'='*60}")
    print(f"{name}")
    print('='*60)
    
    # Cell 1 - Auto-detect
    print("\n--- Cell 1: Auto-Detect ---")
    print(''.join(nb['cells'][1]['source']))
    
    # Cell 2 - Config
    print("\n--- Cell 2: Configuration ---")
    print(''.join(nb['cells'][2]['source']))
