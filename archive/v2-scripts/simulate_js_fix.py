"""Simulate exactly what the JS fix does on the _original_ Keras 3 model.json,
then check if the result is valid for TF.js."""
import json
import copy
import re

# Load original (what SW cache is serving)
with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet\model\tfjs_uint8\model.json") as f:
    original = json.load(f)

# Step 1: Simulate the JS string replacements
raw = json.dumps(original)
raw = raw.replace('"batch_shape"', '"batch_input_shape"')
raw = raw.replace('"silu"', '"swish"')

# Step 2: Parse and check if __keras_tensor__ present
data = json.loads(raw)
has_kt = "__keras_tensor__" in raw
print(f"After string fixes: __keras_tensor__ present: {has_kt}")

# Step 3: Simulate _fixInboundNodes
def fix_inbound_nodes(obj):
    """Exact replica of JS _fixInboundNodes logic"""
    if isinstance(obj, list):
        for item in obj:
            fix_inbound_nodes(item)
    elif isinstance(obj, dict):
        # Traverse wrappers
        if "modelTopology" in obj:
            fix_inbound_nodes(obj["modelTopology"])
        if "model_config" in obj:
            fix_inbound_nodes(obj["model_config"])
        
        # Fix inbound_nodes
        if "inbound_nodes" in obj:
            new_nodes = []
            for node in obj["inbound_nodes"]:
                if isinstance(node, dict) and "args" in node:
                    connections = []
                    for arg in node["args"]:
                        if isinstance(arg, dict) and arg.get("class_name") == "__keras_tensor__":
                            h = arg["config"]["keras_history"]
                            connections.append([h[0], h[1], h[2], {}])
                        elif isinstance(arg, list):
                            for t in arg:
                                if isinstance(t, dict) and t.get("class_name") == "__keras_tensor__":
                                    h = t["config"]["keras_history"]
                                    connections.append([h[0], h[1], h[2], {}])
                    new_nodes.append(connections)
                else:
                    new_nodes.append(node)
            obj["inbound_nodes"] = new_nodes
        
        # Fix dtype
        config = obj.get("config")
        if isinstance(config, dict):
            if isinstance(config.get("dtype"), dict):
                dt = config["dtype"].get("config", {}).get("name", "float32")
                config["dtype"] = "float32" if "float16" in dt else dt
            
            # Strip module/registered_name
            for key in list(config.keys()):
                val = config[key]
                if isinstance(val, dict) and "module" in val and "class_name" in val:
                    config[key] = {"class_name": val["class_name"], "config": val.get("config", {})}
        
            # Recurse into layers
            if config.get("layers"):
                for l in config["layers"]:
                    fix_inbound_nodes(l)
            fix_inbound_nodes(config)

fix_inbound_nodes(data)

# Step 4: Verify the result
output = json.dumps(data)
print(f"\nAfter JS fix simulation:")
print(f"  __keras_tensor__: {output.count('__keras_tensor__')}")
print(f"  module refs: {output.count('\"module\"')}")
print(f"  registered_name: {output.count('registered_name')}")

# Step 5: Check ALL inbound_nodes
topology = data["modelTopology"]["model_config"]

def verify_all(layers, path=""):
    issues = []
    for layer in layers:
        name = layer.get("name", "?")
        for i, node in enumerate(layer.get("inbound_nodes", [])):
            if isinstance(node, dict):
                issues.append(f"OBJECT: {path}{name} node[{i}]")
            elif isinstance(node, list):
                for j, conn in enumerate(node):
                    if isinstance(conn, dict):
                        issues.append(f"OBJECT in array: {path}{name} node[{i}][{j}]: {str(conn)[:100]}")
                    elif isinstance(conn, list):
                        if len(conn) != 4:
                            issues.append(f"BAD LENGTH: {path}{name} node[{i}][{j}]: len={len(conn)}")
        config = layer.get("config", {})
        if isinstance(config, dict) and config.get("layers"):
            issues.extend(verify_all(config["layers"], path + name + "/"))
    return issues

issues = verify_all(topology["config"]["layers"])
print(f"\nInbound nodes issues: {len(issues)}")
for i in issues[:10]:
    print(f"  {i}")

# Step 6: Compare with the fully-converted on-disk model
with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json") as f:
    disk_model = json.load(f)

# Compare a key nested layer
def get_layer(layers, name):
    for l in layers:
        if l.get("name") == name:
            return l
        config = l.get("config", {})
        if isinstance(config, dict) and config.get("layers"):
            result = get_layer(config["layers"], name)
            if result:
                return result
    return None

# Check the efficientnetv2-s nested model config
js_fixed_model = get_layer(topology["config"]["layers"], "efficientnetv2-s")
disk_model_nested = get_layer(disk_model["modelTopology"]["model_config"]["config"]["layers"], "efficientnetv2-s")

if js_fixed_model and disk_model_nested:
    js_keys = set(js_fixed_model.get("config", {}).keys())
    disk_keys = set(disk_model_nested.get("config", {}).keys())
    print(f"\nJS-fixed efficientnetv2-s config keys: {sorted(js_keys)}")
    print(f"Disk efficientnetv2-s config keys: {sorted(disk_keys)}")
    print(f"Keys only in JS-fixed: {js_keys - disk_keys}")
    print(f"Keys only in disk: {disk_keys - js_keys}")
    
    # Compare top-level config values (excluding layers which is huge)
    for key in sorted(js_keys | disk_keys):
        if key == "layers":
            continue
        js_val = js_fixed_model.get("config", {}).get(key)
        disk_val = disk_model_nested.get("config", {}).get(key)
        if json.dumps(js_val) != json.dumps(disk_val):
            print(f"\nDIFFERENCE in efficientnetv2-s.config.{key}:")
            print(f"  JS-fixed: {json.dumps(js_val)[:200]}")
            print(f"  Disk:     {json.dumps(disk_val)[:200]}")

# Also compare a specific inner layer
for name in ["rescaling", "stem_conv", "block1a_add"]:
    js_layer = get_layer(topology["config"]["layers"], name)
    disk_layer = get_layer(disk_model["modelTopology"]["model_config"]["config"]["layers"], name)
    if js_layer and disk_layer:
        js_str = json.dumps(js_layer)
        disk_str = json.dumps(disk_layer)
        if js_str != disk_str:
            # Find the first difference
            for i, (a, b) in enumerate(zip(js_str, disk_str)):
                if a != b:
                    print(f"\nFirst diff in {name} at position {i}:")
                    print(f"  JS-fixed: ...{js_str[max(0,i-30):i+50]}...")
                    print(f"  Disk:     ...{disk_str[max(0,i-30):i+50]}...")
                    break
        else:
            print(f"\n{name}: IDENTICAL")
