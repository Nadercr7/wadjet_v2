"""Create a minimal test kernel and push it to verify Kaggle API works."""
import json
import os
import tempfile
from kaggle.api.kaggle_api_extended import KaggleApi

test_dir = os.path.join(tempfile.gettempdir(), "kaggle_push_test2")
os.makedirs(test_dir, exist_ok=True)

# Minimal valid ipynb
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        }
    },
    "cells": [
        {
            "cell_type": "code",
            "source": "print('hello from wadjet test kernel')",
            "metadata": {},
            "outputs": [],
            "execution_count": None,
            "id": "abc123"
        }
    ]
}

meta = {
    "id": "naderelakany/wadjet-test-push-002",
    "title": "Wadjet Test Push 002",
    "code_file": "test-notebook.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": False,
    "enable_internet": False,
    "dataset_sources": [],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": []
}

with open(os.path.join(test_dir, "test-notebook.ipynb"), "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

with open(os.path.join(test_dir, "kernel-metadata.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

print(f"Files in {test_dir}:")
for fn in os.listdir(test_dir):
    print(f"  {fn}")

# Push
api = KaggleApi()
api.authenticate()
print("\nPushing test kernel...")
result = api.kernels_push(test_dir)
error = getattr(result, "_error", None)
ref = getattr(result, "_ref", "")
ver = getattr(result, "_version_number", None)

if error:
    print(f"ERROR: {error}")
else:
    print(f"SUCCESS — ref={ref}, version={ver}")
