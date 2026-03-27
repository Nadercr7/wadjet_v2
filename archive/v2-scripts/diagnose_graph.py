"""Deep analysis of model.json to find what causes TF.js 'Graph disconnected' error.
Focus on fields that Keras 3 has but TF.js doesn't understand."""
import json

with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json") as f:
    data = json.load(f)

topology = data["modelTopology"]["model_config"]

# 1. Find ALL unique config keys across all layers
all_keys = set()
def collect_keys(layers, level=""):
    for layer in layers:
        cls = layer.get("class_name", "?")
        config = layer.get("config", {})
        if isinstance(config, dict):
            for k in config.keys():
                all_keys.add(f"{cls}.{k}")
        # Also check layer-level keys (outside config)
        for k in layer.keys():
            if k not in ("class_name", "config", "name", "inbound_nodes"):
                all_keys.add(f"LAYER_KEY.{k}")
        if isinstance(config, dict) and config.get("layers"):
            collect_keys(config["layers"], level + "  ")

collect_keys(topology["config"]["layers"])
print("=== All unique layer config keys ===")
for k in sorted(all_keys):
    print(f"  {k}")

# 2. Check the nested Functional model specifically
eff_layer = None
for layer in topology["config"]["layers"]:
    if layer.get("class_name") == "Functional":
        eff_layer = layer
        break

if eff_layer:
    print(f"\n=== Nested Functional model: {eff_layer['name']} ===")
    print(f"Top-level keys: {list(eff_layer.keys())}")
    print(f"Config keys: {list(eff_layer['config'].keys())}")
    
    # Check for any Keras 3 specific configs
    config = eff_layer["config"]
    for key in config:
        if key == "layers":
            continue
        val = config[key]
        print(f"  config.{key}: {json.dumps(val)[:200]}")

# 3. Check InputLayer configs specifically
print("\n=== InputLayer configs ===")
def find_input_layers(layers, path=""):
    for layer in layers:
        if layer.get("class_name") == "InputLayer":
            print(f"\n{path}{layer['name']}:")
            print(json.dumps(layer, indent=2)[:500])
        config = layer.get("config", {})
        if isinstance(config, dict) and config.get("layers"):
            find_input_layers(config["layers"], path + layer["name"] + "/")

find_input_layers(topology["config"]["layers"])

# 4. Check if any layer has unexpected fields like build_config, seed
print("\n=== Unusual fields ===")
unusual_keys = {"build_config", "seed_generator", "seed", "build_input_shape", 
                "is_deterministic", "backend"}
def find_unusual(layers, path=""):
    for layer in layers:
        config = layer.get("config", {})
        if isinstance(config, dict):
            for k in config:
                if k in unusual_keys:
                    print(f"{path}{layer['name']}.config.{k}: {json.dumps(config[k])[:200]}")
        if isinstance(config, dict) and config.get("layers"):
            find_unusual(config["layers"], path + layer["name"] + "/")

find_unusual(topology["config"]["layers"])

# 5. Show complete outer model structure (without inner layers)
print("\n=== Outer model (wadjet_classifier) layers ===")
for layer in topology["config"]["layers"]:
    cls = layer.get("class_name", "?")
    name = layer.get("name", "?")
    inbound = layer.get("inbound_nodes", [])
    print(f"  {name} ({cls}): inbound={json.dumps(inbound)[:100]}")
