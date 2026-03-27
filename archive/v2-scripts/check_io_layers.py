"""Check input_layers/output_layers format in original Keras 3 model."""
import json

# Check the ORIGINAL Keras 3 model (what the SW cache is serving)
with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet\model\tfjs_uint8\model.json") as f:
    original = json.load(f)

print("=== ORIGINAL (Keras 3) ===")
topology = original["modelTopology"]["model_config"]

def show_io_layers(config, name):
    for key in ["input_layers", "output_layers"]:
        val = config.get(key, "NOT PRESENT")
        print(f"\n{name}.{key}:")
        print(json.dumps(val, indent=2)[:500])

show_io_layers(topology["config"], "wadjet_classifier")

# Check nested model
for layer in topology["config"]["layers"]:
    sub_config = layer.get("config", {})
    if isinstance(sub_config, dict) and sub_config.get("layers"):
        show_io_layers(sub_config, layer["name"])

# Also check the converted model on disk
print("\n\n=== CONVERTED (on disk) ===")
with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json") as f:
    converted = json.load(f)

topology2 = converted["modelTopology"]["model_config"]
show_io_layers(topology2["config"], "wadjet_classifier")

for layer in topology2["config"]["layers"]:
    sub_config = layer.get("config", {})
    if isinstance(sub_config, dict) and sub_config.get("layers"):
        show_io_layers(sub_config, layer["name"])

# Check build_input_shape which may also have Keras 3 format
print("\n\n=== build_input_shape in original ===")
for layer in topology["config"]["layers"]:
    cfg = layer.get("config", {})
    if isinstance(cfg, dict):
        bis = cfg.get("build_input_shape")
        if bis:
            print(f"{layer['name']}: {json.dumps(bis)[:200]}")
    if isinstance(cfg, dict) and cfg.get("layers"):
        for sublayer in cfg["layers"]:
            scfg = sublayer.get("config", {})
            if isinstance(scfg, dict):
                bis = scfg.get("build_input_shape")
                if bis:
                    print(f"  {sublayer['name']}: {json.dumps(bis)[:200]}")
                    break  # just one example
        break
