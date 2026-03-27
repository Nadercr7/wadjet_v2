"""
Flatten the nested Functional model topology for TF.js compatibility.

Input:  wadjet_classifier (Functional)
          -> image_input (InputLayer)
          -> efficientnetv2-s (Functional) [513 inner layers]
          -> global_avg_pool
          -> head_dropout
          -> predictions

Output: wadjet_classifier (Functional) [all layers at one level]
          -> image_input (InputLayer)
          -> [all efficientnetv2-s inner layers, rewired]
          -> global_avg_pool (connected to top_activation instead of efficientnetv2-s)
          -> head_dropout
          -> predictions

Also strips Keras 3-only config fields that TF.js doesn't understand.
"""
import json
import copy

MODEL_PATH = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs\model.json"

# Keras 3 config keys to strip (per layer class)
STRIP_KEYS = {
    "InputLayer": {"optional"},
    "Dropout": {"seed"},
    "BatchNormalization": {"synchronized"},
    "Dense": {"quantization_config"},
}

# Keys to strip from ALL layer configs
GLOBAL_STRIP = {"seed_generator", "build_config", "build_input_shape"}


def strip_keras3_fields(layer):
    """Remove Keras 3-only config fields that TF.js doesn't understand."""
    cls = layer.get("class_name", "")
    config = layer.get("config", {})
    
    # Strip class-specific keys
    to_strip = STRIP_KEYS.get(cls, set()) | GLOBAL_STRIP
    for key in to_strip:
        config.pop(key, None)


def flatten_model(data):
    """Flatten nested Functional model into a single-level topology."""
    topology = data["modelTopology"]["model_config"]
    outer_config = topology["config"]
    outer_layers = outer_config["layers"]
    
    # Find the nested Functional model
    nested_model = None
    nested_idx = None
    for i, layer in enumerate(outer_layers):
        if layer.get("class_name") == "Functional":
            nested_model = layer
            nested_idx = i
            break
    
    if not nested_model:
        print("No nested Functional model found — nothing to flatten")
        return
    
    nested_name = nested_model["name"]  # "efficientnetv2-s"
    nested_config = nested_model["config"]
    inner_layers = nested_config["layers"]
    
    # Get inner model's input/output layer names
    inner_input_names = [il[0] for il in nested_config["input_layers"]]  # ["input_layer"]
    inner_output_names = [ol[0] for ol in nested_config["output_layers"]]  # ["top_activation"]
    
    # Get outer model's connection TO the nested model
    # efficientnetv2-s inbound_nodes: [[["image_input", 0, 0, {}]]]
    outer_input_connections = nested_model["inbound_nodes"]  # [[["image_input", 0, 0, {}]]]
    
    # outer_input_connections[0] = [["image_input", 0, 0, {}]]
    # So the inner model's "input_layer" maps to the outer model's "image_input"
    input_mapping = {}
    for call_idx, connections in enumerate(outer_input_connections):
        for conn_idx, conn in enumerate(connections):
            if conn_idx < len(inner_input_names):
                input_mapping[inner_input_names[conn_idx]] = conn[0]  # "input_layer" -> "image_input"
    
    print(f"Input mapping: {input_mapping}")
    print(f"Inner inputs: {inner_input_names}")
    print(f"Inner outputs: {inner_output_names}")
    
    # Build the flattened layer list
    new_layers = []
    
    # 1. Add all outer layers BEFORE the nested model
    for layer in outer_layers[:nested_idx]:
        strip_keras3_fields(layer)
        new_layers.append(layer)
    
    # 2. Add all inner layers, EXCLUDING the InputLayer(s) that map to outer inputs
    for layer in inner_layers:
        name = layer.get("name", "")
        
        if name in inner_input_names:
            # Skip inner InputLayers — they're replaced by outer InputLayers
            continue
        
        # Rewire inbound_nodes: replace references to inner input layers with outer input layers
        new_layer = copy.deepcopy(layer)
        for node in new_layer.get("inbound_nodes", []):
            for conn in node:
                if isinstance(conn, list) and len(conn) >= 1:
                    if conn[0] in input_mapping:
                        conn[0] = input_mapping[conn[0]]
        
        strip_keras3_fields(new_layer)
        new_layers.append(new_layer)
    
    # 3. Add all outer layers AFTER the nested model, rewiring references
    for layer in outer_layers[nested_idx + 1:]:
        new_layer = copy.deepcopy(layer)
        
        # Rewire: replace "efficientnetv2-s" references with inner output layer
        for node in new_layer.get("inbound_nodes", []):
            for conn in node:
                if isinstance(conn, list) and conn[0] == nested_name:
                    # Replace nested model reference with its output layer
                    conn[0] = inner_output_names[0]  # "top_activation"
        
        strip_keras3_fields(new_layer)
        new_layers.append(new_layer)
    
    # Update outer model config
    outer_config["layers"] = new_layers
    
    # Verify input_layers and output_layers still reference existing layers
    layer_names = {l["name"] for l in new_layers}
    for il in outer_config["input_layers"]:
        assert il[0] in layer_names, f"Input layer {il[0]} not in flattened layers"
    for ol in outer_config["output_layers"]:
        assert ol[0] in layer_names, f"Output layer {ol[0]} not in flattened layers"
    
    return len(inner_layers), len(new_layers)


def verify_graph(data):
    """Verify all inbound_node references point to existing layers."""
    topology = data["modelTopology"]["model_config"]
    layers = topology["config"]["layers"]
    
    layer_names = {l["name"] for l in layers}
    issues = []
    
    for layer in layers:
        name = layer.get("name", "?")
        for node in layer.get("inbound_nodes", []):
            for conn in node:
                if isinstance(conn, list) and conn[0] not in layer_names:
                    issues.append(f"{name}: references non-existent layer '{conn[0]}'")
    
    return issues


def main():
    with open(MODEL_PATH) as f:
        data = json.load(f)
    
    inner_count, total_count = flatten_model(data)
    print(f"\nFlattened: {inner_count} inner layers -> {total_count} total layers")
    
    # Verify
    issues = verify_graph(data)
    if issues:
        print(f"\nGraph issues found: {len(issues)}")
        for i in issues:
            print(f"  {i}")
        return
    
    print("Graph verification passed: all references valid")
    
    # Final artifact check
    output = json.dumps(data)
    print(f"\n__keras_tensor__: {output.count('__keras_tensor__')}")
    print(f"module refs: {output.count('\"module\"')}")
    print(f"optional: {output.count('\"optional\"')}")
    print(f"synchronized: {output.count('\"synchronized\"')}")
    print(f"quantization_config: {output.count('quantization_config')}")
    
    # Count layer types
    layers = data["modelTopology"]["model_config"]["config"]["layers"]
    class_counts = {}
    for l in layers:
        cls = l.get("class_name", "?")
        class_counts[cls] = class_counts.get(cls, 0) + 1
    print(f"\nLayer types: {json.dumps(class_counts, indent=2)}")
    
    # Check no nested Functional models remain
    for l in layers:
        if l.get("class_name") == "Functional":
            print(f"\nWARNING: Nested Functional model still present: {l['name']}")
            return
    
    print("\nNo nested Functional models — flat topology!")
    
    # Write
    with open(MODEL_PATH, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    
    size = len(json.dumps(data, separators=(",", ":")))
    print(f"\nWritten: {size} bytes ({size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
