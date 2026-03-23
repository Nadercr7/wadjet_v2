"""Check classifier model input/output signature."""
import json

with open("models/hieroglyph/classifier/model.json", encoding="utf-8") as f:
    d = json.load(f)

sig = d.get("signature", {})
inputs = sig.get("inputs", {})
outputs = sig.get("outputs", {})
for name, info in inputs.items():
    print(f"Input: {name}")
    print(f"  dtype: {info.get('dtype')}")
    print(f"  tensorShape: {info.get('tensorShape')}")
for name, info in outputs.items():
    print(f"Output: {name}")
    print(f"  dtype: {info.get('dtype')}")
    print(f"  tensorShape: {info.get('tensorShape')}")

# Check input nodes
nodes = d["modelTopology"]["node"]
for n in nodes:
    if n["op"] == "Placeholder":
        print(f"Placeholder: {n['name']}")
        attrs = n.get("attr", {})
        if "shape" in attrs:
            print(f"  shape: {attrs['shape']}")
        if "dtype" in attrs:
            print(f"  dtype: {attrs['dtype']}")

# Check what ops have 'T' attr with specific dtypes
from collections import Counter
type_attrs = []
for n in nodes:
    attrs = n.get("attr", {})
    for key, val in attrs.items():
        if key == "T" or key == "DstT" or key == "SrcT":
            type_attrs.append(f"{key}={val.get('type','?')}")
print()
dtype_counts = Counter(type_attrs)
for dt, cnt in dtype_counts.most_common():
    print(f"  {dt}: {cnt}")
