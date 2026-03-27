"""Check weight manifest names vs actual layer names in flattened model."""
import json

with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json") as f:
    data = json.load(f)

# Get all layer names from topology
layers = data["modelTopology"]["model_config"]["config"]["layers"]
layer_names = set()
for l in layers:
    layer_names.add(l["name"])

# Get all weight names from weightsManifest
weight_names = set()
weight_name_to_layer = {}
for group in data["weightsManifest"]:
    for w in group["weights"]:
        wname = w["name"]
        weight_names.add(wname)
        # Extract layer name (everything before the last /)
        parts = wname.rsplit("/", 1)
        if len(parts) == 2:
            lname = parts[0]
            weight_name_to_layer[wname] = lname

# Find weight layer names not in model layers
weight_layer_names = set(weight_name_to_layer.values())
missing_in_model = weight_layer_names - layer_names
extra_in_model = layer_names - weight_layer_names

print(f"Total layers in model: {len(layer_names)}")
print(f"Total weights: {len(weight_names)}")
print(f"Unique weight layer prefixes: {len(weight_layer_names)}")
print(f"\nWeight prefixes NOT in model layers ({len(missing_in_model)}):")
for name in sorted(missing_in_model)[:20]:
    print(f"  {name}")

if len(missing_in_model) > 20:
    print(f"  ... and {len(missing_in_model) - 20} more")

# Check if the missing names have a pattern (e.g. missing prefix)
print(f"\nSample weight names:")
for w in sorted(weight_names)[:10]:
    print(f"  {w}")

# Check if some layers might be named differently
print(f"\nLayers containing 'block5a':")
for n in sorted(layer_names):
    if "block5a" in n:
        print(f"  {n}")

print(f"\nWeights containing 'block5a':")
for w in sorted(weight_names):
    if "block5a" in w:
        print(f"  {w}")
