"""
Convert Keras 3 model to TF.js-compatible format using tf.keras directly.
This avoids the tensorflowjs converter dependency issues.
"""
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import json
import numpy as np

# Try to load the model with keras
print("Loading Keras model...")
import keras
model = keras.saving.load_model(
    r"D:\Personal attachements\Projects\Final_Horus\Wadjet\model\wadjet_model_final.keras"
)
print(f"Model loaded: {model.name}")
print(f"Input shape: {model.input_shape}")
print(f"Output shape: {model.output_shape}")
print(f"Total layers: {len(model.layers)}")

# Get a summary of the model architecture
print("\nModel layers (first 10):")
for i, layer in enumerate(model.layers[:10]):
    print(f"  {i}: {layer.name} ({layer.__class__.__name__})")

print("\nModel layers (last 5):")
for i, layer in enumerate(model.layers[-5:]):
    print(f"  {len(model.layers) - 5 + i}: {layer.name} ({layer.__class__.__name__})")

# Try to export as SavedModel first
saved_model_dir = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\saved_model"
os.makedirs(saved_model_dir, exist_ok=True)

print(f"\nExporting SavedModel to: {saved_model_dir}")
model.export(saved_model_dir)
print("SavedModel exported successfully!")

# Check if we can use tensorflowjs without the decision forests
print("\nTrying direct conversion via tensorflowjs.converters.keras_tfjs_loader...")
try:
    # Import just what we need, avoiding the problematic decision forests import
    import importlib
    import sys
    
    # Block the problematic import
    class BlockModule:
        def __init__(self, *a, **kw): pass
        def __getattr__(self, name): return BlockModule()
    sys.modules['tensorflow_decision_forests'] = BlockModule()
    sys.modules['yggdrasil_decision_forests'] = BlockModule()
    
    from tensorflowjs.converters import keras_tfjs_loader
    
    output_dir = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs_new"
    os.makedirs(output_dir, exist_ok=True)
    
    keras_tfjs_loader.save_keras_model(model, output_dir)
    print(f"TF.js model saved to: {output_dir}")
except Exception as e:
    print(f"tensorflowjs save failed: {e}")
    print("Will try alternative approach...")
