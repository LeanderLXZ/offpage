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

Run:  python -m automation.repair_agent._smoke_triage
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .coordinator import run
from .protocol import (
    FileEntry,
    RepairConfig,
    RetryPolicy,
    SourceContext,
)


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
            t0_max=1, t1_max=1, t2_max=1, t3_max=1, t3_max_per_file=1,
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
            t0_max=1, t1_max=1, t2_max=1, t3_max=1, t3_max_per_file=1,
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
            t0_max=1, t1_max=1, t2_max=1, t3_max=1, t3_max_per_file=1,
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

    print(f"[C] passed={result.passed}  notes={len(result.accepted_notes)}  "
          f"persisted_lines={len(lines)}")
    assert len(result.accepted_notes) <= 2, (
        f"accept cap breached: {len(result.accepted_notes)} > 2")
    assert len(lines) == len(result.accepted_notes)

    print("[C] OK — accept_cap_per_file enforced")


def main() -> int:
    scenario_a_pre_t3_accept()
    scenario_b_bad_quote_rejected()
    scenario_c_cap_enforced()
    print("\nAll triage smoke scenarios passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
