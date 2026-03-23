"""
Fix the KeepAliveCallback placement — it was inserted outside the callbacks list.
Needs to be INSIDE callbacks=[...] before the closing ].
"""
import json

HIERO_NB = r"planning\model-rebuild\pytorch\hieroglyph\hieroglyph_classifier.ipynb"
LAND_NB  = r"planning\model-rebuild\pytorch\landmark\landmark_classifier.ipynb"


def fix_notebook(path):
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    for cell_idx in [10, 11]:
        cell_src = nb["cells"][cell_idx]["source"]
        cell_text = "".join(cell_src)

        if "KeepAliveCallback()" not in cell_text:
            print(f"  Cell {cell_idx}: No KeepAliveCallback() found, skipping")
            continue

        # Remove the wrongly-placed line and re-insert inside the callbacks list
        new_src = []
        removed = False
        for line in cell_src:
            stripped = line.strip()
            # Skip the wrongly-placed KeepAliveCallback() line
            if stripped == "KeepAliveCallback()," and not removed:
                removed = True
                continue
            new_src.append(line)

        if not removed:
            print(f"  Cell {cell_idx}: WARNING — could not find wrongly-placed KeepAliveCallback()")
            continue

        # Now insert KeepAliveCallback() inside the callbacks list
        # Find the "]," that closes the callbacks list (it's right before "logger=False")
        final_src = []
        inserted = False
        for i, line in enumerate(new_src):
            # Look for the "]," line that's followed by "logger=False"
            if not inserted and line.strip() == "]," :
                # Check if the next non-empty line contains "logger=False"
                next_lines = [l for l in new_src[i+1:] if l.strip()]
                if next_lines and "logger=False" in next_lines[0]:
                    # Insert KeepAliveCallback() before the closing ]
                    final_src.append("        KeepAliveCallback(),\n")
                    inserted = True
            final_src.append(line)

        if inserted:
            nb["cells"][cell_idx]["source"] = final_src
            print(f"  Cell {cell_idx}: Fixed KeepAliveCallback() placement (inside callbacks list)")
        else:
            print(f"  Cell {cell_idx}: WARNING — could not find callbacks closing bracket!")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"  Written: {path}")


print("=== Fixing hieroglyph notebook ===")
fix_notebook(HIERO_NB)

print("\n=== Fixing landmark notebook ===")
fix_notebook(LAND_NB)

print("\nDone!")
