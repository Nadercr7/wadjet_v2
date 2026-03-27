"""Read key cells from both notebooks: TFRecord parsing, model, evaluation, dataset build."""
import json

for name, path in [
    ("HIEROGLYPH", "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"),
    ("LANDMARK", "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb"),
]:
    nb = json.load(open(path, encoding='utf-8'))
    print(f"\n{'='*80}")
    print(f"  {name}")
    print('='*80)
    
    for i, c in enumerate(nb['cells']):
        src = ''.join(c.get('source', []))
        # Show specific cells
        keywords = ['TFRecord Parsing', 'Dataset Statistics', 'Build Dataset', 
                     'Evaluation', 'Model Architecture', 'Data Augment']
        title_line = next((l for l in src.split('\n') if l.strip().startswith('# ') and '===' not in l), '')
        if any(k.lower() in title_line.lower() for k in keywords):
            print(f"\n{'─'*60}")
            print(f"Cell {i}: {title_line.strip()}")
            print('─'*60)
            print(src[:3000])
            if len(src) > 3000:
                print(f"\n... ({len(src)-3000} more chars)")
