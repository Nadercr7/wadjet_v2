"""Check if flagged images have bounding box annotations."""
import json
from pathlib import Path

dataset = Path("data/detection/merged")
scores = json.load(open(dataset / "clip_scores.json", encoding="utf-8"))

flagged = [(k, v) for k, v in scores.items() if not v["keep"]]
flagged.sort(key=lambda x: x[1]["pos"])

has_boxes = 0
empty_label = 0
no_label = 0
box_counts = []

for name, s in flagged:
    split = s["split"]
    stem = Path(name).stem
    lbl = dataset / "labels" / split / (stem + ".txt")
    if lbl.exists():
        content = lbl.read_text().strip()
        if content:
            n_boxes = len(content.split("\n"))
            has_boxes += 1
            box_counts.append(n_boxes)
        else:
            empty_label += 1
    else:
        no_label += 1

print(f"Flagged images: {len(flagged)}")
print(f"  With boxes: {has_boxes} (avg {sum(box_counts)/max(1,len(box_counts)):.1f} boxes)")
print(f"  Empty label: {empty_label}")
print(f"  No label file: {no_label}")
print()

# Break down by pos score range
for lo, hi, label in [(0, 0.05, "<0.05"), (0.05, 0.10, "0.05-0.10"), (0.10, 0.15, "0.10-0.15"), (0.15, 0.18, "0.15-0.18")]:
    subset = [(k, v) for k, v in flagged if lo <= v["pos"] < hi]
    with_boxes = 0
    for name, s in subset:
        stem = Path(name).stem
        lbl = dataset / "labels" / s["split"] / (stem + ".txt")
        if lbl.exists() and lbl.read_text().strip():
            with_boxes += 1
    print(f"  {label}: {len(subset)} flagged, {with_boxes} have boxes ({100*with_boxes/max(1,len(subset)):.0f}%)")
