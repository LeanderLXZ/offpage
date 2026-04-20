"""Token-limit pause and resume controller (§11.13).

When a Claude subscription hits the 5-hour rolling window or the weekly cap,
this module:

  1. Parses the reset time from stderr (timezone-aware, DST-safe via
     ``zoneinfo`` for ambiguous abbreviations).
  2. Atomically writes ``rate_limit_pause.json`` (flock + tempfile + replace),
     merging concurrent writes by taking the later ``resume_at``.
  3. Blocks new lane submissions in the orchestrator until the reset passes.
  4. Tracks accumulated pause wall-clock duration so ``--max-runtime`` excludes
     it (deduped by ``resume_at`` — N concurrent lanes sharing one pause
     window count as one, not N).
  5. Probes (with a minimal claude -p call) when the reset time can't be
     parsed. A single leader lane (elected via ``probing_by_pid`` + TTL in
     the pause file) runs the probe; other lanes wait silently.
  6. Raises :class:`RateLimitHardStop` when a pause exceeds
     ``rate_limit.weekly_max_wait_h`` (weekly) or ``rate_limit.probe_max_wait_h``
     (unparseable / probe session). The CLI entry point catches it and exits
     with code 2.

See ``docs/requirements.md`` §11.13 for the full mechanism.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import re
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import RateLimitConfig, get_config

logger = logging.getLogger(__name__)


PAUSE_FILE_NAME = "rate_limit_pause.json"
EXIT_LOG_NAME = "rate_limit_exit.log"
WEEKLY_EXIT_CODE = 2


class RateLimitHardStop(Exception):
    """Raised when a pause crosses a hard-stop threshold.

    Two triggers:
      * ``reason="weekly"`` — weekly wait ≥ ``weekly_max_wait_h``.
      * ``reason="probe_exhausted"`` — single probe session wall-clock wait
        ≥ ``probe_max_wait_h`` (Anthropic appears stuck / error format
        unparseable).

    The CLI entry point (``automation.persona_extraction.cli.main``) catches
    this and exits with :data:`WEEKLY_EXIT_CODE`. When raised from a worker
    thread, the exception is stored in the ``Future``; the main thread
    re-raises it via ``future.result()`` on the next ``as_completed`` yield,
    so the process tears down cleanly (vs. the prior ``sys.exit`` which only
    killed the worker thread).
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail


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

# Unambiguous timezone abbreviations → fixed UTC offset (minutes).
# Season-specific codes (PST/PDT, EST/EDT, ...) carry no DST ambiguity.
_TZ_OFFSETS_MIN: dict[str, int] = {
    "UTC": 0, "GMT": 0, "Z": 0,
    "PST": -8 * 60, "PDT": -7 * 60,
    "MST": -7 * 60, "MDT": -6 * 60,
    "CST": -6 * 60, "CDT": -5 * 60,
    "EST": -5 * 60, "EDT": -4 * 60,
}

# Ambiguous US/Canada codes → IANA zones; resolved via ``zoneinfo`` so the
# offset tracks the DST window on the parsed date. Anthropic's error strings
# typically use "PT"/"ET" without the S/D disambiguation, and a fixed-offset
# fallback would be off by 1 hour on half the calendar.
_TZ_ZONE_NAMES: dict[str, str] = {
    "PT": "America/Los_Angeles",
    "MT": "America/Denver",
    "CT": "America/Chicago",
    "ET": "America/New_York",
}


def _resolve_tz(tz_abbr: str) -> Any:
    """Map a timezone abbreviation to a ``tzinfo``.

    Ambiguous codes (PT/MT/CT/ET) are resolved through ``zoneinfo`` so DST
    is handled correctly. Unknown abbreviations fall back to UTC.
    """
    if tz_abbr in _TZ_ZONE_NAMES:
        try:
            return ZoneInfo(_TZ_ZONE_NAMES[tz_abbr])
        except ZoneInfoNotFoundError:
            logger.warning(
                "rate_limit: tzdata missing for %s; falling back to UTC",
                tz_abbr)
            return timezone.utc
    offset_min = _TZ_OFFSETS_MIN.get(tz_abbr)
    if offset_min is None:
        return timezone.utc
    return timezone(timedelta(minutes=offset_min))


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
        tz = _resolve_tz(tz_abbr)
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
    # Probe leader election (only meaningful when reason == "unknown" +
    # parse_fallback_strategy == "probe"). The leader PID owns the next
    # probe call; other lanes wait silently. The claim expires after
    # ``probe_claim_ttl_s`` so a crashed leader cannot block forever.
    probing_by_pid: int | None = None
    probing_claim_at: datetime | None = None
    # Wall-clock anchor for the probe hard-stop (``probe_max_wait_h``).
    # Carries through merges / new-resume rewrites so the total "since
    # Anthropic first became unreachable" window is preserved across
    # probe attempts. ``None`` for non-probe pauses (5h / weekly).
    probe_session_started_at: datetime | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "resume_at": self.resume_at.isoformat(),
            "reason": self.reason,
            "detected_at": self.detected_at.isoformat(),
            "detected_by": self.detected_by,
            "buffer_applied_s": self.buffer_applied_s,
            "merged_count": self.merged_count,
        }
        if self.probing_by_pid is not None:
            out["probing_by_pid"] = self.probing_by_pid
        if self.probing_claim_at is not None:
            out["probing_claim_at"] = self.probing_claim_at.isoformat()
        if self.probe_session_started_at is not None:
            out["probe_session_started_at"] = (
                self.probe_session_started_at.isoformat())
        return out

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> PauseRecord:
        def _opt_dt(key: str) -> datetime | None:
            v = data.get(key)
            return datetime.fromisoformat(v) if v else None

        probing_pid_raw = data.get("probing_by_pid")
        return cls(
            resume_at=datetime.fromisoformat(data["resume_at"]),
            reason=data.get("reason", "unknown"),
            detected_at=datetime.fromisoformat(
                data.get("detected_at", data["resume_at"])),
            detected_by=data.get("detected_by", "?"),
            buffer_applied_s=int(data.get("buffer_applied_s", 0)),
            merged_count=int(data.get("merged_count", 1)),
            probing_by_pid=(int(probing_pid_raw)
                            if probing_pid_raw is not None else None),
            probing_claim_at=_opt_dt("probing_claim_at"),
            probe_session_started_at=_opt_dt("probe_session_started_at"),
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
        # Wall-clock seconds spent in pause gates, deduped across lanes
        # sharing the same pause window. Subtracted from --max-runtime.
        self._paused_seconds_total: float = 0.0
        # Highest ``resume_at`` already counted into the total. When N lanes
        # sleep through the same pause they all see this same resume_at and
        # only the first lane to reach the accounting block wins.
        self._accounted_resume_at: datetime | None = None
        self._account_lock = threading.Lock()

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
        now = self._clock()
        reset_at = parse_reset_time(stderr, now=now)
        buffer_s = int(self.config.resume_buffer_s)

        if reset_at is not None:
            resume_at = reset_at + timedelta(seconds=buffer_s)
            probe_anchor = None
        else:
            # Unparseable: schedule the first probe one fallback-window
            # away. ``probe_session_started_at`` anchors the probe
            # hard-stop (``probe_max_wait_h``); preserved across
            # follow-up probe rewrites below.
            resume_at = now + timedelta(
                seconds=int(self.config.parse_fallback_sleep_s))
            probe_anchor = now

        new_rec = PauseRecord(
            resume_at=resume_at,
            reason=reason,
            detected_at=now,
            detected_by=lane_name or "?",
            buffer_applied_s=buffer_s,
            probe_session_started_at=probe_anchor,
        )

        with self._locked() as _:
            existing = self._read_unlocked()
            if existing is not None and existing.resume_at >= new_rec.resume_at:
                # The earlier record's pause is at least as long; just bump
                # the merge counter and keep the existing record (preserves
                # its probe_session_started_at and any leader claim).
                merged = PauseRecord(
                    resume_at=existing.resume_at,
                    reason=existing.reason,
                    detected_at=existing.detected_at,
                    detected_by=existing.detected_by,
                    buffer_applied_s=existing.buffer_applied_s,
                    merged_count=existing.merged_count + 1,
                    probing_by_pid=existing.probing_by_pid,
                    probing_claim_at=existing.probing_claim_at,
                    probe_session_started_at=existing.probe_session_started_at,
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
                # Preserve probe anchor across upgrade from short fallback
                # to a parseable reset (or vice versa) within the same run.
                if (existing.probe_session_started_at is not None
                        and new_rec.probe_session_started_at is None):
                    new_rec.probe_session_started_at = (
                        existing.probe_session_started_at)
            self._write_unlocked(new_rec)

        logger.warning(
            "rate_limit: PAUSE recorded by %s. reason=%s "
            "resume_at=%s (in %.0fs)",
            lane_name or "?", new_rec.reason,
            new_rec.resume_at.isoformat(),
            (new_rec.resume_at - now).total_seconds())
        return new_rec

    def wait_if_paused(self, *, probe_fn: Any = None) -> None:
        """Block until any active pause clears.

        ``probe_fn`` is an optional callable invoked when the reason is
        ``unknown`` after each ``parse_fallback_sleep_s`` window. It must
        return ``True`` if the limit is lifted (no more rate-limit error)
        and ``False`` otherwise. When ``None`` (or the strategy is not
        ``"probe"``), the controller treats the recorded ``resume_at`` as
        authoritative and only sleeps once.

        Concurrency contract:
          * ``paused_seconds_total`` accumulates **once per pause window**
            (keyed on ``resume_at``). Ten lanes sleeping through the same
            30-minute window count as 30 minutes total, not 300.
          * Probe calls are serialized via leader election
            (``probing_by_pid`` + TTL in the pause file). Only the leader
            lane hits Anthropic; follower lanes wait silently for the
            leader to update the record.
          * Weekly overruns and exhausted probe sessions raise
            :class:`RateLimitHardStop`, which the CLI catches and maps to
            :data:`WEEKLY_EXIT_CODE`. Raising (vs. ``sys.exit``) lets the
            exception bubble cleanly from worker threads through
            ``Future.result()`` into the main thread.
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

            # Weekly hard-stop — checked before sleeping so the process
            # unwinds promptly even if many lanes are queued on the gate.
            if (rec.reason == "weekly"
                    and self.config.weekly_over_limit_action == "stop"
                    and wait_s >= self.config.weekly_max_wait_h * 3600):
                self._write_exit_log(rec, wait_s)
                logger.error(
                    "rate_limit: weekly limit requires %.1fh wait "
                    "(threshold=%dh). Raising hard-stop (exit %d).",
                    wait_s / 3600.0, self.config.weekly_max_wait_h,
                    WEEKLY_EXIT_CODE)
                raise RateLimitHardStop(
                    "weekly",
                    f"weekly wait {wait_s / 3600.0:.1f}h exceeds "
                    f"threshold {self.config.weekly_max_wait_h}h")

            # Probe hard-stop — Anthropic has been unreachable or the
            # stderr format has been unparseable for longer than a single
            # probe session is allowed to drag on.
            if rec.probe_session_started_at is not None:
                probe_elapsed = (
                    now - rec.probe_session_started_at).total_seconds()
                cap_s = self.config.probe_max_wait_h * 3600
                if probe_elapsed >= cap_s:
                    self._write_exit_log(rec, probe_elapsed,
                                         session_kind="probe")
                    logger.error(
                        "rate_limit: probe session has waited %.1fh "
                        "(cap=%dh) without recovery. Raising hard-stop.",
                        probe_elapsed / 3600.0,
                        self.config.probe_max_wait_h)
                    raise RateLimitHardStop(
                        "probe_exhausted",
                        f"probe session {probe_elapsed / 3600.0:.1f}h "
                        f"exceeds cap {self.config.probe_max_wait_h}h")

            logger.warning(
                "rate_limit: sleeping %.0fs (%.1fm) until %s",
                wait_s, wait_s / 60.0, rec.resume_at.isoformat())
            slept = self._sleep_chunked(wait_s)
            self._account_slept(rec.resume_at, slept)

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

            # Leader election: only one lane probes per window. Others
            # back off briefly and re-check the record, which the leader
            # will have updated (cleared / new resume_at) by then.
            is_leader, rec = self._claim_probe_leadership(rec)
            if not is_leader:
                self._follower_wait()
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
            # Still limited → reschedule another fallback window and
            # release the leader claim so another lane can take over
            # next round if this process crashes.
            new_resume = self._clock() + timedelta(
                seconds=int(self.config.parse_fallback_sleep_s))
            rec = PauseRecord(
                resume_at=new_resume,
                reason="unknown",
                detected_at=self._clock(),
                detected_by="probe",
                buffer_applied_s=int(self.config.resume_buffer_s),
                merged_count=rec.merged_count + 1,
                probing_by_pid=None,
                probing_claim_at=None,
                probe_session_started_at=rec.probe_session_started_at,
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

    def _write_exit_log(
        self,
        rec: PauseRecord,
        wait_s: float,
        *,
        session_kind: str = "weekly",
    ) -> None:
        """Persist exit context for operator triage (shared weekly + probe).

        ``session_kind`` distinguishes the two hard-stop triggers:
          * ``"weekly"`` — weekly wait ≥ ``weekly_max_wait_h``.
          * ``"probe"`` — probe session ≥ ``probe_max_wait_h``.
        """
        self._pause_dir.mkdir(parents=True, exist_ok=True)
        cap = (self.config.weekly_max_wait_h if session_kind == "weekly"
               else self.config.probe_max_wait_h)
        lines = [
            f"session_kind: {session_kind}",
            f"detected_at: {rec.detected_at.isoformat()}",
            f"resume_at:   {rec.resume_at.isoformat()}",
            f"detected_by: {rec.detected_by}",
            f"reason:      {rec.reason}",
            f"wait_hours:  {wait_s / 3600.0:.2f}",
            f"cap_hours:   {cap}",
            "",
            "Re-run `python -m automation.persona_extraction <work_id> "
            "--resume` after the reset time to continue.",
        ]
        try:
            self._exit_log_path.write_text(
                "\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("rate_limit: failed to write exit log: %s", exc)

    def _account_slept(
        self, resume_at: datetime, slept: float,
    ) -> None:
        """Add ``slept`` to paused total only if this pause window isn't
        already accounted.

        Multiple lanes sharing the same ``resume_at`` all call this after
        their chunked sleep. The first caller wins; subsequent ones are
        no-ops. A later pause (different ``resume_at``) resets the anchor
        and counts as a new window.
        """
        with self._account_lock:
            if (self._accounted_resume_at is None
                    or resume_at > self._accounted_resume_at):
                self._paused_seconds_total += slept
                self._accounted_resume_at = resume_at

    def _claim_probe_leadership(
        self, rec: PauseRecord,
    ) -> tuple[bool, PauseRecord]:
        """Try to become the probe leader for the current window.

        Returns ``(is_leader, updated_rec)``. The file-level flock
        serializes the claim so exactly one caller wins per window.
        A claim expires after ``probe_claim_ttl_s`` to cover crashed /
        orphaned leaders.
        """
        my_pid = os.getpid()
        ttl = timedelta(seconds=int(self.config.probe_claim_ttl_s))
        with self._locked() as _:
            existing = self._read_unlocked()
            if existing is None:
                return False, rec  # pause cleared under us
            now = self._clock()
            claim_valid = (
                existing.probing_by_pid is not None
                and existing.probing_claim_at is not None
                and now - existing.probing_claim_at < ttl
            )
            if claim_valid and existing.probing_by_pid != my_pid:
                return False, existing
            claimed = PauseRecord(
                resume_at=existing.resume_at,
                reason=existing.reason,
                detected_at=existing.detected_at,
                detected_by=existing.detected_by,
                buffer_applied_s=existing.buffer_applied_s,
                merged_count=existing.merged_count,
                probing_by_pid=my_pid,
                probing_claim_at=now,
                probe_session_started_at=existing.probe_session_started_at,
            )
            self._write_unlocked(claimed)
            return True, claimed

    def _follower_wait(self) -> None:
        """Back off before re-reading the pause record as a follower.

        Chunked through ``_sleep_chunked`` so SIGINT handling is unchanged
        and so test sleepers stay deterministic. The wait never accumulates
        into ``paused_seconds_total`` — only leaders account, keyed on
        ``resume_at``.
        """
        poll_s = min(
            float(self.config.probe_follower_poll_s),
            float(self.config.probe_claim_ttl_s),
        )
        self._sleep_chunked(poll_s)

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
