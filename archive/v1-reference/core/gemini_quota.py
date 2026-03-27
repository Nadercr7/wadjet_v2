"""
Wadjet AI — Gemini Quota Manager.

Tracks API call volume per minute and per day across all keys.
Provides a gate (``can_call``) that callers check **before** making
a Gemini request, and a ``record_call`` hook to update counters
**after** each successful call.

When the quota is approaching its limit, the manager enters
"degraded" mode, signalling callers to fall back to Keras-only
or cached responses.

Phase 3.14 — Gemini Rate Limit Management.

Free-tier Gemini limits (per key, approximate):
  - 15 RPM  (requests per minute)
  - 1500 RPD (requests per day)

With 17 keys and rotation this gives:
  - ~255 effective RPM
  - ~25 500 effective RPD
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

import structlog

logger = structlog.get_logger("wadjet.quota")

# ---------------------------------------------------------------------------
# Default limits (conservative for 17-key rotation)
# ---------------------------------------------------------------------------

_DEFAULT_RPM_LIMIT: int = 200  # requests/minute (leave headroom below 255)
_DEFAULT_RPD_LIMIT: int = 20_000  # requests/day    (leave headroom below 25 500)
_WARN_THRESHOLD: float = 0.80  # warn at 80 % of limit
_BLOCK_THRESHOLD: float = 0.95  # block at 95 % of limit (leave 5 % emergency)


# ---------------------------------------------------------------------------
# Quota status snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    """Snapshot of the current Gemini quota state."""

    rpm_used: int
    rpm_limit: int
    rpd_used: int
    rpd_limit: int
    is_degraded: bool
    is_blocked: bool
    rpm_utilisation: float  # 0.0 - 1.0
    rpd_utilisation: float  # 0.0 - 1.0
    message: str  # human-readable status


# ---------------------------------------------------------------------------
# Quota Manager
# ---------------------------------------------------------------------------


class GeminiQuotaManager:
    """In-memory sliding-window quota tracker for Gemini API calls.

    Parameters
    ----------
    rpm_limit:
        Maximum requests per minute before blocking.
    rpd_limit:
        Maximum requests per day before blocking.
    warn_threshold:
        Fraction (0-1) of limit at which "degraded" mode activates.
    block_threshold:
        Fraction (0-1) of limit at which requests are blocked entirely.
    """

    def __init__(
        self,
        *,
        rpm_limit: int = _DEFAULT_RPM_LIMIT,
        rpd_limit: int = _DEFAULT_RPD_LIMIT,
        warn_threshold: float = _WARN_THRESHOLD,
        block_threshold: float = _BLOCK_THRESHOLD,
    ) -> None:
        self._rpm_limit = rpm_limit
        self._rpd_limit = rpd_limit
        self._warn_threshold = warn_threshold
        self._block_threshold = block_threshold

        # Sliding windows — timestamps (seconds since epoch) of each call
        self._minute_window: deque[float] = deque()
        self._day_window: deque[float] = deque()

        logger.info(
            "gemini_quota_init",
            rpm_limit=rpm_limit,
            rpd_limit=rpd_limit,
            warn_pct=f"{warn_threshold:.0%}",
            block_pct=f"{block_threshold:.0%}",
        )

    # ── Window housekeeping ─────────────────────

    def _prune(self, now: float | None = None) -> None:
        """Remove expired timestamps from both windows."""
        now = now or time.monotonic()
        one_minute_ago = now - 60.0
        one_day_ago = now - 86_400.0

        while self._minute_window and self._minute_window[0] < one_minute_ago:
            self._minute_window.popleft()
        while self._day_window and self._day_window[0] < one_day_ago:
            self._day_window.popleft()

    # ── Public API ──────────────────────────────

    @property
    def rpm_used(self) -> int:
        """Current requests made in the last 60 seconds."""
        self._prune()
        return len(self._minute_window)

    @property
    def rpd_used(self) -> int:
        """Current requests made in the last 24 hours."""
        self._prune()
        return len(self._day_window)

    @property
    def is_degraded(self) -> bool:
        """Whether we have passed the warning threshold (should reduce Gemini usage)."""
        self._prune()
        rpm_pct = len(self._minute_window) / self._rpm_limit if self._rpm_limit else 0
        rpd_pct = len(self._day_window) / self._rpd_limit if self._rpd_limit else 0
        return rpm_pct >= self._warn_threshold or rpd_pct >= self._warn_threshold

    @property
    def is_blocked(self) -> bool:
        """Whether we have passed the block threshold (must not call Gemini)."""
        self._prune()
        rpm_pct = len(self._minute_window) / self._rpm_limit if self._rpm_limit else 0
        rpd_pct = len(self._day_window) / self._rpd_limit if self._rpd_limit else 0
        return rpm_pct >= self._block_threshold or rpd_pct >= self._block_threshold

    def can_call(self) -> bool:
        """Check if a Gemini call is allowed right now.

        Returns ``True`` if under the block threshold, ``False`` if blocked.
        """
        return not self.is_blocked

    def record_call(self) -> None:
        """Record that one Gemini API call was made."""
        now = time.monotonic()
        self._prune(now)
        self._minute_window.append(now)
        self._day_window.append(now)

        # Log warnings at threshold crossings
        rpm_pct = len(self._minute_window) / self._rpm_limit if self._rpm_limit else 0
        rpd_pct = len(self._day_window) / self._rpd_limit if self._rpd_limit else 0

        if rpm_pct >= self._block_threshold or rpd_pct >= self._block_threshold:
            logger.warning(
                "gemini_quota_blocked",
                rpm_used=len(self._minute_window),
                rpm_limit=self._rpm_limit,
                rpd_used=len(self._day_window),
                rpd_limit=self._rpd_limit,
            )
        elif rpm_pct >= self._warn_threshold or rpd_pct >= self._warn_threshold:
            logger.warning(
                "gemini_quota_degraded",
                rpm_used=len(self._minute_window),
                rpm_limit=self._rpm_limit,
                rpd_used=len(self._day_window),
                rpd_limit=self._rpd_limit,
            )

    def status(self) -> QuotaStatus:
        """Return a snapshot of the current quota state."""
        self._prune()
        rpm_used = len(self._minute_window)
        rpd_used = len(self._day_window)
        rpm_pct = rpm_used / self._rpm_limit if self._rpm_limit else 0.0
        rpd_pct = rpd_used / self._rpd_limit if self._rpd_limit else 0.0

        is_blocked = rpm_pct >= self._block_threshold or rpd_pct >= self._block_threshold
        is_degraded = rpm_pct >= self._warn_threshold or rpd_pct >= self._warn_threshold

        if is_blocked:
            message = "Running in fast mode — AI service temporarily limited"
        elif is_degraded:
            message = "AI quota approaching limit — some features may use cached results"
        else:
            message = "AI service operating normally"

        return QuotaStatus(
            rpm_used=rpm_used,
            rpm_limit=self._rpm_limit,
            rpd_used=rpd_used,
            rpd_limit=self._rpd_limit,
            is_degraded=is_degraded,
            is_blocked=is_blocked,
            rpm_utilisation=round(rpm_pct, 4),
            rpd_utilisation=round(rpd_pct, 4),
            message=message,
        )

    def reset(self) -> None:
        """Clear all counters (mainly for testing)."""
        self._minute_window.clear()
        self._day_window.clear()
        logger.info("gemini_quota_reset")
