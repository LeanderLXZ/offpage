"""Process guard — PID lockfile, memory reading, background support."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Memory reading (Linux /proc)
# ---------------------------------------------------------------------------

def get_rss_mb(pid: int) -> float | None:
    """Read RSS in MB from /proc/{pid}/status. Returns None on failure."""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024  # kB → MB
    except (OSError, ValueError, IndexError):
        return None
    return None


def fmt_memory(mb: float | None) -> str:
    """Format memory as human-readable string."""
    if mb is None:
        return "?"
    if mb < 1024:
        return f"{mb:.0f}MB"
    return f"{mb / 1024:.1f}GB"


# ---------------------------------------------------------------------------
# PID lock — prevents duplicate extraction runs
# ---------------------------------------------------------------------------

class PidLock:
    """File-based PID lock for a work extraction run.

    Default lock file location:
      works/{work_id}/analysis/.extraction.lock

    Use ``lock_name`` to create independent locks (e.g. ".scene_archive.lock").
    """

    def __init__(self, project_root: Path, work_id: str,
                 lock_name: str = ".extraction.lock"):
        self.lock_path = (project_root / "works" / work_id
                          / "analysis" / lock_name)

    def is_held(self) -> dict | None:
        """Check if lock is held by a live process.

        Returns the lock info dict if held, None otherwise.
        Automatically cleans up stale locks from dead processes.
        """
        if not self.lock_path.exists():
            return None

        try:
            data = json.loads(self.lock_path.read_text(encoding="utf-8"))
            pid = data["pid"]
        except (json.JSONDecodeError, KeyError, OSError):
            # Corrupt lock — remove it
            self.lock_path.unlink(missing_ok=True)
            return None

        # Check if process is still alive
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            # Process is dead — stale lock
            logger.info("Removing stale lock (PID %d is dead)", pid)
            self.lock_path.unlink(missing_ok=True)
            return None
        except PermissionError:
            # Process exists but we can't signal it (different user)
            return data

        return data

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns False if held by another process."""
        existing = self.is_held()
        if existing:
            return False

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        # lock_path: works/{work_id}/analysis/{lock_name}
        # parent = analysis/ ; parent.parent = works/{work_id}/ (whose .name is work_id)
        self.lock_path.write_text(
            json.dumps({
                "pid": os.getpid(),
                "started": datetime.now().isoformat(timespec="seconds"),
                "work_id": self.lock_path.parent.parent.name,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Lock acquired (PID %d)", os.getpid())
        return True

    def release(self) -> None:
        """Release the lock (only if we own it)."""
        if not self.lock_path.exists():
            return
        try:
            data = json.loads(self.lock_path.read_text(encoding="utf-8"))
            if data.get("pid") == os.getpid():
                self.lock_path.unlink(missing_ok=True)
                logger.info("Lock released (PID %d)", os.getpid())
        except (json.JSONDecodeError, KeyError, OSError):
            pass


# ---------------------------------------------------------------------------
# Background launcher
# ---------------------------------------------------------------------------

def launch_background(
    work_id: str,
    project_root: Path,
    extra_argv: list[str],
) -> int:
    """Re-launch the orchestrator in background (survives SSH disconnect).

    Returns the child PID.
    """
    log_path = (project_root / "works" / work_id
                / "analysis" / "progress" / "extraction.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Build command: same as current invocation but without --background
    cmd = [sys.executable, "-u", "-m", "automation.persona_extraction"] + extra_argv

    with open(log_path, "a", encoding="utf-8") as log_f:
        log_f.write(f"\n{'=' * 60}\n")
        log_f.write(f"  Background session started: {datetime.now()}\n")
        log_f.write(f"  Command: {' '.join(cmd)}\n")
        log_f.write(f"{'=' * 60}\n\n")
        log_f.flush()

        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # survives SSH disconnect
        )

    print(f"  Started in background: PID {proc.pid}")
    print(f"  Log: {log_path}")
    print(f"  Follow: tail -f \"{log_path}\"")
    print(f"  Stop:   kill {proc.pid}")

    return proc.pid
