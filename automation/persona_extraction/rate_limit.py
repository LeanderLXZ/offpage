"""Token-limit pause and resume controller (§11.13).

When a Claude subscription hits the 5-hour rolling window or the weekly cap,
this module:

  1. Parses the reset time from stderr (timezone-aware).
  2. Atomically writes ``rate_limit_pause.json`` (flock + tempfile + replace),
     merging concurrent writes by taking the later ``resume_at``.
  3. Blocks new lane submissions in the orchestrator until the reset passes.
  4. Tracks accumulated pause duration so ``--max-runtime`` excludes it.
  5. Probes (with a minimal claude -p call) when the reset time can't be
     parsed.
  6. Hard-stops the process with exit code 2 when the weekly limit's wait
     would exceed ``rate_limit.weekly_max_wait_h``.

See ``docs/requirements.md`` §11.13 for the full mechanism.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import RateLimitConfig, get_config

logger = logging.getLogger(__name__)


PAUSE_FILE_NAME = "rate_limit_pause.json"
EXIT_LOG_NAME = "rate_limit_exit.log"
WEEKLY_EXIT_CODE = 2


# ---------------------------------------------------------------------------
# stderr parsing
# ---------------------------------------------------------------------------

# Match e.g. "Resets at 3:00 PM PT", "Reset at 15:30 UTC", "resets at 5:01 am PST"
_RESET_AT_ABS = re.compile(
    r"[Rr]esets?\s+(?:at|by)\s+"
    r"(?P<h>\d{1,2}):(?P<m>\d{2})"
    r"\s*(?P<ampm>am|pm|AM|PM)?"
    r"\s*(?P<tz>[A-Z]{2,4})?",
)

# Match e.g. "Resets in 2h30m", "Reset in 45m", "resets in 3 hours"
_RESET_IN_REL = re.compile(
    r"[Rr]esets?\s+in\s+"
    r"(?:(?P<h>\d+)\s*(?:h|hours?))?"
    r"\s*(?:(?P<m>\d+)\s*(?:m|min|minutes?))?",
)

# Match an explicit ISO 8601 timestamp anywhere in the stderr.
_RESET_ISO = re.compile(
    r"(?P<iso>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?"
    r"(?:[+-]\d{2}:?\d{2}|Z)?)",
)

# Subscription error keywords. Order matters: weekly checked before 5h
# because "weekly usage limit" also contains the substring "usage limit".
_WEEKLY_SIGNALS = ("weekly limit", "weekly usage", "weekly cap")
_FIVEH_SIGNALS = (
    "5-hour limit", "5h limit", "5 hour limit",
    "5-hour usage", "usage limit reached", "session limit",
)
_GENERIC_RATE_SIGNALS = (
    "rate limit", "rate_limit", "too many requests", "429",
)

# Common US-centric timezone abbreviations → fixed UTC offset (minutes).
# Subscription error messages typically use PT/PST/PDT/ET. We don't try to
# handle DST transitions; a 60s buffer (`resume_buffer_s`) absorbs any
# ambiguity at the boundary.
_TZ_OFFSETS_MIN: dict[str, int] = {
    "UTC": 0, "GMT": 0, "Z": 0,
    "PT":  -7 * 60,  "PST": -8 * 60, "PDT": -7 * 60,
    "MT":  -6 * 60,  "MST": -7 * 60, "MDT": -6 * 60,
    "CT":  -5 * 60,  "CST": -6 * 60, "CDT": -5 * 60,
    "ET":  -4 * 60,  "EST": -5 * 60, "EDT": -4 * 60,
}


def classify_error(stderr: str) -> str:
    """Return ``"weekly"`` / ``"5h_window"`` / ``"unknown"``.

    ``"unknown"`` covers the generic ``rate limit`` / ``429`` keywords that
    don't disclose which window was tripped.
    """
    lower = (stderr or "").lower()
    if any(s in lower for s in _WEEKLY_SIGNALS):
        return "weekly"
    if any(s in lower for s in _FIVEH_SIGNALS):
        return "5h_window"
    if any(s in lower for s in _GENERIC_RATE_SIGNALS):
        return "unknown"
    return "unknown"


def parse_reset_time(
    stderr: str, *, now: datetime | None = None,
) -> datetime | None:
    """Extract a timezone-aware reset timestamp from ``stderr``.

    Tries (in order): ISO 8601 → absolute clock-time + tz → relative duration.
    Returns ``None`` if nothing parseable is found.
    """
    if not stderr:
        return None
    now = now or datetime.now(timezone.utc)

    # 1. ISO 8601
    m = _RESET_ISO.search(stderr)
    if m:
        try:
            iso = m.group("iso").replace(" ", "T")
            if iso.endswith("Z"):
                iso = iso[:-1] + "+00:00"
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

    # 2. Absolute clock time + tz: "Resets at 3:00 PM PT"
    m = _RESET_AT_ABS.search(stderr)
    if m:
        h = int(m.group("h"))
        minute = int(m.group("m"))
        ampm = (m.group("ampm") or "").lower()
        if ampm == "pm" and h < 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        tz_abbr = (m.group("tz") or "UTC").upper()
        offset_min = _TZ_OFFSETS_MIN.get(tz_abbr, 0)
        tz = timezone(timedelta(minutes=offset_min))
        # Build candidate datetime in that tz on today's date; if it's in
        # the past, roll forward one day.
        now_in_tz = now.astimezone(tz)
        candidate = now_in_tz.replace(
            hour=h, minute=minute, second=0, microsecond=0)
        if candidate <= now_in_tz:
            candidate = candidate + timedelta(days=1)
        return candidate.astimezone(timezone.utc)

    # 3. Relative duration: "Resets in 2h30m"
    m = _RESET_IN_REL.search(stderr)
    if m and (m.group("h") or m.group("m")):
        hours = int(m.group("h") or 0)
        minutes = int(m.group("m") or 0)
        if hours == 0 and minutes == 0:
            return None
        return now + timedelta(hours=hours, minutes=minutes)

    return None


# ---------------------------------------------------------------------------
# Pause file I/O (atomic + flock-merged)
# ---------------------------------------------------------------------------

@dataclass
class PauseRecord:
    resume_at: datetime
    reason: str                 # "5h_window" | "weekly" | "unknown"
    detected_at: datetime
    detected_by: str
    buffer_applied_s: int
    merged_count: int = 1

    def to_json(self) -> dict[str, Any]:
        return {
            "resume_at": self.resume_at.isoformat(),
            "reason": self.reason,
            "detected_at": self.detected_at.isoformat(),
            "detected_by": self.detected_by,
            "buffer_applied_s": self.buffer_applied_s,
            "merged_count": self.merged_count,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> PauseRecord:
        return cls(
            resume_at=datetime.fromisoformat(data["resume_at"]),
            reason=data.get("reason", "unknown"),
            detected_at=datetime.fromisoformat(
                data.get("detected_at", data["resume_at"])),
            detected_by=data.get("detected_by", "?"),
            buffer_applied_s=int(data.get("buffer_applied_s", 0)),
            merged_count=int(data.get("merged_count", 1)),
        )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".rl_pause.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class RateLimitController:
    """Per-work pause-file manager + scheduling gate.

    One instance per orchestrator process. Wired in as a process-level
    singleton via ``set_active`` / ``get_active`` so deeply-nested call
    sites (``run_with_retry`` inside ``json_repair`` / ``scene_archive``)
    can find it without explicit threading.

    Thread/process safety: ``record_pause`` and ``wait_if_paused`` both use
    ``fcntl.flock`` on a sibling lock file, so concurrent ThreadPoolExecutor
    lanes (and any future multi-process callers) merge consistently.
    """

    def __init__(
        self,
        work_root: Path,
        config: RateLimitConfig | None = None,
        *,
        clock: Any = None,   # injectable for tests; default = datetime.now(tz)
        sleeper: Any = None,  # injectable for tests; default = time.sleep
    ) -> None:
        self.work_root = work_root
        self.config = config or get_config().rate_limit
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sleeper = sleeper or time.sleep
        self._pause_dir = work_root / "analysis" / "progress"
        self._pause_path = self._pause_dir / PAUSE_FILE_NAME
        self._lock_path = self._pause_dir / (PAUSE_FILE_NAME + ".lock")
        self._exit_log_path = self._pause_dir / EXIT_LOG_NAME
        # Total seconds spent in wait_if_paused; subtracted from --max-runtime.
        self._paused_seconds_total: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def paused_seconds_total(self) -> float:
        """Cumulative seconds this process has slept in pause gates."""
        return self._paused_seconds_total

    def is_paused(self) -> bool:
        """Cheap check: file exists AND ``resume_at`` is still in the future."""
        rec = self._read()
        if rec is None:
            return False
        return rec.resume_at > self._clock()

    def record_pause(
        self,
        stderr: str,
        *,
        lane_name: str | None = None,
    ) -> PauseRecord:
        """Parse the failure and write/merge the pause file.

        Returns the record actually persisted (after any merge with an
        already-existing pause from another concurrent lane).
        """
        reason = classify_error(stderr)
        reset_at = parse_reset_time(stderr, now=self._clock())
        buffer_s = int(self.config.resume_buffer_s)

        if reset_at is not None:
            resume_at = reset_at + timedelta(seconds=buffer_s)
        else:
            # Unparseable: schedule the first probe one fallback-window away.
            resume_at = self._clock() + timedelta(
                seconds=int(self.config.parse_fallback_sleep_s))

        new_rec = PauseRecord(
            resume_at=resume_at,
            reason=reason,
            detected_at=self._clock(),
            detected_by=lane_name or "?",
            buffer_applied_s=buffer_s,
        )

        with self._locked() as _:
            existing = self._read_unlocked()
            if existing is not None and existing.resume_at >= new_rec.resume_at:
                # The earlier record's pause is at least as long; just bump
                # the merge counter and keep the existing.
                merged = PauseRecord(
                    resume_at=existing.resume_at,
                    reason=existing.reason,
                    detected_at=existing.detected_at,
                    detected_by=existing.detected_by,
                    buffer_applied_s=existing.buffer_applied_s,
                    merged_count=existing.merged_count + 1,
                )
                self._write_unlocked(merged)
                logger.warning(
                    "rate_limit: %s also hit limit; merged into existing "
                    "pause (resume_at=%s, reason=%s, merge=%d)",
                    lane_name or "?", merged.resume_at.isoformat(),
                    merged.reason, merged.merged_count)
                return merged
            if existing is not None:
                new_rec.merged_count = existing.merged_count + 1
            self._write_unlocked(new_rec)

        logger.warning(
            "rate_limit: PAUSE recorded by %s. reason=%s "
            "resume_at=%s (in %.0fs)",
            lane_name or "?", new_rec.reason,
            new_rec.resume_at.isoformat(),
            (new_rec.resume_at - self._clock()).total_seconds())
        return new_rec

    def wait_if_paused(self, *, probe_fn: Any = None) -> None:
        """Block until any active pause clears.

        ``probe_fn`` is an optional callable invoked when the reason is
        ``unknown`` after each ``parse_fallback_sleep_s`` window. It must
        return ``True`` if the limit is lifted (no more rate-limit error)
        and ``False`` otherwise. When ``None`` (or the strategy is not
        ``"probe"``), the controller treats the recorded ``resume_at`` as
        authoritative and only sleeps once.
        """
        rec = self._read()
        if rec is None:
            return

        while True:
            now = self._clock()
            wait_s = (rec.resume_at - now).total_seconds()
            if wait_s <= 0:
                self._clear()
                logger.info("rate_limit: pause cleared.")
                return

            # Weekly hard-stop check, applied **before** sleeping so the
            # process can exit promptly.
            if (rec.reason == "weekly"
                    and self.config.weekly_over_limit_action == "stop"
                    and wait_s >= self.config.weekly_max_wait_h * 3600):
                self._write_exit_log(rec, wait_s)
                logger.error(
                    "rate_limit: weekly limit requires %.1fh wait "
                    "(threshold=%dh). Exiting with code %d.",
                    wait_s / 3600.0, self.config.weekly_max_wait_h,
                    WEEKLY_EXIT_CODE)
                sys.exit(WEEKLY_EXIT_CODE)

            logger.warning(
                "rate_limit: sleeping %.0fs (%.1fm) until %s",
                wait_s, wait_s / 60.0, rec.resume_at.isoformat())
            slept = self._sleep_chunked(wait_s)
            self._paused_seconds_total += slept

            # After waking, decide whether to probe or just trust resume_at.
            need_probe = (
                rec.reason == "unknown"
                and self.config.parse_fallback_strategy == "probe"
                and probe_fn is not None
            )
            if not need_probe:
                # Re-read in case another lane recorded a later pause while
                # we were sleeping.
                rec2 = self._read()
                if rec2 is None or rec2.resume_at <= self._clock():
                    self._clear()
                    return
                rec = rec2
                continue

            try:
                lifted = bool(probe_fn())
            except Exception:  # noqa: BLE001
                logger.exception("rate_limit: probe raised; treating as "
                                 "still-limited")
                lifted = False
            if lifted:
                self._clear()
                logger.info("rate_limit: probe succeeded, resuming.")
                return
            # Still limited → reschedule another fallback window.
            new_resume = self._clock() + timedelta(
                seconds=int(self.config.parse_fallback_sleep_s))
            rec = PauseRecord(
                resume_at=new_resume,
                reason="unknown",
                detected_at=self._clock(),
                detected_by="probe",
                buffer_applied_s=int(self.config.resume_buffer_s),
                merged_count=rec.merged_count + 1,
            )
            with self._locked() as _:
                self._write_unlocked(rec)
            logger.warning(
                "rate_limit: probe still limited; sleeping another %ds",
                int(self.config.parse_fallback_sleep_s))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read(self) -> PauseRecord | None:
        with self._locked() as _:
            return self._read_unlocked()

    def _read_unlocked(self) -> PauseRecord | None:
        if not self._pause_path.exists():
            return None
        try:
            data = json.loads(self._pause_path.read_text(encoding="utf-8"))
            return PauseRecord.from_json(data)
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            logger.warning("rate_limit: pause file unreadable (%s); "
                           "treating as no-pause", exc)
            return None

    def _write_unlocked(self, rec: PauseRecord) -> None:
        _atomic_write_json(self._pause_path, rec.to_json())

    def _clear(self) -> None:
        with self._locked() as _:
            try:
                self._pause_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("rate_limit: failed to clear pause file: %s",
                               exc)

    def _write_exit_log(self, rec: PauseRecord, wait_s: float) -> None:
        self._pause_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            f"detected_at: {rec.detected_at.isoformat()}",
            f"resume_at:   {rec.resume_at.isoformat()}",
            f"detected_by: {rec.detected_by}",
            f"reason:      {rec.reason}",
            f"wait_hours:  {wait_s / 3600.0:.2f}",
            f"weekly_max_wait_h: {self.config.weekly_max_wait_h}",
            "",
            "Re-run `python -m automation.persona_extraction <work_id> "
            "--resume` after the reset time to continue.",
        ]
        try:
            self._exit_log_path.write_text(
                "\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("rate_limit: failed to write exit log: %s", exc)

    def _sleep_chunked(self, total_s: float) -> float:
        """Sleep ``total_s`` in 30s chunks to stay responsive to SIGINT.

        Returns actual seconds slept. The OS-level signal handler installed
        by the orchestrator (``_handle_interrupt``) calls ``sys.exit(130)``,
        which interrupts even chunked sleeps cleanly. The loop is driven
        from a remaining-counter (not a wall-clock deadline) so tests can
        substitute a no-op sleeper without spinning.
        """
        remaining = max(0.0, float(total_s))
        slept = 0.0
        while remaining > 0:
            chunk = min(30.0, remaining)
            self._sleeper(chunk)
            slept += chunk
            remaining -= chunk
        return slept

    class _LockHandle:
        """Context manager wrapping fcntl.flock on a sibling lock file."""

        def __init__(self, lock_path: Path) -> None:
            self.lock_path = lock_path
            self._fd: int | None = None

        def __enter__(self) -> RateLimitController._LockHandle:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._fd = os.open(
                self.lock_path,
                os.O_RDWR | os.O_CREAT, 0o644,
            )
            fcntl.flock(self._fd, fcntl.LOCK_EX)
            return self

        def __exit__(self, *exc: Any) -> None:
            if self._fd is not None:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                finally:
                    os.close(self._fd)
                    self._fd = None

    def _locked(self) -> _LockHandle:
        return RateLimitController._LockHandle(self._lock_path)


# ---------------------------------------------------------------------------
# Process-wide singleton (so deeply-nested run_with_retry calls find it)
# ---------------------------------------------------------------------------

_active: RateLimitController | None = None


def set_active(controller: RateLimitController | None) -> None:
    """Install the controller used by ``llm_backend.run_with_retry``."""
    global _active
    _active = controller


def get_active() -> RateLimitController | None:
    """Return the installed controller (``None`` outside an extraction run)."""
    return _active
