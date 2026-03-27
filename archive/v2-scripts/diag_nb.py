"""Diagnose notebook cell structure."""
import json

nb_path = "planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for i, cell in enumerate(nb["cells"][:5]):
    print(f"\n--- Cell {i} ---")
    print(f"  cell_type: {cell.get('cell_type')}")
    print(f"  has 'source': {'source' in cell}")
    print(f"  has 'outputs': {'outputs' in cell}")
    src = cell.get("source", "")
    if isinstance(src, list):
        print(f"  source type: list ({len(src)} items)")
        if src:
            print(f"  source[0]: {src[0][:80]}...")
    elif isinstance(src, str):
        print(f"  source type: str ({len(src)} chars)")
        print(f"  source[:80]: {src[:80]}")
    else:
        print(f"  source type: {type(src)}")
    
    # Check for required fields
    meta = cell.get("metadata", {})
    print(f"  metadata: {meta}")
    eid = cell.get("id", cell.get("execution_count", "N/A"))
    print(f"  id: {cell.get('id', 'MISSING')}")
