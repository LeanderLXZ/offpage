"""Programmatic validator — Layer 1 (no LLM tokens).

Checks JSON schema compliance, structural completeness, and field
presence. Runs before the semantic reviewer to catch format issues for free.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore[assignment]


@dataclass
class ValidationIssue:
    severity: str   # "error" or "warning"
    file: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.file}: {self.message}"


@dataclass
class ValidationReport:
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def summary(self) -> str:
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        lines = [f"Validation: {'PASSED' if self.passed else 'FAILED'}",
                 f"  Errors: {len(errors)}, Warnings: {len(warnings)}"]
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


def validate_batch(
    project_root: Path,
    work_id: str,
    stage_id: str,
    character_ids: list[str],
    schema_dir: Path | None = None,
) -> ValidationReport:
    """Run all programmatic checks for a batch's output."""
    issues: list[ValidationIssue] = []
    schema_dir = schema_dir or (project_root / "schemas")
    work_dir = project_root / "works" / work_id

    # ---- World checks ----
    issues.extend(_check_world(work_dir, stage_id, schema_dir))

    # ---- Character checks (for each target character) ----
    for char_id in character_ids:
        issues.extend(_check_character(work_dir, char_id, stage_id, schema_dir))

    # ---- Cross-consistency ----
    issues.extend(_check_cross_consistency(work_dir, stage_id, character_ids))

    passed = not any(i.severity == "error" for i in issues)
    return ValidationReport(passed=passed, issues=issues)


# ---------------------------------------------------------------------------
# World validation
# ---------------------------------------------------------------------------

def _check_world(work_dir: Path, stage_id: str,
                 schema_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    world_dir = work_dir / "world"

    # stage_catalog.json exists
    catalog_path = world_dir / "stage_catalog.json"
    if not catalog_path.exists():
        issues.append(ValidationIssue(
            "error", str(catalog_path), "stage_catalog.json missing"))
    else:
        catalog = _load_json(catalog_path)
        if catalog is not None:
            # Check stage_id exists in catalog
            stage_ids = [s.get("stage_id") for s in catalog.get("stages", [])]
            if stage_id not in stage_ids:
                issues.append(ValidationIssue(
                    "error", str(catalog_path),
                    f"stage_id '{stage_id}' not found in stage_catalog"))

    # World stage snapshot exists and validates
    snapshot_path = world_dir / "stage_snapshots" / f"{stage_id}.json"
    if not snapshot_path.exists():
        issues.append(ValidationIssue(
            "error", str(snapshot_path), "World stage snapshot missing"))
    else:
        snapshot = _load_json(snapshot_path)
        if snapshot is not None:
            issues.extend(_validate_schema(
                snapshot, schema_dir / "world_stage_snapshot.schema.json",
                str(snapshot_path)))
            # Check key fields are non-empty
            for fld in ("snapshot_summary", "evidence_refs"):
                val = snapshot.get(fld)
                if not val:
                    issues.append(ValidationIssue(
                        "warning", str(snapshot_path),
                        f"Field '{fld}' is empty or missing"))

    return issues


# ---------------------------------------------------------------------------
# Character validation
# ---------------------------------------------------------------------------

def _check_character(work_dir: Path, char_id: str, stage_id: str,
                     schema_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    char_dir = work_dir / "characters" / char_id / "canon"

    # Stage snapshot
    snapshot_path = char_dir / "stage_snapshots" / f"{stage_id}.json"
    if not snapshot_path.exists():
        issues.append(ValidationIssue(
            "error", str(snapshot_path),
            f"Character stage snapshot missing for {char_id}"))
    else:
        snapshot = _load_json(snapshot_path)
        if snapshot is not None:
            issues.extend(_validate_schema(
                snapshot, schema_dir / "stage_snapshot.schema.json",
                str(snapshot_path)))
            # Self-contained check: key sections present
            for section in ("voice_state", "behavior_state",
                            "boundary_state", "relationships"):
                if not snapshot.get(section):
                    issues.append(ValidationIssue(
                        "error", str(snapshot_path),
                        f"Self-contained field '{section}' is empty "
                        f"(snapshot must be self-contained)"))
            # evidence_refs
            if not snapshot.get("evidence_refs"):
                issues.append(ValidationIssue(
                    "warning", str(snapshot_path),
                    "evidence_refs is empty"))

    # Memory timeline
    memory_path = char_dir / "memory_timeline" / f"{stage_id}.jsonl"
    if not memory_path.exists():
        issues.append(ValidationIssue(
            "error", str(memory_path),
            f"Memory timeline missing for {char_id} stage {stage_id}"))
    else:
        issues.extend(_check_memory_timeline(memory_path, schema_dir))

    # Stage catalog
    catalog_path = char_dir / "stage_catalog.json"
    if not catalog_path.exists():
        issues.append(ValidationIssue(
            "warning", str(catalog_path),
            f"Character stage_catalog.json missing for {char_id}"))

    return issues


def _check_memory_timeline(path: Path,
                           schema_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    schema_path = schema_dir / "memory_timeline_entry.schema.json"

    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
    except Exception as e:
        issues.append(ValidationIssue("error", str(path), f"Cannot read: {e}"))
        return issues

    if not lines or lines == [""]:
        issues.append(ValidationIssue(
            "warning", str(path), "Memory timeline is empty"))
        return issues

    for i, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            issues.append(ValidationIssue(
                "error", str(path), f"Line {i}: invalid JSON"))
            continue

        issues.extend(_validate_schema(entry, schema_path,
                                       f"{path}:line{i}"))

        # source_type check
        if not entry.get("source_type"):
            issues.append(ValidationIssue(
                "warning", f"{path}:line{i}",
                "source_type not set"))

    return issues


# ---------------------------------------------------------------------------
# Cross-consistency
# ---------------------------------------------------------------------------

def _check_cross_consistency(work_dir: Path, stage_id: str,
                             character_ids: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    # World and character snapshots should use the same stage_id
    world_snapshot = work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"
    for char_id in character_ids:
        char_snapshot = (work_dir / "characters" / char_id / "canon"
                         / "stage_snapshots" / f"{stage_id}.json")
        if world_snapshot.exists() and not char_snapshot.exists():
            issues.append(ValidationIssue(
                "error", str(char_snapshot),
                f"World snapshot exists for {stage_id} but character "
                f"snapshot missing for {char_id}"))
        if char_snapshot.exists() and not world_snapshot.exists():
            issues.append(ValidationIssue(
                "error", str(world_snapshot),
                f"Character snapshot exists for {char_id}/{stage_id} but "
                f"world snapshot missing"))

    # stage_catalog counts should match
    world_catalog = work_dir / "world" / "stage_catalog.json"
    if world_catalog.exists():
        wc = _load_json(world_catalog)
        if wc:
            world_stages = {s.get("stage_id") for s in wc.get("stages", [])}
            snapshot_dir = work_dir / "world" / "stage_snapshots"
            if snapshot_dir.exists():
                snapshot_files = {f.stem for f in snapshot_dir.glob("*.json")}
                missing = world_stages - snapshot_files
                if missing:
                    issues.append(ValidationIssue(
                        "warning", str(snapshot_dir),
                        f"stage_catalog has stages without snapshots: "
                        f"{missing}"))

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Cannot load %s: %s", path, e)
        return None


def _validate_schema(data: dict, schema_path: Path,
                     file_label: str) -> list[ValidationIssue]:
    """Validate data against a JSON Schema. Requires jsonschema package."""
    if jsonschema is None:
        return []  # Skip if jsonschema not installed

    if not schema_path.exists():
        return [ValidationIssue("warning", file_label,
                                f"Schema not found: {schema_path.name}")]

    schema = _load_json(schema_path)
    if schema is None:
        return [ValidationIssue("warning", file_label,
                                f"Cannot load schema: {schema_path.name}")]

    issues: list[ValidationIssue] = []
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        # Report the first error with path
        path_str = ".".join(str(p) for p in e.absolute_path) or "(root)"
        issues.append(ValidationIssue(
            "error", file_label,
            f"Schema violation at {path_str}: {e.message}"))
    except jsonschema.SchemaError as e:
        issues.append(ValidationIssue(
            "warning", file_label,
            f"Schema itself is invalid: {e.message}"))

    return issues
