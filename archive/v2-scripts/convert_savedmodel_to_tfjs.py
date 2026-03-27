"""Convert SavedModel to TF.js Graph Model format with uint8 quantization.

Strategy: Pre-seed sys.modules with dummy modules for ALL broken transitive
dependencies so Python never touches the real (broken) packages on disk.
"""
import os
import sys
import types

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# ---------------------------------------------------------------------------
# 1. Build a dummy module that absorbs any attribute access
# ---------------------------------------------------------------------------
class _Dummy(types.ModuleType):
    def __init__(self, name="dummy"):
        super().__init__(name)
        self.__path__ = []          # pretend to be a package
        self.__file__ = "<dummy>"
    def __getattr__(self, name):
        child = _Dummy(f"{self.__name__}.{name}")
        setattr(self, name, child)  # cache for repeated access
        return child
    def __call__(self, *a, **kw):
        return _Dummy()
    def __iter__(self):
        return iter([])
    def __bool__(self):
        return False

# ---------------------------------------------------------------------------
# 2. Pre-seed sys.modules for ALL broken dependency trees
#    This must happen BEFORE any import that could pull them in.
# ---------------------------------------------------------------------------
_BLOCKED_TOP = [
    'tensorflow_decision_forests',
    'yggdrasil_decision_forests',
    'jax',
    'jaxlib',
    'flax',
]

# Pre-seed the top-level module and common submodules
for top in _BLOCKED_TOP:
    d = _Dummy(top)
    sys.modules[top] = d
    # Cover 3 nesting levels of submodule access
    for sub in ['keras', 'core', 'component', 'inspector', 'py_tree',
                'condition', 'dataspec', 'dataset', 'data_spec_pb2',
                'experimental', 'jax2tf', 'interpreters', 'xla_bridge',
                '__init__']:
        key = f"{top}.{sub}"
        if key not in sys.modules:
            sys.modules[key] = _Dummy(key)

# Also cover deep chains seen in tracebacks
_DEEP = [
    'tensorflow_decision_forests.keras',
    'tensorflow_decision_forests.keras.core',
    'tensorflow_decision_forests.component',
    'tensorflow_decision_forests.component.inspector',
    'tensorflow_decision_forests.component.inspector.inspector',
    'tensorflow_decision_forests.component.py_tree',
    'tensorflow_decision_forests.component.py_tree.condition',
    'tensorflow_decision_forests.component.py_tree.dataspec',
    'yggdrasil_decision_forests.dataset',
    'yggdrasil_decision_forests.dataset.data_spec_pb2',
    'jax.experimental',
    'jax.experimental.jax2tf',
]
for m in _DEEP:
    if m not in sys.modules:
        sys.modules[m] = _Dummy(m)

# ---------------------------------------------------------------------------
# 3. Meta-path finder as fallback for any submodule we missed
# ---------------------------------------------------------------------------
class _BlockingFinder:
    _PREFIXES = tuple(p + '.' for p in _BLOCKED_TOP)
    _TOPS = set(_BLOCKED_TOP)

    def find_module(self, fullname, path=None):
        if fullname in self._TOPS:
            return self
        for pfx in self._PREFIXES:
            if fullname.startswith(pfx):
                return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        mod = _Dummy(fullname)
        sys.modules[fullname] = mod
        return mod

sys.meta_path.insert(0, _BlockingFinder())

# ---------------------------------------------------------------------------
# 4. Now safe to import tensorflowjs
# ---------------------------------------------------------------------------
from tensorflowjs.converters import converter

input_dir = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\saved_model"

# ── Convert with float16 quantization (like V1 used) ──
output_f16 = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs_f16"
import shutil
if os.path.exists(output_f16):
    shutil.rmtree(output_f16)
os.makedirs(output_f16, exist_ok=True)

print("Converting SavedModel → TF.js Graph Model (float16) ...")
converter.convert([
    "--input_format=tf_saved_model",
    "--output_format=tfjs_graph_model",
    "--quantize_float16",
    "--signature_name=serving_default",
    input_dir,
    output_f16,
])
print("float16 conversion complete!")
for f in sorted(os.listdir(output_f16)):
    size = os.path.getsize(os.path.join(output_f16, f))
    print(f"  {f}: {size / 1024:.0f} KB")

# ── Convert with NO quantization (float32, largest but most compatible) ──
output_f32 = r"D:\Personal attachements\Projects\Final_Horus\Wadjet-v2\models\landmark\tfjs_f32"
if os.path.exists(output_f32):
    shutil.rmtree(output_f32)
os.makedirs(output_f32, exist_ok=True)

print("\nConverting SavedModel → TF.js Graph Model (float32, no quantization) ...")
converter.convert([
    "--input_format=tf_saved_model",
    "--output_format=tfjs_graph_model",
    "--signature_name=serving_default",
    input_dir,
    output_f32,
])
print("float32 conversion complete!")
for f in sorted(os.listdir(output_f32)):
    size = os.path.getsize(os.path.join(output_f32, f))
    print(f"  {f}: {size / 1024:.0f} KB")
