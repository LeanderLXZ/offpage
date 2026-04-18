"""Smoke test for L3 gate + T3 per-file cap.

Scenario: a file has a persistent semantic issue that T1/T2/T3 all
falsely claim to fix. Without the L3 gate, this slips through Phase B
and is only caught at Phase C. With the gate, it's caught mid-loop
and T3 is capped at 1 global use.

Run:  python -m automation.repair_agent._smoke_l3_gate
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .protocol import (
    FileEntry, Issue, RepairConfig, RetryPolicy, SourceContext,
)
from .coordinator import run


def _make_stub_llm(state: dict):
    """LLM stub driven by call counters in ``state``."""

    def stub(prompt: str, timeout: int = 600) -> str:
        state["calls"] += 1
        text = prompt

        # Regen fixer prompts include "regeneration tool" in the system.
        if "regeneration tool" in text:
            state["regen_calls"] += 1
            # Return valid JSON that looks "fixed" but isn't — file stays
            # broken so the gate should still flag it.
            return json.dumps({"summary": "regenerated placeholder"})

        # Semantic review prompts: always report the same unresolved
        # issue — simulating "LLM keeps finding the same problem".
        if "quality reviewer" in text:
            state["semantic_calls"] += 1
            return json.dumps([{
                "json_path": "$.summary",
                "severity": "error",
                "rule": "fact_mismatch",
                "message": "summary contradicts source (stub)",
            }])

        # Local/source patch prompts — fixer expects a patch object.
        # Return something that passes json.loads but contains no edits,
        # so the fingerprint does NOT show up in resolved_fingerprints.
        state["patch_calls"] += 1
        return "[]"

    return stub


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_"))
    target = tmp / "stage.json"
    target.write_text(
        json.dumps({"summary": "original broken content"}), encoding="utf-8")

    state = {"calls": 0, "semantic_calls": 0,
             "regen_calls": 0, "patch_calls": 0}
    llm = _make_stub_llm(state)

    cfg = RepairConfig(
        max_rounds=3,
        run_semantic=True,
        l3_gate_enabled=True,
        retry_policy=RetryPolicy(
            t0_max=1, t1_max=1, t2_max=1, t3_max=1, t3_max_per_file=1,
            max_total_rounds=3,
        ),
    )

    result = run(
        files=[FileEntry(path=str(target))],
        config=cfg,
        source_context=None,
        llm_call=llm,
    )

    print(f"passed:           {result.passed}")
    print(f"final issues:     {len(result.issues)}")
    print(f"total LLM calls:  {state['calls']}")
    print(f"  semantic:       {state['semantic_calls']}")
    print(f"  regen (T3):     {state['regen_calls']}")
    print(f"  patch (T1/T2):  {state['patch_calls']}")

    # Expectations
    assert not result.passed, "should fail — issue never actually fixed"
    assert state["regen_calls"] <= 1, (
        f"T3 per-file cap breached: {state['regen_calls']} regen calls")
    assert state["semantic_calls"] >= 2, (
        f"L3 gate did not run: {state['semantic_calls']} semantic calls "
        f"(expected Phase A + at least 1 gate)")

    print("\nOK — L3 gate fired, T3 capped at 1, verdict FAIL as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
