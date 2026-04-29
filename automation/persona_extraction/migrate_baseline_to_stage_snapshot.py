"""One-shot migration: deprecate 4-piece character baseline → inline into stage_snapshot.

Run from repo root:
    python -m automation.persona_extraction.migrate_baseline_to_stage_snapshot --dry-run
    python -m automation.persona_extraction.migrate_baseline_to_stage_snapshot --apply

What it does (per ``works/{wid}/characters/{cid}/canon/``):

1. If ``failure_modes.json`` exists, copy its content (4 sub-arrays:
   common_failures / tone_traps / relationship_traps / knowledge_leaks)
   into every existing ``stage_snapshots/{stage_id}.json`` under the new
   top-level ``failure_modes`` field. Schema metadata (schema_version /
   work_id / character_id) is dropped — the snapshot already has its own.
2. Move all four deprecated baseline files (voice_rules / behavior_rules /
   boundaries / failure_modes) into ``canon/.archive/baseline_{ts}/`` so
   they remain available for inspection but no longer participate in
   extraction or runtime.

The script is intentionally idempotent: if a snapshot already has a
``failure_modes`` field it is left alone; if the deprecated files are
already archived it is a no-op.

This script does NOT regenerate voice_state / behavior_state /
boundary_state in existing stage_snapshots — those fields already exist
per stage and the deprecated voice_rules / behavior_rules / boundaries
files are structurally redundant with them. Re-extracting a stage from
scratch (post-migration) will use the new prompt that derives the
failure_modes field from identity + source.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEPRECATED_FILES = (
    "voice_rules.json",
    "behavior_rules.json",
    "boundaries.json",
    "failure_modes.json",
)

FAILURE_MODE_SUBFIELDS = (
    "common_failures",
    "tone_traps",
    "relationship_traps",
    "knowledge_leaks",
)


def discover_canon_dirs(project_root: Path) -> list[Path]:
    works_dir = project_root / "works"
    if not works_dir.exists():
        return []
    canons: list[Path] = []
    for canon in works_dir.glob("*/characters/*/canon"):
        if canon.is_dir():
            canons.append(canon)
    return sorted(canons)


def extract_failure_modes_payload(fm_path: Path) -> dict | None:
    try:
        data = json.loads(fm_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  [WARN] cannot parse {fm_path}: {exc}", file=sys.stderr)
        return None
    payload = {k: data[k] for k in FAILURE_MODE_SUBFIELDS if k in data}
    return payload or None


def inline_failure_modes_into_snapshots(
    canon_dir: Path,
    payload: dict,
    *,
    apply: bool,
) -> list[Path]:
    snapshots_dir = canon_dir / "stage_snapshots"
    if not snapshots_dir.exists():
        return []
    touched: list[Path] = []
    for snap_path in sorted(snapshots_dir.glob("S*.json")):
        try:
            snap = json.loads(snap_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  [WARN] cannot parse {snap_path}: {exc}",
                  file=sys.stderr)
            continue
        if "failure_modes" in snap:
            continue  # idempotent: already migrated
        snap["failure_modes"] = payload
        if apply:
            snap_path.write_text(
                json.dumps(snap, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        touched.append(snap_path)
    return touched


def archive_deprecated_files(
    canon_dir: Path,
    timestamp: str,
    *,
    apply: bool,
) -> list[Path]:
    moved: list[Path] = []
    archive_dir = canon_dir / ".archive" / f"baseline_{timestamp}"
    for name in DEPRECATED_FILES:
        src = canon_dir / name
        if not src.exists():
            continue
        dst = archive_dir / name
        if apply:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        moved.append(src)
    return moved


def migrate_one_canon(canon_dir: Path, timestamp: str, *, apply: bool) -> dict:
    print(f"\n[work] {canon_dir.relative_to(canon_dir.parents[3])}")

    fm_path = canon_dir / "failure_modes.json"
    inlined: list[Path] = []
    if fm_path.exists():
        payload = extract_failure_modes_payload(fm_path)
        if payload is None:
            print("  [skip] failure_modes.json has no migratable subfields"
                  " — falling back to empty placeholder")
            payload = {}
    else:
        # No baseline failure_modes file → still need to put a placeholder
        # into every existing stage_snapshot so the new schema's required
        # `failure_modes` field is satisfied. Subsequent re-extraction can
        # populate it properly.
        print("  [info] no failure_modes.json baseline; inserting empty"
              " placeholder into existing stage_snapshots")
        payload = {}

    inlined = inline_failure_modes_into_snapshots(
        canon_dir, payload, apply=apply)
    for p in inlined:
        tag = "[would inline]" if not apply else "[inlined]"
        suffix = " (empty placeholder)" if not payload else ""
        print(f"  {tag} failure_modes → "
              f"{p.relative_to(canon_dir)}{suffix}")

    moved = archive_deprecated_files(canon_dir, timestamp, apply=apply)
    for p in moved:
        tag = "[would archive]" if not apply else "[archived]"
        print(f"  {tag} {p.name} → .archive/baseline_{timestamp}/")
    if not moved:
        print("  [no-op] no deprecated baseline files present")

    return {
        "canon": str(canon_dir),
        "inlined_snapshots": [str(p) for p in inlined],
        "archived_files": [p.name for p in moved],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Inline character failure_modes baseline into "
                     "stage_snapshots and archive deprecated 4-piece "
                     "baseline files."))
    parser.add_argument(
        "--apply",
        action="store_true",
        help=("Actually modify disk. Without this flag the script runs "
              "in dry-run mode (default)."))
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root (default: cwd).")
    args = parser.parse_args()

    apply = bool(args.apply)
    if not apply:
        print("[DRY-RUN] no files will be modified. "
              "Re-run with --apply to commit changes.")
    else:
        print("[APPLY] modifying disk.")

    canons = discover_canon_dirs(args.project_root)
    if not canons:
        print("No canon directories found under works/. Nothing to do.")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = []
    for canon in canons:
        summary.append(migrate_one_canon(canon, timestamp, apply=apply))

    print(f"\nProcessed {len(summary)} canon dir(s).")
    if apply:
        print("\n[hint] If you ran this on an extraction/* branch where"
              " works/ is tracked, consider adding"
              " `works/*/characters/*/canon/.archive/` to that branch's"
              " .gitignore before `git add` to avoid committing the"
              " archived baseline blobs.")
    if not apply:
        print("Re-run with --apply to commit the changes shown above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
