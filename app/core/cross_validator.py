"""Cross-Validator — compare AI Vision reading vs ONNX classification.

When both AI and ONNX results are available, this module compares them
by matching glyphs via bounding box overlap, flags disagreements, and
produces a merged result with confidence scores.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GlyphComparison:
    """Comparison of AI vs ONNX for a single glyph position."""

    index: int
    ai_code: str = ""
    onnx_code: str = ""
    ai_confidence: float = 0.0
    onnx_confidence: float = 0.0
    agreed: bool = False
    final_code: str = ""
    final_confidence: float = 0.0
    source: str = ""  # "ai", "onnx", "both"


@dataclass
class ValidationResult:
    """Result of cross-validating AI and ONNX readings."""

    comparisons: list[GlyphComparison] = field(default_factory=list)
    agreement_rate: float = 0.0
    ai_only_count: int = 0
    onnx_only_count: int = 0
    disagreement_count: int = 0

    def to_dict(self) -> dict:
        return {
            "agreement_rate": round(self.agreement_rate, 2),
            "ai_only_count": self.ai_only_count,
            "onnx_only_count": self.onnx_only_count,
            "disagreement_count": self.disagreement_count,
            "comparisons": [
                {
                    "index": c.index,
                    "ai_code": c.ai_code,
                    "onnx_code": c.onnx_code,
                    "agreed": c.agreed,
                    "final_code": c.final_code,
                    "source": c.source,
                }
                for c in self.comparisons
            ],
        }


def _bbox_iou(a_x1, a_y1, a_x2, a_y2, b_x1, b_y1, b_x2, b_y2) -> float:
    """Intersection-over-Union for two bounding boxes."""
    ix1 = max(a_x1, b_x1)
    iy1 = max(a_y1, b_y1)
    ix2 = min(a_x2, b_x2)
    iy2 = min(a_y2, b_y2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0.0:
        return 0.0
    area_a = max(0.0, a_x2 - a_x1) * max(0.0, a_y2 - a_y1)
    area_b = max(0.0, b_x2 - b_x1) * max(0.0, b_y2 - b_y1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def cross_validate(
    ai_glyphs: list[dict],
    onnx_glyphs: list,
    image_width: int,
    image_height: int,
    iou_threshold: float = 0.3,
) -> ValidationResult:
    """Compare AI-detected glyphs against ONNX-detected glyphs.

    Args:
        ai_glyphs: List of dicts from AIHieroglyphReader (bbox_pct in %).
        onnx_glyphs: List of GlyphResult from ONNX pipeline (pixel coords).
        image_width, image_height: For converting AI bbox_pct to pixels.
        iou_threshold: Minimum IoU to consider a spatial match.

    Returns:
        ValidationResult with per-glyph comparisons and agreement stats.
    """
    comparisons = []
    matched_onnx = set()

    # Convert AI bbox_pct to pixel coordinates
    ai_pixel_bboxes = []
    for g in ai_glyphs:
        bbox = g.get("bbox_pct", [0, 0, 100, 100])
        ai_pixel_bboxes.append((
            bbox[0] * image_width / 100.0,
            bbox[1] * image_height / 100.0,
            bbox[2] * image_width / 100.0,
            bbox[3] * image_height / 100.0,
        ))

    # Match each AI glyph to nearest ONNX glyph by IoU
    for i, (ai_g, ai_bbox) in enumerate(zip(ai_glyphs, ai_pixel_bboxes)):
        ai_code = ai_g.get("gardiner_code", "").upper()
        ai_conf = float(ai_g.get("confidence", 0.8))

        best_iou = 0.0
        best_j = -1
        for j, og in enumerate(onnx_glyphs):
            if j in matched_onnx:
                continue
            iou = _bbox_iou(
                ai_bbox[0], ai_bbox[1], ai_bbox[2], ai_bbox[3],
                og.x1, og.y1, og.x2, og.y2,
            )
            if iou > best_iou:
                best_iou = iou
                best_j = j

        if best_j >= 0 and best_iou >= iou_threshold:
            matched_onnx.add(best_j)
            og = onnx_glyphs[best_j]
            onnx_code = og.gardiner_code.upper()
            onnx_conf = og.class_confidence
            agreed = ai_code == onnx_code

            # Pick winner: if they agree, both. If not, pick higher confidence.
            if agreed:
                final_code = ai_code
                final_conf = max(ai_conf, onnx_conf)
                source = "both"
            elif ai_conf >= onnx_conf:
                final_code = ai_code
                final_conf = ai_conf
                source = "ai"
            else:
                final_code = onnx_code
                final_conf = onnx_conf
                source = "onnx"

            comparisons.append(GlyphComparison(
                index=i,
                ai_code=ai_code,
                onnx_code=onnx_code,
                ai_confidence=ai_conf,
                onnx_confidence=onnx_conf,
                agreed=agreed,
                final_code=final_code,
                final_confidence=final_conf,
                source=source,
            ))
        else:
            # AI-only glyph (no ONNX match)
            comparisons.append(GlyphComparison(
                index=i,
                ai_code=ai_code,
                ai_confidence=ai_conf,
                agreed=False,
                final_code=ai_code,
                final_confidence=ai_conf,
                source="ai",
            ))

    # ONNX-only glyphs (not matched to any AI glyph)
    for j, og in enumerate(onnx_glyphs):
        if j not in matched_onnx:
            comparisons.append(GlyphComparison(
                index=len(ai_glyphs) + j,
                onnx_code=og.gardiner_code.upper(),
                onnx_confidence=og.class_confidence,
                agreed=False,
                final_code=og.gardiner_code.upper(),
                final_confidence=og.class_confidence,
                source="onnx",
            ))

    # Stats
    matched_count = sum(1 for c in comparisons if c.ai_code and c.onnx_code)
    agreed_count = sum(1 for c in comparisons if c.agreed)
    ai_only = sum(1 for c in comparisons if c.source == "ai" and not c.onnx_code)
    onnx_only = sum(1 for c in comparisons if c.source == "onnx" and not c.ai_code)
    disagreed = matched_count - agreed_count

    return ValidationResult(
        comparisons=comparisons,
        agreement_rate=agreed_count / matched_count if matched_count > 0 else 0.0,
        ai_only_count=ai_only,
        onnx_only_count=onnx_only,
        disagreement_count=disagreed,
    )
