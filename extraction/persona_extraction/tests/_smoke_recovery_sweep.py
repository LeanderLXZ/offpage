"""Smoke test for Phase 0 recovery sweep (decision #49).

Three scenarios:
  (A) Mixed candidates — sweep picks only ``state=='failed'`` AND
      ``recovery_attempted==False`` AND error contains ``'timed out'``
      / ``'error_max_turns'``; other failed kinds (e.g. schema fail) and
      already-swept candidates are skipped.
  (B) Recovery success — mock ``_summarize_chunk`` returns success →
      chunk state flips ``failed → done``, ``recovery_attempted=True``.
  (C) Recovery failure — mock ``_summarize_chunk`` returns failure →
      chunk stays ``failed``, ``recovery_attempted=True`` so subsequent
      runs skip it.

Run:  python -m extraction.persona_extraction.tests._smoke_recovery_sweep
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from ..lifecycle.progress import ChunkEntry, Phase0Progress
from ..orchestrator import ExtractionOrchestrator


def _build_progress(work_id: str = "smoke") -> Phase0Progress:
    """Construct a Phase0Progress with 5 chunks covering 4 sweep cases."""
    p = Phase0Progress(
        work_id=work_id,
        total_chapters=100,
        chunk_size=20,
        total_chunks=5,
    )
    # 1 done, 4 failed across different cases:
    p.chunks["chunk_001"] = ChunkEntry(
        chunk_id="chunk_001", chapters="C0001-C0020", state="done")
    # candidate: failed + timed out + not swept
    p.chunks["chunk_002"] = ChunkEntry(
        chunk_id="chunk_002", chapters="C0021-C0040",
        state="failed", retry_count=1,
        error_message="claude -p timed out")
    # candidate: failed + max_turns + not swept
    p.chunks["chunk_003"] = ChunkEntry(
        chunk_id="chunk_003", chapters="C0041-C0060",
        state="failed", retry_count=1,
        error_message="exit 1 [subtype=error_max_turns num_turns=81]: ")
    # NOT a candidate: failed but already swept
    p.chunks["chunk_004"] = ChunkEntry(
        chunk_id="chunk_004", chapters="C0061-C0080",
        state="failed", retry_count=2,
        error_message="recovery (effort=high) failed: still timed out",
        recovery_attempted=True)
    # NOT a candidate: failed but error is schema (not timeout/max_turns)
    p.chunks["chunk_005"] = ChunkEntry(
        chunk_id="chunk_005", chapters="C0081-C0100",
        state="failed", retry_count=1,
        error_message="Schema validation failed (L3 also failed): "
                      "summaries/3/summary: 'xxx' is too short")
    return p


def _make_stub_orchestrator(work_id: str = "smoke"):
    """Bare orchestrator with just enough plumbing for _run_recovery_sweep
    to call _summarize_chunk (which we patch). No real backend / disk."""
    # Build a minimal instance bypassing __init__ to avoid backend setup.
    o = object.__new__(ExtractionOrchestrator)
    o.project_root = Path(tempfile.mkdtemp(prefix="recovery_smoke_"))
    o.work_id = work_id
    o.concurrency = 4
    o.pipeline = None
    o.phase3 = None
    o.backend = None
    o.reviewer_backend = None
    o.start_phase = "auto"
    o.chunk_size = 20
    o.max_runtime_minutes = 0
    return o


def _scenario_a_b_c_combined() -> None:
    """Run sweep with mocked _summarize_chunk that succeeds for chunk_002
    and fails for chunk_003; verify only those two are touched."""
    o = _make_stub_orchestrator()
    phase0 = _build_progress()
    # Patch save() to a no-op so we don't need a real disk layout.
    phase0.save = lambda root: None  # type: ignore[assignment]

    summaries_dir = o.project_root / "summaries"
    summaries_dir.mkdir(exist_ok=True)
    chunks = [
        (1, 1, 20), (2, 21, 40), (3, 41, 60), (4, 61, 80), (5, 81, 100),
    ]

    swept_ids: list[int] = []

    def fake_summarize_chunk(idx, total_chunks, start, end, sdir,
                              **kwargs):
        # Verify _recovery_effort is propagated as 'high'
        assert kwargs.get("_recovery_effort") == "high", kwargs
        swept_ids.append(idx)
        if idx == 2:
            return idx, True, ""
        # idx == 3: simulate failure
        return idx, False, "claude -p timed out"

    with patch.object(o, "_summarize_chunk", side_effect=fake_summarize_chunk):
        o._run_recovery_sweep(phase0, summaries_dir, total_chunks=5,
                              chunks=chunks)

    # Scenario A: only chunks 002 + 003 swept (timeout / max_turns + not
    # already attempted). chunk_001 (done), chunk_004 (already attempted),
    # chunk_005 (schema fail not in scope) must NOT be touched.
    assert sorted(swept_ids) == [2, 3], (
        f"sweep should touch only chunks 2 + 3, got {sorted(swept_ids)}")

    # Scenario B: chunk_002 success → done + recovery_attempted=True
    e2 = phase0.chunks["chunk_002"]
    assert e2.state == "done", e2
    assert e2.recovery_attempted is True, e2
    assert e2.error_message == "", e2
    assert e2.retry_count == 2, e2  # was 1, sweep increments

    # Scenario C: chunk_003 fail → state stays failed but
    # recovery_attempted=True so next resume skips
    e3 = phase0.chunks["chunk_003"]
    assert e3.state == "failed", e3
    assert e3.recovery_attempted is True, e3
    assert "recovery (effort=high) failed" in e3.error_message, e3
    assert e3.retry_count == 2, e3

    # Untouched chunks
    e1 = phase0.chunks["chunk_001"]
    assert e1.state == "done" and e1.recovery_attempted is False, e1
    e4 = phase0.chunks["chunk_004"]
    assert e4.state == "failed" and e4.recovery_attempted is True, e4  # unchanged
    e5 = phase0.chunks["chunk_005"]
    assert e5.state == "failed" and e5.recovery_attempted is False, e5  # unchanged

    print("  [A] Sweep candidate filter — only timeout/max_turns + "
          "not-attempted passed through (skipped done / already-attempted "
          "/ schema-fail)")
    print("  [B] Recovery success — chunk_002 state=done, "
          "recovery_attempted=True, error cleared")
    print("  [C] Recovery failure — chunk_003 state=failed but "
          "recovery_attempted=True (no further sweep on resume)")


def _scenario_d_no_candidates() -> None:
    """Empty / no-candidate case — sweep must be a no-op and not crash."""
    o = _make_stub_orchestrator()
    phase0 = Phase0Progress(work_id="smoke_empty", total_chapters=20,
                             chunk_size=20, total_chunks=1)
    phase0.chunks["chunk_001"] = ChunkEntry(
        chunk_id="chunk_001", chapters="C0001-C0020", state="done")
    phase0.save = lambda root: None  # type: ignore[assignment]
    summaries_dir = o.project_root / "summaries_empty"
    summaries_dir.mkdir(exist_ok=True)

    called = [False]

    def must_not_call(*a, **kw):
        called[0] = True
        return 0, True, ""

    with patch.object(o, "_summarize_chunk", side_effect=must_not_call):
        o._run_recovery_sweep(phase0, summaries_dir, total_chunks=1,
                              chunks=[(1, 1, 20)])

    assert called[0] is False, "sweep called _summarize_chunk on no-candidate run"
    print("  [D] No-candidate — sweep is a no-op, _summarize_chunk not called")


def main() -> int:
    print("Scenario A/B/C combined: sweep filter + success + failure")
    _scenario_a_b_c_combined()
    print("Scenario D: no candidates → no-op")
    _scenario_d_no_candidates()
    print("\nOK — recovery sweep behaves as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
