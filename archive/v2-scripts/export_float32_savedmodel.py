"""Export the Keras model as a pure float32 SavedModel (no mixed_float16).

The original model was trained with mixed_float16 policy, which embeds
DT_HALF Cast ops into the TF graph.  TF.js WebGL backend doesn't support
float16 tensors for many kernels (Mul, etc.), causing runtime crashes.

This script:
1. Loads the .keras model
2. Forces the global dtype policy to float32
3. Rebuilds the model so every layer uses float32
4. Exports a clean SavedModel with zero DT_HALF ops
"""
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["KERAS_BACKEND"] = "tensorflow"

import keras
import numpy as np

# ── 1. Force float32 globally ──────────────────────────────────────
keras.mixed_precision.set_global_policy("float32")

# ── 2. Load model ──────────────────────────────────────────────────
SRC = r"D:\Personal attachements\Projects\Final_Horus\Wadjet\model\wadjet_model_final.keras"
print("Loading model …")
model = keras.saving.load_model(SRC)
print(f"  name={model.name}  layers={len(model.layers)}  "
      f"input={model.input_shape}  output={model.output_shape}")

# ── 3. Cast all weights to float32 ─────────────────────────────────
count = 0
for layer in model.layers:
    for w in layer.weights:
        if w.dtype != "float32":
            w.assign(w.numpy().astype(np.float32))
            count += 1
print(f"  Cast {count} weight tensors to float32")

# ── 4. Verify dtype policy on every layer ───────────────────────────
mixed = [l.name for l in model.layers
         if hasattr(l, "dtype_policy") and "float16" in str(l.dtype_policy)]
if mixed:
    print(f"  WARNING: {len(mixed)} layers still have float16 policy: {mixed[:5]}")
else:
    print("  All layers are float32 ✓")

# ── 5. Trace a concrete function with float32 input ─────────────────
import tensorflow as tf

@tf.function(input_signature=[
    tf.TensorSpec(shape=[None, 384, 384, 3], dtype=tf.float32, name="image_input")
])
def serving_fn(image_input):
    return model(image_input, training=False)

# Verify the concrete function has no DT_HALF
cf = serving_fn.get_concrete_function()
graph_def = cf.graph.as_graph_def()
half_ops = [n.name for n in graph_def.node if "DT_HALF" in str(n)]
print(f"  DT_HALF ops in traced graph: {len(half_ops)}")

# ── 6. Export SavedModel ────────────────────────────────────────────
DST = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\saved_model_f32"
if os.path.exists(DST):
    import shutil
    shutil.rmtree(DST)

tf.saved_model.save(
    model,
    DST,
    signatures={"serving_default": serving_fn},
)
print(f"\n  SavedModel (float32) exported → {DST}")

# Quick verify
loaded = tf.saved_model.load(DST)
dummy = tf.zeros([1, 384, 384, 3], dtype=tf.float32)
out = loaded.signatures["serving_default"](image_input=dummy)
key = list(out.keys())[0]
print(f"  Verify: output key={key}  shape={out[key].shape}  dtype={out[key].dtype}")
print("  Done ✓")
