"""Deep verification of model.json structure for TF.js compatibility."""
import json

with open(r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json") as f:
    data = json.load(f)

topology = data["modelTopology"]["model_config"]

# 1. Check ALL inbound_nodes recursively
def check_all(layers, path=""):
    issues = []
    for layer in layers:
        name = layer.get("name", "?")
        cls = layer.get("class_name", "?")
        inbound = layer.get("inbound_nodes", [])
        
        if not isinstance(inbound, list):
            issues.append(f"ISSUE: {path}{name} inbound_nodes is {type(inbound).__name__}")
            continue
            
        for i, node in enumerate(inbound):
            if not isinstance(node, list):
                issues.append(f"ISSUE: {path}{name} node[{i}] is {type(node).__name__}: {str(node)[:100]}")
            else:
                for j, conn in enumerate(node):
                    if not isinstance(conn, list):
                        issues.append(f"ISSUE: {path}{name} node[{i}][{j}] is {type(conn).__name__}: {str(conn)[:100]}")
                    elif len(conn) != 4:
                        issues.append(f"ISSUE: {path}{name} node[{i}][{j}] has {len(conn)} elements: {conn}")
        
        config = layer.get("config", {})
        if isinstance(config, dict) and config.get("layers"):
            issues.extend(check_all(config["layers"], path + name + "/"))
    return issues

issues = check_all(topology["config"]["layers"])
print(f"Inbound nodes issues: {len(issues)}")
for i in issues:
    print(i)

# 2. Check input_layers / output_layers at each Functional level
def check_io_layers(config, name="root"):
    for key in ["input_layers", "output_layers"]:
        val = config.get(key, [])
        print(f"\n{name}.{key}: {json.dumps(val)[:300]}")
        if val:
            for i, item in enumerate(val):
                if not isinstance(item, list):
                    print(f"  ISSUE: {key}[{i}] is {type(item).__name__}: {str(item)[:100]}")
    
    for layer in config.get("layers", []):
        sub_config = layer.get("config", {})
        if isinstance(sub_config, dict) and sub_config.get("layers"):
            check_io_layers(sub_config, layer["name"])

check_io_layers(topology["config"])

# 3. Check for any remaining Keras 3 artifacts  
raw = json.dumps(data)
print(f"\n\n=== Keras 3 artifact scan ===")
print(f"__keras_tensor__: {raw.count('__keras_tensor__')}")
print(f"batch_shape (not batch_input_shape): {'batch_shape' in raw.replace('batch_input_shape', '')}")
print(f"silu: {raw.count('\"silu\"')}")
print(f"DTypePolicy: {raw.count('DTypePolicy')}")
print(f"module: keras: {raw.count('\"module\": \"keras')}")

# 4. Check top-level keys  
print(f"\n=== Top-level model topology keys ===")
print(list(data["modelTopology"].keys()))
print(f"\n=== model_config keys ===")
print(list(topology.keys()))
print(f"\n=== model_config.config keys ===")
print(list(topology["config"].keys()))

# 5. Look for any dict values where arrays expected
print(f"\n=== Checking for unexpected object types ===")
def find_objects_in_arrays(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "inbound_nodes" and isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        print(f"FOUND: {path}.{k}[{i}] is dict")
            find_objects_in_arrays(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_objects_in_arrays(item, f"{path}[{i}]")

find_objects_in_arrays(data)
