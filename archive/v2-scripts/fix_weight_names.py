"""Fix DepthwiseConv2D weight names: kernel -> depthwise_kernel"""
import json

MODEL_PATH = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json"

with open(MODEL_PATH) as f:
    data = json.load(f)

# Find all DepthwiseConv2D layer names
layers = data["modelTopology"]["model_config"]["config"]["layers"]
dwconv_names = set()
for l in layers:
    if l.get("class_name") == "DepthwiseConv2D":
        dwconv_names.add(l["name"])

print(f"DepthwiseConv2D layers: {len(dwconv_names)}")

# Rename weights in manifest
rename_count = 0
for group in data["weightsManifest"]:
    for w in group["weights"]:
        parts = w["name"].rsplit("/", 1)
        if len(parts) == 2 and parts[0] in dwconv_names and parts[1] == "kernel":
            old_name = w["name"]
            w["name"] = parts[0] + "/depthwise_kernel"
            rename_count += 1
            if rename_count <= 3:
                print(f"  Renamed: {old_name} -> {w['name']}")

print(f"Total weights renamed: {rename_count}")

# Also check if there are any other potential mismatches
# TF.js expects Dense/Conv2D weights as "kernel" and "bias" — those should be fine
# Let's verify by checking what TF.js expects for each layer type
print("\nAll weight name suffixes by layer type:")
weight_suffixes = {}
for group in data["weightsManifest"]:
    for w in group["weights"]:
        parts = w["name"].rsplit("/", 1)
        if len(parts) == 2:
            layer_name = parts[0]
            suffix = parts[1]
            # Find the layer class
            for l in layers:
                if l["name"] == layer_name:
                    cls = l["class_name"]
                    key = f"{cls}.{suffix}"
                    if key not in weight_suffixes:
                        weight_suffixes[key] = 0
                    weight_suffixes[key] += 1
                    break

for key in sorted(weight_suffixes.keys()):
    print(f"  {key}: {weight_suffixes[key]}")

# Write the fixed model
with open(MODEL_PATH, "w") as f:
    json.dump(data, f, separators=(",", ":"))

size = len(json.dumps(data, separators=(",", ":")))
print(f"\nWritten: {size} bytes ({size/1024:.0f} KB)")
