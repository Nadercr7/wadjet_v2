"""Debug: visualize what crops the pipeline actually processes."""
import cv2
import numpy as np
import os
from app.core.hieroglyph_pipeline import HieroglyphPipeline

pipeline = HieroglyphPipeline(enable_translation=False)

# Use a real detection image
img_path = "data/detection/downloads/mohiey/Heroglyphics_Signs/test/images/AAA-16-_jpg.rf.dcf5cc205f44e2b0e1209fd7607f561d.jpg"
image = cv2.imread(img_path)
print(f"Image: {image.shape}")

# Run detection
detections = pipeline._detect(image)
print(f"Detections: {len(detections)}")

# Save a few crops (raw vs padded) for debugging
out_dir = "tmp_debug_crops"
os.makedirs(out_dir, exist_ok=True)

size = 128
PAD_RATIO = 0.25
h, w = image.shape[:2]

for i, det in enumerate(detections[:6]):
    # Raw crop (old way)
    x1_raw = max(0, int(det.x1))
    y1_raw = max(0, int(det.y1))
    x2_raw = min(w, int(det.x2))
    y2_raw = min(h, int(det.y2))
    raw_crop = image[y1_raw:y2_raw, x1_raw:x2_raw]
    cv2.imwrite(os.path.join(out_dir, f"crop_{i}_raw.png"), raw_crop)
    
    # Expanded + letterboxed crop (new way)
    bw = det.x2 - det.x1
    bh = det.y2 - det.y1
    x1 = max(0, int(det.x1 - bw * PAD_RATIO))
    y1 = max(0, int(det.y1 - bh * PAD_RATIO))
    x2 = min(w, int(det.x2 + bw * PAD_RATIO))
    y2 = min(h, int(det.y2 + bh * PAD_RATIO))
    crop = image[y1:y2, x1:x2]
    
    # Letterbox
    ch, cw = crop.shape[:2]
    scale = size / max(ch, cw)
    nw_r, nh_r = int(cw * scale), int(ch * scale)
    resized = cv2.resize(crop, (nw_r, nh_r))
    canvas = np.full((size, size, 3), 128, dtype=np.uint8)
    yo = (size - nh_r) // 2
    xo = (size - nw_r) // 2
    canvas[yo:yo+nh_r, xo:xo+nw_r] = resized
    cv2.imwrite(os.path.join(out_dir, f"crop_{i}_padded.png"), canvas)
    
    print(f"  Det {i}: bbox=({x1_raw},{y1_raw},{x2_raw},{y2_raw}) conf={det.confidence:.2f}")

# Run classification
results = pipeline._classify_crops(image, detections[:6])
for i, r in enumerate(results):
    print(f"  Result {i}: {r.gardiner_code} conf={r.class_confidence:.1%}")

print(f"\nCrops saved to {out_dir}/")
