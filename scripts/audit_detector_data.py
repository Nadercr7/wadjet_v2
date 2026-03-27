r"""Comprehensive audit of hierarchical detection + classification datasets.

Outputs:
    data/detection/merged/audit_report.json   — machine-readable report
    stdout                                     — human-readable summary

Checks:
    1. Source distribution & domain bias
    2. Image size distribution (flagging tiny / huge)
    3. Bounding-box quality (degenerate, tiny, huge, aspect ratio)
    4. Annotation density per source
    5. Empty / missing labels
    6. Split-level balance per source
    7. Unannotated scraped images
    8. Classification dataset balance

Usage:
    python scripts/audit_detector_data.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DET_DIR = ROOT / "data" / "detection" / "merged"
CLS_DIR = ROOT / "data" / "hieroglyph_classification"
SCRAPED_DIR = ROOT / "data" / "detection" / "scraped"
REPORT_PATH = DET_DIR / "audit_report.json"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

# Thresholds
TINY_IMG_PX = 64        # images smaller than this on any side
HUGE_IMG_PX = 4000      # images larger than this on any side
TINY_BOX_AREA = 0.0005  # normalised area
HUGE_BOX_AREA = 0.80
BAD_ASPECT = 15.0       # w/h or h/w > this
DOMAIN_BIAS_THRESHOLD = 0.70  # single source > this % = bias warning


# ── Helpers ──────────────────────────────────────────────────────────────
def source_from_name(name: str) -> str:
    """Extract source tag from YOLO image filename prefix."""
    n = name.lower()
    if n.startswith("mohiey"):
        return "mohiey"
    if n.startswith("synthetic"):
        return "synthetic"
    if n.startswith("signs") or n.startswith("sign_seg"):
        return "signs_seg"
    if n.startswith("v1") or n.startswith("v1_raw"):
        return "v1_raw"
    if n.startswith("hla"):
        return "hla"
    if n.startswith("scraped") or n.startswith("met_") or n.startswith("wiki"):
        return "scraped"
    return "unknown"


def read_label(path: Path) -> list[list[float]]:
    """Read YOLO label file → list of [cls, cx, cy, w, h]."""
    boxes = []
    if not path.exists():
        return boxes
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return boxes
    for line in text.split("\n"):
        parts = line.strip().split()
        if len(parts) >= 5:
            boxes.append([float(p) for p in parts[:5]])
    return boxes


def image_size(path: Path) -> tuple[int, int] | None:
    """Get (w, h) without fully decoding."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    h, w = img.shape[:2]
    return (w, h)


# ── 1. Detection Dataset Audit ──────────────────────────────────────────
def audit_detection() -> dict:
    report: dict = {
        "dataset_path": str(DET_DIR),
        "splits": {},
        "sources": {},
        "totals": {},
        "issues": [],
        "size_distribution": {},
        "box_quality": {},
    }

    all_sources = Counter()
    all_box_counts: list[int] = []
    all_box_areas: list[float] = []
    all_widths: list[int] = []
    all_heights: list[int] = []
    source_per_split: dict[str, Counter] = defaultdict(Counter)
    boxes_per_source: dict[str, list[int]] = defaultdict(list)
    issue_list: list[str] = []
    empty_labels: list[str] = []
    missing_labels: list[str] = []
    tiny_images: list[str] = []
    huge_images: list[str] = []
    bad_boxes: list[str] = []
    total_images = 0
    total_boxes = 0

    for split in ("train", "val", "test"):
        img_dir = DET_DIR / "images" / split
        lbl_dir = DET_DIR / "labels" / split
        if not img_dir.exists():
            issue_list.append(f"Missing split directory: {split}")
            continue

        imgs = sorted(
            p for p in img_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTS
        )
        split_count = len(imgs)
        total_images += split_count
        report["splits"][split] = {"images": split_count, "sources": {}}

        for img_path in imgs:
            stem = img_path.stem
            src = source_from_name(stem)
            all_sources[src] += 1
            source_per_split[split][src] += 1

            # Label check
            lbl_path = lbl_dir / (stem + ".txt")
            if not lbl_path.exists():
                missing_labels.append(f"{split}/{img_path.name}")
                boxes = []
            else:
                boxes = read_label(lbl_path)
                if not boxes:
                    empty_labels.append(f"{split}/{img_path.name}")

            n_boxes = len(boxes)
            all_box_counts.append(n_boxes)
            boxes_per_source[src].append(n_boxes)
            total_boxes += n_boxes

            # Box quality
            for b in boxes:
                _, cx, cy, w, h = b
                area = w * h
                all_box_areas.append(area)
                if area < TINY_BOX_AREA:
                    bad_boxes.append(f"{split}/{img_path.name}: tiny box area={area:.6f}")
                if area > HUGE_BOX_AREA:
                    bad_boxes.append(f"{split}/{img_path.name}: huge box area={area:.4f}")
                if w > 0 and h > 0:
                    ar = max(w / h, h / w)
                    if ar > BAD_ASPECT:
                        bad_boxes.append(
                            f"{split}/{img_path.name}: extreme aspect={ar:.1f}"
                        )
                if cx < 0 or cy < 0 or cx > 1 or cy > 1:
                    bad_boxes.append(f"{split}/{img_path.name}: center OOB ({cx},{cy})")
                if cx - w / 2 < -0.01 or cy - h / 2 < -0.01:
                    bad_boxes.append(f"{split}/{img_path.name}: box extends OOB")

            # Image size (sample 20% for speed)
            if np.random.random() < 0.20:
                sz = image_size(img_path)
                if sz:
                    iw, ih = sz
                    all_widths.append(iw)
                    all_heights.append(ih)
                    if iw < TINY_IMG_PX or ih < TINY_IMG_PX:
                        tiny_images.append(f"{split}/{img_path.name} ({iw}x{ih})")
                    if iw > HUGE_IMG_PX or ih > HUGE_IMG_PX:
                        huge_images.append(f"{split}/{img_path.name} ({iw}x{ih})")

        report["splits"][split]["sources"] = dict(source_per_split[split])

    # Totals
    report["totals"] = {
        "images": total_images,
        "boxes": total_boxes,
        "avg_boxes_per_image": round(total_boxes / max(total_images, 1), 2),
        "empty_labels": len(empty_labels),
        "missing_labels": len(missing_labels),
    }

    # Source distribution
    src_dict = {}
    for src, count in all_sources.most_common():
        pct = count / max(total_images, 1) * 100
        avg_boxes = (
            round(np.mean(boxes_per_source[src]), 1) if boxes_per_source[src] else 0
        )
        src_dict[src] = {
            "count": count,
            "pct": round(pct, 1),
            "avg_boxes_per_image": avg_boxes,
        }
    report["sources"] = src_dict

    # Domain bias check
    top_src, top_count = all_sources.most_common(1)[0]
    top_pct = top_count / max(total_images, 1)
    if top_pct > DOMAIN_BIAS_THRESHOLD:
        issue_list.append(
            f"DOMAIN BIAS: '{top_src}' is {top_pct*100:.1f}% of data "
            f"(threshold: {DOMAIN_BIAS_THRESHOLD*100:.0f}%)"
        )

    # Size distribution
    if all_widths:
        report["size_distribution"] = {
            "sample_pct": "~20%",
            "width": {
                "min": int(min(all_widths)),
                "max": int(max(all_widths)),
                "median": int(np.median(all_widths)),
                "mean": int(np.mean(all_widths)),
            },
            "height": {
                "min": int(min(all_heights)),
                "max": int(max(all_heights)),
                "median": int(np.median(all_heights)),
                "mean": int(np.mean(all_heights)),
            },
            "tiny_images": len(tiny_images),
            "huge_images": len(huge_images),
        }

    # Box quality
    if all_box_areas:
        report["box_quality"] = {
            "total_boxes": total_boxes,
            "area_min": round(min(all_box_areas), 6),
            "area_max": round(max(all_box_areas), 4),
            "area_median": round(float(np.median(all_box_areas)), 6),
            "area_mean": round(float(np.mean(all_box_areas)), 6),
            "tiny_boxes": sum(1 for a in all_box_areas if a < TINY_BOX_AREA),
            "huge_boxes": sum(1 for a in all_box_areas if a > HUGE_BOX_AREA),
            "bad_aspect_ratio": len(
                [b for b in bad_boxes if "aspect" in b]
            ),
        }

    # Box distribution stats
    if all_box_counts:
        bc = np.array(all_box_counts)
        report["boxes_per_image"] = {
            "min": int(bc.min()),
            "max": int(bc.max()),
            "median": int(np.median(bc)),
            "mean": round(float(bc.mean()), 1),
            "p95": int(np.percentile(bc, 95)),
            "zero_box_images": int(np.sum(bc == 0)),
        }

    # Compile issues
    issue_list.extend(
        [f"EMPTY_LABEL: {e}" for e in empty_labels[:10]]
    )
    if len(empty_labels) > 10:
        issue_list.append(f"  ...and {len(empty_labels) - 10} more empty labels")
    issue_list.extend([f"MISSING_LABEL: {m}" for m in missing_labels[:10]])
    issue_list.extend([f"TINY_IMAGE: {t}" for t in tiny_images[:10]])
    if len(tiny_images) > 10:
        issue_list.append(f"  ...and {len(tiny_images) - 10} more tiny images")
    issue_list.extend([f"HUGE_IMAGE: {h}" for h in huge_images[:10]])

    report["issues"] = issue_list
    report["issue_counts"] = {
        "empty_labels": len(empty_labels),
        "missing_labels": len(missing_labels),
        "tiny_images": len(tiny_images),
        "huge_images": len(huge_images),
        "bad_boxes": len(bad_boxes),
    }

    return report


# ── 2. Classification Dataset Audit ─────────────────────────────────────
def audit_classification() -> dict:
    report: dict = {"dataset_path": str(CLS_DIR), "splits": {}}

    if not CLS_DIR.exists():
        report["error"] = "Classification dataset directory not found"
        return report

    all_classes: set[str] = set()
    for split in ("train", "val", "test"):
        split_dir = CLS_DIR / split
        if not split_dir.exists():
            continue

        classes = sorted(d.name for d in split_dir.iterdir() if d.is_dir())
        all_classes.update(classes)
        counts = {}
        for cls_dir in split_dir.iterdir():
            if cls_dir.is_dir():
                n = sum(
                    1
                    for f in cls_dir.iterdir()
                    if f.suffix.lower() in SUPPORTED_EXTS
                )
                counts[cls_dir.name] = n

        total = sum(counts.values())
        values = list(counts.values())
        report["splits"][split] = {
            "total_images": total,
            "num_classes": len(counts),
            "min_per_class": min(values) if values else 0,
            "max_per_class": max(values) if values else 0,
            "median_per_class": int(np.median(values)) if values else 0,
            "mean_per_class": round(np.mean(values), 1) if values else 0,
            "classes_under_20": sum(1 for v in values if v < 20),
            "classes_under_50": sum(1 for v in values if v < 50),
        }

    report["total_classes"] = len(all_classes)
    return report


# ── 3. Unannotated Images Audit ─────────────────────────────────────────
def audit_unannotated() -> dict:
    report: dict = {"scraped_path": str(SCRAPED_DIR), "sources": {}}

    if not SCRAPED_DIR.exists():
        report["error"] = "Scraped directory does not exist"
        return report

    for source_dir in sorted(SCRAPED_DIR.iterdir()):
        if source_dir.is_dir():
            img_dir = source_dir / "images"
            if img_dir.exists():
                imgs = [
                    f
                    for f in img_dir.iterdir()
                    if f.suffix.lower() in SUPPORTED_EXTS
                ]
                report["sources"][source_dir.name] = len(imgs)
            else:
                # Check for images directly in dir
                imgs = [
                    f
                    for f in source_dir.iterdir()
                    if f.suffix.lower() in SUPPORTED_EXTS
                ]
                if imgs:
                    report["sources"][source_dir.name] = len(imgs)

    report["total_unannotated"] = sum(report["sources"].values())
    return report


# ── Print Report ─────────────────────────────────────────────────────────
def print_report(det: dict, cls: dict, unann: dict) -> None:
    print("=" * 70)
    print("  WADJET DETECTOR DATA AUDIT")
    print("=" * 70)

    # Detection summary
    t = det["totals"]
    print(f"\n■ DETECTION DATASET: {t['images']} images, {t['boxes']} boxes")
    print(f"  Avg boxes/image: {t['avg_boxes_per_image']}")
    print(f"  Empty labels: {t['empty_labels']}, Missing labels: {t['missing_labels']}")

    # Splits
    print("\n  Splits:")
    for sp, info in det["splits"].items():
        print(f"    {sp}: {info['images']} images")

    # Source distribution
    print("\n■ SOURCE DISTRIBUTION (domain bias analysis):")
    for src, info in det["sources"].items():
        bar = "█" * int(info["pct"] / 2)
        flag = " ⚠ BIAS" if info["pct"] > DOMAIN_BIAS_THRESHOLD * 100 else ""
        print(f"    {src:15s} {info['count']:>6d} ({info['pct']:>5.1f}%) "
              f"avg-boxes={info['avg_boxes_per_image']:>5.1f} {bar}{flag}")

    # Box quality
    if det.get("box_quality"):
        bq = det["box_quality"]
        print(f"\n■ BOX QUALITY:")
        print(f"    Total boxes: {bq['total_boxes']}")
        print(f"    Area: min={bq['area_min']:.6f}  max={bq['area_max']:.4f}  "
              f"median={bq['area_median']:.6f}  mean={bq['area_mean']:.6f}")
        print(f"    Tiny boxes (area < {TINY_BOX_AREA}): {bq['tiny_boxes']}")
        print(f"    Huge boxes (area > {HUGE_BOX_AREA}): {bq['huge_boxes']}")
        print(f"    Bad aspect ratio (> {BAD_ASPECT}:1): {bq['bad_aspect_ratio']}")

    # Boxes per image
    if det.get("boxes_per_image"):
        bpi = det["boxes_per_image"]
        print(f"\n■ BOXES PER IMAGE:")
        print(f"    min={bpi['min']}  max={bpi['max']}  median={bpi['median']}  "
              f"mean={bpi['mean']}  p95={bpi['p95']}")
        print(f"    Zero-box images: {bpi['zero_box_images']}")

    # Size distribution
    if det.get("size_distribution"):
        sd = det["size_distribution"]
        print(f"\n■ IMAGE SIZES (sampled {sd['sample_pct']}):")
        print(f"    Width:  min={sd['width']['min']}  max={sd['width']['max']}  "
              f"median={sd['width']['median']}  mean={sd['width']['mean']}")
        print(f"    Height: min={sd['height']['min']}  max={sd['height']['max']}  "
              f"median={sd['height']['median']}  mean={sd['height']['mean']}")
        print(f"    Tiny images (<{TINY_IMG_PX}px): {sd['tiny_images']}")
        print(f"    Huge images (>{HUGE_IMG_PX}px): {sd['huge_images']}")

    # Issues
    if det.get("issues"):
        print(f"\n■ ISSUES ({len(det['issues'])} total):")
        for iss in det["issues"][:20]:
            print(f"    • {iss}")
        if len(det["issues"]) > 20:
            print(f"    ...and {len(det['issues']) - 20} more")

    # Classification
    print(f"\n{'='*70}")
    print(f"■ CLASSIFICATION DATASET: {cls.get('total_classes', '?')} classes")
    for sp, info in cls.get("splits", {}).items():
        print(f"    {sp}: {info['total_images']} images, {info['num_classes']} classes")
        print(f"      per-class: min={info['min_per_class']} max={info['max_per_class']} "
              f"median={info['median_per_class']} mean={info['mean_per_class']}")
        if info["classes_under_20"] > 0:
            print(f"      ⚠ {info['classes_under_20']} classes have < 20 images")

    # Unannotated
    print(f"\n{'='*70}")
    print(f"■ UNANNOTATED SCRAPED IMAGES: {unann.get('total_unannotated', 0)}")
    for src, count in unann.get("sources", {}).items():
        print(f"    {src}: {count} images")

    # Recommendations
    print(f"\n{'='*70}")
    print("■ RECOMMENDATIONS:")
    recs = []

    # Domain bias
    det_sources = det.get("sources", {})
    if det_sources:
        top_src = max(det_sources, key=lambda k: det_sources[k]["count"])
        top_pct = det_sources[top_src]["pct"]
        if top_pct > 70:
            recs.append(
                f"CRITICAL: '{top_src}' = {top_pct}% of data. "
                f"Balance by adding diverse sources or undersampling."
            )

    # Empty labels
    if t["empty_labels"] > 0:
        recs.append(f"Remove or re-annotate {t['empty_labels']} empty-label images.")

    # Unannotated
    un_total = unann.get("total_unannotated", 0)
    if un_total > 0:
        recs.append(
            f"Annotate {un_total} scraped museum images with GroundingDINO "
            f"to add domain diversity."
        )

    # Tiny/huge images
    ic = det.get("issue_counts", {})
    if ic.get("tiny_images", 0) > 0:
        recs.append(f"Remove or upscale {ic['tiny_images']} tiny images (<{TINY_IMG_PX}px).")
    if ic.get("huge_images", 0) > 0:
        recs.append(f"Downscale {ic['huge_images']} huge images (>{HUGE_IMG_PX}px) to ≤2048px.")

    # Box issues
    if ic.get("bad_boxes", 0) > 50:
        recs.append(f"Review {ic['bad_boxes']} problematic boxes (tiny/huge/bad-aspect).")

    for i, r in enumerate(recs, 1):
        print(f"  {i}. {r}")

    if not recs:
        print("  (none)")


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    np.random.seed(42)

    print("Auditing detection dataset...")
    det_report = audit_detection()

    print("Auditing classification dataset...")
    cls_report = audit_classification()

    print("Auditing unannotated images...")
    unann_report = audit_unannotated()

    full_report = {
        "detection": det_report,
        "classification": cls_report,
        "unannotated": unann_report,
    }

    REPORT_PATH.write_text(
        json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nJSON report saved to: {REPORT_PATH}")

    print_report(det_report, cls_report, unann_report)


if __name__ == "__main__":
    main()
