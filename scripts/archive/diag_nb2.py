"""Diagnose what's wrong with our notebooks vs the working test format."""
import json

# Load our notebook
with open("planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb", "r", encoding="utf-8") as f:
    ours = json.load(f)

print("=== OUR NOTEBOOK ===")
print(f"nbformat: {ours['nbformat']}")
print(f"nbformat_minor: {ours['nbformat_minor']}")
print(f"metadata keys: {list(ours['metadata'].keys())}")
print(f"kernelspec: {ours['metadata'].get('kernelspec')}")
print(f"Num cells: {len(ours['cells'])}")

# Check all cells
for i, cell in enumerate(ours["cells"]):
    keys = sorted(cell.keys())
    ct = cell.get("cell_type")
    has_id = "id" in cell
    has_exec = "execution_count" in cell
    has_outputs = "outputs" in cell
    src = cell.get("source", "")
    src_type = type(src).__name__
    src_len = len(src) if isinstance(src, str) else sum(len(s) for s in src)
    
    # Check source format
    issue = ""
    if isinstance(src, list) and len(src) > 0:
        # Check if source lines end with \n except the last one
        for j, line in enumerate(src[:-1]):
            if not line.endswith("\n"):
                issue = f"source[{j}] missing trailing newline"
                break
    
    print(f"  Cell {i}: type={ct}, keys={keys}, src_type={src_type}, src_chars={src_len}, has_id={has_id}, has_exec={has_exec}, has_outputs={has_outputs} {issue}")

# Try to reproduce the exact format Kaggle expects
# Kaggle API joins source lists into strings
print("\n=== SIMULATING KAGGLE PROCESSING ===")
test_body = json.loads(json.dumps(ours))
for cell in test_body["cells"]:
    if "outputs" in cell and cell["cell_type"] == "code":
        cell["outputs"] = []
    if "source" in cell and isinstance(cell["source"], list):
        cell["source"] = "".join(cell["source"])

# Check if the result is valid
for i, cell in enumerate(test_body["cells"][:3]):
    src = cell["source"]
    print(f"  Cell {i}: source type={type(src).__name__}, len={len(src)}, starts_with={repr(src[:50])}")

# Size check
full_json = json.dumps(test_body)
print(f"\nFull notebook JSON size: {len(full_json)} bytes ({len(full_json)/1024:.0f} KB)")
