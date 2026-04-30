"""Smoke test for source-discrepancy triage.

Builds a fake work layout with one character file whose summary field
contradicts a line from a fake source chapter. Drives the coordinator
with a stub LLM that:
  * emits one persistent L3 issue from the semantic reviewer
  * refuses to apply any T1/T2 patch
  * when asked to triage, accepts the issue as source_inherent with a
    verbatim quote from the fake chapter

Scenarios exercised:
  (a) pre-T3 triage accepts a valid quote → T3 never fires
  (b) bad-quote triage is rejected by program verification
  (c) accept_cap_per_file caps acceptance
  (d) non-semantic issues cannot reach the LLM-triage path
  (e) T3-only self-reports are still tracked for post-gate triage
  (f) coverage_shortage accepted via 0-token verdict;
      Phase C must not resurface the accepted issue (H1 regression guard)

Run:  python -m automation.repair_agent._smoke_triage
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .coordinator import _run_triage_round, run
from .notes_writer import NotesWriter
from .protocol import (
    FileEntry,
    Issue,
    RepairConfig,
    RetryPolicy,
    SourceContext,
)
from .triage import Triager


CHAPTER_TEXT = (
    "A001 walked into the hall.\n"
    "S002 was waiting by the window.\n"
    "Later, the narrator called A001 'the wanderer' but A001 was "
    "already named 'the seeker' in chapter one.\n"
)


def _write_work_layout(root: Path, stage_id: str = "S001") -> tuple[
    Path, SourceContext]:
    """Lay out a minimal work directory the triage path can navigate."""
    work = root / "works" / "smoke"
    chars = work / "characters" / "A001" / "canon" / "stage_snapshots"
    chars.mkdir(parents=True, exist_ok=True)

    target = chars / f"{stage_id}.json"
    target.write_text(
        json.dumps({"summary": "A001 is the wanderer — single name"},
                   ensure_ascii=False),
        encoding="utf-8",
    )

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
                                "chapters": "0001-0001"}]}),
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
    state = {"semantic": 0, "triage": 0, "patch": 0, "regen": 0}

    def stub(prompt: str, timeout: int = 600) -> str:
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
        if "regeneration tool" in prompt:
            state["regen"] += 1
            return json.dumps({"summary": "still broken"})
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


def scenario_a_pre_t3_accept() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_triage_a_"))
    target, ctx = _write_work_layout(tmp)

    stub, state = _stub_llm_accepting(
        "Later, the narrator called A001 'the wanderer' but A001 was "
        "already named 'the seeker' in chapter one.")
    cfg = RepairConfig(
        max_rounds=2, run_semantic=True, l3_gate_enabled=True,
        triage_enabled=True, accept_cap_per_file=3,
        retry_policy=RetryPolicy(
            t0_max=1, t1_max=1, t2_max=1, t3_max=1,
            max_total_rounds=2),
    )

    result = run(files=[FileEntry(path=str(target))],
                 config=cfg, source_context=ctx, llm_call=stub)

    notes_path = (Path(ctx.work_path) / "characters" / "A001" / "canon"
                  / "extraction_notes" / "S001.jsonl")

    print(f"[A] passed={result.passed}  notes={len(result.accepted_notes)}  "
          f"T3 regen calls={state['regen']}  triage calls={state['triage']}")
    assert result.accepted_notes, "expected at least one accepted note"
    assert state["regen"] == 0, "T3 should be skipped when triage accepts"
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

    print("[A] OK — pre-T3 triage accepted, notes persisted")


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
            t0_max=1, t1_max=1, t2_max=1, t3_max=1,
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

    def stub(prompt: str, timeout: int = 600) -> str:
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
        if "regeneration tool" in prompt:
            return json.dumps({"summary": "still broken"})
        return "[]"

    cfg = RepairConfig(
        max_rounds=1, run_semantic=True, l3_gate_enabled=True,
        triage_enabled=True, accept_cap_per_file=2,
        retry_policy=RetryPolicy(
            t0_max=1, t1_max=1, t2_max=1, t3_max=1,
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

    # Cap is per-lifecycle (independent counters per cycle); disk JSONL
    # is append-only across lifecycles. With cap=2 and the default
    # max_lifecycles_per_file=2, lifecycle 1 may accept 2 and lifecycle 2
    # may accept up to 2 more before hitting cap again — total ≤ 4 lines
    # on disk. The PER-CYCLE invariant is the one being enforced.
    cycles = cfg.max_lifecycles_per_file
    cap = cfg.accept_cap_per_file
    print(f"[C] passed={result.passed}  notes={len(result.accepted_notes)}  "
          f"persisted_lines={len(lines)}")
    assert len(result.accepted_notes) <= cycles * cap, (
        f"per-lifecycle cap × {cycles} cycles breached: "
        f"{len(result.accepted_notes)} > {cycles * cap}")
    assert len(lines) == len(result.accepted_notes)

    print(f"[C] OK — per-lifecycle accept_cap_per_file enforced "
          f"(cap={cap}, cycles={cycles}, total notes={len(result.accepted_notes)})")


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

    def stub(prompt: str, timeout: int = 600) -> str:
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
    accepted_notes = []
    notes_per_file = {}

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


def scenario_e_t3_self_report_tracked() -> None:
    """Regression: T3 that only self-reports must still be tracked.

    With bug B present, ``t3_files`` would be derived from
    ``resolved_fingerprints`` only. When T3 self-reports every issue,
    that set is empty → L3 gate skips the file → post-gate triage never
    fires → no SourceNote is accepted. Post-fix, the union with
    ``source_inherent_candidates`` keeps the file in ``modified_files``
    so the gate runs, post-gate triage accepts, and the T3 cap increments.
    """
    tmp = Path(tempfile.mkdtemp(prefix="repair_smoke_triage_e_"))
    target, ctx = _write_work_layout(tmp)

    valid_quote = (
        "Later, the narrator called A001 'the wanderer' but A001 was "
        "already named 'the seeker' in chapter one.")

    state = {"triage": 0, "regen": 0, "semantic": 0}

    def stub(prompt: str, timeout: int = 600) -> str:
        if "quality reviewer" in prompt:
            state["semantic"] += 1
            return json.dumps([{
                "json_path": "$.summary",
                "severity": "error",
                "rule": "fact_mismatch",
                "message": "summary contradicts source",
            }])
        if "source-discrepancy triage tool" in prompt:
            state["triage"] += 1
            # Pre-T3 (first triage call): refuse, force T3 to run.
            if state["triage"] == 1:
                return json.dumps({"verdicts": []})
            # Post-gate triage: accept with the fixer's prior.
            fps = [l.split("fingerprint:", 1)[1].strip()
                   for l in prompt.splitlines()
                   if l.strip().startswith("fingerprint:")]
            return json.dumps({"verdicts": [
                {"issue_fingerprint": fp,
                 "source_inherent": True,
                 "discrepancy_type": "author_contradiction",
                 "chapter_number": 1,
                 "line_range": [3, 3],
                 "quote": valid_quote,
                 "rationale": "source has conflicting names",
                 "extraction_choice": "kept 'the wanderer'"}
                for fp in fps
            ]})
        if "regeneration tool" in prompt:
            state["regen"] += 1
            # T3 writes a valid file AND self-reports the issue — nothing
            # is "resolved" from T3's own accounting.
            return json.dumps({
                "summary": "A001 is called 'the wanderer' and 'the seeker'",
                "__source_inherent__": [{
                    "issue_fingerprint":
                        f"{target}::$.summary::fact_mismatch",
                    "discrepancy_type": "author_contradiction",
                    "chapter_number": 1,
                    "line_range": [3, 3],
                    "quote": valid_quote,
                    "rationale": "source conflicts",
                    "extraction_choice": "preserved both",
                }],
            })
        # Force T1/T2 to fail parse so escalation reaches T3.
        return "NOT_JSON_FORCE_ESCALATE"

    cfg = RepairConfig(
        max_rounds=2, run_semantic=True, l3_gate_enabled=True,
        triage_enabled=True, accept_cap_per_file=3,
        retry_policy=RetryPolicy(
            t0_max=1, t1_max=1, t2_max=1, t3_max=1,
            max_total_rounds=2),
    )

    result = run(files=[FileEntry(path=str(target))],
                 config=cfg, source_context=ctx, llm_call=stub)

    notes_path = (Path(ctx.work_path) / "characters" / "A001" / "canon"
                  / "extraction_notes" / "S001.jsonl")

    print(f"[E] passed={result.passed}  notes={len(result.accepted_notes)}  "
          f"T3 calls={state['regen']}  triage calls={state['triage']}")
    # T3 ran (pre-T3 triage refused).
    assert state["regen"] >= 1, "T3 should have run after pre-T3 refusal"
    # Post-gate triage fired — only possible if modified_files includes
    # the T3-touched file (Bug B fix).
    assert result.accepted_notes, (
        "post-gate triage should have accepted the T3 self-report; "
        "if empty, Bug B likely regressed (T3 file not in modified_files)")
    assert notes_path.exists(), "notes file should be persisted"

    print("[E] OK — T3 self-report tracked, post-gate triage accepted")


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
    work = tmp / "works" / "smoke"
    chars = work / "characters" / "A001" / "canon" / "stage_snapshots"
    chars.mkdir(parents=True, exist_ok=True)

    target = chars / "S001.json"
    # 主角 → threshold 5; one example → shortage of 4.
    target.write_text(json.dumps({
        "voice_state": {
            "target_voice_map": [{
                "target_character_id": "A001",
                "dialogue_examples": ["only example"],
            }],
        },
    }, ensure_ascii=False), encoding="utf-8")

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
        json.dumps({"stages": [{"stage_id": "S001",
                                "chapters": "0001-0001"}]}),
        encoding="utf-8",
    )

    ctx = SourceContext(
        work_path=str(work),
        stage_id="S001",
        chapter_summaries_dir=str(summaries_dir),
        chapters_dir=str(chapters_dir),
    )

    # Count any stray triage-prompt calls — they should stay at 0.
    calls = {"triage": 0, "patch": 0, "regen": 0, "semantic": 0}

    def stub(prompt: str, timeout: int = 600) -> str:
        if "quality reviewer" in prompt:
            calls["semantic"] += 1
            return "[]"
        if "source-discrepancy triage tool" in prompt:
            calls["triage"] += 1
            return json.dumps({"verdicts": []})
        if "regeneration tool" in prompt:
            calls["regen"] += 1
            return json.dumps({})
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
            t0_max=1, t1_max=1, t2_max=1, t3_max=1,
            max_total_rounds=2),
    )

    result = run(
        files=[FileEntry(path=str(target))],
        config=cfg, source_context=ctx, llm_call=stub,
        importance_map={"A001": "主角"},
    )

    notes_path = (Path(ctx.work_path) / "characters" / "A001" / "canon"
                  / "extraction_notes" / "S001.jsonl")

    print(f"[F] passed={result.passed}  notes={len(result.accepted_notes)}  "
          f"triage_calls={calls['triage']}  regen_calls={calls['regen']}")

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
    assert calls["regen"] == 0, (
        f"coverage_shortage issues must not escalate to T3; saw "
        f"{calls['regen']} regen calls")
    assert notes_path.exists(), f"notes file not written: {notes_path}"

    print("[F] OK — coverage_shortage accepted at 0 token, Phase C clean")


def main() -> int:
    scenario_a_pre_t3_accept()
    scenario_b_bad_quote_rejected()
    scenario_c_cap_enforced()
    scenario_d_non_semantic_rejected()
    scenario_e_t3_self_report_tracked()
    scenario_f_coverage_shortage_accepted()
    print("\nAll triage smoke scenarios passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
