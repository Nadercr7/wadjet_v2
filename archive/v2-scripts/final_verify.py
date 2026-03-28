"""Final verification of cleaned model.json."""
import json

with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json") as f:
    data = json.load(f)

raw = json.dumps(data)
checks = {
    "module": raw.count('"module"'),
    "registered_name": raw.count("registered_name"),
    "__keras_tensor__": raw.count("__keras_tensor__"),
    "DTypePolicy": raw.count("DTypePolicy"),
    "silu": raw.count('"silu"'),
}
print("=== Keras 3 artifact counts ===")
for k, v in checks.items():
    status = "CLEAN" if v == 0 else f"FOUND {v}"
    print(f"  {k}: {status}")

print(f"\nFile size: {len(raw)} bytes")

# Show example layer config
topology = data["modelTopology"]["model_config"]
for layer in topology["config"]["layers"]:
    config = layer.get("config", {})
    if isinstance(config, dict) and config.get("layers"):
        for sublayer in config["layers"]:
            if sublayer.get("class_name") == "Conv2D":
                print("\nExample Conv2D config (kernel_initializer):")
                print(json.dumps(sublayer["config"]["kernel_initializer"], indent=2))
                print("\nExample Conv2D config (dtype):")
                print(json.dumps(sublayer["config"]["dtype"]))
                break
        break
