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
