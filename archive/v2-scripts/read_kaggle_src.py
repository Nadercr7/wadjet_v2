"""Read Kaggle API source for kernels_push."""
import inspect
from kaggle.api.kaggle_api_extended import KaggleApi

src = inspect.getsource(KaggleApi.kernels_push)
lines = src.split('\n')
for i, line in enumerate(lines[120:200], 121):
    print(f"{i:3d}: {line}")
