"""Per-lane product paths + JSON parseability checks (T-RESUME).

The Phase 3 extraction pipeline runs 1+2N parallel lanes per stage
(1 ``world`` + N ``snapshot:{char_id}`` + N ``support:{char_id}``). Each
lane writes its own per-stage JSON product; ``support`` additionally
modifies the cumulative ``identity.json`` baseline file.

Lane-level resume (see requirements.md §11.5) only trusts a lane as
complete when both conditions hold:

1. the subprocess returned success
2. the lane's per-stage product file(s) parse as JSON

This module centralises path construction and parse verification so
the orchestrator and reconcile routines agree on what "lane output" means.
"""

from __future__ import annotations

import json
from pathlib import Path


WORLD_LANE = "world"
SNAPSHOT_PREFIX = "snapshot:"
SUPPORT_PREFIX = "support:"

# Sub-lane partial directory (decision #55) — sibling of the per-stage
# product directory, gitignored. Each sub-lane writes
# ``.partial/{stage_id}_{sub_lane}.json`` here; ``merge_partials`` reads
# them, writes the merged file to ``stage_snapshots/{stage_id}.json``,
# and the orchestrator cleans the .partial entries.
SNAPSHOT_PARTIAL_DIRNAME = ".partial"

# Sub-lane prev-snapshot slice directory (decision #55, 4-lane topology) —
# lives under ``works/{wid}/analysis/progress/.partial_prev/{char_id}/``,
# gitignored (the ``progress/`` parent is already in .gitignore; we add an
# explicit ``.partial_prev/`` entry for defence-in-depth). The orchestrator
# writes ``{prev_stage_id}_{sub_lane}.json`` slices here before each stage
# runs, and the prompt_builder injects the appropriate slice path(s) into
# each sub-lane's prompt. Cleanup mirrors ``.partial/``: R3 pre-clear
# before write, plus explicit clear after repair / before commit / on
# any sub-lane failure.
SNAPSHOT_PARTIAL_PREV_DIRNAME = ".partial_prev"

# char_support lane's cumulative baseline file. Lives under
# works/{wid}/characters/{char_id}/canon/ and is NOT per-stage; we
# restore it from HEAD before re-running an incomplete support lane
# so a prior partial write cannot bleed into the retry.
BASELINE_FILENAMES = (
    "identity.json",
)


def expected_lane_names(target_characters: list[str]) -> list[str]:
    """Ordered list of lane names the orchestrator will launch per stage."""
    names = [WORLD_LANE]
    for c in target_characters:
        names.append(f"{SNAPSHOT_PREFIX}{c}")
        names.append(f"{SUPPORT_PREFIX}{c}")
    return names


def lane_product_path(work_root: Path, stage_id: str, lane_name: str) -> Path:
    """Return the per-stage product file for a given lane.

    ``work_root`` is ``works/{work_id}``. Raises ``ValueError`` on an
    unrecognised lane name.
    """
    if lane_name == WORLD_LANE:
        return work_root / "world" / "stage_snapshots" / f"{stage_id}.json"
    if lane_name.startswith(SNAPSHOT_PREFIX):
        char_id = lane_name[len(SNAPSHOT_PREFIX):]
        return (work_root / "characters" / char_id / "canon"
                / "stage_snapshots" / f"{stage_id}.json")
    if lane_name.startswith(SUPPORT_PREFIX):
        char_id = lane_name[len(SUPPORT_PREFIX):]
        return (work_root / "characters" / char_id / "canon"
                / "memory_timeline" / f"{stage_id}.json")
    raise ValueError(f"unknown lane name: {lane_name!r}")


def snapshot_partial_dir(work_root: Path, char_id: str) -> Path:
    """``.partial/`` directory for a character's stage_snapshot sub-lane
    partials (decision #55). Gitignored."""
    return (work_root / "characters" / char_id / "canon"
            / "stage_snapshots" / SNAPSHOT_PARTIAL_DIRNAME)


def snapshot_partial_path(work_root: Path, char_id: str,
                          stage_id: str, sub_lane: str) -> Path:
    """Path of a single sub-lane partial file. ``sub_lane`` is one of
    the names in ``snapshot_merge.SUB_LANE_NAMES`` (validated there —
    not re-checked here to keep this module dependency-free)."""
    return snapshot_partial_dir(work_root, char_id) / f"{stage_id}_{sub_lane}.json"


def prev_snapshot_slice_dir(work_root: Path, char_id: str) -> Path:
    """``.partial_prev/{char_id}/`` directory for per-lane slices of the
    previous stage's snapshot (decision #55 — 4-lane prev slice).
    Gitignored via ``progress/`` parent (with explicit ``.partial_prev/``
    entry as belt-and-suspenders)."""
    return (work_root / "analysis" / "progress"
            / SNAPSHOT_PARTIAL_PREV_DIRNAME / char_id)


def prev_snapshot_slice_path(work_root: Path, char_id: str,
                             prev_stage_id: str, sub_lane: str) -> Path:
    """Path of a single per-lane prev-snapshot slice file. ``sub_lane``
    is one of the names in ``snapshot_merge.SUB_LANE_NAMES`` (validated
    by the caller)."""
    return (prev_snapshot_slice_dir(work_root, char_id)
            / f"{prev_stage_id}_{sub_lane}.json")


def baseline_paths(work_root: Path, char_id: str) -> list[Path]:
    """Cumulative baseline files a support lane may have edited."""
    canon = work_root / "characters" / char_id / "canon"
    return [canon / name for name in BASELINE_FILENAMES]


def verify_lane_output(work_root: Path, stage_id: str,
                       lane_name: str) -> tuple[bool, str]:
    """Check a lane's per-stage product exists and parses as JSON.

    Returns (ok, reason). On success ``reason`` is empty; on failure
    ``reason`` is a short, loggable string suitable for inclusion in a
    LLMResult.error field.
    """
    try:
        path = lane_product_path(work_root, stage_id, lane_name)
    except ValueError as exc:
        return False, str(exc)
    if not path.exists():
        return False, f"missing output file: {path.name}"
    try:
        with path.open("r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as exc:
        return False, f"invalid JSON in {path.name}: {exc.msg}"
    except OSError as exc:
        return False, f"cannot read {path.name}: {exc}"
    return True, ""


def expected_lane_dirty_paths(work_root: Path, stage_id: str,
                               target_characters: list[str]) -> list[str]:
    """Path substrings preflight should tolerate during partial-resume.

    Returns repo-relative strings suitable for preflight_check's
    substring-match ignore_patterns. Covers every lane's per-stage
    product file plus each character's identity.json baseline file,
    since an incomplete support lane may have partially written it.
    """
    patterns: list[str] = []
    for name in expected_lane_names(target_characters):
        p = lane_product_path(work_root, stage_id, name)
        patterns.append(str(p.relative_to(work_root.parent.parent)))
    for c in target_characters:
        for p in baseline_paths(work_root, c):
            patterns.append(str(p.relative_to(work_root.parent.parent)))
    return patterns
