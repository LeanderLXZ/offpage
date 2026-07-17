"""Smoke test for the single-pass repair loop + L3 gate.

After T-REPAIR-NO-REEXTRACT there is no full-file regeneration tier and
no lifecycle reset — a run is one Phase A→B→C pass with per-tier-capped
fixers (T0/T1/T2). Three scenarios:

  (A) Phase A clean → run short-circuits to PASS, no fixer / regen calls.
  (B) Persistent semantic issue with no source_context — T2 can't touch
      it, nothing gets regenerated (there is no regen tier), the L3
      fallback re-flags it and the run FAILs. Asserts no whole-file
      regeneration ever happens.
  (C) Length-bound tolerance gate — strict minLength=100 fails on a
      95-char summary; T0 disabled so programmatic padding can't fix;
      T1 fails; after the capped tiers the decision #48 tolerance gate
      relaxes minLength × 0.9 to 90, accepts 95, and returns PASS.

Run:  python -m extraction.repair.tests._smoke_l3_gate
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ..protocol import (
    FileEntry, RepairConfig, RetryPolicy,
)
from ..coordinator import run


def _new_target(content: dict) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_"))
    target = tmp / "stage.json"
    target.write_text(json.dumps(content), encoding="utf-8")
    return target


def _scenario_a() -> None:
    """Phase A clean → run returns PASS without entering Phase B."""
    target = _new_target({"summary": "fine"})
    state = {"semantic_calls": 0, "patch_calls": 0}
    cfg = RepairConfig(
        max_rounds=3,
        run_semantic=True,
        l3_gate_enabled=True,
        retry_policy=RetryPolicy(t0_max=1, t1_max=1, t2_max=1,
                                 max_total_rounds=3),
    )

    def stub(prompt: str, timeout: int = 600,
             effort: str | None = None) -> str:
        if "quality reviewer" in prompt:
            state["semantic_calls"] += 1
            return json.dumps([])
        state["patch_calls"] += 1
        return "[]"

    result = run(files=[FileEntry(path=str(target))], config=cfg,
                 source_context=None, llm_call=stub)
    assert result.passed, "scenario A should PASS"
    assert state["patch_calls"] == 0, "no fixer should run on a clean file"
    print(f"  [A] PASS — semantic_calls={state['semantic_calls']}, "
          f"patch_calls={state['patch_calls']}")


def _scenario_b() -> None:
    """Persistent semantic issue, no source → FAIL, nothing regenerated."""
    target = _new_target({"summary": "original broken content"})
    state = {"semantic_calls": 0, "patch_calls": 0}

    def stub(prompt: str, timeout: int = 600,
             effort: str | None = None) -> str:
        if "quality reviewer" in prompt:
            state["semantic_calls"] += 1
            return json.dumps([{
                "json_path": "$.summary",
                "severity": "error",
                "rule": "fact_mismatch",
                "message": "summary contradicts source (stub)",
            }])
        # Any patch fixer call → malformed so nothing resolves.
        state["patch_calls"] += 1
        return "<<<malformed"

    cfg = RepairConfig(max_rounds=3, run_semantic=True, l3_gate_enabled=True,
                       triage_enabled=False,
                       retry_policy=RetryPolicy(t0_max=1, t1_max=1, t2_max=1,
                                                max_total_rounds=3))
    result = run(files=[FileEntry(path=str(target))], config=cfg,
                 source_context=None, llm_call=stub)
    assert not result.passed, "scenario B should FAIL (semantic unresolved)"
    assert any(i.rule == "fact_mismatch" for i in result.issues), (
        f"the semantic issue should surface in the result; got "
        f"{[i.rule for i in result.issues]}")
    assert "T3" not in result.report, (
        f"there is no T3 anymore; report must not mention it:\n{result.report}")
    print(f"  [B] FAIL as expected — semantic_calls={state['semantic_calls']}")


def _scenario_c() -> None:
    """Length-bound tolerance gate accepts a persistent length-only fail.

    T0 disabled (``t0_max=0``) so the programmatic length-padder can't
    auto-fix; T1 fails (LLM stub returns malformed). schema_minLength
    routes start=T0 / cap=T1, so after the capped tiers the residual is a
    single minLength miss. The decision #48 tolerance gate re-validates
    against the relaxed schema (minLength × 0.9 = 90); 95 ≥ 90 → accept.
    Run PASSES.
    """
    target = _new_target({"summary": "x" * 95})
    state = {"semantic_calls": 0, "patch_calls": 0}

    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "minLength": 100, "maxLength": 150}
        },
        "required": ["summary"],
        "additionalProperties": False,
    }

    def stub(prompt: str, timeout: int = 600,
             effort: str | None = None) -> str:
        if "quality reviewer" in prompt:
            state["semantic_calls"] += 1
            return json.dumps([])  # no semantic issues
        state["patch_calls"] += 1
        return "<<<malformed"  # T1 patch fixer fails

    cfg = RepairConfig(
        max_rounds=3,
        run_semantic=True,
        l3_gate_enabled=True,
        retry_policy=RetryPolicy(
            t0_max=0,  # disable T0 padding so the length issue persists
            t1_max=1, t2_max=1, max_total_rounds=3),
    )
    result = run(
        files=[FileEntry(path=str(target), schema=schema)],
        config=cfg, source_context=None, llm_call=stub)

    assert result.passed, (
        f"scenario C should PASS via length-bound tolerance gate; got "
        f"passed={result.passed}, report=\n{result.report}")
    print(f"  [C] PASS via tolerance — patch_calls={state['patch_calls']}")


def main() -> int:
    print("Scenario A: Phase A clean → PASS")
    _scenario_a()
    print("Scenario B: persistent semantic issue → FAIL, no regen")
    _scenario_b()
    print("Scenario C: length-bound tolerance gate PASS")
    _scenario_c()
    print("\nOK — single-pass repair behaves as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
