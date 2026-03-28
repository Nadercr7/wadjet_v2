"""
Wadjet AI — Feedback Service (Phase 7.15).

Server-side storage and retrieval for user feedback:
  - Identification correctness votes
  - Description quality ratings (1-5 stars)
  - General free-text feedback

Data is persisted as JSONL (one JSON object per line) in ``data/feedback/``.
This keeps things simple, file-based, and dependency-free — no database
required.  Each feedback type gets its own file:

    data/feedback/identification.jsonl
    data/feedback/ratings.jsonl
    data/feedback/general.jsonl

A lightweight in-memory stats cache is refreshed lazily so the aggregated
endpoint is fast.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from app.core.logging import get_logger

logger = get_logger("wadjet.feedback")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FEEDBACK_DIR = Path("data/feedback")
_ID_FILE = _FEEDBACK_DIR / "identification.jsonl"
_RATING_FILE = _FEEDBACK_DIR / "ratings.jsonl"
_GENERAL_FILE = _FEEDBACK_DIR / "general.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    """Generate a short unique feedback ID."""
    return f"fb-{uuid.uuid4().hex[:12]}"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _append_jsonl(path: Path, record: dict) -> None:
    """Append a single JSON line to *path*, creating parents if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    async with aiofiles.open(path, "a", encoding="utf-8") as fh:
        await fh.write(line)


async def _read_jsonl(path: Path) -> list[dict]:
    """Read all records from a JSONL file.  Returns [] if missing."""
    if not path.exists():
        return []
    records: list[dict] = []
    async with aiofiles.open(path, encoding="utf-8") as fh:
        async for raw_line in fh:
            line = raw_line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("corrupt_jsonl_line", file=str(path))
    return records


# ---------------------------------------------------------------------------
# FeedbackService
# ---------------------------------------------------------------------------


class FeedbackService:
    """Stateless service for persisting and querying user feedback."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        base = storage_dir or _FEEDBACK_DIR
        self._id_file = base / "identification.jsonl"
        self._rating_file = base / "ratings.jsonl"
        self._general_file = base / "general.jsonl"
        logger.info("feedback_service_init", storage=str(base))

    # -- Identification correctness ----------------------------------------

    async def submit_identification(
        self,
        *,
        landmark_class: str,
        was_correct: bool,
        confidence: float = 0.0,
        correct_class: str | None = None,
    ) -> str:
        """Record whether a user agrees with an identification.

        Returns the feedback_id.
        """
        fid = _new_id()
        record = {
            "feedback_id": fid,
            "landmark_class": landmark_class,
            "was_correct": was_correct,
            "confidence": round(confidence, 4),
            "correct_class": correct_class,
            "timestamp": _utcnow_iso(),
        }
        await _append_jsonl(self._id_file, record)
        logger.info(
            "identification_feedback",
            landmark=landmark_class,
            correct=was_correct,
            fid=fid,
        )
        return fid

    # -- Description rating ------------------------------------------------

    async def submit_rating(
        self,
        *,
        landmark_class: str,
        rating: int,
        comment: str | None = None,
    ) -> str:
        """Record a 1-5 star rating for a landmark description.

        Returns the feedback_id.
        """
        fid = _new_id()
        record = {
            "feedback_id": fid,
            "landmark_class": landmark_class,
            "rating": rating,
            "comment": comment,
            "timestamp": _utcnow_iso(),
        }
        await _append_jsonl(self._rating_file, record)
        logger.info(
            "rating_feedback",
            landmark=landmark_class,
            rating=rating,
            fid=fid,
        )
        return fid

    # -- General feedback --------------------------------------------------

    async def submit_general(
        self,
        *,
        category: str,
        message: str,
        page: str | None = None,
    ) -> str:
        """Record free-text general feedback.

        Returns the feedback_id.
        """
        fid = _new_id()
        record = {
            "feedback_id": fid,
            "category": category,
            "message": message,
            "page": page,
            "timestamp": _utcnow_iso(),
        }
        await _append_jsonl(self._general_file, record)
        logger.info("general_feedback", category=category, fid=fid)
        return fid

    # -- Statistics --------------------------------------------------------

    async def get_stats(self) -> dict:
        """Return aggregated feedback statistics (all-time)."""
        id_records = await _read_jsonl(self._id_file)
        rating_records = await _read_jsonl(self._rating_file)
        general_records = await _read_jsonl(self._general_file)

        # Identification stats
        total_id = len(id_records)
        correct = sum(1 for r in id_records if r.get("was_correct"))
        incorrect = total_id - correct
        agreement = (correct / total_id * 100) if total_id else 0.0

        # Top incorrectly-identified classes
        incorrect_counter: Counter[str] = Counter()
        for r in id_records:
            if not r.get("was_correct"):
                incorrect_counter[r.get("landmark_class", "unknown")] += 1
        top_incorrect = [
            {"class": cls, "count": cnt} for cls, cnt in incorrect_counter.most_common(10)
        ]

        # Rating stats
        total_ratings = len(rating_records)
        avg_rating = 0.0
        if total_ratings:
            avg_rating = round(
                sum(r.get("rating", 0) for r in rating_records) / total_ratings,
                2,
            )

        return {
            "total_identification_votes": total_id,
            "correct_votes": correct,
            "incorrect_votes": incorrect,
            "accuracy_agreement": round(agreement, 1),
            "total_ratings": total_ratings,
            "average_rating": avg_rating,
            "total_general": len(general_records),
            "top_incorrect_classes": top_incorrect,
        }
