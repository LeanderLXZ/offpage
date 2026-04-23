"""Structured JSONL recorder for repair agent events.

One file per repaired target at
``works/{work_id}/analysis/progress/repair_{stage_id}_{slug(file)}.jsonl``.
Each line is a self-describing JSON object. The repair coordinator emits
events at key transitions (phase starts, issue discovery, escalations,
fixes, triage verdicts, round summaries, completion). Consumers can
replay the run without re-parsing free-form log lines.

Orchestrator dispatches ``coordinator.run(files=[single])`` per file in
parallel (see ``[repair_agent].repair_concurrency``); each worker opens
its own recorder, so writes are naturally lock-free.

Intentionally minimal: open / write / close. No rotation, no query
helpers — read the JSONL with `jq` or a one-off Python script.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

logger = logging.getLogger(__name__)


class RepairRecorder:
    """Append-only JSONL sink for a single file's repair run.

    Open at the start of one file's repair, call ``write(event, **fields)``
    at each transition, then ``close()`` (or use as a context manager).
    Every call flushes so partial state survives a crash. One recorder
    instance owns one JSONL file; parallel per-file repair workers each
    hold their own recorder, so writes are lock-free by construction.
    """

    def __init__(self, path: Path):
        self.path: Path = path
        self._fh: TextIO | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.path, "a", encoding="utf-8")
        except OSError as exc:
            logger.warning("RepairRecorder: could not open %s: %s",
                           self.path, exc)
            self._fh = None

    def write(self, event: str, **fields: Any) -> None:
        if self._fh is None:
            return
        rec: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event,
        }
        rec.update(fields)
        try:
            self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self._fh.flush()
        except OSError as exc:
            logger.warning("RepairRecorder write failed: %s", exc)

    def close(self) -> None:
        if self._fh is None:
            return
        try:
            self._fh.close()
        except OSError:
            pass
        self._fh = None

    def __enter__(self) -> "RepairRecorder":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
