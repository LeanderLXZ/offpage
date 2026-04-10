"""Programmatic post-processing for Phase 3 batch extraction.

After LLM extraction produces stage_snapshots and memory_timelines,
this module programmatically maintains derived files:
  - memory_digest.jsonl  (compressed index of memory_timeline)
  - stage_catalog.json   (stage directory with upsert semantics)

These were previously written by the LLM agent, consuming tokens and
risking format drift. Programmatic generation is deterministic, idempotent,
and free (0 token).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import jsonschema as _jsonschema
except ImportError:
    _jsonschema = None


# ---------------------------------------------------------------------------
# memory_digest.jsonl generation
# ---------------------------------------------------------------------------

def generate_memory_digest(
    timeline_path: Path,
    digest_path: Path,
    stage_id: str,
    schema_dir: Path | None = None,
) -> list[str]:
    """Generate memory_digest entries from a memory_timeline file.

    Reads ``memory_timeline/{stage_id}.json`` (a JSON array of timeline
    entries) and produces one digest entry per timeline entry.  Existing
    digest entries for other stages are preserved; entries matching the
    current ``stage_id`` are replaced (upsert semantics).

    Returns a list of warning/error messages (empty = success).
    """
    issues: list[str] = []

    # --- read timeline ---
    if not timeline_path.exists():
        issues.append(f"memory_timeline not found: {timeline_path}")
        return issues

    try:
        timeline_entries: list[dict] = json.loads(
            timeline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as e:
        issues.append(f"Cannot parse memory_timeline: {e}")
        return issues

    if not isinstance(timeline_entries, list):
        issues.append("memory_timeline is not a JSON array")
        return issues

    # --- build new digest entries ---
    new_entries: list[dict] = []
    for entry in timeline_entries:
        digest = _timeline_to_digest(entry, stage_id)
        if digest is not None:
            new_entries.append(digest)

    if not new_entries:
        issues.append(f"No digest entries generated for stage '{stage_id}'")
        return issues

    # --- validate against schema ---
    if schema_dir and _jsonschema:
        schema_path = schema_dir / "memory_digest_entry.schema.json"
        if schema_path.exists():
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            for i, entry in enumerate(new_entries):
                try:
                    _jsonschema.validate(entry, schema)
                except _jsonschema.ValidationError as e:
                    path_str = ".".join(
                        str(p) for p in e.absolute_path) or "(root)"
                    issues.append(
                        f"digest entry [{i}] schema error at {path_str}: "
                        f"{e.message}")

    # --- upsert into existing digest ---
    existing_lines: list[dict] = []
    if digest_path.exists():
        text = digest_path.read_text(encoding="utf-8").strip()
        if text:
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    existing_lines.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # drop malformed lines

    # Remove old entries for this stage_id
    kept = [e for e in existing_lines if e.get("stage_id") != stage_id]

    # Deduplicate by memory_id within new entries
    seen_ids: set[str] = set()
    deduped_new: list[dict] = []
    for entry in new_entries:
        mid = entry.get("memory_id", "")
        if mid not in seen_ids:
            seen_ids.add(mid)
            deduped_new.append(entry)

    # Append new entries
    final = kept + deduped_new

    # --- write ---
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(digest_path, "w", encoding="utf-8") as f:
        for entry in final:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info("memory_digest: wrote %d entries for stage '%s' "
                "(%d total lines)", len(deduped_new), stage_id, len(final))
    return issues


def _timeline_to_digest(entry: dict, stage_id: str) -> dict | None:
    """Map a single memory_timeline entry to a memory_digest entry."""
    memory_id = entry.get("memory_id")
    if not memory_id:
        return None

    digest: dict[str, Any] = {
        "memory_id": memory_id,
        "stage_id": entry.get("stage_id", stage_id),
        "event_summary": entry.get("event_summary", ""),
        "memory_importance": entry.get("memory_importance", "minor"),
    }

    # Optional fields — copy if present
    for field in ("time_in_story", "location"):
        val = entry.get(field)
        if val:
            digest[field] = val

    # emotional_tags: copy emotional_impact directly
    emotional_impact = entry.get("emotional_impact")
    if emotional_impact:
        digest["emotional_tags"] = emotional_impact

    # involved_targets: extract target names from relationship_impact
    rel_impact = entry.get("relationship_impact")
    if isinstance(rel_impact, list) and rel_impact:
        targets = [r.get("target") for r in rel_impact
                   if isinstance(r, dict) and r.get("target")]
        if targets:
            digest["involved_targets"] = targets

    return digest


# ---------------------------------------------------------------------------
# stage_catalog.json maintenance
# ---------------------------------------------------------------------------

def upsert_stage_catalog(
    catalog_path: Path,
    stage_id: str,
    order: int,
    snapshot_path_rel: str,
    snapshot_data: dict,
    work_id: str,
    character_id: str | None = None,
    chapter_scope: dict | None = None,
    schema_dir: Path | None = None,
) -> list[str]:
    """Upsert a stage entry into a stage_catalog.json file.

    If the catalog file doesn't exist, creates it with proper structure.
    If an entry with the same stage_id exists, replaces it.
    Entries are sorted by ``order`` after upsert.

    Args:
        catalog_path: Path to stage_catalog.json
        stage_id: The stage identifier
        order: Numeric ordering (batch index)
        snapshot_path_rel: Relative path to the snapshot file
        snapshot_data: Parsed snapshot JSON (to extract title, summary)
        work_id: Work identifier
        character_id: Character identifier (None for world catalog)
        chapter_scope: {"from": "NNNN", "to": "NNNN"} or None
        schema_dir: Path to schemas/ directory for validation

    Returns a list of warning/error messages (empty = success).
    """
    issues: list[str] = []

    # --- build the new stage entry ---
    new_entry: dict[str, Any] = {
        "stage_id": stage_id,
        "order": order,
        "title": snapshot_data.get("title", stage_id),
        "short_summary": snapshot_data.get("snapshot_summary", stage_id),
        "snapshot_path": snapshot_path_rel,
    }

    # Optional fields from snapshot
    timeline_anchor = snapshot_data.get("timeline_anchor")
    if timeline_anchor:
        new_entry["timeline_anchor"] = timeline_anchor

    if chapter_scope:
        new_entry["chapter_scope"] = chapter_scope

    # Character catalog extra summary fields (from snapshot if available)
    if character_id is not None:
        for src_field, cat_field in _CHAR_CATALOG_SUMMARY_FIELDS:
            val = snapshot_data.get(src_field)
            if val and isinstance(val, str):
                new_entry[cat_field] = val

    # World catalog extra summary fields
    if character_id is None:
        # current_world_state as summary (take first item if array)
        cws = snapshot_data.get("current_world_state")
        if isinstance(cws, list) and cws:
            new_entry["current_world_summary"] = cws[0]
        elif isinstance(cws, str):
            new_entry["current_world_summary"] = cws
        # key_events: copy from snapshot (1-sentence summaries per stage)
        ke = snapshot_data.get("key_events")
        if isinstance(ke, list) and ke:
            new_entry["key_events"] = ke

    # --- load or create catalog ---
    catalog: dict[str, Any]
    if catalog_path.exists():
        try:
            catalog = json.loads(
                catalog_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            issues.append(f"Cannot parse existing catalog: {e}")
            return issues
    else:
        catalog = {
            "schema_version": "1.0",
            "work_id": work_id,
            "stages": [],
        }
        if character_id is not None:
            catalog["character_id"] = character_id

    # --- upsert ---
    stages: list[dict] = catalog.get("stages", [])
    # Remove existing entry with same stage_id
    stages = [s for s in stages if s.get("stage_id") != stage_id]
    stages.append(new_entry)
    # Sort by order
    stages.sort(key=lambda s: s.get("order", 0))
    catalog["stages"] = stages

    # --- validate against schema ---
    if schema_dir and _jsonschema:
        schema_name = ("world_stage_catalog.schema.json"
                       if character_id is None
                       else "stage_catalog.schema.json")
        schema_path = schema_dir / schema_name
        if schema_path.exists():
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            try:
                _jsonschema.validate(catalog, schema)
            except _jsonschema.ValidationError as e:
                path_str = ".".join(
                    str(p) for p in e.absolute_path) or "(root)"
                issues.append(
                    f"stage_catalog schema error at {path_str}: "
                    f"{e.message}")

    # --- write ---
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    logger.info("stage_catalog: upserted stage '%s' (order=%d) into %s",
                stage_id, order, catalog_path.name)
    return issues


# Character catalog optional summary fields:
# (snapshot_field, catalog_field)
_CHAR_CATALOG_SUMMARY_FIELDS = [
    # These fields don't exist as top-level strings in stage_snapshot,
    # but we try to extract them if present for richer catalog entries.
    # If not found, the entry is simply omitted (all are optional).
]


# ---------------------------------------------------------------------------
# Batch-level post-processing orchestration
# ---------------------------------------------------------------------------

def run_batch_post_processing(
    project_root: Path,
    work_id: str,
    stage_id: str,
    batch_order: int,
    character_ids: list[str],
    chapter_range: str,
) -> list[str]:
    """Run all programmatic post-processing for a completed batch.

    Called after world + character extraction succeeds, before review.
    Generates memory_digest entries and updates stage_catalogs.

    Returns a list of issues (empty = all clean).
    """
    issues: list[str] = []
    work_dir = project_root / "works" / work_id
    schema_dir = project_root / "schemas"

    # Parse chapter scope
    chapter_scope = _parse_chapter_scope(chapter_range)

    # --- World stage_catalog ---
    world_snapshot_path = (work_dir / "world" / "stage_snapshots"
                           / f"{stage_id}.json")
    world_catalog_path = work_dir / "world" / "stage_catalog.json"

    if world_snapshot_path.exists():
        try:
            snapshot_data = json.loads(
                world_snapshot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            issues.append(f"Cannot parse world snapshot: {e}")
            snapshot_data = {}

        if snapshot_data:
            catalog_issues = upsert_stage_catalog(
                catalog_path=world_catalog_path,
                stage_id=stage_id,
                order=batch_order,
                snapshot_path_rel=f"stage_snapshots/{stage_id}.json",
                snapshot_data=snapshot_data,
                work_id=work_id,
                character_id=None,
                chapter_scope=chapter_scope,
                schema_dir=schema_dir,
            )
            issues.extend(f"[world catalog] {i}" for i in catalog_issues)
    else:
        issues.append(f"World snapshot not found: {world_snapshot_path}")

    # --- Per-character: memory_digest + stage_catalog ---
    for char_id in character_ids:
        char_dir = work_dir / "characters" / char_id / "canon"

        # memory_digest
        timeline_path = char_dir / "memory_timeline" / f"{stage_id}.json"
        digest_path = char_dir / "memory_digest.jsonl"
        digest_issues = generate_memory_digest(
            timeline_path=timeline_path,
            digest_path=digest_path,
            stage_id=stage_id,
            schema_dir=schema_dir,
        )
        issues.extend(f"[{char_id} digest] {i}" for i in digest_issues)

        # stage_catalog
        snapshot_path = char_dir / "stage_snapshots" / f"{stage_id}.json"
        catalog_path = char_dir / "stage_catalog.json"

        if snapshot_path.exists():
            try:
                snapshot_data = json.loads(
                    snapshot_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError) as e:
                issues.append(f"[{char_id}] Cannot parse snapshot: {e}")
                continue

            catalog_issues = upsert_stage_catalog(
                catalog_path=catalog_path,
                stage_id=stage_id,
                order=batch_order,
                snapshot_path_rel=(
                    f"canon/stage_snapshots/{stage_id}.json"),
                snapshot_data=snapshot_data,
                work_id=work_id,
                character_id=char_id,
                chapter_scope=chapter_scope,
                schema_dir=schema_dir,
            )
            issues.extend(
                f"[{char_id} catalog] {i}" for i in catalog_issues)
        else:
            issues.append(
                f"[{char_id}] Snapshot not found: {snapshot_path}")

    return issues


def _parse_chapter_scope(chapter_range: str) -> dict[str, str] | None:
    """Parse 'NNNN-NNNN' chapter range into chapter_scope dict."""
    if not chapter_range or "-" not in chapter_range:
        return None
    parts = chapter_range.split("-", 1)
    if len(parts) == 2:
        return {"from": parts[0].strip(), "to": parts[1].strip()}
    return None
