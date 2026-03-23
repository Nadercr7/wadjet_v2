"""Convert V1's Keras 3 layers-model JSON to Keras 2 format on disk.

Fixes ALL Keras 3 artifacts that TF.js 4.22 loadLayersModel cannot handle:
1. batch_shape → batch_input_shape
2. inbound_nodes {args, kwargs} → [[name, idx, tidx, {}]]
3. DTypePolicy dtype objects → string
4. silu → swish
5. Strip module/registered_name wrapper objects
"""
import json, copy, sys

SRC = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json"

with open(SRC) as f:
    model = json.load(f)

stats = {"batch_shape": 0, "inbound_nodes": 0, "dtype_policy": 0,
         "silu": 0, "module_strip": 0}


def fix_layer(layer):
    """Recursively fix a single layer config."""
    cfg = layer.get("config", {})

    # 1. batch_shape → batch_input_shape
    if "batch_shape" in cfg and "batch_input_shape" not in cfg:
        cfg["batch_input_shape"] = cfg.pop("batch_shape")
        stats["batch_shape"] += 1

    # 2. Fix inbound_nodes: Keras 3 {args, kwargs} → Keras 2 [[name, idx, tidx, {}]]
    if "inbound_nodes" in layer:
        new_nodes = []
        for node in layer["inbound_nodes"]:
            if isinstance(node, dict) and "args" in node:
                # Keras 3 format
                connections = []
                args = node["args"]
                # args can be a single tensor or a list of tensors
                if not isinstance(args, list):
                    args = [args]
                for arg in args:
                    if isinstance(arg, dict) and arg.get("class_name") == "__keras_tensor__":
                        h = arg["config"]["keras_history"]
                        connections.append([h[0], h[1], h[2], {}])
                    elif isinstance(arg, list):
                        # List of tensors (e.g., for Add/Multiply layers)
                        for t in arg:
                            if isinstance(t, dict) and t.get("class_name") == "__keras_tensor__":
                                h = t["config"]["keras_history"]
                                connections.append([h[0], h[1], h[2], {}])
                if connections:
                    new_nodes.append(connections)
                    stats["inbound_nodes"] += 1
                else:
                    new_nodes.append(node)  # keep as-is if no tensors found
            elif isinstance(node, list):
                new_nodes.append(node)  # already Keras 2 format
            else:
                new_nodes.append(node)
        layer["inbound_nodes"] = new_nodes

    # 3. Fix DTypePolicy dtype objects → string
    if isinstance(cfg.get("dtype"), dict):
        dp = cfg["dtype"]
        if dp.get("class_name") == "DTypePolicy":
            name = dp.get("config", {}).get("name", "float32")
            cfg["dtype"] = "float32" if "float16" in name else name
        else:
            cfg["dtype"] = dp.get("config", {}).get("name", "float32")
        stats["dtype_policy"] += 1

    # 4. silu → swish
    if cfg.get("activation") == "silu":
        cfg["activation"] = "swish"
        stats["silu"] += 1

    # 5. Strip module/registered_name wrapper objects in config values
    for key in list(cfg.keys()):
        val = cfg[key]
        if isinstance(val, dict) and "module" in val and "class_name" in val:
            cfg[key] = {"class_name": val["class_name"],
                        "config": val.get("config", {})}
            stats["module_strip"] += 1

    # Recurse into nested layers (e.g., Functional model inside)
    if "layers" in cfg:
        for sub in cfg["layers"]:
            fix_layer(sub)


# Fix all layers at every level
topo = model["modelTopology"]
mc = topo.get("model_config", {})
layers = mc.get("config", {}).get("layers", [])
print(f"Fixing {len(layers)} top-level layers...")
for layer in layers:
    fix_layer(layer)
    # Also recurse into nested Functional models
    nested_layers = layer.get("config", {}).get("layers", [])
    for nl in nested_layers:
        fix_layer(nl)

# Write back
with open(SRC, "w") as f:
    json.dump(model, f)

print(f"\nFixed on disk: {SRC}")
for k, v in stats.items():
    print(f"  {k}: {v}")
print(f"  File size: {len(json.dumps(model)) // 1024} KB")

# Verify no remaining issues
text = json.dumps(model)
remaining = {
    "__keras_tensor__": text.count("__keras_tensor__"),
    "DTypePolicy": text.count("DTypePolicy"),
    '"batch_shape"': text.count('"batch_shape"'),
    '"silu"': text.count('"silu"'),
}
print("\nRemaining artifacts:")
for k, v in remaining.items():
    status = "✓" if v == 0 else f"WARNING: {v}"
    print(f"  {k}: {status}")
