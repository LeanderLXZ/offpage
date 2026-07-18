"""Smoke test for the single-pass repair loop + L3 gate.

After T-REPAIR-NO-REEXTRACT there is no full-file regeneration tier and
no lifecycle reset — a run is one Phase A→B→C pass with per-tier-capped
fixers (T0/T1/T2). Scenarios:

  (A) Phase A clean → run short-circuits to PASS, no fixer / regen calls.
  (B) Persistent semantic issue with no source_context — T2 can't touch
      it, nothing gets regenerated (there is no regen tier), the L3
      fallback re-flags it and the run FAILs. Asserts no whole-file
      regeneration ever happens.
  (C) Length-bound tolerance gate — strict minLength=100 fails on a
      95-char summary; T0 disabled so programmatic padding can't fix;
      T1 fails; after the capped tiers the decision #48 tolerance gate
      relaxes minLength × 0.9 to 90, accepts 95, and returns PASS.

Scoped L3 gate (T-GATE-SCOPED-RECHECK) — the round-level convergence fix
lives in the SemanticChecker / pipeline layer (the coordinator just feeds it
the touched json_paths), so D/E exercise it there rather than driving the
full T2 source-retrieval stack, which would test the retriever more than the
gate:

  (D) Scope filter — check_scoped keeps issues on (or under) a touched path
      and drops a nit on an untouched field. The kept in-scope finding is
      exactly what a round diff marks ``introduced``, so a real regression on
      a patched path still surfaces (the whole point of not going blind), while
      the whack-a-mole jitter that never converged is filtered.
  (E) Backend-failure preservation — a ``$``-anchored ``semantic_unavailable``
      issue survives scope filtering, so "review couldn't run" never collapses
      into a false clean pass. Also exercises ``run_semantic_scoped`` routing.
  (G) Ungated-file carry (T-GATE-UNMODIFIED-FILE-CARRY) — end-to-end: a file no
      fix touched this round is never gated, so its open semantic issue must be
      carried into the round diff rather than read as ``resolved``. Two files
      (one T0-fixable so the gate runs at all, one unfixable) → run must FAIL.

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
from ..checkers import CheckerPipeline
from ..checkers.semantic import SemanticChecker, SemanticReviewLLMUnavailable


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


def _scenario_d_scope_filter() -> None:
    """Scoped gate keeps only issues on (or under) a touched path.

    The stub reports three findings: one ON the touched path (``$.a``), one
    on a leaf UNDER it (``$.a.b`` — a genuinely new problem the fix may have
    introduced), and one on an UNTOUCHED field (``$.unrelated`` — the kind of
    nondeterministic nit the old full-file gate re-surfaced every round). With
    scope ``["$.a"]`` the first two survive and the third is dropped by the
    program guarantee — not left to the LLM's soft focus hint. Keeping the
    in-scope finding is what lets a real regression on a patched path still be
    marked ``introduced``; dropping the untouched-field one is what makes the
    loop converge.
    """
    target = _new_target({"a": {"b": "x"}, "unrelated": "y"})

    def stub(prompt: str, effort: str | None = None, **kwargs) -> str:
        assert "Focus review on these paths" in prompt, (
            "check_scoped must pass the focus hint into the prompt")
        return json.dumps([
            {"json_path": "$.a", "severity": "error",
             "rule": "fact_mismatch", "message": "problem on touched path"},
            {"json_path": "$.a.b", "severity": "error",
             "rule": "leaf_nit", "message": "new problem under touched path"},
            {"json_path": "$.unrelated", "severity": "error",
             "rule": "jitter", "message": "untouched-field review jitter"},
        ])

    issues = SemanticChecker(llm_call=stub).check_scoped(
        [FileEntry(path=str(target))], paths=["$.a"])
    rules = {i.rule for i in issues}
    assert rules == {"fact_mismatch", "leaf_nit"}, (
        f"scope filter should keep $.a + $.a.b and drop $.unrelated; "
        f"got {sorted(rules)}")
    print(f"  [D] PASS — scoped filter kept {sorted(rules)}, dropped jitter")


def _scenario_e_backend_failure_kept() -> None:
    """A backend-failure issue survives scope filtering → never a false pass.

    ``check_scoped`` filters to touched paths, but a ``$``-anchored
    ``semantic_unavailable`` (the review COULD NOT RUN) must not be filtered
    out — dropping it would report a clean pass on a file that was never
    reviewed. Also exercises ``pipeline.run_semantic_scoped`` → ``check_scoped``
    routing (the entry the Phase B gate uses).
    """
    target = _new_target({"a": 1})

    def stub(prompt: str, effort: str | None = None, **kwargs) -> str:
        raise SemanticReviewLLMUnavailable("backend down (stub)")

    pipeline = CheckerPipeline()
    pipeline.register(SemanticChecker(llm_call=stub))
    issues = pipeline.run_semantic_scoped(
        [FileEntry(path=str(target))], paths=["$.a"])
    assert len(issues) == 1 and issues[0].rule == "semantic_unavailable", (
        f"backend failure must survive scope filtering; "
        f"got {[i.rule for i in issues]}")
    print("  [E] PASS — backend-failure issue survived scope filtering")


def _scenario_f_gate_scope_carries_unfixed() -> None:
    """Gate scope for a file = touched paths ∪ still-open semantic paths.

    The regression this pins: if the scope carried ONLY the paths a fix
    touched, an unfixed semantic issue on an untouched path would never
    re-enter the gate result, the round diff would read it as ``resolved``,
    and a still-broken file would PASS. So a file where the round fixed S2 on
    ``$.y`` but left S1 on ``$.x`` must still scope ``$.x`` (carried) — and a
    same-named path on another file must not bleed into this file's scope.
    """
    from ..coordinator import _gate_scope
    from ..protocol import Issue

    s1 = Issue(file="F", json_path="$.x", category="semantic",
               severity="error", rule="fact_mismatch", message="unfixed")
    s2 = Issue(file="F", json_path="$.y", category="semantic",
               severity="error", rule="fact_mismatch", message="fixed")
    other = Issue(file="G", json_path="$.x", category="semantic",
                  severity="error", rule="fact_mismatch", message="other file")

    # This round touched only $.y on F (S2 fixed); S1@$.x untouched.
    scope_f = _gate_scope("F", {"F": {"$.y"}}, [s1, s2, other])
    assert scope_f == ["$.x", "$.y"], (
        f"F's scope must carry unfixed $.x AND touched $.y; got {scope_f}")
    # G shares the path string $.x but is a different file — no cross-file
    # bleed, and G isn't touched so only its own carried semantic path shows.
    scope_g = _gate_scope("G", {"F": {"$.y"}}, [s1, s2, other])
    assert scope_g == ["$.x"], (
        f"G's scope is its own $.x only, no bleed from F; got {scope_g}")
    print(f"  [F] PASS — scope carries unfixed + touched, no cross-file bleed "
          f"(F={scope_f}, G={scope_g})")


def _scenario_g_unmodified_file_carry() -> None:
    """A file no fix touched this round keeps its open semantic issue.

    Two files. ``g_schema.json`` overruns ``maxLength`` and T0 truncates it
    deterministically (note: T0 deliberately does NOT pad ``minLength`` —
    inventing text is fabrication — so an over-long value is the reliable way
    to make T0 actually land a patch here). The round therefore HAS patches and
    the L3 gate runs — but only on G, because ``gate_targets`` is
    ``modified_files``-gated. ``f_semantic.json`` carries a semantic error
    nothing can fix (no ``source_context`` → T2 skips it), so F is never
    modified and therefore never gated.

    That split matters: G being genuinely fixed is what makes ``gate_ever_ran``
    true, which sends Phase C down the **reuse** branch. Were no patch to land,
    the run would break early and Phase C's full-file **fallback** would
    re-detect F's issue anyway — the run would FAIL for the wrong reason and
    the test would pass even with the carry removed.

    Without the carry, F's issue has no source to re-enter
    ``combined_blocking``: the round diff reads it as ``resolved``, the loop
    early-exits on "all resolved", and Phase C's gate-reuse path reports PASS
    on a file with a known factual error (T-GATE-UNMODIFIED-FILE-CARRY). This
    asserts the run FAILs and F's issue survives into the result.
    """
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_carry_"))
    f_path = tmp / "f_semantic.json"
    g_path = tmp / "g_schema.json"
    f_path.write_text(
        json.dumps({"marker": "F-FILE", "note": "n" * 120}), encoding="utf-8")
    g_path.write_text(
        json.dumps({"marker": "G-FILE", "summary": "y" * 200}),
        encoding="utf-8")

    g_schema = {
        "type": "object",
        "properties": {
            "marker": {"type": "string"},
            "summary": {"type": "string", "minLength": 10, "maxLength": 150},
        },
        "required": ["marker", "summary"],
        "additionalProperties": False,
    }

    def stub(prompt: str, timeout: int = 600,
             effort: str | None = None) -> str:
        if "quality reviewer" in prompt:
            if "F-FILE" in prompt:
                return json.dumps([{
                    "json_path": "$.note",
                    "severity": "error",
                    "rule": "fact_mismatch",
                    "message": "F: contradicts source (stub)",
                }])
            return json.dumps([])       # G is semantically clean
        return "<<<malformed"           # any LLM fixer call fails

    cfg = RepairConfig(
        max_rounds=3, run_semantic=True, l3_gate_enabled=True,
        triage_enabled=False,
        retry_policy=RetryPolicy(t0_max=1, t1_max=1, t2_max=1,
                                 max_total_rounds=3))
    result = run(
        files=[FileEntry(path=str(f_path)),
               FileEntry(path=str(g_path), schema=g_schema)],
        config=cfg, source_context=None, llm_call=stub)

    assert not result.passed, (
        "F's unfixed semantic error must not be dropped just because no fix "
        f"touched F this round; report=\n{result.report}")
    assert any(i.rule == "fact_mismatch" for i in result.issues), (
        f"F's carried semantic issue must surface in the result; got "
        f"{[i.rule for i in result.issues]}")
    print("  [G] FAIL as expected — ungated file's open semantic issue carried")


def main() -> int:
    print("Scenario A: Phase A clean → PASS")
    _scenario_a()
    print("Scenario B: persistent semantic issue → FAIL, no regen")
    _scenario_b()
    print("Scenario C: length-bound tolerance gate PASS")
    _scenario_c()
    print("Scenario D: scoped gate filters to touched paths")
    _scenario_d_scope_filter()
    print("Scenario E: backend failure survives scope filter")
    _scenario_e_backend_failure_kept()
    print("Scenario F: gate scope carries unfixed semantic paths")
    _scenario_f_gate_scope_carries_unfixed()
    print("Scenario G: ungated file keeps its open semantic issue")
    _scenario_g_unmodified_file_carry()
    print("\nOK — single-pass repair behaves as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
