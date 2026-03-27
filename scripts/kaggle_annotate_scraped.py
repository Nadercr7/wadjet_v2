r"""Annotate scraped museum images with GroundingDINO on Kaggle GPU.

Upload the scraped images as a Kaggle dataset, then run this notebook.
It annotates with GDino on GPU (~2-5s/image instead of 65s on CPU),
saves YOLO labels, and outputs a zip to download.

Setup on Kaggle:
  - GPU T4 x2
  - Internet ON (for model download)
  - Dataset: upload data/detection/scraped/ as "wadjet-scraped-images"
"""
# %% [markdown]
# # Wadjet — GroundingDINO Auto-Annotation
# Annotate 459 scraped museum images (Met + Wikimedia) with GroundingDINO on GPU.

# %% Cell 1: Install dependencies
# !pip install -q transformers torch torchvision Pillow opencv-python-headless numpy

# %% Cell 2: Imports and config
import json
import shutil
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

# ── Config ──
MODEL_ID = "IDEA-Research/grounding-dino-base"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

# Detection settings
BOX_THRESHOLD = 0.20
TEXT_THRESHOLD = 0.15
PROMPTS = ["hieroglyph", "Egyptian hieroglyphic sign", "carved symbol on stone"]

# Size filters
MIN_BOX_FRAC = 0.008
MAX_BOX_FRAC = 0.60

# Paths — adjust if Kaggle dataset name differs
INPUT_MET = Path("/kaggle/input/wadjet-scraped-images/met/images")
INPUT_WIKI = Path("/kaggle/input/wadjet-scraped-images/wikimedia/images")
OUTPUT_DIR = Path("/kaggle/working/scraped_annotated")

print(f"Device: {DEVICE}")
print(f"PyTorch: {torch.__version__}")

# %% Cell 3: Load model
print(f"Loading {MODEL_ID}...")
t0 = time.time()
processor = AutoProcessor.from_pretrained(MODEL_ID)
model = AutoModelForZeroShotObjectDetection.from_pretrained(MODEL_ID).to(DEVICE)
model.eval()
print(f"Model loaded in {time.time() - t0:.1f}s")


# %% Cell 4: Detection functions
def detect_hieroglyphs(pil_image, prompts=PROMPTS):
    """Run GroundingDINO on a single image. Returns list of box dicts."""
    w, h = pil_image.size
    all_boxes = []

    # Downscale large images
    MAX_DIM = 1200
    scale = 1.0
    proc_image = pil_image
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        proc_image = pil_image.resize((new_w, new_h), Image.LANCZOS)
    pw, ph = proc_image.size

    for prompt in prompts:
        text = prompt if prompt.endswith(".") else prompt + "."
        inputs = processor(images=proc_image, text=text, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            outputs = model(**inputs)
        results = processor.post_process_grounded_object_detection(
            outputs, inputs["input_ids"],
            text_threshold=TEXT_THRESHOLD,
            target_sizes=[(ph, pw)],
        )[0]

        for box, score, label in zip(
            results["boxes"].cpu().numpy(),
            results["scores"].cpu().numpy(),
            results["labels"],
        ):
            if float(score) < BOX_THRESHOLD:
                continue
            x1, y1, x2, y2 = box.tolist()
            if scale != 1.0:
                x1 /= scale; y1 /= scale; x2 /= scale; y2 /= scale
            all_boxes.append({
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "confidence": float(score), "label": label,
            })

    # NMS
    if all_boxes:
        all_boxes = nms_boxes(all_boxes)
    # Size filter
    all_boxes = filter_by_size(all_boxes, w, h)
    return all_boxes


def nms_boxes(boxes, iou_threshold=0.5):
    boxes.sort(key=lambda b: b["confidence"], reverse=True)
    coords = np.array([[b["x1"], b["y1"], b["x2"], b["y2"]] for b in boxes], dtype=np.float32)
    scores = np.array([b["confidence"] for b in boxes], dtype=np.float32)
    indices = cv2.dnn.NMSBoxes(coords.tolist(), scores.tolist(), 0.0, iou_threshold)
    if len(indices) == 0:
        return []
    return [boxes[i] for i in np.array(indices).flatten()]


def filter_by_size(boxes, img_w, img_h):
    filtered = []
    for b in boxes:
        bw = b["x2"] - b["x1"]
        bh = b["y2"] - b["y1"]
        fw, fh = bw / img_w, bh / img_h
        if fw < MIN_BOX_FRAC or fh < MIN_BOX_FRAC:
            continue
        if fw > MAX_BOX_FRAC and fh > MAX_BOX_FRAC:
            continue
        aspect = max(bw, bh) / (min(bw, bh) + 1e-6)
        if aspect > 8.0:
            continue
        filtered.append(b)
    return filtered


def boxes_to_yolo(boxes, img_w, img_h):
    lines = []
    for b in boxes:
        cx = max(0, min(1, ((b["x1"] + b["x2"]) / 2) / img_w))
        cy = max(0, min(1, ((b["y1"] + b["y2"]) / 2) / img_h))
        w = max(0, min(1, (b["x2"] - b["x1"]) / img_w))
        h = max(0, min(1, (b["y2"] - b["y1"]) / img_h))
        lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


# %% Cell 5: Process both sources
def process_source(input_dir, source_name):
    """Annotate all images in a source directory."""
    if not input_dir.exists():
        print(f"SKIP: {input_dir} does not exist")
        return {}

    out_images = OUTPUT_DIR / source_name / "images"
    out_labels = OUTPUT_DIR / source_name / "labels"
    out_previews = OUTPUT_DIR / source_name / "previews"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)
    out_previews.mkdir(parents=True, exist_ok=True)

    image_files = sorted([
        f for f in input_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTS
    ])
    print(f"\n{'='*60}")
    print(f"Processing {source_name}: {len(image_files)} images")
    print(f"{'='*60}")

    stats = {"total": len(image_files), "annotated": 0, "empty": 0,
             "total_boxes": 0, "errors": 0, "per_image": {}}
    all_times = []

    for i, img_path in enumerate(image_files):
        stem = img_path.stem
        label_path = out_labels / f"{stem}.txt"

        # Resume support
        if label_path.exists():
            continue

        if (i + 1) % 20 == 0 or i == 0:
            avg_t = f" ({np.mean(all_times):.2f}s/img)" if all_times else ""
            print(f"  [{i+1}/{len(image_files)}]{avg_t}", flush=True)

        try:
            pil_image = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"  ERROR {img_path.name}: {e}")
            stats["errors"] += 1
            continue

        w, h = pil_image.size
        t0 = time.time()
        boxes = detect_hieroglyphs(pil_image)
        dt = time.time() - t0
        all_times.append(dt)

        # Write YOLO labels
        yolo_lines = boxes_to_yolo(boxes, w, h)
        label_path.write_text("\n".join(yolo_lines) + ("\n" if yolo_lines else ""),
                              encoding="utf-8")

        # Copy image
        dest = out_images / img_path.name
        if not dest.exists():
            shutil.copy2(img_path, dest)

        n_boxes = len(boxes)
        if n_boxes > 0:
            stats["annotated"] += 1
            stats["total_boxes"] += n_boxes
        else:
            stats["empty"] += 1

        stats["per_image"][stem] = {"boxes": n_boxes, "time_s": round(dt, 2)}

        # Preview for first 30 images
        if i < 30 and boxes:
            img_cv = cv2.imread(str(img_path))
            if img_cv is not None:
                for b in boxes:
                    x1, y1 = int(b["x1"]), int(b["y1"])
                    x2, y2 = int(b["x2"]), int(b["y2"])
                    color = (0, 215, 55) if b["confidence"] >= 0.4 else (0, 165, 255)
                    cv2.rectangle(img_cv, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(img_cv, f"{b['confidence']:.2f}",
                                (x1, max(12, y1-5)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
                cv2.imwrite(str(out_previews / f"{stem}_preview.jpg"), img_cv,
                            [cv2.IMWRITE_JPEG_QUALITY, 85])

    stats["avg_time_s"] = round(float(np.mean(all_times)), 2) if all_times else 0
    stats["avg_boxes"] = round(stats["total_boxes"] / max(stats["annotated"], 1), 1)

    print(f"\n  Results: {stats['annotated']} annotated, {stats['empty']} empty, "
          f"{stats['total_boxes']} total boxes, "
          f"avg {stats['avg_time_s']}s/img")

    return stats


# Run both sources
met_stats = process_source(INPUT_MET, "met")
wiki_stats = process_source(INPUT_WIKI, "wikimedia")

# Save combined metadata
combined = {"met": met_stats, "wikimedia": wiki_stats}
meta_path = OUTPUT_DIR / "annotation_metadata.json"
meta_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nMetadata saved to {meta_path}")


# %% Cell 6: Package output
# Zip for download
shutil.make_archive("/kaggle/working/scraped_annotated", "zip", OUTPUT_DIR)
print("Output zipped: /kaggle/working/scraped_annotated.zip")
print("Download this and extract to data/detection/scraped_annotated/")

# Final summary
print(f"\n{'='*60}")
print(f"  Met:       {met_stats.get('annotated', 0)} annotated / {met_stats.get('total', 0)} total")
print(f"  Wikimedia: {wiki_stats.get('annotated', 0)} annotated / {wiki_stats.get('total', 0)} total")
total_boxes = met_stats.get("total_boxes", 0) + wiki_stats.get("total_boxes", 0)
print(f"  Total new boxes: {total_boxes}")
print(f"{'='*60}")
