"""Quick check: hieroglyph TFRecord parsing cell uses split_prefix for flat layout,
and landmark uses subdirectories."""
import json

for name, path in [
    ("HIEROGLYPH", "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"),
    ("LANDMARK", "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb"),
]:
    nb = json.load(open(path, encoding='utf-8'))
    # Find cells with "glob" or "tfrecord" pattern
    for i, c in enumerate(nb['cells']):
        src = ''.join(c.get('source', []))
        if 'tf.data.TFRecordDataset' in src or 'glob.glob' in src or 'load_dataset' in src:
            title = [l for l in src.split('\n') if l.strip().startswith('#') and '===' not in l]
            title = title[0] if title else f"Cell {i}"
            print(f"\n{name} Cell {i}: {title.strip()}")
            # Show relevant lines
            for ln in src.split('\n'):
                if any(k in ln for k in ['glob', 'TFRecord', 'split', 'TRAIN_DIR', 'VAL_DIR', 'TEST_DIR', 'DATA_DIR']):
                    print(f"  {ln.rstrip()}")
