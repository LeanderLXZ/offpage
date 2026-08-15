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
# is safe at runtime — and reusing its predicates keeps the "what counts as a
# coverage_shortage" / "what counts as a failed review" judgements in one
# place, matching how ``route_tiers`` sees them. The dataclasses below stay
# TYPE_CHECKING-only imports.
from ...repair.protocol import BACKEND_FAILURE_RULES, is_coverage_shortage

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


def is_unverified_row(record: dict[str, Any]) -> bool:
    """True when a ledger row records a failed *review*, not a defect.

    Judged on ``rule`` rather than ``category``: the checker files these
    under ``semantic`` (they surface from the L3 semantic checker), and the
    rows already on disk were written that way. Keying on the rule is what
    lets an existing ledger be reclassified without rewriting it.

    The distinction is load-bearing. A content debt is settled by patching a
    field; a failed review is settled by *running the review again*. Treated
    as a semantic content debt, such a row anchors at ``$`` with no field to
    patch and no route to a resolution record — an unfalsifiable claim that
    fails the gate forever.
    """
    return record.get("rule", "") in BACKEND_FAILURE_RULES


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


def append_deferred_repairs(
    work_root: Path, stage_id: str, records: list[dict[str, Any]],
) -> int:
    """Append ledger rows that are not already filed. Returns rows written.

    Separate from ``write_deferred_repairs`` because the two have opposite
    contracts: a stage's own repair *replaces* its ledger (one repair run,
    one statement of what it could not fix), whereas a later phase *adds* to
    it without disturbing what is already there.

    This is what keeps a finding from vanishing. A cross-stage review finding
    that no fix could settle lives nowhere else — it is not in the ledger the
    verdict reads, so it would silently drop out of the run it was found in
    and have to be rediscovered (at full review cost) by the next one.

    Rows are matched by ``issue_key``, so re-filing an already-recorded debt
    is a no-op rather than a duplicate — within one call as well as against
    what is already on disk.
    """
    path = deferred_ledger_path(work_root, stage_id)
    existing = {issue_key(r) for r in _read_jsonl(path)}
    fresh: list[dict[str, Any]] = []
    for record in records:
        key = issue_key(record)
        if key in existing:
            continue
        existing.add(key)
        fresh.append(record)
    if not fresh:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for record in fresh:
            fh.write(json.dumps(
                {**record, "stage_id": stage_id}, ensure_ascii=False) + "\n")
    logger.warning("Filed %d unsettled finding(s) for stage %s → %s",
                   len(fresh), stage_id, path)
    return len(fresh)


# ---------------------------------------------------------------------------
# Resolutions — the Phase 3.5 write-back side of the ledger
# ---------------------------------------------------------------------------
#
# The ledger itself is an append-only historical statement: it records what a
# stage's repair could not fix at the time it ran, and is never rewritten
# afterwards. Phase 3.5 settles those debts, so it needs somewhere to record
# "this one is now fixed" — otherwise a settled debt keeps failing the gate
# forever.
#
# Three shapes of debt, three ways to clear:
#
#   * schema-class debts are re-verifiable by code — Phase 3.5 simply
#     re-validates the current file and the debt disappears on its own. No
#     resolution record needed, and none is trusted: the file is the truth.
#   * semantic-class debts cannot be re-verified programmatically, so a
#     resolution record IS the evidence. It is written per issue the moment
#     that issue is fixed, so an interrupted Phase 3.5 re-run skips what it
#     already settled instead of re-paying it.
#   * unverified rows (``is_unverified_row``) record that the review itself
#     failed. They clear by running the review again — a resolution record
#     stands for "the check ran this time", not for "a field was patched".
#
# Kept in a sidecar file rather than mutating the ledger so the original
# statement stays intact and both files remain append-only.
#
# Two kinds of resolution, and they claim different things:
#
#   * ``fixed`` — "this is repaired". Written only for debts code cannot
#     re-derive; writing one for a schema debt would suppress it forever
#     even if the field broke again later.
#   * ``given_up`` — "two attempts failed; recorded and released". It claims
#     nothing about the file, so it is safe for every category: the debt
#     stays visible (a schema one still fails re-validation), it is only
#     demoted from blocking to reported. An infrastructure failure is never
#     given up this way — a crashed run has not spent its attempts.

RESOLUTION_FIXED = "fixed"
RESOLUTION_GIVEN_UP = "given_up"


def resolution_ledger_path(work_root: Path, stage_id: str) -> Path:
    """Path of the resolution sidecar for ``stage_id``'s deferred ledger."""
    return (work_root / "analysis" / "deferred_repairs"
            / f"{stage_id}.resolved.jsonl")


def issue_key(record: dict[str, Any]) -> str:
    """Stable identity of a ledger row: ``file::json_path::rule``.

    Deliberately not the repair framework's ``fingerprint`` — that is derived
    from message text, which a fix legitimately changes. Location plus rule is
    what stays constant between "the debt was recorded" and "the debt was
    settled".
    """
    return (f"{record.get('file', '')}::{record.get('json_path', '')}"
            f"::{record.get('rule', '')}")


def read_deferred_ledger(work_root: Path, stage_id: str) -> list[dict]:
    """Read a stage's deferred ledger. Missing / unreadable → empty list."""
    return _read_jsonl(deferred_ledger_path(work_root, stage_id))


def read_resolutions(work_root: Path, stage_id: str) -> dict[str, dict]:
    """Return ``issue_key -> resolution row`` for the stage.

    A row written before ``resolution`` existed carries no kind; it dates
    from when the only outcome was a fix, so it reads as ``fixed``. Later
    rows win on a repeated key — a debt re-opened and then settled should
    read as settled.
    """
    out: dict[str, dict] = {}
    for rec in _read_jsonl(resolution_ledger_path(work_root, stage_id)):
        key = rec.get("issue_key")
        if not key:
            continue
        rec.setdefault("resolution", RESOLUTION_FIXED)
        out[key] = rec
    return out


def append_resolution(
    work_root: Path,
    stage_id: str,
    record: dict[str, Any],
    *,
    resolved_by: str,
    resolution: str = RESOLUTION_FIXED,
    attempts: int = 0,
    last_error: str = "",
    note: str = "",
) -> None:
    """Append one resolution row, flushed immediately.

    Written per issue rather than batched at the end of the pass: a crash
    mid-pass must not lose the record of work already done, otherwise the
    re-run pays for the same fixes again.

    Re-recording a row identical to the last one for that key is skipped —
    the read side dedupes anyway, and a sidecar that grows a row per re-run
    makes the history unreadable. Anything that actually changed still
    appends, including a new ``last_error``: freezing the first failure
    reason would leave whoever picks the debt up chasing a stale cause.
    """
    last_error = last_error[:200]
    key = issue_key(record)
    prior = read_resolutions(work_root, stage_id).get(key)
    if prior is not None and all(
            prior.get(k) == v for k, v in (
                ("resolution", resolution), ("attempts", attempts),
                ("last_error", last_error))):
        return
    path = resolution_ledger_path(work_root, stage_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "issue_key": key,
        "stage_id": stage_id,
        "file": record.get("file", ""),
        "json_path": record.get("json_path", ""),
        "rule": record.get("rule", ""),
        "resolution": resolution,
        "resolved_by": resolved_by,
        "attempts": attempts,
        "last_error": last_error,
        "note": note,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return []
    return rows
