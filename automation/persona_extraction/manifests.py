"""Programmatic manifest writers.

Two canon-side manifests are produced deterministically from upstream
artifacts (no LLM involvement):

- ``works/{work_id}/manifest.json`` — written at Phase 1.5 end, after
  the user confirms characters and stage range. Derives its fields from
  the source manifest + ``analysis/stage_plan.json`` + the confirmed
  character list.

- ``works/{work_id}/world/manifest.json`` — written at Phase 2 end,
  alongside the world foundation. Derives its fields from the stage
  plan only; no LLM content required.

Both writers are idempotent: running them again with the same inputs
produces the same output (except for ``updated_at``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_works_manifest(
    project_root: Path,
    work_id: str,
    character_ids: list[str],
) -> Path:
    """Write ``works/{work_id}/manifest.json``.

    Called at the end of Phase 1.5, once the user has confirmed which
    characters to extract. ``character_ids`` is the confirmed list.
    """
    source_dir = project_root / "sources" / "works" / work_id
    work_dir = project_root / "works" / work_id

    source_manifest = _read_json(source_dir / "manifest.json") or {}
    chapter_index = _read_json(source_dir / "metadata" / "chapter_index.json")
    stage_plan = _read_json(work_dir / "analysis" / "stage_plan.json") or {}

    chapter_count = len(chapter_index) if isinstance(chapter_index, list) else 0
    stages = stage_plan.get("stages", []) if isinstance(stage_plan, dict) else []
    stage_ids = [s["stage_id"] for s in stages if isinstance(s, dict)
                 and s.get("stage_id")]

    manifest_path = work_dir / "manifest.json"
    existing = _read_json(manifest_path) or {}
    created_at = existing.get("created_at") or _now_iso()

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "work_id": work_id,
        "title": source_manifest.get("title", work_id),
        "language": source_manifest.get("language", "zh"),
        "source_package_ref": f"sources/works/{work_id}",
        "paths": {
            "world_root": "world",
            "characters_root": "characters",
            "analysis_root": "analysis",
            "retrieval_root": "retrieval",
        },
        "chapter_count": chapter_count,
        "stage_count": len(stage_ids),
        "character_count": len(character_ids),
        "stage_ids": stage_ids,
        "character_ids": list(character_ids),
        "created_at": created_at,
        "updated_at": _now_iso(),
    }
    _write_json(manifest_path, manifest)
    return manifest_path


def write_world_manifest(project_root: Path, work_id: str) -> Path:
    """Write ``works/{work_id}/world/manifest.json``.

    Called at the end of Phase 2 baseline production. Derives all
    fields from the stage plan; no LLM content required.
    """
    work_dir = project_root / "works" / work_id
    stage_plan = _read_json(work_dir / "analysis" / "stage_plan.json") or {}
    stages = stage_plan.get("stages", []) if isinstance(stage_plan, dict) else []
    stage_ids = [s["stage_id"] for s in stages if isinstance(s, dict)
                 and s.get("stage_id")]

    manifest_path = work_dir / "world" / "manifest.json"
    existing = _read_json(manifest_path) or {}
    created_at = existing.get("created_at") or _now_iso()

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "work_id": work_id,
        "world_id": f"{work_id}_world",
        "paths": {
            "foundation_path": "foundation/foundation.json",
            "fixed_relationships_path": "foundation/fixed_relationships.json",
            "stage_catalog_path": "stage_catalog.json",
            "stage_snapshot_root": "stage_snapshots",
            "world_event_digest_path": "world_event_digest.jsonl",
        },
        "stage_ids": stage_ids,
        "created_at": created_at,
        "updated_at": _now_iso(),
    }
    _write_json(manifest_path, manifest)
    return manifest_path
