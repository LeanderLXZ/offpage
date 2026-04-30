"""L2 — Cross-file targets-keys-equal-baseline checker.

Enforces D4 (decisions.md #13): the three target structures inside a
character ``stage_snapshot.json`` —
``voice_state.target_voice_map`` /
``behavior_state.target_behavior_map`` /
top-level ``relationships`` — must each have a key set
**exactly equal** to ``target_baseline.targets[].target_character_id``
of the owning character. All three structures key by
``target_character_id`` (voice_map / behavior_map carry ``target_type``
only as sibling metadata).

The check resolves the baseline by walking the stage_snapshot path:
``characters/{char_id}/canon/stage_snapshots/{stage_id}.json`` →
``characters/{char_id}/canon/target_baseline.json``. Files that don't
match this layout (world snapshots, memory_timeline entries, etc.) are
silently skipped — the rule applies only to character stage snapshots.

A missing baseline file produces an error against the snapshot. Missing
keys (baseline lists a target the snapshot omits) and extra keys
(snapshot writes a target outside baseline) both fail; tri-state is
encoded in field-level emptiness, not in key presence.

Zero LLM tokens.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import BaseChecker
from ..protocol import FileEntry, Issue


class TargetsKeysEqBaselineChecker(BaseChecker):
    """Layer 2: cross-file ``set(snapshot 三结构 keys) == set(baseline keys)``."""

    layer = 2

    def check(self, files: list[FileEntry], **kwargs) -> list[Issue]:
        issues: list[Issue] = []
        for f in files:
            content = f.content if f.content is not None else f.load()
            if not isinstance(content, dict):
                continue
            p = Path(f.path)
            if not _is_character_stage_snapshot(p):
                continue
            baseline_path = _baseline_path_for(p)
            if baseline_path is None:
                continue
            baseline_keys = _load_baseline_keys(baseline_path)
            if baseline_keys is None:
                issues.append(Issue(
                    file=f.path, json_path="$",
                    category="cross_file", severity="error",
                    rule="targets_baseline_missing",
                    message=(
                        f"target_baseline.json missing or unreadable at "
                        f"{baseline_path}; cannot validate D4 keys=="
                        f"baseline."),
                    context={"baseline_path": str(baseline_path)},
                ))
                continue
            issues.extend(_check_one(f.path, content, baseline_keys))
        return issues


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _is_character_stage_snapshot(p: Path) -> bool:
    parts = p.parts
    if len(parts) < 5:
        return False
    return (
        "characters" in parts
        and "stage_snapshots" in parts
        and p.suffix == ".json"
    )


def _baseline_path_for(p: Path) -> Path | None:
    """``.../characters/{cid}/canon/stage_snapshots/{sid}.json`` →
    ``.../characters/{cid}/canon/target_baseline.json``.
    """
    parts = list(p.parts)
    try:
        snap_idx = parts.index("stage_snapshots")
    except ValueError:
        return None
    canon_parts = parts[:snap_idx] + ["target_baseline.json"]
    return Path(*canon_parts)


def _load_baseline_keys(path: Path) -> set[str] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    targets = data.get("targets") if isinstance(data, dict) else None
    if not isinstance(targets, list):
        return None
    keys: set[str] = set()
    for entry in targets:
        if not isinstance(entry, dict):
            continue
        cid = entry.get("target_character_id")
        if isinstance(cid, str) and cid:
            keys.add(cid)
    return keys


# ---------------------------------------------------------------------------
# Set-equality check
# ---------------------------------------------------------------------------

def _collect_keys(entries: object) -> set[str]:
    """Pull ``target_character_id`` from every dict entry of an array."""
    if not isinstance(entries, list):
        return set()
    keys: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        cid = entry.get("target_character_id")
        if isinstance(cid, str) and cid:
            keys.add(cid)
    return keys


def _check_one(file_path: str, snapshot: dict,
               baseline: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    voice_state = snapshot.get("voice_state") or {}
    behavior_state = snapshot.get("behavior_state") or {}
    structures = (
        ("$.voice_state.target_voice_map",
         voice_state.get("target_voice_map")),
        ("$.behavior_state.target_behavior_map",
         behavior_state.get("target_behavior_map")),
        ("$.relationships",
         snapshot.get("relationships")),
    )
    for json_path, entries in structures:
        if entries is None:
            issues.append(Issue(
                file=file_path, json_path=json_path,
                category="cross_file", severity="error",
                rule="targets_keys_eq_baseline_missing_structure",
                message=(
                    f"{json_path} missing; cannot satisfy D4 keys=="
                    f"baseline (must hold an entry per baseline target)."),
                context={"baseline_size": len(baseline)},
            ))
            continue
        snap_keys = _collect_keys(entries)
        missing = sorted(baseline - snap_keys)
        extra = sorted(snap_keys - baseline)
        if missing:
            issues.append(Issue(
                file=file_path, json_path=json_path,
                category="cross_file", severity="error",
                rule="targets_keys_eq_baseline_missing",
                message=(
                    f"{json_path} missing baseline targets "
                    f"{missing} (must include every "
                    f"baseline.targets[].target_character_id; never-"
                    f"appeared targets keep an empty entry)."),
                context={
                    "missing": missing,
                    "snapshot_keys": sorted(snap_keys),
                    "baseline_keys": sorted(baseline),
                },
            ))
        if extra:
            issues.append(Issue(
                file=file_path, json_path=json_path,
                category="cross_file", severity="error",
                rule="targets_keys_eq_baseline_extra",
                message=(
                    f"{json_path} writes targets not in baseline "
                    f"{extra} (record the gap in stage_delta and "
                    f"re-run after editing baseline; no escape hatch)."),
                context={
                    "extra": extra,
                    "snapshot_keys": sorted(snap_keys),
                    "baseline_keys": sorted(baseline),
                },
            ))
    return issues
