"""Smoke test for the Phase 3.5 settlement collector loop (decision #74).

Regression cover for the hole `/post-check` found in the first cut: the
success path of ``_settle_one`` returned one element fewer than the caller
unpacked, so **every** successful settlement raised inside ``fut.result()``
and was swallowed by the generic ``except`` as an infrastructure fault. No
``fixed`` resolution was ever written, the file never entered ``modified``
(so segment 5 skipped its re-projection), and a debt that had actually been
repaired was re-filed as unsettled. Six validation criteria passed at the
time because not one of them reached this path.

The LLM is never called: ``run_repair`` is stubbed, so what is under test is
purely the collector's contract — arity, bucket routing, and what lands in
the resolution sidecar.

Scenarios:
  (A) repair passes            → file in ``modified``, nothing unsettled,
                                 a ``fixed`` row written for the semantic debt
  (B) repair fails twice       → unsettled, a ``given_up`` row with attempts=2
  (C) backend failure residual → unsettled, NO resolution row (an outage is
                                 not a spent attempt)
  (D) unlocatable (`$`) debt   → unsettled, NO resolution row (never attempted,
                                 so it keeps blocking rather than being released)

Run:  python -m extraction.persona_extraction.tests._smoke_phase35_settle
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from extraction.persona_extraction import orchestrator as orch
from extraction.persona_extraction.orchestrator import ExtractionOrchestrator
from extraction.persona_extraction.lifecycle.deferred_repair_log import (
    RESOLUTION_FIXED, RESOLUTION_GIVEN_UP, read_resolutions)
from extraction.repair import FileEntry, Issue, RepairResult
from extraction.validation.gates.phase3_5_consistency import ConsistencyIssue

STAGE_ID = "S001"
_failures: list[str] = []


def _check(label: str, ok: bool, detail: str = "") -> None:
    print(("  PASS: " if ok else "  FAIL: ") + label
          + (f" — {detail}" if detail else ""))
    if not ok:
        _failures.append(label)


def _debt(work_dir: Path, json_path: str = "$.a",
          rule: str = "fact_mismatch") -> ConsistencyIssue:
    target = work_dir / "characters" / "c" / "canon" / f"{STAGE_ID}.json"
    return ConsistencyIssue(
        "error", "semantic", STAGE_ID, "m", layer="L3", file=str(target),
        json_path=json_path, rule=rule, stage_id=STAGE_ID)


def _orchestrator(work_dir: Path, project_root: Path,
                  debt: ConsistencyIssue) -> ExtractionOrchestrator:
    """A bare orchestrator with only what ``_p35_settle_debts`` reads."""
    o = ExtractionOrchestrator.__new__(ExtractionOrchestrator)
    o.project_root = project_root
    o.pipeline = type("P", (), {"work_id": "smoke",
                                "target_characters": ["c"]})()
    o.phase3 = type("S", (), {"stages": []})()
    o.backend = o.reviewer_backend = None
    target = Path(debt.file)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")
    o._p35_repair_files = lambda *a, **k: {  # type: ignore[method-assign]
        str(target): FileEntry(path=str(target), schema=None)}
    return o


def _run(work_dir: Path, project_root: Path, debt: ConsistencyIssue,
         results: list[RepairResult]) -> tuple[set, list]:
    """Drive one settlement with ``run_repair`` stubbed to ``results``."""
    calls = iter(results)
    original = orch.run_repair
    orch.run_repair = lambda **kw: next(calls)  # type: ignore[assignment]
    try:
        o = _orchestrator(work_dir, project_root, debt)
        return o._p35_settle_debts(work_dir, [debt])
    finally:
        orch.run_repair = original  # type: ignore[assignment]


def _fresh(tmp: Path, name: str) -> tuple[Path, Path]:
    root = tmp / name
    work_dir = root / "works" / "smoke"
    (work_dir / "analysis").mkdir(parents=True)
    return work_dir, root


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p35-settle-") as td:
        tmp = Path(td)

        # ---- (A) repair passes -------------------------------------------
        work_dir, root = _fresh(tmp, "a")
        debt = _debt(work_dir)
        modified, unsettled = _run(
            work_dir, root, debt, [RepairResult(passed=True)])
        _check("A: a successful settlement is not swallowed as a fault",
               unsettled == [], f"unsettled={len(unsettled)}")
        _check("A: the repaired file enters `modified` (segment 5 re-projects)",
               modified == {debt.file}, f"modified={modified}")
        rows = read_resolutions(work_dir, STAGE_ID)
        _check("A: a `fixed` resolution row is written",
               len(rows) == 1
               and next(iter(rows.values()))["resolution"] == RESOLUTION_FIXED,
               f"rows={list(rows.values())}")

        # ---- (B) repair fails twice ---------------------------------------
        work_dir, root = _fresh(tmp, "b")
        debt = _debt(work_dir)
        residual = Issue(file=debt.file, json_path="$.a", category="semantic",
                         severity="error", rule="fact_mismatch", message="m")
        fail = RepairResult(passed=False, issues=[residual])
        modified, unsettled = _run(work_dir, root, debt, [fail, fail])
        _check("B: two failed attempts leave the debt unsettled",
               len(unsettled) == 1)
        rows = read_resolutions(work_dir, STAGE_ID)
        row = next(iter(rows.values()), {})
        _check("B: a `given_up` row records the spent attempts",
               row.get("resolution") == RESOLUTION_GIVEN_UP
               and row.get("attempts") == 2, f"row={row}")

        # ---- (C) backend failure is not a spent attempt --------------------
        work_dir, root = _fresh(tmp, "c")
        debt = _debt(work_dir)
        outage = Issue(file=debt.file, json_path="$", category="semantic",
                       severity="error", rule="semantic_unavailable",
                       message="backend down")
        down = RepairResult(passed=False, issues=[outage])
        modified, unsettled = _run(work_dir, root, debt, [down, down])
        _check("C: an outage keeps the debt blocking", len(unsettled) == 1)
        _check("C: an outage writes NO resolution row",
               read_resolutions(work_dir, STAGE_ID) == {},
               f"rows={read_resolutions(work_dir, STAGE_ID)}")

        # ---- (D) unlocatable debt is never released ------------------------
        work_dir, root = _fresh(tmp, "d")
        debt = _debt(work_dir, json_path="$", rule="whole_file_claim")
        modified, unsettled = _run(work_dir, root, debt, [])
        _check("D: an unattemptable `$` debt keeps blocking",
               len(unsettled) == 1)
        _check("D: an unattemptable debt is NOT given up on zero attempts",
               read_resolutions(work_dir, STAGE_ID) == {},
               f"rows={read_resolutions(work_dir, STAGE_ID)}")

        # ---- (E) a debt on an ungoverned file ------------------------------
        # The remaining return path. A wiring fault is not a spent attempt
        # either, so it must keep blocking without a resolution row.
        work_dir, root = _fresh(tmp, "e")
        debt = _debt(work_dir)
        o = _orchestrator(work_dir, root, debt)
        o._p35_repair_files = lambda *a, **k: {}  # type: ignore[method-assign]
        modified, unsettled = o._p35_settle_debts(work_dir, [debt])
        _check("E: a debt on a file this phase does not govern keeps blocking",
               len(unsettled) == 1)
        _check("E: a wiring fault writes NO resolution row",
               read_resolutions(work_dir, STAGE_ID) == {})


    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("OK — Phase 3.5 settlement collector behaves as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
