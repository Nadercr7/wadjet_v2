"""Push Kaggle kernels and monitor their execution.

Usage:
    python scripts/kaggle_push.py hieroglyph   # Push & run hieroglyph classifier
    python scripts/kaggle_push.py landmark      # Push & run landmark classifier
    python scripts/kaggle_push.py status        # Check status of both kernels
    python scripts/kaggle_push.py download      # Download outputs when complete
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_DIR = PROJECT_ROOT / "planning" / "model-rebuild" / "notebooks"

KERNELS = {
    "hieroglyph": {
        "dir": NOTEBOOK_DIR / "hieroglyph",
        "ref": "nadermohamedcr7/wadjet-v2-hieroglyph-onnx",
        "output_dir": PROJECT_ROOT / "models" / "hieroglyph" / "classifier",
        "expected_files": [
            "hieroglyph_classifier_uint8.onnx",
            "hieroglyph_classifier.onnx",
            "model_metadata.json",
        ],
    },
    "landmark": {
        "dir": NOTEBOOK_DIR / "landmark",
        "ref": "nadermohamedcr7/wadjet-v2-landmark-onnx",
        "output_dir": PROJECT_ROOT / "models" / "landmark" / "onnx",
        "expected_files": [
            "landmark_classifier_uint8.onnx",
            "landmark_classifier.onnx",
            "model_metadata.json",
        ],
    },
}


def get_api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    return api


def push_kernel(name: str):
    """Push a kernel to Kaggle and trigger execution."""
    kernel = KERNELS[name]
    kernel_dir = str(kernel["dir"])
    print(f"\n{'='*60}")
    print(f"Pushing kernel: {name}")
    print(f"Directory: {kernel_dir}")
    print(f"{'='*60}")

    api = get_api()
    api.kernels_push(kernel_dir)
    print(f"\n✅ Kernel pushed: {kernel['ref']}")
    print(f"   View at: https://www.kaggle.com/code/{kernel['ref']}")
    print(f"\n   Run `python scripts/kaggle_push.py status` to check progress.")


def check_status():
    """Check the status of both kernels."""
    api = get_api()
    print(f"\n{'='*60}")
    print("Kernel Status")
    print(f"{'='*60}")

    for name, kernel in KERNELS.items():
        ref = kernel["ref"]
        try:
            status = api.kernels_status(ref)
            state = status.get("status", "unknown") if isinstance(status, dict) else getattr(status, "status", str(status))
            print(f"\n  {name}: {state}")
            print(f"    Ref: {ref}")
            if isinstance(status, dict):
                if status.get("failureMessage"):
                    print(f"    Error: {status['failureMessage']}")
            else:
                failure = getattr(status, "failureMessage", None)
                if failure:
                    print(f"    Error: {failure}")
        except Exception as e:
            print(f"\n  {name}: Error checking status — {e}")


def download_outputs(name: str | None = None):
    """Download kernel outputs and copy to model directories."""
    api = get_api()
    names = [name] if name else list(KERNELS.keys())

    for n in names:
        kernel = KERNELS[n]
        ref = kernel["ref"]
        output_dir = kernel["output_dir"]
        tmp_dir = PROJECT_ROOT / "tmp_kaggle_output" / n

        print(f"\n{'='*60}")
        print(f"Downloading outputs: {n}")
        print(f"{'='*60}")

        # Download to temp dir
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            api.kernels_output(ref, path=str(tmp_dir))
        except Exception as e:
            print(f"  ❌ Download failed: {e}")
            continue

        # List downloaded files
        downloaded = list(tmp_dir.iterdir())
        print(f"  Downloaded {len(downloaded)} files:")
        for f in downloaded:
            size_kb = f.stat().st_size / 1024
            print(f"    {f.name} ({size_kb:.0f} KB)")

        # Copy to model directory
        output_dir.mkdir(parents=True, exist_ok=True)
        for expected_file in kernel["expected_files"]:
            src = tmp_dir / expected_file
            dst = output_dir / expected_file
            if src.exists():
                shutil.copy2(src, dst)
                print(f"  ✅ Copied: {expected_file} → {output_dir.relative_to(PROJECT_ROOT)}/")
            else:
                print(f"  ⚠️  Missing: {expected_file}")

        # Cleanup temp
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Cleanup parent tmp dir if empty
    tmp_parent = PROJECT_ROOT / "tmp_kaggle_output"
    if tmp_parent.exists() and not any(tmp_parent.iterdir()):
        tmp_parent.rmdir()

    print(f"\n✅ Done. Models are in their deployment directories.")


def poll_until_complete(name: str, interval: int = 60, timeout: int = 3600):
    """Poll kernel status until completion."""
    api = get_api()
    kernel = KERNELS[name]
    ref = kernel["ref"]
    start = time.time()

    print(f"\nPolling {ref} every {interval}s (timeout: {timeout}s)...")
    while time.time() - start < timeout:
        try:
            status = api.kernels_status(ref)
            state = status.get("status", "unknown") if isinstance(status, dict) else getattr(status, "status", str(status))
        except Exception as e:
            print(f"  [{int(time.time()-start)}s] Error: {e}")
            time.sleep(interval)
            continue

        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] Status: {state}")

        if state in ("complete", "error", "cancelAcknowledged"):
            if state == "complete":
                print(f"\n✅ Kernel completed! Downloading outputs...")
                download_outputs(name)
            else:
                failure = ""
                if isinstance(status, dict):
                    failure = status.get("failureMessage", "")
                else:
                    failure = getattr(status, "failureMessage", "")
                print(f"\n❌ Kernel failed: {failure}")
            return state

        time.sleep(interval)

    print(f"\n⚠️  Timeout after {timeout}s. Check status manually.")
    return "timeout"


def main():
    parser = argparse.ArgumentParser(description="Kaggle kernel manager for Wadjet v2")
    parser.add_argument("action", choices=["hieroglyph", "landmark", "status", "download", "poll"],
                        help="Action to perform")
    parser.add_argument("--name", choices=["hieroglyph", "landmark"],
                        help="Kernel name (for download/poll)")
    parser.add_argument("--interval", type=int, default=60,
                        help="Poll interval in seconds")
    parser.add_argument("--timeout", type=int, default=3600,
                        help="Poll timeout in seconds")
    args = parser.parse_args()

    if args.action in ("hieroglyph", "landmark"):
        push_kernel(args.action)
    elif args.action == "status":
        check_status()
    elif args.action == "download":
        download_outputs(args.name)
    elif args.action == "poll":
        if not args.name:
            parser.error("--name required for poll action")
        poll_until_complete(args.name, args.interval, args.timeout)


if __name__ == "__main__":
    main()
