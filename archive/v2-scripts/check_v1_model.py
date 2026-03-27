"""Check the original v1 model.json for Keras 3 multi-input layer format."""
import json
import os

v1_path = r"D:\Personal attachements\Projects\Final_Horus\Wadjet\models\landmark\tfjs\model.json"

if not os.path.exists(v1_path):
    print("V1 original: NOT FOUND")
    exit(1)

with open(v1_path) as f:
    data = json.load(f)

topology = data["modelTopology"]["model_config"]
layers = topology["config"]["layers"]

def find_multi(layers):
    found = False
    for layer in layers:
        cls = layer.get("class_name", "")
        name = layer.get("name", "?")
        if cls in ("Add", "Multiply"):
            inbound = layer.get("inbound_nodes", [])
            print(f"\n{name} ({cls}):")
            print(json.dumps(inbound, indent=2)[:500])
            if not found:
                found = True
        if layer.get("config", {}).get("layers"):
            find_multi(layer["config"]["layers"])

find_multi(layers)

# Check format
raw = json.dumps(data)
print(f"\nHas __keras_tensor__: {'__keras_tensor__' in raw}")
print(f"Has batch_shape (not batch_input_shape): {'batch_shape' in raw and 'batch_input_shape' not in raw}")
