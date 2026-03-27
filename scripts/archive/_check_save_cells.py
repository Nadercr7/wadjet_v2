"""Show the ONNX export and save/output cells for both notebooks."""
import json

for name, path in [
    ("HIEROGLYPH", "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"),
    ("LANDMARK", "planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb"),
]:
    nb = json.load(open(path, encoding='utf-8'))
    print(f"\n{'='*60}")
    print(f"{name} ({len(nb['cells'])} cells)")
    print('='*60)
    for i, c in enumerate(nb['cells']):
        src = ''.join(c.get('source', []))
        # Show ONNX export, quantization, validate, save, download cells
        if any(k in src.lower() for k in ['onnx export', 'quantization', 'validate onnx', 'save model', 'save outputs', 'download']):
            title = src.split('\n')[1].strip() if len(src.split('\n')) > 1 else ""
            print(f"\n--- Cell {i}: {title} ---")
            print(src[:2000])
            if len(src) > 2000:
                print("... (truncated)")
