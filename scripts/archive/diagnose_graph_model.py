"""Validate graph connectivity and diagnose Multiply op issues."""
import json
from collections import Counter

MODEL = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json"

d = json.load(open(MODEL))
nodes = d["modelTopology"]["node"]
node_map = {n["name"]: n for n in nodes}
node_names = set(node_map.keys())

# 1. Check for dangling references
print("=== Graph Connectivity ===")
missing = []
for n in nodes:
    for inp in n.get("input", []):
        raw = inp.lstrip("^").split(":")[0]
        if raw not in node_names:
            missing.append((n["name"], n["op"], raw))
print(f"Total nodes: {len(nodes)}")
print(f"Missing input refs: {len(missing)}")
for m in missing[:20]:
    print(f"  {m[1]} '{m[0]}' → missing '{m[2]}'")

# 2. Look at Mul nodes and their input chains
print("\n=== Mul Op Analysis ===")
mul_nodes = [n for n in nodes if n["op"] == "Mul"]
print(f"Mul nodes: {len(mul_nodes)}")

def trace_input(name, depth=0, max_depth=4):
    """Trace input chain for a node."""
    if depth > max_depth or name not in node_map:
        return f"{'  '*depth}[{name} - NOT FOUND]" if name not in node_map else ""
    n = node_map[name]
    lines = [f"{'  '*depth}{n['op']} '{name}'"]
    if n.get("attr"):
        # Show dtype if present
        for k in ["T", "dtype", "DstT", "SrcT"]:
            if k in n["attr"]:
                lines[-1] += f"  {k}={n['attr'][k]}"
    if depth < max_depth:
        for inp in n.get("input", [])[:2]:
            raw = inp.lstrip("^").split(":")[0]
            sub = trace_input(raw, depth+1, max_depth)
            if sub:
                lines.append(sub)
    return "\n".join(lines)

# Show first 3 Mul nodes with their input chains
for m in mul_nodes[:3]:
    print(f"\n--- {m['name']} ---")
    print(trace_input(m["name"], max_depth=3))

# 3. Check weight manifest
print("\n=== Weight Manifest ===")
wm = d.get("weightsManifest", [])
total_weights = sum(len(g.get("weights", [])) for g in wm)
print(f"Weight groups: {len(wm)}")
print(f"Total weight entries: {total_weights}")

# Check dtypes in weight manifest
weight_dtypes = Counter(w.get("dtype") for g in wm for w in g.get("weights", []))
print(f"Weight dtypes: {dict(weight_dtypes)}")

# Check quantization info
quant_types = Counter(
    w.get("quantization", {}).get("dtype", "none")
    for g in wm for w in g.get("weights", [])
)
print(f"Quantization dtypes: {dict(quant_types)}")

# 4. Check if any remaining DT_HALF
text = json.dumps(d)
print(f"\nDT_HALF in entire model.json: {text.count('DT_HALF')}")
print(f"float16 in entire model.json: {text.count('float16')}")

# 5. Check op types
ops = Counter(n["op"] for n in nodes)
print(f"\n=== All Op Types ===")
for op, count in ops.most_common():
    print(f"  {op}: {count}")
