"""Deferred-repair ledger for unresolved SEMANTIC (L3) repair issues.

When ``[repair].defer_unresolved_semantic`` is on and a Phase 3 stage's
repair ends with only ``category=="semantic"`` error issues remaining, the
stage is committed anyway (record-and-continue) instead of failing. The
unresolved issues are written here to a durable, per-stage ledger:

    works/{work_id}/analysis/deferred_repairs/{stage_id}.jsonl

The ledger lives under ``works/{work_id}/`` (NOT the gitignored
``progress/`` subtree), so ``commit_stage``'s ``git add -A works/{work_id}/``
commits it alongside the stage. A later Phase 3.5 fix pass reads the
committed ledgers and applies precise field-level repairs without
re-extracting the stage.

Only semantic issues are deferrable: any remaining json_syntax / schema /
structural / cross_file error would leave the file schema-invalid or
structurally broken for downstream stages, so those still force ERROR.
``deferrable_semantic_issues`` is the pure decision helper; it returns the
issue list to defer, or ``None`` when the stage must hard-fail.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:  # avoid a runtime import cycle with the repair package
    from ...repair.protocol import Issue, RepairFileEntry, RepairResult

logger = logging.getLogger(__name__)

DEFERRABLE_CATEGORY = "semantic"


def deferrable_semantic_issues(
    failed_entries: Iterable[tuple["RepairFileEntry", "RepairResult"]],
) -> list["Issue"] | None:
    """Decide whether a stage's repair failure is safe to defer.

    ``failed_entries`` is the ``(entry, result)`` pairs whose repair did NOT
    pass. Returns the list of remaining error-severity issues to defer when
    **every** such issue is ``category=="semantic"``; otherwise ``None``
    (the stage must hard-fail).

    ``None`` is also returned when there are no error-severity issues at all
    — e.g. a repair worker raised an exception (synthetic ``RepairResult``
    with empty ``issues``): a crash is not a deferrable semantic finding.
    """
    error_issues: list[Issue] = [
        i
        for _entry, result in failed_entries
        for i in result.issues
        if i.severity == "error"
    ]
    if not error_issues:
        return None
    if all(i.category == DEFERRABLE_CATEGORY for i in error_issues):
        return error_issues
    return None


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
