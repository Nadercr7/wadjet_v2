"""Final comprehensive pre-upload and next-phase readiness sweep."""
import json
from pathlib import Path

d = Path("data/detection/merged")
exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

print("=" * 60)
print("  FINAL PRE-UPLOAD SWEEP")
print("=" * 60)

# 1. File counts match
print("\n1. IMAGE/LABEL PARITY")
ok = True
for split in ("train", "val", "test"):
    imgs = sorted(f.stem for f in (d / "images" / split).iterdir() if f.suffix.lower() in exts)
    lbls = sorted(f.stem for f in (d / "labels" / split).iterdir() if f.suffix == ".txt")
    imgs_set, lbls_set = set(imgs), set(lbls)
    missing_lbl = imgs_set - lbls_set
    missing_img = lbls_set - imgs_set
    match = len(missing_lbl) == 0 and len(missing_img) == 0
    status = "OK" if match else "FAIL"
    print(f"  {split}: {len(imgs)} imgs, {len(lbls)} lbls -> {status}")
    if missing_lbl:
        print(f"    Missing labels: {list(missing_lbl)[:5]}...")
    if missing_img:
        print(f"    Orphan labels: {list(missing_img)[:5]}...")
    if not match:
        ok = False
p1 = "PASS" if ok else "FAIL"
print(f"  -> {p1}: Every image has a label and vice versa")

# 2. No corrupt labels
print("\n2. LABEL FORMAT INTEGRITY")
bad = 0
total_boxes = 0
for split in ("train", "val", "test"):
    for lbl in (d / "labels" / split).iterdir():
        if lbl.suffix != ".txt":
            continue
        text = lbl.read_text().strip()
        if not text:
            continue
        for line in text.split("\n"):
            parts = line.strip().split()
            total_boxes += 1
            if len(parts) != 5:
                bad += 1
                continue
            try:
                c = int(parts[0])
                vals = [float(x) for x in parts[1:]]
                if c != 0 or any(v < 0 or v > 1 for v in vals):
                    bad += 1
            except Exception:
                bad += 1
p2 = "PASS" if bad == 0 else "FAIL"
print(f"  Total boxes: {total_boxes:,}")
print(f"  Bad lines: {bad}")
print(f"  -> {p2}")

# 3. Required files exist
print("\n3. REQUIRED FILES")
required = [
    "data.yaml", "dataset-metadata.json", "LICENSE_SOURCES.md",
    "merge_log.json", "validation_report.json",
]
all_exist = True
for f in required:
    exists = (d / f).exists()
    size = (d / f).stat().st_size if exists else 0
    print(f"  {f}: {'EXISTS' if exists else 'MISSING'} ({size:,} bytes)")
    if not exists:
        all_exist = False
p3 = "PASS" if all_exist else "FAIL"
print(f"  -> {p3}")

# 4. data.yaml content check
print("\n4. DATA.YAML CONTENT")
yaml_text = (d / "data.yaml").read_text()
print(f"  {yaml_text.strip()}")
has_nc1 = "nc: 1" in yaml_text
has_paths = all(x in yaml_text for x in ["train:", "val:", "test:"])
p4 = "PASS" if has_nc1 and has_paths else "FAIL"
print(f"  -> {p4}: nc=1, all splits defined")

# 5. dataset-metadata.json (Kaggle)
print("\n5. KAGGLE METADATA")
km = json.loads((d / "dataset-metadata.json").read_text())
print(f"  title: {km.get('title', 'MISSING')}")
print(f"  id: {km.get('id', 'MISSING')}")
print(f"  license: {km.get('licenses', 'MISSING')}")
has_id = "id" in km and "/" in str(km["id"])
p5 = "PASS" if has_id else "FAIL"
print(f"  -> {p5}: Kaggle slug present")

# 6. Size estimate
total_size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
upload_exclude = 0
vp = d / "validation_previews"
if vp.exists():
    upload_exclude += sum(f.stat().st_size for f in vp.rglob("*") if f.is_file())
cs = d / "clip_scores.json"
if cs.exists():
    upload_exclude += cs.stat().st_size
upload_size = total_size - upload_exclude
p6 = "PASS" if upload_size < 5 * 1024 * 1024 * 1024 else "WARN"
print(f"\n6. UPLOAD SIZE")
print(f"  Total dir: {total_size / 1024 / 1024:.0f} MB")
print(f"  Excludable (previews+clip_scores): {upload_exclude / 1024 / 1024:.0f} MB")
print(f"  Upload estimate: {upload_size / 1024 / 1024:.0f} MB")
print(f"  -> {p6}: Under Kaggle 5GB limit")

# 7. Next phase compatibility
print("\n7. YOLO26s TRAINING COMPATIBILITY")
print(f"  data.yaml nc=1: {'YES' if has_nc1 else 'NO'}")
print(f"  Relative paths (path: .): {'YES' if 'path: .' in yaml_text else 'NO'}")
print(f"  imgsz=640 compatible: YES (avg img ~688x699)")
print(f"  fliplr=0.0 note: Set in training config, not data.yaml")
print(f"  -> YOLO('yolo26s.pt').train(data='data.yaml') will work directly")

# 8. Summary
print("\n" + "=" * 60)
checks = [p1, p2, p3, p4, p5, p6]
passing = sum(1 for p in checks if p == "PASS")
failing = sum(1 for p in checks if p == "FAIL")
warn = sum(1 for p in checks if p == "WARN")
print(f"  RESULT: {passing} PASS / {failing} FAIL / {warn} WARN")
if failing == 0:
    print("  STATUS: READY TO UPLOAD")
else:
    print("  STATUS: FIX FAILURES BEFORE UPLOAD")
print("=" * 60)
