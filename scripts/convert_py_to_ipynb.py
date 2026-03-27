"""Convert percent-format .py scripts to Jupyter .ipynb notebooks."""

import json
import re
import sys
from pathlib import Path


def py_to_ipynb(py_path: str, ipynb_path: str) -> None:
    with open(py_path, "r", encoding="utf-8") as f:
        content = f.read()

    cells = []

    # Split on '# %%' markers
    parts = re.split(r"\n# %%", content)

    # First part is usually a module docstring
    first = parts[0].strip()
    if first.startswith('r"""') or first.startswith('"""'):
        # Extract docstring as markdown
        doc = first.lstrip("r").strip('"').strip()
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in doc.split("\n")],
        })
        parts = parts[1:]
    elif first:
        cells.append({
            "cell_type": "code",
            "metadata": {},
            "source": [line + "\n" for line in first.split("\n")],
            "outputs": [],
            "execution_count": None,
        })
        parts = parts[1:]

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith("[markdown]"):
            md_content = part[len("[markdown]"):].strip()
            lines = []
            for line in md_content.split("\n"):
                # Remove leading '# ' that jupytext uses for markdown
                if line.startswith("# "):
                    lines.append(line[2:])
                elif line == "#":
                    lines.append("")
                else:
                    lines.append(line)
            cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": [line + "\n" for line in lines],
            })
        else:
            source_lines = part.split("\n")
            # Uncomment pip installs
            final_lines = []
            for line in source_lines:
                if line.startswith("# !pip"):
                    final_lines.append(line[2:])
                else:
                    final_lines.append(line)

            cells.append({
                "cell_type": "code",
                "metadata": {},
                "source": [line + "\n" for line in final_lines],
                "outputs": [],
                "execution_count": None,
            })

    # Fix: remove trailing newline from last line of each cell
    for cell in cells:
        if cell["source"]:
            cell["source"][-1] = cell["source"][-1].rstrip("\n")

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12.0",
            },
        },
        "cells": cells,
    }

    with open(ipynb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)

    n_code = sum(1 for c in cells if c["cell_type"] == "code")
    n_md = sum(1 for c in cells if c["cell_type"] == "markdown")
    print(f"Converted: {py_path} -> {ipynb_path}")
    print(f"  {len(cells)} cells ({n_code} code, {n_md} markdown)")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent

    # Detector v3
    py_to_ipynb(
        str(root / "planning/model-rebuild/pytorch/detector/hieroglyph_detector_v3.py"),
        str(root / "planning/model-rebuild/pytorch/detector/hieroglyph_detector_v3.ipynb"),
    )

    # Classifier v2
    py_to_ipynb(
        str(root / "planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier_v2.py"),
        str(root / "planning/model-rebuild/pytorch/hieroglyph/hieroglyph_classifier_v2.ipynb"),
    )
