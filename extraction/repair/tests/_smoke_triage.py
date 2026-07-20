"""Smoke test for source-discrepancy triage.

Builds a fake work layout with one character file whose summary field
contradicts a line from a fake source chapter. Drives the coordinator
with a stub LLM that:
  * emits one persistent L3 issue from the semantic reviewer
  * refuses to apply any T1/T2 patch
  * when asked to triage, accepts the issue as source_inherent with a
    verbatim quote from the fake chapter

The fixture satisfies ``TargetsKeysEqBaselineChecker`` — it writes a
``target_baseline.json`` plus the three matching target structures
inside the snapshot. Miss either half and that L2 checker errors, the
pipeline then skips L3 for the file by design, and every scenario below
silently stops testing triage at all. The two halves fail differently:
a missing baseline file yields ``targets_baseline_missing`` anchored at
the root (``json_path="$"``), which routes to ``NO_FIX_TIER``; a missing
structure yields ``targets_keys_eq_baseline_missing_structure`` anchored
at that structure's own path, which does not.

Scenarios exercised:
  (a) triage accepts a valid quote → the semantic residual is accepted
      as a SourceNote
  (b) bad-quote triage is rejected by program verification
  (c) accept_cap_per_file caps acceptance within a single run
  (d) non-semantic issues cannot reach the LLM-triage path
  (f) coverage_shortage accepted via 0-token verdict;
      Phase C must not resurface the accepted issue (H1 regression guard)

Run:  python -m extraction.repair.tests._smoke_triage
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ..coordinator import _run_triage_round, run
from ..notes_writer import NotesWriter
from ..protocol import (
    FileEntry,
    Issue,
    RepairConfig,
    RetryPolicy,
    SourceContext,
    SourceNote,
)
from ..triage import Triager


CHAPTER_TEXT = (
    "A001 walked into the hall.\n"
    "S002 was waiting by the window.\n"
    "Later, the narrator called A001 'the wanderer' but A001 was "
    "already named 'the seeker' in chapter one.\n"
)


def _d4_structures(targets: tuple[str, ...]) -> dict:
    """The three target structures a character snapshot must carry.

    ``TargetsKeysEqBaselineChecker`` (L2) demands each of them exist and
    key exactly on ``target_baseline.targets[].target_character_id``.
    Examples arrays stay empty — the structural checker skips empty
    entries (never-appeared target, D4 state 3), so the fixture adds no
    unintended min_examples shortage.
    """
    return {
        "voice_state": {"target_voice_map": [
            {"target_character_id": t, "dialogue_examples": []}
            for t in targets]},
        "behavior_state": {"target_behavior_map": [
            {"target_character_id": t, "action_examples": []}
            for t in targets]},
        "relationships": [{"target_character_id": t} for t in targets],
    }


def _write_work_layout(
    root: Path,
    stage_id: str = "S001",
    baseline_targets: tuple[str, ...] = (),
    snapshot_overrides: dict | None = None,
) -> tuple[Path, SourceContext]:
    """Lay out a minimal work directory the triage path can navigate.

    Writes a character package that satisfies
    ``TargetsKeysEqBaselineChecker``: a ``target_baseline.json`` holding
    ``baseline_targets`` plus a snapshot carrying the matching three
    target structures. ``snapshot_overrides`` replaces top-level snapshot
    keys wholesale (scenario F swaps in a short ``target_voice_map``).
    """
    work = root / "works" / "smoke"
    canon = work / "characters" / "A001" / "canon"
    chars = canon / "stage_snapshots"
    chars.mkdir(parents=True, exist_ok=True)

    (canon / "target_baseline.json").write_text(
        json.dumps({"targets": [{"target_character_id": t}
                                for t in baseline_targets]},
                   ensure_ascii=False),
        encoding="utf-8",
    )

    snapshot: dict = {"summary": "A001 is the wanderer — single name"}
    snapshot.update(_d4_structures(baseline_targets))
    snapshot.update(snapshot_overrides or {})

    target = chars / f"{stage_id}.json"
    target.write_text(
        json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    chapters_dir = work / "sources" / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    (chapters_dir / "0001.txt").write_text(CHAPTER_TEXT, encoding="utf-8")

    summaries_dir = work / "sources" / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    (summaries_dir / "0001.json").write_text(
        json.dumps({"summary": "A001 gets two names"}), encoding="utf-8")

    analysis = work / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (analysis / "stage_plan.json").write_text(
        json.dumps({"stages": [{"stage_id": stage_id,
                                "chapters": "C0001-C0001"}]}),
        encoding="utf-8",
    )

    ctx = SourceContext(
        work_path=str(work),
        stage_id=stage_id,
        chapter_summaries_dir=str(summaries_dir),
        chapters_dir=str(chapters_dir),
    )
    return target, ctx


def _stub_llm_accepting(quote: str):
    """LLM that always triages the single issue as source_inherent."""
    state = {"semantic": 0, "triage": 0, "patch": 0}

    def stub(prompt: str, timeout: int = 600,
             effort: str | None = None, **kwargs) -> str:
        if "quality reviewer" in prompt:
            state["semantic"] += 1
            return json.dumps([{
                "json_path": "$.summary",
                "severity": "error",
                "rule": "fact_mismatch",
                "message": "summary uses one name but source gives two",
            }])
        if "source-discrepancy triage tool" in prompt:
            state["triage"] += 1
            return json.dumps({"verdicts": [{
                "issue_fingerprint": _expected_fingerprint(prompt),
                "source_inherent": True,
                "discrepancy_type": "author_contradiction",
                "chapter_number": 1,
                "line_range": [3, 3],
                "quote": quote,
                "rationale": "chapter uses two different names for A001",
                "extraction_choice": "kept 'the wanderer' — the later one",
            }]})
        state["patch"] += 1
        return "[]"

    return stub, state


def _expected_fingerprint(prompt: str) -> str:
    # Simple scan: fingerprint is printed into the triage prompt under
    # "fingerprint: ..." lines. Return the first match.
    for line in prompt.splitlines():
        line = line.strip()
        if line.startswith("fingerprint:"):
            return line.split("fingerprint:", 1)[1].strip()
    return ""


def scenario_a_triage_accept() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_triage_a_"))
    target, ctx = _write_work_layout(tmp)

    stub, state = _stub_llm_accepting(
        "Later, the narrator called A001 'the wanderer' but A001 was "
        "already named 'the seeker' in chapter one.")
    cfg = RepairConfig(
        max_rounds=2, run_semantic=True, l3_gate_enabled=True,
        triage_enabled=True, accept_cap_per_file=3,
        retry_policy=RetryPolicy(
            t0_max=1, t1_max=1, t2_max=1,
            max_total_rounds=2),
    )

    result = run(files=[FileEntry(path=str(target))],
                 config=cfg, source_context=ctx, llm_call=stub)

    notes_path = (Path(ctx.work_path) / "characters" / "A001" / "canon"
                  / "extraction_notes" / "S001.jsonl")

    print(f"[A] passed={result.passed}  notes={len(result.accepted_notes)}  "
          f"triage calls={state['triage']}")
    assert result.accepted_notes, "expected at least one accepted note"
    assert notes_path.exists(), f"notes file not written: {notes_path}"

    lines = [l for l in notes_path.read_text(encoding="utf-8").splitlines()
             if l.strip()]
    assert len(lines) == len(result.accepted_notes), (
        f"expected {len(result.accepted_notes)} lines, got {len(lines)}")
    parsed = json.loads(lines[0])
    assert parsed["note_id"] == "SN-S001-01", parsed["note_id"]
    assert parsed["issue_category"] == "semantic"
    assert parsed["discrepancy_type"] == "author_contradiction"
    assert parsed["triage_round"] in (1, 2)
    assert parsed["source_evidence"]["chapter_number"] == 1
    assert len(parsed["source_evidence"]["quote_sha256"]) == 64

    print("[A] OK — triage accepted, notes persisted")


def scenario_b_bad_quote_rejected() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_triage_b_"))
    target, ctx = _write_work_layout(tmp)

    # Quote does NOT appear in chapter text — verification must reject.
    stub, state = _stub_llm_accepting(
        "This sentence is NOT in the chapter at all.")
    cfg = RepairConfig(
        max_rounds=1, run_semantic=True, l3_gate_enabled=True,
        triage_enabled=True, accept_cap_per_file=3,
        retry_policy=RetryPolicy(
            t0_max=1, t1_max=1, t2_max=1,
            max_total_rounds=1),
    )

    result = run(files=[FileEntry(path=str(target))],
                 config=cfg, source_context=ctx, llm_call=stub)

    notes_path = (Path(ctx.work_path) / "characters" / "A001" / "canon"
                  / "extraction_notes" / "S001.jsonl")

    print(f"[B] passed={result.passed}  notes={len(result.accepted_notes)}")
    assert not result.passed, "should fail — bad quote means no acceptance"
    assert not result.accepted_notes, "bad quote must not produce a note"
    assert not notes_path.exists() or (
        not notes_path.read_text(encoding="utf-8").strip()), (
        "no notes file should be written when all quotes fail verification")

    print("[B] OK — bad quote rejected by program verification")


def scenario_c_cap_enforced() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_triage_c_"))
    target, ctx = _write_work_layout(tmp)

    # Semantic reviewer emits FIVE distinct issues; triage accepts all;
    # cap of 2 should hold.
    valid_quote = (
        "Later, the narrator called A001 'the wanderer' but A001 was "
        "already named 'the seeker' in chapter one.")

    def stub(prompt: str, timeout: int = 600,
             effort: str | None = None, **kwargs) -> str:
        if "quality reviewer" in prompt:
            return json.dumps([
                {"json_path": f"$.field_{n}",
                 "severity": "error",
                 "rule": f"rule_{n}",
                 "message": f"issue {n}"}
                for n in range(5)
            ])
        if "source-discrepancy triage tool" in prompt:
            fps = [l.split("fingerprint:", 1)[1].strip()
                   for l in prompt.splitlines()
                   if l.strip().startswith("fingerprint:")]
            return json.dumps({"verdicts": [
                {"issue_fingerprint": fp,
                 "source_inherent": True,
                 "discrepancy_type": "typo",
                 "chapter_number": 1,
                 "line_range": [3, 3],
                 "quote": valid_quote,
                 "rationale": "source typo",
                 "extraction_choice": "kept as-is"}
                for fp in fps
            ]})
        return "[]"

    cfg = RepairConfig(
        max_rounds=1, run_semantic=True, l3_gate_enabled=True,
        triage_enabled=True, accept_cap_per_file=2,
        retry_policy=RetryPolicy(
            t0_max=1, t1_max=1, t2_max=1,
            max_total_rounds=1),
    )

    result = run(files=[FileEntry(path=str(target))],
                 config=cfg, source_context=ctx, llm_call=stub)

    notes_path = (Path(ctx.work_path) / "characters" / "A001" / "canon"
                  / "extraction_notes" / "S001.jsonl")
    if notes_path.exists():
        lines = [l for l in notes_path.read_text(encoding="utf-8").splitlines()
                 if l.strip()]
    else:
        lines = []

    # A run is a single pass now — accept_cap_per_file caps the notes
    # accepted, and the disk JSONL matches 1:1.
    cap = cfg.accept_cap_per_file
    print(f"[C] passed={result.passed}  notes={len(result.accepted_notes)}  "
          f"persisted_lines={len(lines)}")
    assert len(result.accepted_notes) <= cap, (
        f"accept_cap breached: {len(result.accepted_notes)} > {cap}")
    assert len(lines) == len(result.accepted_notes)

    print(f"[C] OK — accept_cap_per_file enforced "
          f"(cap={cap}, total notes={len(result.accepted_notes)})")


def scenario_d_non_semantic_rejected() -> None:
    """Regression: the LLM-triage path (`_run_triage_round`) only accepts
    ``semantic`` issues.

    Structural ``coverage_shortage`` SourceNotes are built by the 0-token
    ``Triager.build_coverage_shortage_verdict`` path instead — they never
    reach ``_run_triage_round``. A structural (L2) issue sent through
    ``_run_triage_round`` — even if a compromised LLM stub returns a
    valid-looking verdict — must NOT produce a SourceNote: the category
    filter at the top of ``_run_triage_round`` drops it before any LLM
    call (the ``issue_category`` enum itself now admits both ``semantic``
    and ``structural`` to support the coverage_shortage path).
    """
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_triage_d_"))
    target, ctx = _write_work_layout(tmp)

    # An adversarial LLM that would happily triage anything as inherent.
    valid_quote = (
        "Later, the narrator called A001 'the wanderer' but A001 was "
        "already named 'the seeker' in chapter one.")

    def stub(prompt: str, timeout: int = 600,
             effort: str | None = None, **kwargs) -> str:
        if "source-discrepancy triage tool" in prompt:
            fps = [l.split("fingerprint:", 1)[1].strip()
                   for l in prompt.splitlines()
                   if l.strip().startswith("fingerprint:")]
            return json.dumps({"verdicts": [
                {"issue_fingerprint": fp,
                 "source_inherent": True,
                 "discrepancy_type": "other",
                 "chapter_number": 1,
                 "line_range": [3, 3],
                 "quote": valid_quote,
                 "rationale": "would accept anything",
                 "extraction_choice": "n/a"}
                for fp in fps
            ]})
        return "[]"

    structural_issue = Issue(
        file=str(target),
        json_path="$.required_field",
        category="structural",
        severity="error",
        rule="min_examples",
        message="needs more examples",
    )
    semantic_issue = Issue(
        file=str(target),
        json_path="$.summary",
        category="semantic",
        severity="error",
        rule="fact_mismatch",
        message="contradicts source",
    )

    cfg = RepairConfig(triage_enabled=True, accept_cap_per_file=3)
    triager = Triager(llm_call=stub)
    notes_writer = NotesWriter(ctx.work_path)
    accepted_notes: list[SourceNote] = []
    notes_per_file: dict[str, int] = {}

    remaining = _run_triage_round(
        triager=triager, notes_writer=notes_writer, config=cfg,
        source_ctx=ctx,
        issues=[structural_issue, semantic_issue],
        triage_round=1,
        accepted_notes=accepted_notes,
        notes_per_file=notes_per_file,
        fixer_candidates={},
    )

    print(f"[D] returned_remaining={len(remaining)}  "
          f"notes={len(accepted_notes)}")
    # Structural issue must pass through untouched; semantic one accepted.
    assert any(i.category == "structural" for i in remaining), (
        "structural issue must be returned untouched")
    # All accepted notes must have issue_category == "semantic"
    for n in accepted_notes:
        assert n.issue_category == "semantic", (
            f"schema violation: note {n.note_id} has "
            f"issue_category={n.issue_category!r}")
    # The structural issue's fingerprint must never become a note.
    assert not any(n.issue_fingerprint == structural_issue.fingerprint
                   for n in accepted_notes), (
        "structural issue must not produce a SourceNote")

    print("[D] OK — non-semantic issue refused, semantic one accepted")


def scenario_f_coverage_shortage_accepted() -> None:
    """Regression guard for the L2 ``coverage_shortage`` fast path (H1).

    Crafts a stage_snapshot whose ``target_voice_map[0].dialogue_examples``
    holds fewer entries than ``importance_min_examples`` demands for a
    主角. Drives the coordinator end-to-end with a no-op T2 stub so the
    shortage survives the single T2 attempt. Expectations:

    * The 0-token ``build_coverage_shortage_verdict`` path produces one
      ``SourceNote`` (``discrepancy_type="coverage_shortage"``,
      ``issue_category="structural"``); zero LLM calls on the triage
      channel.
    * Phase C final validation reruns structural checks — the shortage
      is still there because accept_with_notes never edits the JSON —
      yet ``result.passed`` must be True because the coordinator filters
      already-accepted fingerprints out of the final blocking set. This
      is the H1 regression that would otherwise FAIL the stage.
    """
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_triage_f_"))
    # Target is S002, NOT the owning character A001 — a baseline listing
    # its own character is a `target_self_reference` error in phase 2.
    # 主角 → threshold 5; one example → shortage of 4. The behavior map
    # and relationships keep their empty S002 entries from the shared
    # fixture, so this is the run's only coverage shortage (the two
    # relationships warnings it also raises never enter the blocking set).
    # The three S002 literals below — baseline target, voice-map key, and
    # importance_map key — must stay in sync: a mismatched importance key
    # silently drops the threshold to 1 and the shortage disappears.
    target, ctx = _write_work_layout(
        tmp,
        baseline_targets=("S002",),
        snapshot_overrides={
            "voice_state": {
                "target_voice_map": [{
                    "target_character_id": "S002",
                    "dialogue_examples": ["only example"],
                }],
            },
        },
    )

    # Count any stray triage-prompt calls — they should stay at 0.
    calls = {"triage": 0, "patch": 0, "semantic": 0}

    def stub(prompt: str, timeout: int = 600,
             effort: str | None = None, **kwargs) -> str:
        if "quality reviewer" in prompt:
            calls["semantic"] += 1
            return "[]"
        if "source-discrepancy triage tool" in prompt:
            calls["triage"] += 1
            return json.dumps({"verdicts": []})
        # T2 source_patch prompt — return malformed JSON so the fixer
        # takes the ``except json.JSONDecodeError`` branch and applies
        # nothing. Returning "[]" would be parsed as an empty list and
        # silently overwrite the field with [], pre-empting the
        # coverage_shortage fast path.
        calls["patch"] += 1
        return "not valid json"

    cfg = RepairConfig(
        max_rounds=2, run_semantic=False, l3_gate_enabled=True,
        triage_enabled=True, accept_cap_per_file=5,
        retry_policy=RetryPolicy(
            t0_max=1, t1_max=1, t2_max=1,
            max_total_rounds=2),
    )

    result = run(
        files=[FileEntry(path=str(target))],
        config=cfg, source_context=ctx, llm_call=stub,
        importance_map={"S002": "主角"},
    )

    notes_path = (Path(ctx.work_path) / "characters" / "A001" / "canon"
                  / "extraction_notes" / "S001.jsonl")

    print(f"[F] passed={result.passed}  notes={len(result.accepted_notes)}  "
          f"triage_calls={calls['triage']}")

    assert result.passed, (
        "Phase C must not FAIL after coverage_shortage accept; H1 "
        "regression suspected (accepted fingerprint resurfaced in "
        "final validation)")
    assert len(result.accepted_notes) == 1, (
        f"expected exactly one coverage_shortage SourceNote, "
        f"got {len(result.accepted_notes)}")
    note = result.accepted_notes[0]
    assert note.discrepancy_type == "coverage_shortage", note.discrepancy_type
    assert note.issue_category == "structural", note.issue_category
    assert note.extraction_choice == "keep_current_count", (
        note.extraction_choice)
    assert calls["triage"] == 0, (
        f"coverage_shortage must be 0-token; saw {calls['triage']} "
        f"triage LLM calls")
    assert notes_path.exists(), f"notes file not written: {notes_path}"

    print("[F] OK — coverage_shortage accepted at 0 token, Phase C clean")


def main() -> int:
    scenario_a_triage_accept()
    scenario_b_bad_quote_rejected()
    scenario_c_cap_enforced()
    scenario_d_non_semantic_rejected()
    scenario_f_coverage_shortage_accepted()
    print("\nAll triage smoke scenarios passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
