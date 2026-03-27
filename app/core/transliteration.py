"""Transliteration engine: converts detected + classified glyphs to
transliterated text.

Pipeline:
1. Detection boxes + classification results -> BBox list with Gardiner codes
2. Reading order analysis (layout, direction, line clustering, quadrats)
3. For each glyph in order: look up transliteration value
4. Mark determinatives (non-phonetic, shown in brackets)
5. Output: transliteration string in Manuel de Codage (MdC) notation

Manuel de Codage (MdC) conventions:
- Transliteration uses ASCII-friendly encoding of Egyptian consonants
- A = aleph, i = yod, a = ayin, w, b, p, f, m, n, r, h, H, x, X, s, S, q, k, g, t, T, d, D
- Determinatives shown in angle brackets: <D54> or as semantic notes
- Quadrat separators: - (within word), space (between words)
- Unknown signs: [code] in square brackets
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.gardiner import (
    GARDINER_TRANSLITERATION,
    SignType,
    get_determinative_class,
    get_sign_type,
    get_transliteration,
    is_determinative,
)
from app.core.reading_order import (
    BBox,
    Direction,
    GlyphGroup,
    LayoutMode,
    detect_layout_mode,
    detect_reading_direction,
    establish_reading_order,
)


@dataclass
class TransliterationResult:
    """Result of transliterating an inscription."""
    mdc_transliteration: str            # Manuel de Codage string
    gardiner_sequence: str              # Raw Gardiner code sequence
    direction: Direction                # Detected writing direction
    layout: LayoutMode                  # Detected layout mode
    num_glyphs: int                     # Total detected glyphs
    num_groups: int                     # Number of quadrat groups
    num_lines: int                      # Number of text lines
    num_determinatives: int             # Determinatives found
    num_unknown: int                    # Signs not in mapping
    per_glyph_details: list[dict] = field(default_factory=list)


class TransliterationEngine:
    """Main transliteration engine.

    Takes detected bounding boxes with Gardiner code classifications
    and produces transliterated text.
    """

    def __init__(
        self,
        label_mapping_path: Optional[str | Path] = None,
        show_determinatives: bool = True,
        show_unknown: bool = True,
        group_separator: str = "-",
        word_separator: str = " ",
    ):
        self.show_determinatives = show_determinatives
        self.show_unknown = show_unknown
        self.group_separator = group_separator
        self.word_separator = word_separator

        # Load label mapping for idx->Gardiner conversion
        self.idx_to_gardiner: dict[int, str] = {}
        if label_mapping_path is not None:
            self._load_label_mapping(label_mapping_path)

    def _load_label_mapping(self, path: str | Path) -> None:
        """Load the idx_to_gardiner mapping from label_mapping.json."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.idx_to_gardiner = {
            int(k): v for k, v in data.get("idx_to_gardiner", {}).items()
        }

    def boxes_to_bboxes(
        self,
        boxes: list[dict],
    ) -> list[BBox]:
        """Convert raw detection + classification results to BBox objects.

        Expected input format per box:
        {
            "x1": float, "y1": float, "x2": float, "y2": float,
            "class_id": int, "confidence": float,
            "gardiner_code": str (optional, if already resolved)
        }
        """
        bboxes = []
        for box in boxes:
            gardiner = box.get("gardiner_code", "")
            if not gardiner and "class_id" in box:
                gardiner = self.idx_to_gardiner.get(box["class_id"], "")

            bboxes.append(BBox(
                x1=box["x1"],
                y1=box["y1"],
                x2=box["x2"],
                y2=box["y2"],
                class_id=box.get("class_id", -1),
                gardiner_code=gardiner,
                confidence=box.get("confidence", 0.0),
            ))
        return bboxes

    def transliterate(
        self,
        boxes: list[BBox],
        direction: Optional[Direction] = None,
    ) -> TransliterationResult:
        """Full transliteration pipeline.

        Args:
            boxes: List of BBox objects with gardiner_code set.
            direction: Override reading direction (None = auto-detect).

        Returns:
            TransliterationResult with transliteration and metadata.
        """
        if not boxes:
            return TransliterationResult(
                mdc_transliteration="",
                gardiner_sequence="",
                direction=Direction.UNKNOWN,
                layout=LayoutMode.HORIZONTAL,
                num_glyphs=0,
                num_groups=0,
                num_lines=0,
                num_determinatives=0,
                num_unknown=0,
            )

        # Step 1: Reading order analysis
        layout = detect_layout_mode(boxes)
        if direction is None:
            direction = detect_reading_direction(boxes, layout)

        groups = establish_reading_order(boxes, direction)

        # Step 2: Transliterate each group
        mdc_parts: list[str] = []
        gardiner_parts: list[str] = []
        per_glyph: list[dict] = []
        num_det = 0
        num_unknown = 0
        prev_row = -1

        for group in groups:
            # Word boundary (new line)
            if prev_row != -1 and group.row_idx != prev_row:
                mdc_parts.append(self.word_separator)
                gardiner_parts.append(self.word_separator)
            elif prev_row != -1:
                mdc_parts.append(self.group_separator)
                gardiner_parts.append(self.group_separator)

            # Transliterate glyphs within the quadrat
            group_mdc: list[str] = []
            group_gardiner: list[str] = []

            for glyph in sorted(group.glyphs, key=lambda g: g.cy):
                code = glyph.gardiner_code
                group_gardiner.append(code)

                # Get transliteration
                translit = get_transliteration(code)
                sign_type = get_sign_type(code)
                det = is_determinative(code)
                det_class = get_determinative_class(code)

                glyph_info = {
                    "gardiner_code": code,
                    "transliteration": translit,
                    "sign_type": sign_type.value,
                    "is_determinative": det,
                    "determinative_class": det_class,
                    "confidence": glyph.confidence,
                    "position": {
                        "x1": glyph.x1, "y1": glyph.y1,
                        "x2": glyph.x2, "y2": glyph.y2,
                    },
                }
                per_glyph.append(glyph_info)

                if det and self.show_determinatives:
                    if det_class:
                        group_mdc.append(f"<{det_class}>")
                    else:
                        group_mdc.append(f"<{code}>")
                    num_det += 1
                elif translit.startswith("["):
                    if self.show_unknown:
                        group_mdc.append(translit)
                    num_unknown += 1
                else:
                    group_mdc.append(translit)

            # Handle stacking within quadrats
            if len(group_mdc) == 1:
                mdc_parts.append(group_mdc[0])
            else:
                mdc_parts.append(":".join(group_mdc))

            gardiner_parts.append(":".join(group_gardiner) if len(group_gardiner) > 1
                                  else group_gardiner[0] if group_gardiner else "")

            prev_row = group.row_idx

        num_lines = len({g.row_idx for g in groups})

        return TransliterationResult(
            mdc_transliteration="".join(mdc_parts),
            gardiner_sequence="".join(gardiner_parts),
            direction=direction,
            layout=layout,
            num_glyphs=len(boxes),
            num_groups=len(groups),
            num_lines=num_lines,
            num_determinatives=num_det,
            num_unknown=num_unknown,
            per_glyph_details=per_glyph,
        )

    def transliterate_from_raw(
        self,
        raw_boxes: list[dict],
        direction: Optional[Direction] = None,
    ) -> TransliterationResult:
        """Convenience method: raw detection dicts -> transliteration."""
        bboxes = self.boxes_to_bboxes(raw_boxes)
        return self.transliterate(bboxes, direction)

    def transliterate_gardiner_sequence(
        self,
        gardiner_codes: list[str],
    ) -> str:
        """Simple transliteration from a known sequence of Gardiner codes.

        This bypasses spatial analysis -- useful for testing against
        known inscriptions where the reading order is already known.
        """
        parts = []
        for code in gardiner_codes:
            if is_determinative(code):
                det_class = get_determinative_class(code)
                if det_class and self.show_determinatives:
                    parts.append(f"<{det_class}>")
                elif self.show_determinatives:
                    parts.append(f"<{code}>")
            else:
                parts.append(get_transliteration(code))
        return self.group_separator.join(parts)
