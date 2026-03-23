"""
Fix Kaggle/papermill IOPub timeout by adding a KeepAliveCallback
that prints dots every 10 batches, preventing the 4-second IOPub
timeout from killing long-running training cells.

Applied to BOTH hieroglyph and landmark notebooks.
"""
import json
import copy

HIERO_NB = r"planning\model-rebuild\pytorch\hieroglyph\hieroglyph_classifier.ipynb"
LAND_NB  = r"planning\model-rebuild\pytorch\landmark\landmark_classifier.ipynb"

# ── KeepAliveCallback definition (appended to cell 9) ──
KEEPALIVE_CALLBACK = '''

# Prevent Kaggle/papermill IOPub timeout (4s) during long training
class KeepAliveCallback(L.Callback):
    """Prints dots every N batches to keep IOPub alive."""
    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        if batch_idx % 10 == 0:
            print(".", end="", flush=True)
    def on_validation_end(self, trainer, pl_module):
        metrics = trainer.callback_metrics
        acc = metrics.get("val_acc", 0)
        print(f" val_acc={acc:.4f}", flush=True)

print("KeepAliveCallback defined")'''


def fix_notebook(path):
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # ── Cell 9: Append KeepAliveCallback class definition ──
    cell9_src = nb["cells"][9]["source"]
    # Check if already has KeepAliveCallback
    cell9_text = "".join(cell9_src)
    if "KeepAliveCallback" in cell9_text:
        print(f"  Cell 9: KeepAliveCallback already present, skipping")
    else:
        # Append the callback definition as new lines
        new_lines = KEEPALIVE_CALLBACK.split("\n")
        for i, line in enumerate(new_lines):
            if i < len(new_lines) - 1:
                cell9_src.append(line + "\n")
            else:
                cell9_src.append(line)  # Last line no trailing newline
        nb["cells"][9]["source"] = cell9_src
        print(f"  Cell 9: Added KeepAliveCallback class")

    # ── Cells 10 & 11: Add KeepAliveCallback() to callbacks list ──
    for cell_idx in [10, 11]:
        cell_src = nb["cells"][cell_idx]["source"]
        cell_text = "".join(cell_src)

        if "KeepAliveCallback()" in cell_text:
            print(f"  Cell {cell_idx}: KeepAliveCallback() already in callbacks, skipping")
            continue

        # Find the line with "logger=False," and insert KeepAliveCallback before it
        # Or find the callbacks list and add to it
        new_src = []
        added = False
        for line in cell_src:
            # Add KeepAliveCallback() right before the closing ] of callbacks
            # Strategy: find "logger=False" line, insert KeepAliveCallback before it
            if not added and "logger=False" in line:
                # Insert KeepAliveCallback() callback line before logger=False
                new_src.append("        KeepAliveCallback(),\n")
                added = True
            new_src.append(line)

        if added:
            nb["cells"][cell_idx]["source"] = new_src
            print(f"  Cell {cell_idx}: Added KeepAliveCallback() to callbacks")
        else:
            print(f"  Cell {cell_idx}: WARNING — could not find insertion point!")

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"  Written: {path}")


print("=== Fixing hieroglyph notebook ===")
fix_notebook(HIERO_NB)

print("\n=== Fixing landmark notebook ===")
fix_notebook(LAND_NB)

print("\nDone!")
