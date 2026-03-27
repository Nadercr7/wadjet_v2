"""Quick analysis of CLIP scores for flagged images."""
import json
import statistics

scores = json.load(open("data/detection/merged/clip_scores.json", encoding="utf-8"))
flagged = [(k, v) for k, v in scores.items() if not v["keep"]]
flagged.sort(key=lambda x: x[1]["pos"])

print(f"Total flagged: {len(flagged)}")
print()
print("=== WORST 20 (lowest positive score) ===")
for name, s in flagged[:20]:
    print(f"  pos={s['pos']:.3f} neg={s['neg']:.3f} | {name[:80]}")

print()
print("=== BORDERLINE 20 (highest pos among flagged) ===")
for name, s in flagged[-20:]:
    print(f"  pos={s['pos']:.3f} neg={s['neg']:.3f} | {name[:80]}")

pos_scores = [v["pos"] for _, v in flagged]
print(f"\nFlagged pos score stats: min={min(pos_scores):.3f} max={max(pos_scores):.3f} "
      f"median={statistics.median(pos_scores):.3f} mean={statistics.mean(pos_scores):.3f}")

very_low = sum(1 for p in pos_scores if p < 0.10)
low = sum(1 for p in pos_scores if 0.10 <= p < 0.15)
borderline = sum(1 for p in pos_scores if 0.15 <= p < 0.18)
print(f"Very low (<0.10): {very_low}")
print(f"Low (0.10-0.15): {low}")
print(f"Borderline (0.15-0.18): {borderline}")
