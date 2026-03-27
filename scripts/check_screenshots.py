"""Check Screen-Shot images in CLIP scores."""
import json
from pathlib import Path

scores = json.load(open("data/detection/merged/clip_scores.json", encoding="utf-8"))

ss = {k: v for k, v in scores.items() if "Screen-Shot" in k}
ss_flagged = sum(1 for v in ss.values() if not v["keep"])
ss_kept = sum(1 for v in ss.values() if v["keep"])
print(f"Screen-Shot images in CLIP scores: {len(ss)}")
print(f"  Already flagged: {ss_flagged}")
print(f"  Currently kept: {ss_kept}")

if ss_kept:
    print()
    for k, v in sorted(ss.items(), key=lambda x: -x[1]["pos"]):
        if v["keep"]:
            print(f"  KEPT: pos={v['pos']:.3f} neg={v['neg']:.3f} | {k[:80]}")
