"""Analyze V1's proven working model."""
import json, os, glob

# Find V1 model
candidates = [
    r"D:\Personal attachements\Projects\Final_Horus\Wadjet\model\tfjs\model.json",
    r"D:\Personal attachements\Projects\Final_Horus\Wadjet\models\landmark\tfjs\model.json",
]
path = None
for c in candidates:
    if os.path.exists(c):
        path = c
        break

if not path:
    found = glob.glob(r"D:\Personal attachements\Projects\Final_Horus\Wadjet\**\model.json", recursive=True)
    print("All model.json files in V1:")
    for f in found:
        print(f"  {f} ({os.path.getsize(f)//1024} KB)")
    exit(1)

d = json.load(open(path))
txt = json.dumps(d)

print(f"Path: {path}")
print(f"format: {d.get('format')}")
print(f"generatedBy: {d.get('generatedBy')}")

checks = [
    ("batch_shape (K3)", '"batch_shape"'),
    ("batch_input_shape (K2)", '"batch_input_shape"'),
    ("__keras_tensor__", "__keras_tensor__"),
    ("DTypePolicy", "DTypePolicy"),
]
for label, needle in checks:
    print(f"  {label}: {txt.count(needle)}")

topo = d.get("modelTopology", {})
mc = topo.get("model_config", {})
layers = mc.get("config", {}).get("layers", [])
print(f"\n  Top-level layers: {len(layers)}")

nested = [l for l in layers if l.get("class_name") == "Functional"]
print(f"  Nested Functional: {len(nested)}")
if nested:
    for n in nested:
        inner = n.get("config", {}).get("layers", [])
        print(f"    -> {n.get('name', '?')}: {len(inner)} layers")
