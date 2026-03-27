"""Quick status check."""
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()
for ref in ["nadermohamedcr7/wadjet-v2-hieroglyph-onnx", "nadermohamedcr7/wadjet-v2-landmark-onnx"]:
    s = api.kernels_status(ref)
    state = str(s.get("status") if isinstance(s, dict) else getattr(s, "status", s))
    fail = s.get("failureMessage") if isinstance(s, dict) else getattr(s, "failureMessage", None)
    name = ref.split("/")[-1]
    msg = f"{name}: {state}"
    if fail:
        msg += f" | FAIL={fail}"
    print(msg)
