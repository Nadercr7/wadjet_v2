"""Analyze the original v1 model.json and properly re-convert for TF.js."""
import json
import os
import copy

V1_PATH = r"D:\Personal attachements\Projects\Final_Horus\Wadjet\model\tfjs\model.json"
V2_PATH = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json"

# Step 1: Analyze original
with open(V1_PATH, "r") as f:
    original = json.load(f)

raw = json.dumps(original)
print("=== Original V1 model.json ===")
print(f"Has __keras_tensor__: {'__keras_tensor__' in raw}")
print(f'Has "batch_shape": {"batch_shape" in raw}')
print(f'Has "silu": {"silu" in raw}')
print(f"Size: {len(raw)} bytes")

# Step 2: Show first Add layer's inbound_nodes
topology = original["modelTopology"]["model_config"]

def find_multi_input(layers, limit=3):
    count = 0
    for layer in layers:
        cls = layer.get("class_name", "")
        name = layer.get("name", "?")
        if cls in ("Add", "Multiply") and count < limit:
            inbound = layer.get("inbound_nodes", [])
            print(f"\n--- {name} ({cls}) inbound_nodes ---")
            print(json.dumps(inbound, indent=2)[:600])
            count += 1
        if layer.get("config", {}).get("layers"):
            find_multi_input(layer["config"]["layers"], limit - count)

find_multi_input(topology["config"]["layers"])
