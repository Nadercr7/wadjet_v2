"""Quick test: POST /api/scan with a real image."""
import requests
import sys

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8766"
img_path = "data/detection/merged/images/test/hla_annotated_21.9.455_v2-BB-GC.jpg"

print(f"Testing {url}/api/scan ...")
with open(img_path, "rb") as f:
    r = requests.post(f"{url}/api/scan", files={"file": ("test.jpg", f, "image/jpeg")})

print(f"Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"Detections: {d.get('num_detections', 0)}")
    print(f"Glyphs: {len(d.get('glyphs', []))}")
    for g in d.get("glyphs", [])[:5]:
        print(f"  {g.get('gardiner_code')} det={g.get('detection_confidence',0):.3f} cls={g.get('class_confidence',0):.3f}")
    print(f"Gardiner: {d.get('gardiner_sequence', '')[:80]}")
    print(f"Direction: {d.get('reading_direction', '')}")
    t = d.get("timing", {})
    print(f"Timing: det={t.get('detection_ms',0):.0f}ms cls={t.get('classification_ms',0):.0f}ms total={t.get('total_ms',0):.0f}ms")
    print("SCAN API TEST PASSED")
else:
    print(f"ERROR: {r.text[:500]}")
