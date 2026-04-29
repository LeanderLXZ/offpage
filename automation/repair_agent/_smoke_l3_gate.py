"""Smoke test for L3 gate + lifecycle reset.

Three scenarios:
  (A) Single-lifecycle PASS — Phase A finds nothing → run short-circuits.
  (B) Lifecycle 1 T3 → lifecycle 2 PASS — T1/T2 fail, T3 fires, the
      semantic stub flips to "clean" on lifecycle 2 so Phase A passes.
  (C) Lifecycle 1 T3 → lifecycle 2 T3_EXHAUSTED — semantic stub keeps
      reporting the same issue forever; lifecycle 2 hits T3_EXHAUSTED
      because T3 is disabled.

Run:  python -m automation.repair_agent._smoke_l3_gate
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .protocol import (
    FileEntry, RepairConfig, RetryPolicy,
)
from .coordinator import run


def _make_stub_llm(state: dict, *, semantic_clean_after_cycle: int | None = None):
    """LLM stub driven by call counters in ``state``.

    ``semantic_clean_after_cycle``: once the semantic checker has been
    invoked this many times, subsequent semantic calls return ``[]``
    (no issues). Used to simulate "lifecycle 2 sees a clean file".
    """

    def stub(prompt: str, timeout: int = 600) -> str:
        state["calls"] += 1
        text = prompt

        if "regeneration tool" in text:
            state["regen_calls"] += 1
            return json.dumps({"summary": "regenerated placeholder"})

        if "quality reviewer" in text:
            state["semantic_calls"] += 1
            if (semantic_clean_after_cycle is not None
                    and state["semantic_calls"] > semantic_clean_after_cycle):
                return json.dumps([])
            return json.dumps([{
                "json_path": "$.summary",
                "severity": "error",
                "rule": "fact_mismatch",
                "message": "summary contradicts source (stub)",
            }])

        # T1/T2 patch fixers feed the response into json.loads. Return
        # malformed JSON so each patcher fails silently and the
        # escalation chain reaches T3.
        state["patch_calls"] += 1
        return "<<<malformed"

    return stub


def _new_target(content: dict) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_"))
    target = tmp / "stage.json"
    target.write_text(json.dumps(content), encoding="utf-8")
    return target


def _scenario_a() -> None:
    """Phase A clean → run returns PASS without entering Phase B."""
    target = _new_target({"summary": "fine"})
    state = {"calls": 0, "semantic_calls": 0, "regen_calls": 0, "patch_calls": 0}
    cfg = RepairConfig(
        max_rounds=3,
        run_semantic=True,
        l3_gate_enabled=True,
        retry_policy=RetryPolicy(t0_max=1, t1_max=1, t2_max=1, t3_max=1,
                                 max_total_rounds=3),
    )
    # Stub returns no semantic issues from the start.
    def stub(prompt: str, timeout: int = 600) -> str:
        state["calls"] += 1
        if "quality reviewer" in prompt:
            state["semantic_calls"] += 1
            return json.dumps([])
        return "[]"

    result = run(files=[FileEntry(path=str(target))], config=cfg,
                 source_context=None, llm_call=stub)
    assert result.passed, "scenario A should PASS"
    assert state["regen_calls"] == 0, "T3 must not fire on clean run"
    print(f"  [A] PASS — semantic_calls={state['semantic_calls']}, "
          f"regen={state['regen_calls']}")


def _scenario_b() -> None:
    """Lifecycle 1 T3 fires; lifecycle 2 sees a clean file → PASS."""
    target = _new_target({"summary": "original broken content"})
    state = {"calls": 0, "semantic_calls": 0, "regen_calls": 0, "patch_calls": 0}
    # Lifecycle 1 Phase A returns 1 issue (call #1); Phase B may invoke
    # the semantic stub again only via L3 gate (which we suppress by
    # going straight to T3 here, so #1 is the only flagging call).
    # Lifecycle 2 Phase A is call #2 — return [] from there onward.
    llm = _make_stub_llm(state, semantic_clean_after_cycle=1)
    cfg = RepairConfig(max_rounds=3, run_semantic=True, l3_gate_enabled=True,
                       retry_policy=RetryPolicy(t0_max=1, t1_max=1, t2_max=1,
                                                t3_max=1, max_total_rounds=3))
    result = run(files=[FileEntry(path=str(target))], config=cfg,
                 source_context=None, llm_call=llm)
    assert result.passed, (
        f"scenario B should PASS after lifecycle reset; got "
        f"passed={result.passed}, report=\n{result.report}")
    assert state["regen_calls"] == 1, (
        f"T3 should fire exactly once in lifecycle 1, got "
        f"regen={state['regen_calls']}")
    print(f"  [B] PASS — semantic_calls={state['semantic_calls']}, "
          f"regen={state['regen_calls']}")


def _scenario_c() -> None:
    """Persistent issue → lifecycle 1 T3 → lifecycle 2 T3_EXHAUSTED."""
    target = _new_target({"summary": "original broken content"})
    state = {"calls": 0, "semantic_calls": 0, "regen_calls": 0, "patch_calls": 0}
    llm = _make_stub_llm(state)
    cfg = RepairConfig(max_rounds=3, run_semantic=True, l3_gate_enabled=True,
                       retry_policy=RetryPolicy(t0_max=1, t1_max=1, t2_max=1,
                                                t3_max=1, max_total_rounds=3))
    result = run(files=[FileEntry(path=str(target))], config=cfg,
                 source_context=None, llm_call=llm)
    assert not result.passed, "scenario C should FAIL"
    assert "T3_EXHAUSTED" in result.report, (
        f"expected T3_EXHAUSTED termination marker in report:\n{result.report}")
    assert state["regen_calls"] == 1, (
        f"T3 should fire exactly once (lifecycle 1 only), got "
        f"regen={state['regen_calls']}")
    print(f"  [C] T3_EXHAUSTED — semantic_calls={state['semantic_calls']}, "
          f"regen={state['regen_calls']}")


def main() -> int:
    print("Scenario A: single-lifecycle PASS")
    _scenario_a()
    print("Scenario B: lifecycle 1 T3 → lifecycle 2 PASS")
    _scenario_b()
    print("Scenario C: persistent issue → T3_EXHAUSTED")
    _scenario_c()
    print("\nOK — lifecycle reset behaves as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
