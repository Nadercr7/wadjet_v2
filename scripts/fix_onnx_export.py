"""
Rewrite cell 13 (ONNX export) in both notebooks:
- Use dynamo=False for legacy exporter (keeps weights internal, no .onnx.data)
- opset_version=18 (PyTorch 2.10 minimum, avoids broken version conversion)
"""
import json

HIERO = r"planning\model-rebuild\pytorch\hieroglyph\hieroglyph_classifier.ipynb"
LAND  = r"planning\model-rebuild\pytorch\landmark\landmark_classifier.ipynb"

HIERO_CELL13 = [
    '# ── ONNX Export (float32, NCHW, opset 18) ────────────────────────\n',
    'model.eval()\n',
    'model.to("cpu")\n',
    '\n',
    'dummy = torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE)\n',
    'onnx_fp32_path = os.path.join(OUT_DIR, "hieroglyph_classifier.onnx")\n',
    '\n',
    '# Export with opset 18 (PyTorch 2.10 minimum)\n',
    '# dynamo=False → legacy exporter, keeps weights internal (no .onnx.data file)\n',
    'torch.onnx.export(\n',
    '    model.model, dummy, onnx_fp32_path,\n',
    '    opset_version=18,\n',
    '    input_names=["input"],\n',
    '    output_names=["output"],\n',
    '    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},\n',
    '    dynamo=False,\n',
    ')\n',
    '\n',
    'size_mb = os.path.getsize(onnx_fp32_path) / 1e6\n',
    'print(f"ONNX fp32 exported: {onnx_fp32_path}")\n',
    'print(f"Size: {size_mb:.1f} MB")',
]

LAND_CELL13 = [
    '# ── ONNX Export (float32, NCHW, opset 18) ────────────────────────\n',
    'model.eval()\n',
    'model.to("cpu")\n',
    '\n',
    'dummy = torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE)\n',
    'onnx_fp32_path = os.path.join(OUT_DIR, "landmark_classifier.onnx")\n',
    '\n',
    '# Export with opset 18 (PyTorch 2.10 minimum)\n',
    '# dynamo=False → legacy exporter, keeps weights internal (no .onnx.data file)\n',
    'torch.onnx.export(\n',
    '    model.model, dummy, onnx_fp32_path,\n',
    '    opset_version=18,\n',
    '    input_names=["input"],\n',
    '    output_names=["output"],\n',
    '    dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},\n',
    '    dynamo=False,\n',
    ')\n',
    '\n',
    'size_mb = os.path.getsize(onnx_fp32_path) / 1e6\n',
    'print(f"ONNX fp32 exported: {onnx_fp32_path}")\n',
    'print(f"Size: {size_mb:.1f} MB")',
]

for path, cell13, label in [
    (HIERO, HIERO_CELL13, "HIEROGLYPH"),
    (LAND, LAND_CELL13, "LANDMARK"),
]:
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    nb["cells"][13]["source"] = cell13
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"{label}: Cell 13 rewritten (dynamo=False, opset 18)")

print("Done!")
