"""
Fix v5: Comprehensive fixes for both notebooks.
1. Landmark: build_model cell already restored (previous script)
2. Hieroglyph Cell 18: Fix hardcoded metadata path, guard ONNX file size checks
3. Landmark Cell 20: Fix indentation so cross-validation is inside ONNX guard
"""
import json, copy, uuid

# ── HIEROGLYPH: Fix Cell 18 (Save Model Metadata + All Outputs) ──
hiero_path = 'planning/model-rebuild/notebooks/hieroglyph/hieroglyph_classifier.ipynb'
nb = json.load(open(hiero_path, encoding='utf-8'))

NEW_HIERO_CELL18 = '''# ============================================================
# Save Model Metadata + All Outputs
# ============================================================
# Load label mapping from the Kaggle dataset
label_map_path = os.path.join(DATA_DIR, "classification", "metadata.json")
if not os.path.exists(label_map_path):
    # Try alternate location
    label_map_path = os.path.join(DATA_DIR, "metadata.json")

if os.path.exists(label_map_path):
    with open(label_map_path) as f:
        metadata = json.load(f)
    print(f"Loaded metadata from {label_map_path}")
else:
    metadata = {"num_classes": NUM_CLASSES, "image_size": IMAGE_SIZE}
    print("No metadata.json found, using defaults")

# Determine what format was actually exported
has_onnx = os.path.exists(ONNX_FLOAT_PATH)
has_onnx_q = os.path.exists(ONNX_UINT8_PATH)
export_format = "onnx" if has_onnx else "savedmodel"

# Create output metadata
output_metadata = {
    "model_name": "wadjet_hieroglyph_classifier_v2",
    "architecture": "MobileNetV3Small",
    "input_size": IMAGE_SIZE,
    "num_classes": NUM_CLASSES,
    "format": export_format,
    "load_method": "ort.InferenceSession.create(url)" if has_onnx else "convert SavedModel to ONNX locally",
    "preprocessing": {
        "normalize": "divide_by_255",
        "input_range": [0.0, 1.0],
    },
    "training": {
        "precision": "float32",
        "loss": f"FocalLoss(gamma={FOCAL_GAMMA})",
        "head_epochs": HEAD_EPOCHS,
        "finetune_epochs": FINETUNE_EPOCHS,
        "test_accuracy": float(accuracy),
    },
    "original_metadata": metadata,
}

with open(METADATA_PATH, "w") as f:
    json.dump(output_metadata, f, indent=2)
print(f"Metadata saved to: {METADATA_PATH}")

# Save .keras model (backup)
model.save(BEST_MODEL_PATH)
print(f"Keras model saved to: {BEST_MODEL_PATH}")

# Summary of all outputs
print("\\n" + "=" * 60)
print("ALL OUTPUTS:")
print("=" * 60)
print(f"  1. Keras model (backup): {BEST_MODEL_PATH}")
if has_onnx:
    print(f"  2. ONNX float32: {ONNX_FLOAT_PATH} ({os.path.getsize(ONNX_FLOAT_PATH)/(1024*1024):.1f} MB)")
else:
    sm_path = os.path.join(OUTPUT_DIR, 'hieroglyph_classifier_savedmodel')
    print(f"  2. SavedModel: {sm_path}")
if has_onnx_q:
    print(f"  3. ONNX uint8: {ONNX_UINT8_PATH} ({os.path.getsize(ONNX_UINT8_PATH)/(1024*1024):.1f} MB)")
else:
    print(f"  3. ONNX uint8: (not exported — convert locally)")
print(f"  4. Metadata: {METADATA_PATH}")
'''

nb['cells'][18]['source'] = NEW_HIERO_CELL18.split('\n')
# Fix: source lines should have \n except last
lines = NEW_HIERO_CELL18.split('\n')
nb['cells'][18]['source'] = [l + '\n' for l in lines[:-1]] + [lines[-1]]

with open(hiero_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("✅ Hieroglyph Cell 18 fixed")


# ── LANDMARK: Fix Cell 20 (Validate ONNX + Save Outputs) ──
land_path = 'planning/model-rebuild/notebooks/landmark/landmark_classifier.ipynb'
nb2 = json.load(open(land_path, encoding='utf-8'))

NEW_LAND_CELL20 = '''# ============================================================
# Validate ONNX + Save Outputs
# ============================================================
has_onnx = os.path.exists(ONNX_FLOAT_PATH)
has_onnx_q = os.path.exists(ONNX_UINT8_PATH)

if HAS_ORT and has_onnx:
    import onnxruntime as ort

    # Validate ONNX models
    onnx_files = [(ONNX_FLOAT_PATH, "float32")]
    if has_onnx_q:
        onnx_files.append((ONNX_UINT8_PATH, "uint8"))

    for onnx_path, label in onnx_files:
        sess = ort.InferenceSession(onnx_path)
        inp = sess.get_inputs()[0]
        out = sess.get_outputs()[0]
        print(f"\\n[{label}] ONNX validation:")
        print(f"  Input: name={inp.name}, shape={inp.shape}, type={inp.type}")
        print(f"  Output: name={out.name}, shape={out.shape}, type={out.type}")

        dummy = np.random.rand(1, IMAGE_SIZE, IMAGE_SIZE, 3).astype(np.float32)
        result = sess.run(None, {inp.name: dummy})
        probs = result[0]
        print(f"  Output shape: {probs.shape}, sum: {probs.sum():.4f}")
        assert probs.shape[-1] == NUM_CLASSES, f"Expected {NUM_CLASSES} classes, got {probs.shape[-1]}"
        print(f"  ✅ PASS")

    # Cross-validate Keras vs ONNX float32
    dummy = np.random.rand(1, IMAGE_SIZE, IMAGE_SIZE, 3).astype(np.float32)
    keras_out = model.predict(dummy, verbose=0)
    onnx_sess = ort.InferenceSession(ONNX_FLOAT_PATH)
    onnx_out = onnx_sess.run(None, {onnx_sess.get_inputs()[0].name: dummy})[0]
    max_diff = np.abs(keras_out - onnx_out).max()
    print(f"\\nKeras vs ONNX float32 max diff: {max_diff:.6f}")
    assert max_diff < 1e-4, f"ONNX output diverges from Keras: max_diff={max_diff}"
    print("✅ Keras and ONNX outputs match")
else:
    print("Skipping ONNX validation (ONNX not exported or onnxruntime not available)")

# Load landmark class names if available
landmark_meta_path = os.path.join(DATA_DIR, "tfrecord_log.json")
if os.path.exists(landmark_meta_path):
    with open(landmark_meta_path) as f:
        landmark_meta = json.load(f)
    print(f"Loaded landmark metadata")
else:
    landmark_meta = {}

# Determine export format
export_format = "onnx" if has_onnx else "savedmodel"

# Save output metadata
output_metadata = {
    "model_name": "wadjet_landmark_classifier_v2",
    "architecture": "EfficientNetV2B0",
    "input_size": IMAGE_SIZE,
    "num_classes": NUM_CLASSES,
    "format": export_format,
    "load_method": "ort.InferenceSession.create(url)" if has_onnx else "convert SavedModel to ONNX locally",
    "preprocessing": {
        "normalize": "divide_by_255",
        "input_range": [0.0, 1.0],
    },
    "training": {
        "precision": "float32",
        "loss": f"CategoricalFocalLoss(gamma={FOCAL_GAMMA})",
        "head_epochs": HEAD_EPOCHS,
        "finetune_epochs": FINETUNE_EPOCHS,
        "test_accuracy": float(test_acc),
    },
    "landmark_metadata": landmark_meta,
}

with open(METADATA_PATH, "w") as f:
    json.dump(output_metadata, f, indent=2)
print(f"Metadata saved to: {METADATA_PATH}")

# Save .keras backup
model.save(BEST_MODEL_PATH)
print(f"Keras model saved to: {BEST_MODEL_PATH}")

# Summary
print("\\n" + "=" * 60)
print("ALL OUTPUTS:")
print("=" * 60)
print(f"  1. Keras model: {BEST_MODEL_PATH}")
if has_onnx:
    print(f"  2. ONNX float32: {ONNX_FLOAT_PATH} ({os.path.getsize(ONNX_FLOAT_PATH)/(1024*1024):.1f} MB)")
else:
    sm_path = os.path.join(OUTPUT_DIR, 'landmark_classifier_savedmodel')
    print(f"  2. SavedModel: {sm_path}")
if has_onnx_q:
    print(f"  3. ONNX uint8: {ONNX_UINT8_PATH} ({os.path.getsize(ONNX_UINT8_PATH)/(1024*1024):.1f} MB)")
else:
    print(f"  3. ONNX uint8: (not exported — convert locally)")
print(f"  4. Metadata: {METADATA_PATH}")
'''

# Replace cell content
lines = NEW_LAND_CELL20.split('\n')
nb2['cells'][20]['source'] = [l + '\n' for l in lines[:-1]] + [lines[-1]]

with open(land_path, 'w', encoding='utf-8') as f:
    json.dump(nb2, f, indent=1, ensure_ascii=False)
print("✅ Landmark Cell 20 fixed")

# ── Verify both notebooks ──
for name, path in [
    ("HIEROGLYPH", hiero_path),
    ("LANDMARK", land_path),
]:
    nb = json.load(open(path, encoding='utf-8'))
    print(f"\n{name} ({len(nb['cells'])} cells):")
    for i, c in enumerate(nb['cells']):
        src = ''.join(c.get('source', []))
        title = ""
        for ln in src.split('\n'):
            ln = ln.strip()
            if ln.startswith('# ') and not ln.startswith('# ==='):
                title = ln
                break
        if not title:
            for ln in src.split('\n'):
                ln = ln.strip()
                if ln and not ln.startswith('#'):
                    title = ln[:60]
                    break
        print(f"  {i:2d}: {title}")
