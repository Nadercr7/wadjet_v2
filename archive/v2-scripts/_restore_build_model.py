"""Restore the missing build_model cell in the landmark notebook.
Also check hieroglyph notebook for the same issue."""
import json, uuid

# ── Fix Landmark ──
land_path = 'planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb'
nb = json.load(open(land_path, encoding='utf-8'))

# Check if build_model exists
has_build = any('def build_model' in ''.join(c.get('source', [])) for c in nb['cells'])
print(f"Landmark build_model present: {has_build}")

if not has_build:
    # Get the build_model cell from the original notebook
    orig = json.load(open('planning/model-rebuild/notebooks/landmark_classifier.ipynb', encoding='utf-8'))
    build_cell = orig['cells'][12].copy()
    build_cell['id'] = str(uuid.uuid4())[:8]
    
    # Modify to use USE_PRETRAINED
    new_source = []
    for line in build_cell['source']:
        if 'weights="imagenet"' in line:
            line = line.replace('weights="imagenet"', 'weights="imagenet" if USE_PRETRAINED else None')
        new_source.append(line)
    build_cell['source'] = new_source
    
    # Insert before the Phase 1 cell
    # Find Phase 1 cell index
    phase1_idx = None
    for i, c in enumerate(nb['cells']):
        if 'Phase 1' in ''.join(c.get('source', [])) and 'Head Training' in ''.join(c.get('source', [])):
            phase1_idx = i
            break
    
    if phase1_idx:
        nb['cells'].insert(phase1_idx, build_cell)
        print(f"  Inserted build_model cell at index {phase1_idx}")
    else:
        print("  ERROR: Could not find Phase 1 cell!")
    
    with open(land_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("  ✅ Landmark notebook saved")

# ── Check Hieroglyph ──
hiero_path = 'planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb'
nb2 = json.load(open(hiero_path, encoding='utf-8'))
has_build2 = any('MobileNetV3' in ''.join(c.get('source', [])) for c in nb2['cells'])
print(f"\nHieroglyph MobileNetV3 cell present: {has_build2}")
if not has_build2:
    # Check original
    orig2 = json.load(open('planning/model-rebuild/notebooks/hieroglyph_classifier.ipynb', encoding='utf-8'))
    for i, c in enumerate(orig2['cells']):
        if 'MobileNetV3' in ''.join(c.get('source', [])):
            print(f"  Found in original Cell {i}")
            break
    
    # Find where it should go in the modified notebook
    for i, c in enumerate(nb2['cells']):
        src = ''.join(c.get('source', []))
        if 'Phase 1' in src and 'Head Training' in src:
            print(f"  Phase 1 is at index {i}")
            # Insert the original model cell before Phase 1
            model_cell = orig2['cells'][10].copy()  # Model Architecture cell
            model_cell['id'] = str(uuid.uuid4())[:8]
            nb2['cells'].insert(i, model_cell)
            print(f"  Inserted MobileNetV3 cell at index {i}")
            
            with open(hiero_path, 'w', encoding='utf-8') as f:
                json.dump(nb2, f, indent=1, ensure_ascii=False)
            print("  ✅ Hieroglyph notebook saved")
            break

# Print final structure
print("\n=== Final Structure ===")
for name, path in [
    ("HIEROGLYPH", hiero_path),
    ("LANDMARK", land_path),
]:
    nb = json.load(open(path, encoding='utf-8'))
    print(f"\n{name} ({len(nb['cells'])} cells):")
    for i, c in enumerate(nb['cells']):
        src = ''.join(c.get('source', []))
        title = ""
        for ln in src.split('\n'):
            ln = ln.strip()
            if ln and not ln.startswith('# ==='):
                title = ln[:80]
                break
        print(f"  Cell {i:2d}: {title}")
