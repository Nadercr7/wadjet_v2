"""
Properly convert Keras 3 model.json to Keras 2 format for TF.js compatibility.
Handles ALL cases including multi-input layers (Add, Multiply, Concatenate).
"""
import json
import sys

V1_PATH = r"D:\Personal attachements\Projects\Final_Horus\Wadjet\model\tfjs_uint8\model.json"
V2_PATH = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json"


def extract_keras_tensor(t):
    """Convert a __keras_tensor__ object to Keras 2 tuple format."""
    if isinstance(t, dict) and t.get("class_name") == "__keras_tensor__":
        history = t["config"]["keras_history"]
        return [history[0], history[1], history[2], {}]
    return None


def convert_inbound_node(node):
    """Convert a single Keras 3 inbound_node to Keras 2 format.
    
    Keras 3: {"args": [...], "kwargs": {...}}
    Keras 2: [["layer_name", node_idx, tensor_idx, {}], ...]
    """
    if not isinstance(node, dict) or "args" not in node:
        return node  # Already Keras 2 or unknown format

    args = node["args"]
    connections = []

    for arg in args:
        if isinstance(arg, dict) and arg.get("class_name") == "__keras_tensor__":
            # Single tensor argument
            conn = extract_keras_tensor(arg)
            if conn:
                connections.append(conn)
        elif isinstance(arg, list):
            # List of tensors (multi-input layers like Add, Multiply)
            for item in arg:
                conn = extract_keras_tensor(item)
                if conn:
                    connections.append(conn)

    return connections


def convert_layers(layers, stats):
    """Recursively convert all layers in-place."""
    for layer in layers:
        name = layer.get("name", "?")
        cls = layer.get("class_name", "?")

        # Fix batch_shape -> batch_input_shape
        config = layer.get("config", {})
        if "batch_shape" in config and "batch_input_shape" not in config:
            config["batch_input_shape"] = config.pop("batch_shape")
            stats["batch_shape"] += 1

        # Fix silu -> swish activation
        if config.get("activation") == "silu":
            config["activation"] = "swish"
            stats["silu"] += 1

        # Fix dtype objects -> string
        if isinstance(config.get("dtype"), dict):
            dtype_config = config["dtype"].get("config", {})
            dtype_name = dtype_config.get("name", "float32")
            # TF.js doesn't support mixed_float16, use float32
            if "float16" in dtype_name:
                config["dtype"] = "float32"
            else:
                config["dtype"] = dtype_name
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

        # Recurse into nested Functional models
        if config.get("layers"):
            convert_layers(config["layers"], stats)


def main():
    print(f"Reading original from: {V1_PATH}")
    with open(V1_PATH, "r") as f:
        data = json.load(f)

    stats = {"batch_shape": 0, "silu": 0, "dtype": 0, "inbound_nodes": 0}

    topology = data["modelTopology"]["model_config"]
    convert_layers(topology["config"]["layers"], stats)

    # Verify no Keras 3 artifacts remain
    output = json.dumps(data)
    assert "__keras_tensor__" not in output, "Still has __keras_tensor__!"
    assert '"batch_shape"' not in output or '"batch_input_shape"' in output, "Still has batch_shape!"
    assert '"silu"' not in output, "Still has silu!"

    # Check multi-input layers
    def verify_multi_input(layers):
        for layer in layers:
            cls = layer.get("class_name", "")
            name = layer.get("name", "?")
            if cls in ("Add", "Multiply", "Concatenate"):
                inbound = layer.get("inbound_nodes", [])
                for node in inbound:
                    assert isinstance(node, list), f"{name}: inbound_node is not a list: {type(node)}"
                    assert len(node) >= 2, f"{name}: Add/Multiply should have >= 2 connections, got {len(node)}"
                    for conn in node:
                        assert isinstance(conn, list) and len(conn) == 4, f"{name}: bad connection: {conn}"
            if layer.get("config", {}).get("layers"):
                verify_multi_input(layer["config"]["layers"])

    verify_multi_input(topology["config"]["layers"])
    print("Verification passed: all multi-input layers have proper connections")

    print(f"\nConversion stats:")
    print(f"  batch_shape -> batch_input_shape: {stats['batch_shape']}")
    print(f"  silu -> swish: {stats['silu']}")
    print(f"  dtype object -> string: {stats['dtype']}")
    print(f"  inbound_nodes Keras3 -> Keras2: {stats['inbound_nodes']}")

    print(f"\nWriting to: {V2_PATH}")
    with open(V2_PATH, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"Output size: {len(output)} bytes")
    print("Done!")


if __name__ == "__main__":
    main()
