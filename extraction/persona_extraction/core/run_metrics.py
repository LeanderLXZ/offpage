"""Run-level LLM metrics ledger — per-call time / token / cost recording.

Every ``claude -p`` / ``codex`` invocation parses ``duration_seconds`` /
``num_turns`` / ``total_cost_usd`` and (on success) a ``usage`` block, but
historically only the *failure* path persisted them (``failed_lane_log``).
Successful runs discarded the numbers, so there was no structured per-phase
time / token account.

This module adds a process-wide append-only ledger. The orchestrator calls
``init_run_metrics`` once at run start (fixing the output filename via the
run-start timestamp) and ``set_phase`` at each phase boundary; the single
choke point ``llm_backend.run_with_retry`` calls ``record`` after every
``backend.run`` return. ``summarize`` prints a per-phase / per-lane aggregate
at run end.

Design constraints:
  * **Never raises into the caller.** Metrics are diagnostic; a broken ledger
    must not abort an extraction. Every public entry wraps its body in a
    best-effort ``try/except``.
  * **No-op until initialised.** Ad-hoc callers of ``run_with_retry`` (unit
    tests, ``json_repair``) that never call ``init_run_metrics`` see ``record``
    silently return.
  * **Reads from ``LLMResult`` only** — no coupling to backend internals. Token
    counts come from ``result.raw['usage']`` (populated on the success path);
    when ``raw`` is empty (failure path) it falls back to parsing
    ``result.raw_stdout``.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .llm_backend import LLMResult

logger = logging.getLogger(__name__)


class RunMetricsRecorder:
    """Append-only JSONL ledger of per-call LLM metrics for one run."""

    def __init__(self, jsonl_path: Path) -> None:
        self.jsonl_path = jsonl_path
        self.phase: str = "unknown"
        self._lock = threading.Lock()
        self._rows: list[dict[str, Any]] = []
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    def record(self, lane_name: str | None, result: "LLMResult",
               call_type: str | None = None) -> None:
        """Append one metrics row for a completed backend.run call.

        ``call_type`` sub-classifies a call *within* a lane. It exists because
        ``lane=repair`` alone cannot answer "how much did checking cost vs
        fixing" — the question `T-SEMANTIC-FULLFILE-COST` is blocked on. The
        label is supplied by the **call site**, never inferred here: only the
        caller knows whether it is checking or fixing, and inferring it from
        surrounding log lines is exactly the guesswork that stopped
        reproducing once the L3 gate went scoped (decision #66).

        Values are a closed set — extend it here, not ad hoc at call sites:

        ``check_full``    Phase A full semantic check (cold read, whole file)
        ``check_scoped``  L3 gate scoped re-check (decision #66)
        ``fix_t1``        T1 local patch
        ``fix_t2``        T2 source patch
        ``triage``        source-discrepancy triage

        ``None`` (the default) means "not a repair call" — extraction lanes,
        Phase 0 summarize, Phase 1/2 lanes. Those are already separable by
        ``lane`` (``world`` / ``char_snapshot`` / ``char_support``), so they
        get no second-level label rather than a made-up one.
        """
        usage = _extract_usage(result)
        row: dict[str, Any] = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "phase": self.phase,
            "lane": lane_name or "?",
            "call_type": call_type,
            "success": bool(result.success),
            "duration_s": round(result.duration_seconds, 1),
            "num_turns": result.num_turns,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cache_read": usage.get("cache_read_input_tokens"),
            "cache_creation": usage.get("cache_creation_input_tokens"),
            "cost": result.total_cost_usd,
        }
        line = json.dumps(row, ensure_ascii=False)
        with self._lock:
            self._rows.append(row)
            with self.jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def summarize(self) -> None:
        """Print a per-phase / per-lane-type / per-call-type aggregate table."""
        with self._lock:
            rows = list(self._rows)
        if not rows:
            return
        # Aggregate by (phase, lane-type, call-type). A lane-type collapses the
        # per-id tail: ``snapshot:<character_id>`` /
        # ``char_snapshot:<character_id>:char_social`` → ``snapshot`` /
        # ``char_snapshot`` so the table stays compact. The call-type splits a
        # lane into its check / fix / triage components — without it the whole
        # repair lane collapses into one row and "checking vs fixing" is
        # unanswerable. Unlabelled (non-repair) calls render as ``-``.
        agg: dict[tuple[str, str, str], dict[str, float]] = {}
        for r in rows:
            key = (r["phase"], _lane_type(r["lane"]),
                   r.get("call_type") or "-")
            a = agg.setdefault(
                key, {"calls": 0, "dur": 0.0, "in": 0, "out": 0, "cost": 0.0})
            a["calls"] += 1
            a["dur"] += r.get("duration_s") or 0.0
            a["in"] += r.get("input_tokens") or 0
            a["out"] += r.get("output_tokens") or 0
            a["cost"] += r.get("cost") or 0.0

        print("\n" + "=" * 60)
        print(f"  Run metrics summary  ({len(rows)} LLM calls)")
        print(f"  → {self.jsonl_path}")
        print("=" * 60)
        header = (f"  {'phase':<8} {'lane':<15} {'call_type':<13} {'calls':>5} "
                  f"{'dur_s':>8} {'in_tok':>9} {'out_tok':>9} {'cost':>8}")
        print(header)
        print("  " + "-" * (len(header) - 2))
        tot_calls = tot_in = tot_out = 0
        tot_dur = tot_cost = 0.0
        for (phase, lane, ctype), a in sorted(agg.items()):
            print(f"  {phase:<8} {lane:<15} {ctype:<13} {int(a['calls']):>5} "
                  f"{a['dur']:>8.1f} {int(a['in']):>9} {int(a['out']):>9} "
                  f"{a['cost']:>8.4f}")
            tot_calls += int(a["calls"])
            tot_dur += a["dur"]
            tot_in += int(a["in"])
            tot_out += int(a["out"])
            tot_cost += a["cost"]
        print("  " + "-" * (len(header) - 2))
        print(f"  {'TOTAL':<8} {'':<15} {'':<13} {tot_calls:>5} {tot_dur:>8.1f} "
              f"{tot_in:>9} {tot_out:>9} {tot_cost:>8.4f}")
        print("=" * 60)


def _lane_type(lane: str) -> str:
    """Collapse a lane name to its type prefix for aggregation."""
    # ``char_snapshot:<character_id>:char_social`` → ``char_snapshot``;
    # ``snapshot:<character_id>`` → ``snapshot``; ``repair[S001]`` → ``repair``.
    if "[" in lane:
        return lane.split("[", 1)[0]
    if ":" in lane:
        return lane.split(":", 1)[0]
    return lane


def _extract_usage(result: "LLMResult") -> dict[str, Any]:
    """Pull the ``usage`` block from a result.

    Success path stores the parsed claude JSON in ``result.raw``; failure
    path leaves ``raw`` empty but keeps (capped) stdout, so fall back to
    parsing that. Returns an empty dict when neither yields a usage block.
    """
    raw = result.raw if isinstance(result.raw, dict) else {}
    usage = raw.get("usage")
    if not isinstance(usage, dict):
        # Fallback: failure path — try the captured stdout.
        try:
            parsed = json.loads(result.raw_stdout or "")
            if isinstance(parsed, dict):
                usage = parsed.get("usage")
        except (json.JSONDecodeError, ValueError, TypeError):
            usage = None
    return usage if isinstance(usage, dict) else {}


# ---------------------------------------------------------------------------
# Process-wide singleton — so deeply-nested run_with_retry calls find it.
# ---------------------------------------------------------------------------

_recorder: RunMetricsRecorder | None = None


def init_run_metrics(project_root: Path, work_id: str) -> None:
    """Start a fresh ledger for this run.

    Output file: ``logs/runs/{work_id}_{YYYY-MM-DD_HHMMSS}.jsonl`` under the
    project root, timestamp fixed at call time so each run gets its own file.
    Best-effort: on any error the ledger stays uninitialised (record no-ops).
    """
    global _recorder
    try:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = project_root / "logs" / "runs" / f"{work_id}_{ts}.jsonl"
        _recorder = RunMetricsRecorder(path)
        logger.info("Run metrics ledger: %s", path)
    except Exception:  # noqa: BLE001
        logger.exception("init_run_metrics failed; metrics disabled")
        _recorder = None


def set_phase(phase: str) -> None:
    """Tag subsequent ``record`` rows with ``phase`` (no-op if uninitialised)."""
    if _recorder is not None:
        try:
            _recorder.set_phase(phase)
        except Exception:  # noqa: BLE001
            logger.exception("set_phase failed")


def record(lane_name: str | None, result: "LLMResult",
           call_type: str | None = None) -> None:
    """Append one metrics row (no-op if uninitialised or on any error).

    ``call_type`` — see ``Recorder.record`` for the closed value set.
    """
    if _recorder is None:
        return
    try:
        _recorder.record(lane_name, result, call_type)
    except Exception:  # noqa: BLE001
        logger.exception("run-metrics record failed (non-fatal)")


def summarize() -> None:
    """Print the run's aggregate table (no-op if uninitialised or on error)."""
    if _recorder is None:
        return
    try:
        _recorder.summarize()
    except Exception:  # noqa: BLE001
        logger.exception("run-metrics summarize failed (non-fatal)")
