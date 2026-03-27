"""Check Keras 3 "module" format objects that TF.js may not understand."""
import json

with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json") as f:
    data = json.load(f)

raw = json.dumps(data)

# Find unique patterns of "module" usage
def find_module_refs(obj, path="", results=None):
    if results is None:
        results = set()
    if isinstance(obj, dict):
        if "module" in obj and "class_name" in obj:
            # This is a Keras 3 serialized object
            key = f"{obj['module']}.{obj['class_name']}"
            if key not in results:
                results.add(key)
                print(f"\nKeras 3 object at {path}:")
                print(json.dumps(obj, indent=2)[:300])
        for k, v in obj.items():
            find_module_refs(v, f"{path}.{k}", results)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_module_refs(item, f"{path}[{i}]", results)
    return results

results = find_module_refs(data)
print(f"\n\n=== Total unique Keras 3 object types: {len(results)} ===")
for r in sorted(results):
    print(f"  {r}")
    
# Count total
count = raw.count('"module"')
print(f"\nTotal 'module' references: {count}")

# Show specific example from a Conv2D config
topology = data["modelTopology"]["model_config"]
for layer in topology["config"]["layers"]:
    config = layer.get("config", {})
    if isinstance(config, dict) and config.get("layers"):
        for sublayer in config["layers"]:
            if sublayer.get("class_name") == "Conv2D":
                print(f"\n=== Example Conv2D layer config ===")
                print(json.dumps(sublayer["config"], indent=2)[:800])
                break
        break
