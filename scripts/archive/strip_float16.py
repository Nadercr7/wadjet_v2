"""Strip all DT_HALF (float16) Cast operations from the TF.js graph model.

The model was trained with mixed_float16, so the graph contains Cast ops:
  float32 → DT_HALF (before compute-heavy ops like Conv2D)
  DT_HALF → float32 (after compute, before BN/Add)

TF.js WebGL doesn't support float16 for many kernels (Mul, etc.).
This script rewires the graph to skip all Cast nodes and ensures every
op runs in DT_FLOAT.
"""
import json, copy, sys

SRC = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs_new\model.json"
DST = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs_new\model_f32.json"

print("Loading model.json …")
with open(SRC) as f:
    model = json.load(f)

nodes = model["modelTopology"]["node"]
print(f"  Total nodes: {len(nodes)}")

# ── 1. Identify all Cast nodes ──────────────────────────────────────
cast_nodes = {n["name"]: n for n in nodes if n["op"] == "Cast"}
print(f"  Cast nodes: {len(cast_nodes)}")

# ── 2. Build skip-map: cast_output_name → its_input_name ────────────
# Each Cast node has exactly one input.  We want to "short-circuit" it
# so any downstream node that reads from the Cast reads from the
# Cast's input instead.
skip = {}
for name, node in cast_nodes.items():
    inp = node["input"][0]
    # Chase transitive casts  (Cast → Cast → … → real op)
    while inp in cast_nodes:
        inp = cast_nodes[inp]["input"][0]
    skip[name] = inp

print(f"  Skip mappings built: {len(skip)}")

# ── 3. Rewire every non-Cast node's inputs ──────────────────────────
rewired = 0
for node in nodes:
    if node["op"] == "Cast":
        continue
    new_inputs = []
    for inp in node.get("input", []):
        # Handle control-dependency syntax  "^node_name"
        is_ctrl = inp.startswith("^")
        raw = inp[1:] if is_ctrl else inp
        # Node references may include ":N" output index
        parts = raw.split(":")
        base = parts[0]
        suffix = ":" + parts[1] if len(parts) > 1 else ""
        if base in skip:
            # The Cast we're skipping was an identity-like op with one output,
            # so its output index should map to the original tensor.
            replacement = skip[base]
            if is_ctrl:
                replacement = "^" + replacement
            # Keep the original suffix only if the replacement doesn't have one
            # and the skipped Cast's input didn't have one (most cases).
            new_inputs.append(replacement)
            rewired += 1
        else:
            new_inputs.append(inp)
    node["input"] = new_inputs

print(f"  Rewired {rewired} input references")

# ── 4. Remove Cast nodes ────────────────────────────────────────────
model["modelTopology"]["node"] = [n for n in nodes if n["op"] != "Cast"]
print(f"  Nodes after removal: {len(model['modelTopology']['node'])}")

# ── 5. Change any remaining DT_HALF type attrs to DT_FLOAT ──────────
def fix_dtypes(obj):
    """Recursively replace DT_HALF with DT_FLOAT in attr dicts."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if v == "DT_HALF":
                obj[k] = "DT_FLOAT"
            else:
                fix_dtypes(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if v == "DT_HALF":
                obj[i] = "DT_FLOAT"
            else:
                fix_dtypes(v)

for node in model["modelTopology"]["node"]:
    fix_dtypes(node.get("attr", {}))

# Also fix signature dtypes
fix_dtypes(model.get("signature", {}))

# ── 6. Quick sanity check ───────────────────────────────────────────
text = json.dumps(model["modelTopology"])
remaining_half = text.count("DT_HALF")
print(f"  Remaining DT_HALF references: {remaining_half}")
if remaining_half:
    print("  WARNING: some DT_HALF refs remain!")

# ── 7. Save ─────────────────────────────────────────────────────────
with open(DST, "w") as f:
    json.dump(model, f)
print(f"\n  Saved → {DST}  ({len(open(DST).read()) / 1024:.0f} KB)")
print("  Done ✓")
