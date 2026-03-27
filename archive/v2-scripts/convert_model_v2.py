"""
Properly convert Keras 3 model.json to Keras 2 format for TF.js compatibility.
Handles: inbound_nodes, batch_shape, silu, dtype objects, AND Keras 3 module-style objects.
"""
import json
import copy

V1_PATH = r"D:\Personal attachements\Projects\Final_Horus\Wadjet\model\tfjs_uint8\model.json"
V2_PATH = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json"


def extract_keras_tensor(t):
    """Convert a __keras_tensor__ object to Keras 2 tuple format."""
    if isinstance(t, dict) and t.get("class_name") == "__keras_tensor__":
        history = t["config"]["keras_history"]
        return [history[0], history[1], history[2], {}]
    return None


def convert_inbound_node(node):
    """Convert a single Keras 3 inbound_node to Keras 2 format."""
    if not isinstance(node, dict) or "args" not in node:
        return node

    args = node["args"]
    connections = []

    for arg in args:
        if isinstance(arg, dict) and arg.get("class_name") == "__keras_tensor__":
            conn = extract_keras_tensor(arg)
            if conn:
                connections.append(conn)
        elif isinstance(arg, list):
            for item in arg:
                conn = extract_keras_tensor(item)
                if conn:
                    connections.append(conn)

    return connections


def strip_keras3_module(obj):
    """
    Recursively convert Keras 3 serialized objects to Keras 2 format.
    
    Keras 3: {"module": "keras.initializers", "class_name": "Zeros", "config": {}, "registered_name": null}
    Keras 2: {"class_name": "Zeros", "config": {}}
    """
    if isinstance(obj, dict):
        # If this is a Keras 3 serialized object, strip module/registered_name
        if "module" in obj and "class_name" in obj:
            result = {"class_name": obj["class_name"], "config": strip_keras3_module(obj.get("config", {}))}
            return result
        # Otherwise recurse
        return {k: strip_keras3_module(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [strip_keras3_module(item) for item in obj]
    return obj


def convert_layers(layers, stats):
    """Recursively convert all layers in-place."""
    for i, layer in enumerate(layers):
        name = layer.get("name", "?")
        config = layer.get("config", {})

        # Fix batch_shape -> batch_input_shape
        if isinstance(config, dict) and "batch_shape" in config and "batch_input_shape" not in config:
            config["batch_input_shape"] = config.pop("batch_shape")
            stats["batch_shape"] += 1

        # Fix silu -> swish activation
        if isinstance(config, dict) and config.get("activation") == "silu":
            config["activation"] = "swish"
            stats["silu"] += 1

        # Fix dtype objects -> string
        if isinstance(config, dict) and isinstance(config.get("dtype"), dict):
            dtype_config = config["dtype"].get("config", {})
            dtype_name = dtype_config.get("name", "float32")
            config["dtype"] = "float32" if "float16" in dtype_name else dtype_name
            stats["dtype"] += 1

        # Convert inbound_nodes
        inbound = layer.get("inbound_nodes", [])
        new_inbound = []
        for node in inbound:
            if isinstance(node, dict):
                converted = convert_inbound_node(node)
                new_inbound.append(converted)
                stats["inbound_nodes"] += 1
            else:
                new_inbound.append(node)
        layer["inbound_nodes"] = new_inbound

        # Strip module/registered_name from ALL config values (initializers, etc.)
        if isinstance(config, dict):
            for key in list(config.keys()):
                if isinstance(config[key], dict) and "module" in config[key]:
                    old = config[key]
                    config[key] = strip_keras3_module(old)
                    stats["module_stripped"] += 1

        # Recurse into nested Functional models
        if isinstance(config, dict) and config.get("layers"):
            convert_layers(config["layers"], stats)


def main():
    print(f"Reading original from: {V1_PATH}")
    with open(V1_PATH, "r") as f:
        data = json.load(f)

    stats = {"batch_shape": 0, "silu": 0, "dtype": 0, "inbound_nodes": 0, "module_stripped": 0}

    topology = data["modelTopology"]["model_config"]
    convert_layers(topology["config"]["layers"], stats)

    # Verify no Keras 3 artifacts remain
    output = json.dumps(data)
    assert "__keras_tensor__" not in output, "Still has __keras_tensor__!"
    assert '"silu"' not in output, "Still has silu!"
    
    module_remaining = output.count('"module"')
    print(f"Remaining 'module' references: {module_remaining}")
    
    # Verify multi-input layers
    def verify_multi_input(layers):
        for layer in layers:
            cls = layer.get("class_name", "")
            name = layer.get("name", "?")
            if cls in ("Add", "Multiply", "Concatenate"):
                inbound = layer.get("inbound_nodes", [])
                for node in inbound:
                    assert isinstance(node, list), f"{name}: inbound_node is not a list"
                    assert len(node) >= 2, f"{name}: should have >= 2 connections, got {len(node)}"
                    for conn in node:
                        assert isinstance(conn, list) and len(conn) == 4, f"{name}: bad connection: {conn}"
            if layer.get("config", {}).get("layers"):
                verify_multi_input(layer["config"]["layers"])

    verify_multi_input(topology["config"]["layers"])
    print("Verification passed: all multi-input layers OK")

    # Verify no object inbound_nodes
    def verify_inbound(layers):
        for layer in layers:
            for node in layer.get("inbound_nodes", []):
                assert isinstance(node, list), f"{layer['name']}: node is {type(node)}"
                for conn in node:
                    assert isinstance(conn, list), f"{layer['name']}: conn is {type(conn)}: {conn}"
            if layer.get("config", {}).get("layers"):
                verify_inbound(layer["config"]["layers"])
    
    verify_inbound(topology["config"]["layers"])
    print("Verification passed: all inbound_nodes are arrays")

    print(f"\nConversion stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print(f"\nWriting to: {V2_PATH}")
    with open(V2_PATH, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    
    final_size = len(json.dumps(data, separators=(",", ":")))
    print(f"Output size: {final_size} bytes ({final_size/1024/1024:.1f} MB)")
    print("Done!")


if __name__ == "__main__":
    main()
