"""Poll both Kaggle kernels until completion."""
import time
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

KERNELS = [
    "nadermohamedcr7/wadjet-v2-hieroglyph-onnx",
    "nadermohamedcr7/wadjet-v2-landmark-onnx",
]

POLL_INTERVAL = 60  # seconds
MAX_WAIT = 7200     # 2 hours

start = time.time()
completed = set()

print(f"Polling every {POLL_INTERVAL}s (max {MAX_WAIT//60} min)...\n")

while time.time() - start < MAX_WAIT:
    elapsed = int(time.time() - start)
    all_done = True

    for ref in KERNELS:
        if ref in completed:
            continue
        try:
            status = api.kernels_status(ref)
            state = str(status.get("status") if isinstance(status, dict) else getattr(status, "status", status))
            fail = (status.get("failureMessage") if isinstance(status, dict) else getattr(status, "failureMessage", None))
        except Exception as e:
            state = f"ERROR: {e}"
            fail = None

        mins = elapsed // 60
        secs = elapsed % 60
        print(f"  [{mins:02d}:{secs:02d}] {ref.split('/')[-1]}: {state}")

        if "COMPLETE" in state.upper():
            completed.add(ref)
            print(f"    => DONE!")
        elif "ERROR" in state.upper() or "CANCEL" in state.upper():
            print(f"    => FAILED: {fail}")
            completed.add(ref)
        else:
            all_done = False

    if all_done or len(completed) == len(KERNELS):
        break

    print(f"  Waiting {POLL_INTERVAL}s...\n")
    time.sleep(POLL_INTERVAL)

elapsed = int(time.time() - start)
print(f"\nDone polling after {elapsed//60}m {elapsed%60}s")
print(f"Completed: {len(completed)}/{len(KERNELS)}")

if len(completed) == len(KERNELS):
    print("\nAll kernels finished! Run: python scripts/kaggle_push.py download")
