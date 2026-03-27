"""Strip DT_HALF Cast ops from BOTH float16 and float32 TF.js graph models."""
import json, os

def strip_float16_casts(src, dst):
    """Remove Cast nodes and rewire graph to be pure DT_FLOAT."""
    with open(src) as f:
        model = json.load(f)
    
    nodes = model["modelTopology"]["node"]
    total = len(nodes)
    
    # Build skip map: cast_name → input_name (chase transitive)
    cast_nodes = {n["name"]: n for n in nodes if n["op"] == "Cast"}
    skip = {}
    for name, node in cast_nodes.items():
        inp = node["input"][0]
        while inp in cast_nodes:
            inp = cast_nodes[inp]["input"][0]
        skip[name] = inp
    
    # Rewire non-Cast nodes
    rewired = 0
    for node in nodes:
        if node["op"] == "Cast":
            continue
        new_inputs = []
        for inp in node.get("input", []):
            is_ctrl = inp.startswith("^")
            raw = inp[1:] if is_ctrl else inp
            base = raw.split(":")[0]
            if base in skip:
                replacement = ("^" if is_ctrl else "") + skip[base]
                new_inputs.append(replacement)
                rewired += 1
            else:
                new_inputs.append(inp)
        node["input"] = new_inputs
    
    # Remove Cast nodes
    model["modelTopology"]["node"] = [n for n in nodes if n["op"] != "Cast"]
    
    # Fix any remaining DT_HALF attrs
    def fix_dt(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if v == "DT_HALF":
                    obj[k] = "DT_FLOAT"
                else:
                    fix_dt(v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                if v == "DT_HALF":
                    obj[i] = "DT_FLOAT"
                else:
                    fix_dt(v)
    
    for node in model["modelTopology"]["node"]:
        fix_dt(node.get("attr", {}))
    fix_dt(model.get("signature", {}))
    
    remaining = json.dumps(model["modelTopology"]).count("DT_HALF")
    final_nodes = len(model["modelTopology"]["node"])
    
    with open(dst, "w") as f:
        json.dump(model, f)
    
    print(f"  {total} → {final_nodes} nodes, stripped {len(cast_nodes)} Cast, "
          f"rewired {rewired}, DT_HALF remaining: {remaining}")

BASE = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark"

print("Float16 model:")
strip_float16_casts(
    os.path.join(BASE, "tfjs_f16", "model.json"),
    os.path.join(BASE, "tfjs_f16", "model.json"),  # overwrite in-place
)

print("Float32 model:")
strip_float16_casts(
    os.path.join(BASE, "tfjs_f32", "model.json"),
    os.path.join(BASE, "tfjs_f32", "model.json"),  # overwrite in-place
)

print("Done ✓")
