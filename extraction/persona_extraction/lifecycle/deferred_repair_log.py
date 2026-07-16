"""Deferred-repair ledger for unresolved repair issues.

When ``[repair].defer_unresolved_semantic`` is on and a Phase 3 stage's
repair ends with only deferrable error issues remaining, the stage is
committed anyway (record-and-continue) instead of failing. The unresolved
issues are written here to a durable, per-stage ledger:

    works/{work_id}/analysis/deferred_repairs/{stage_id}.jsonl

The ledger lives under ``works/{work_id}/`` (NOT the gitignored
``progress/`` subtree), so ``commit_stage``'s ``git add -A works/{work_id}/``
commits it alongside the stage. A later Phase 3.5 fix pass reads the
committed ledgers and applies precise field-level repairs without
re-extracting the stage.

Deferrable categories (decision #60 extended by T-REPAIR-NO-REEXTRACT):
the capped tiers (T0–T2, no full-file regen) may leave semantic, schema,
structural or cross_file errors that no automatic tier could fix — those
are all recorded to the ledger and the stage continues. A ``coverage_shortage``
residue defers too: it is ``severity=warning`` but still blocks the
coordinator, so judging on severity alone would hard-ERROR a stage over thin
content. A ``json_syntax`` error is NOT deferrable: it leaves the file
unparseable, which breaks every downstream read, so it still forces ERROR.
A repair-worker crash (a failed entry with no blocking issues to show for
itself) also still hard-fails.

``deferrable_issues`` is the pure decision helper; it returns the issue
list to defer, or ``None`` when the stage must hard-fail. It judges **per
entry** — see its docstring for why the flattened view was unsafe.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

# ``repair.protocol`` imports nothing from this package (stdlib only), so this
# is safe at runtime — and reusing its predicate keeps the "what counts as a
# coverage_shortage" judgement in one place, matching how ``route_tiers`` sees
# it. The dataclasses below stay TYPE_CHECKING-only imports.
from ...repair.protocol import is_coverage_shortage

if TYPE_CHECKING:  # avoid a runtime import cycle with the repair package
    from ...repair.protocol import Issue, RepairFileEntry, RepairResult

logger = logging.getLogger(__name__)

# Error categories the capped tiers may leave behind and that a Phase 3.5
# fix pass can still repair precisely. ``json_syntax`` is deliberately
# excluded — an unparseable file must hard-fail, not commit.
DEFERRABLE_CATEGORIES: frozenset[str] = frozenset(
    {"semantic", "schema", "structural", "cross_file"})


def _is_deferrable_issue(issue: "Issue") -> bool:
    """True when a single remaining issue may be deferred to the ledger.

    Two shapes qualify: an error whose category the capped tiers legitimately
    could not fix, and a ``coverage_shortage`` residue. The latter is
    ``severity=warning`` yet still blocks the coordinator, so judging on
    severity alone would let it hard-ERROR a stage over thin content — the
    exact min_examples deadlock decision #62 set out to remove.
    """
    if is_coverage_shortage(issue):
        return True
    return (issue.severity == "error"
            and issue.category in DEFERRABLE_CATEGORIES)


def deferrable_issues(
    failed_entries: Iterable[tuple["RepairFileEntry", "RepairResult"]],
) -> list["Issue"] | None:
    """Decide whether a stage's repair failure is safe to defer.

    ``failed_entries`` is the ``(entry, result)`` pairs whose repair did NOT
    pass. Returns the list of remaining issues to defer when **every** failed
    entry is individually deferrable; otherwise ``None`` (the stage must
    hard-fail).

    The judgement is **per entry**, not over the flattened issue list: a
    repair worker that raised produces a synthetic ``RepairResult`` with empty
    ``issues``, which contributes nothing to a flattened set. Judging the pool
    as a whole therefore let a crashed file ride along on a sibling's
    deferrable issue — committed unvalidated and absent from the ledger, so
    the Phase 3.5 fix pass would never learn about it. Any single crashed
    entry now hard-fails the stage.
    """
    to_defer: list[Issue] = []
    for _entry, result in failed_entries:
        entry_issues = [i for i in result.issues if _is_deferrable_issue(i)]
        blocking = [
            i for i in result.issues
            if i.severity == "error" or is_coverage_shortage(i)
        ]
        # A failed entry with nothing blocking to show for it is a worker
        # crash, not a finding — never deferrable.
        if not blocking:
            return None
        # An entry carrying any non-deferrable blocker (e.g. json_syntax:
        # the file is unparseable) hard-fails the stage.
        if len(entry_issues) != len(blocking):
            return None
        to_defer.extend(entry_issues)
    if not to_defer:
        return None
    return to_defer


def deferred_ledger_path(work_root: Path, stage_id: str) -> Path:
    """Path of the deferred-repair ledger for ``stage_id`` under a work."""
    return work_root / "analysis" / "deferred_repairs" / f"{stage_id}.jsonl"


def write_deferred_repairs(
    work_root: Path, stage_id: str, issues: list["Issue"],
) -> Path:
    """Write ``issues`` to the stage's deferred-repair ledger (truncating).

    One JSON object per line with the fields a Phase 3.5 fix pass needs to
    locate and repair each finding: ``stage_id`` / ``file`` / ``json_path``
    / ``category`` / ``severity`` / ``rule`` / ``message``. Overwrites any
    prior ledger for the stage so a re-run replaces rather than accumulates.
    """
    path = deferred_ledger_path(work_root, stage_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for issue in issues:
        record: dict[str, Any] = {
            "stage_id": stage_id,
            "file": issue.file,
            "json_path": issue.json_path,
            "category": issue.category,
            "severity": issue.severity,
            "rule": issue.rule,
            "message": issue.message,
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.warning(
        "Deferred %d unresolved semantic issue(s) for stage %s → %s",
        len(issues), stage_id, path)
    return path
