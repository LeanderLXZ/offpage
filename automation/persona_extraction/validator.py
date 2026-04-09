"""Programmatic validator — Layer 1 (no LLM tokens).

Checks JSON schema compliance, structural completeness, and field
presence. Runs before the semantic reviewer to catch format issues for free.

Before validation, any malformed JSON files are automatically repaired
via the three-level repair pipeline (see ``json_repair.py``).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .json_repair import try_repair_json_file, try_repair_jsonl_file

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


def _load_importance_map(project_root: Path, work_id: str) -> dict[str, str]:
    """Load character importance from candidate_characters.json.

    Returns {character_name: importance} e.g. {"王枫": "主角", "萧浩": "重要配角"}.
    """
    path = (project_root / "works" / work_id / "analysis"
            / "incremental" / "candidate_characters.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {c["character_id"]: c.get("importance", "")
                for c in data.get("candidates", [])
                if c.get("character_id")}
    except (json.JSONDecodeError, OSError, KeyError):
        return {}


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
    importance_map = _load_importance_map(project_root, work_id)
    for char_id in character_ids:
        issues.extend(_check_character(
            work_dir, char_id, stage_id, schema_dir, importance_map))

    # ---- Baseline file checks (first batch creates them) ----
    for char_id in character_ids:
        issues.extend(_check_baselines(work_dir, char_id, schema_dir))

    # ---- Manifest checks ----
    for char_id in character_ids:
        issues.extend(_check_manifest(work_dir, char_id, schema_dir))

    # ---- Cross-consistency ----
    issues.extend(_check_cross_consistency(work_dir, stage_id, character_ids))

    passed = not any(i.severity == "error" for i in issues)
    return ValidationReport(passed=passed, issues=issues)


def validate_lane(
    project_root: Path,
    work_id: str,
    stage_id: str,
    character_ids: list[str],
    lane_type: str = "all",
    lane_character_id: str | None = None,
    schema_dir: Path | None = None,
) -> ValidationReport:
    """Run programmatic checks scoped to a single review lane.

    Args:
        lane_type: "world", "character", or "all" (full batch).
        lane_character_id: Required when lane_type is "character".
    """
    if lane_type == "all":
        return validate_batch(project_root, work_id, stage_id,
                              character_ids, schema_dir)

    issues: list[ValidationIssue] = []
    schema_dir = schema_dir or (project_root / "schemas")
    work_dir = project_root / "works" / work_id

    if lane_type == "world":
        issues.extend(_check_world(work_dir, stage_id, schema_dir))
    elif lane_type == "character" and lane_character_id:
        importance_map = _load_importance_map(project_root, work_id)
        issues.extend(_check_character(
            work_dir, lane_character_id, stage_id, schema_dir,
            importance_map))
        issues.extend(_check_baselines(
            work_dir, lane_character_id, schema_dir))
        issues.extend(_check_manifest(
            work_dir, lane_character_id, schema_dir))

    passed = not any(i.severity == "error" for i in issues)
    return ValidationReport(passed=passed, issues=issues)


def validate_baseline(
    project_root: Path,
    work_id: str,
    character_ids: list[str],
    schema_dir: Path | None = None,
) -> ValidationReport:
    """Validate Phase 2.5 baseline outputs (identity, manifest, foundation).

    Run after baseline production to catch issues early before Phase 3.
    """
    issues: list[ValidationIssue] = []
    schema_dir = schema_dir or (project_root / "schemas")
    work_dir = project_root / "works" / work_id

    # World foundation
    foundation_path = work_dir / "world" / "foundation" / "foundation.json"
    if not foundation_path.exists():
        issues.append(ValidationIssue(
            "error", str(foundation_path), "foundation.json missing"))
    else:
        data = _load_json(foundation_path)
        if data is None:
            issues.append(ValidationIssue(
                "error", str(foundation_path), "Invalid JSON"))
        elif not data.get("work_id"):
            issues.append(ValidationIssue(
                "error", str(foundation_path), "work_id is empty"))

    # Per-character baseline checks
    for char_id in character_ids:
        char_dir = work_dir / "characters" / char_id / "canon"

        # identity.json
        id_path = char_dir / "identity.json"
        if not id_path.exists():
            issues.append(ValidationIssue(
                "error", str(id_path), "identity.json missing"))
        else:
            try_repair_json_file(id_path)
            identity = _load_json(id_path)
            if identity is None:
                issues.append(ValidationIssue(
                    "error", str(id_path), "Invalid JSON"))
            else:
                # Schema validation
                issues.extend(_validate_schema(
                    identity, schema_dir / "identity.schema.json",
                    str(id_path)))
                # Required field non-null checks
                if not identity.get("canonical_name"):
                    issues.append(ValidationIssue(
                        "error", str(id_path),
                        "canonical_name is empty or missing"))
                # Check aliases have valid names
                for i, alias in enumerate(identity.get("aliases", [])):
                    if not alias.get("name"):
                        issues.append(ValidationIssue(
                            "error", str(id_path),
                            f"aliases[{i}].name is empty or null"))

        # manifest.json
        manifest_path = char_dir.parent / "manifest.json"
        if not manifest_path.exists():
            issues.append(ValidationIssue(
                "error", str(manifest_path), "manifest.json missing"))
        else:
            try_repair_json_file(manifest_path)
            manifest = _load_json(manifest_path)
            if manifest is None:
                issues.append(ValidationIssue(
                    "error", str(manifest_path), "Invalid JSON"))
            else:
                issues.extend(_validate_schema(
                    manifest,
                    schema_dir / "character_manifest.schema.json",
                    str(manifest_path)))

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
                     schema_dir: Path,
                     importance_map: dict[str, str] | None = None,
                     ) -> list[ValidationIssue]:
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
            issues.extend(_check_snapshot_depth(
                snapshot, str(snapshot_path), importance_map))

    # Memory timeline (.json array format)
    memory_path = char_dir / "memory_timeline" / f"{stage_id}.json"
    if not memory_path.exists():
        issues.append(ValidationIssue(
            "error", str(memory_path),
            f"Memory timeline missing for {char_id} stage {stage_id}"))
    else:
        issues.extend(_check_memory_timeline(memory_path, schema_dir))

    # Memory digest (should have entries for this stage)
    digest_path = char_dir / "memory_digest.jsonl"
    if not digest_path.exists():
        issues.append(ValidationIssue(
            "warning", str(digest_path),
            f"memory_digest.jsonl missing for {char_id}"))
    else:
        issues.extend(_check_memory_digest(
            digest_path, stage_id, schema_dir))

    # Stage catalog — schema validation + entry completeness
    catalog_path = char_dir / "stage_catalog.json"
    if not catalog_path.exists():
        issues.append(ValidationIssue(
            "warning", str(catalog_path),
            f"Character stage_catalog.json missing for {char_id}"))
    else:
        catalog = _load_json(catalog_path)
        if catalog is not None:
            issues.extend(_validate_schema(
                catalog, schema_dir / "stage_catalog.schema.json",
                str(catalog_path)))

    return issues


def _min_examples_for_target(target: str,
                             importance_map: dict[str, str]) -> int:
    """Return minimum example count based on character importance.

    主角 → 5, 重要配角 → 3, others/unknown → 1.
    Uses substring matching (target_type may contain extra context).
    """
    for name, importance in importance_map.items():
        if name in target:
            if importance == "主角":
                return 5
            if importance == "重要配角":
                return 3
            return 1
    return 1


def _check_snapshot_depth(snapshot: dict,
                          label: str,
                          importance_map: dict[str, str] | None = None,
                          ) -> list[ValidationIssue]:
    """Deep checks on snapshot self-containedness and quality.

    Args:
        importance_map: {character_name: importance} from candidate_characters.
            主角 targets require ≥5 examples, 重要配角 ≥3, others ≥1.
    """
    issues: list[ValidationIssue] = []
    _imp = importance_map or {}

    # --- Top-level sections must exist and be non-empty ---
    for section in ("voice_state", "behavior_state",
                    "boundary_state", "relationships"):
        if not snapshot.get(section):
            issues.append(ValidationIssue(
                "error", label,
                f"Self-contained field '{section}' is empty "
                f"(snapshot must be self-contained)"))

    if not snapshot.get("evidence_refs"):
        issues.append(ValidationIssue(
            "warning", label, "evidence_refs is empty"))

    # --- voice_state depth ---
    vs = snapshot.get("voice_state") or {}
    if vs:
        if not vs.get("emotional_voice_map"):
            issues.append(ValidationIssue(
                "warning", label,
                "voice_state.emotional_voice_map is empty — "
                "emotions will lack voice differentiation"))
        if not vs.get("target_voice_map"):
            issues.append(ValidationIssue(
                "warning", label,
                "voice_state.target_voice_map is empty — "
                "different targets will sound the same"))
        else:
            for i, entry in enumerate(vs["target_voice_map"]):
                examples = entry.get("dialogue_examples") or []
                target = entry.get("target_type", f"[{i}]")
                min_ex = _min_examples_for_target(target, _imp)
                if len(examples) < min_ex:
                    issues.append(ValidationIssue(
                        "warning", label,
                        f"target_voice_map '{target}' has "
                        f"{len(examples)} dialogue_examples "
                        f"(want >={min_ex})"))

    # --- behavior_state depth ---
    bs = snapshot.get("behavior_state") or {}
    if bs:
        if not bs.get("target_behavior_map"):
            issues.append(ValidationIssue(
                "warning", label,
                "behavior_state.target_behavior_map is empty — "
                "different targets will behave identically"))
        else:
            for i, entry in enumerate(bs["target_behavior_map"]):
                examples = entry.get("action_examples") or []
                target = entry.get("target_type", f"[{i}]")
                min_ex = _min_examples_for_target(target, _imp)
                if len(examples) < min_ex:
                    issues.append(ValidationIssue(
                        "warning", label,
                        f"target_behavior_map '{target}' has "
                        f"{len(examples)} action_examples "
                        f"(want >={min_ex})"))

    # --- relationships depth ---
    rels = snapshot.get("relationships") or []
    for i, rel in enumerate(rels):
        target = rel.get("target_character_id") or rel.get(
            "target_label", f"[{i}]")
        if not rel.get("driving_events"):
            issues.append(ValidationIssue(
                "warning", label,
                f"relationship '{target}' missing driving_events"))
        if not rel.get("relationship_history_summary"):
            issues.append(ValidationIssue(
                "warning", label,
                f"relationship '{target}' missing "
                f"relationship_history_summary"))

    # --- goals/obsessions split check ---
    if bs:
        has_old = bool(bs.get("core_drives"))
        has_new = bool(bs.get("core_goals")) or bool(bs.get("obsessions"))
        if has_old and not has_new:
            issues.append(ValidationIssue(
                "warning", label,
                "behavior_state uses legacy 'core_drives' — "
                "new extractions should use 'core_goals' + 'obsessions'"))

    eb = snapshot.get("emotional_baseline") or {}
    if eb:
        has_old_desires = bool(eb.get("active_desires"))
        has_new_desires = (bool(eb.get("active_goals"))
                          or bool(eb.get("active_obsessions")))
        if has_old_desires and not has_new_desires:
            issues.append(ValidationIssue(
                "warning", label,
                "emotional_baseline uses legacy 'active_desires' — "
                "new extractions should use 'active_goals' + "
                "'active_obsessions'"))

    # --- character_arc check (stages after the first) ---
    stage_delta = snapshot.get("stage_delta")
    character_arc = snapshot.get("character_arc")
    if stage_delta and not character_arc:
        issues.append(ValidationIssue(
            "warning", label,
            "character_arc is missing — "
            "snapshot should include overall arc from stage 1 to current"))

    # --- source_notes distribution ---
    source_notes = snapshot.get("source_notes") or []
    if source_notes:
        types = [n.get("source_type") for n in source_notes]
        if types and all(t == "canon" for t in types):
            issues.append(ValidationIssue(
                "warning", label,
                f"source_notes: all {len(types)} entries are 'canon' — "
                f"expected some inference/ambiguous"))

    return issues


def _check_baselines(work_dir: Path, char_id: str,
                     schema_dir: Path) -> list[ValidationIssue]:
    """Validate baseline files against their schemas."""
    issues: list[ValidationIssue] = []
    char_dir = work_dir / "characters" / char_id / "canon"

    baseline_checks = [
        ("voice_rules.json", "voice_rules.schema.json"),
        ("behavior_rules.json", "behavior_rules.schema.json"),
        ("boundaries.json", "boundaries.schema.json"),
        ("failure_modes.json", "failure_modes.schema.json"),
    ]

    for data_file, schema_file in baseline_checks:
        data_path = char_dir / data_file
        if not data_path.exists():
            # Baselines may not exist until first batch
            continue
        data = _load_json(data_path)
        if data is not None:
            issues.extend(_validate_schema(
                data, schema_dir / schema_file, str(data_path)))

    # --- identity.json depth checks ---
    identity_path = char_dir / "identity.json"
    if identity_path.exists():
        identity = _load_json(identity_path)
        if identity is not None:
            issues.extend(_validate_schema(
                identity, schema_dir / "identity.schema.json",
                str(identity_path)))
            if not identity.get("core_wounds"):
                issues.append(ValidationIssue(
                    "warning", str(identity_path),
                    "core_wounds is empty — identity should include "
                    "root psychological traumas"))
            if not identity.get("key_relationships"):
                issues.append(ValidationIssue(
                    "warning", str(identity_path),
                    "key_relationships is empty — identity should "
                    "include cross-story relationship arcs"))
            # Check goals/obsessions split in behavior_rules
            br_path = char_dir / "behavior_rules.json"
            if br_path.exists():
                br = _load_json(br_path)
                if br and br.get("core_drives") and not (
                        br.get("core_goals") or br.get("obsessions")):
                    issues.append(ValidationIssue(
                        "warning", str(br_path),
                        "behavior_rules uses legacy 'core_drives' — "
                        "new extractions should use 'core_goals' + "
                        "'obsessions'"))

    return issues


def _check_manifest(work_dir: Path, char_id: str,
                    schema_dir: Path) -> list[ValidationIssue]:
    """Validate manifest.json and check paths point to real directories."""
    issues: list[ValidationIssue] = []
    manifest_path = work_dir / "characters" / char_id / "manifest.json"

    if not manifest_path.exists():
        issues.append(ValidationIssue(
            "warning", str(manifest_path),
            f"manifest.json missing for {char_id}"))
        return issues

    data = _load_json(manifest_path)
    if data is None:
        return issues

    issues.extend(_validate_schema(
        data, schema_dir / "character_manifest.schema.json",
        str(manifest_path)))

    # Check that paths.stage_snapshot_root points to real directory
    paths = data.get("paths") or {}
    snapshot_root = paths.get("stage_snapshot_root", "")
    if snapshot_root:
        actual_dir = work_dir / snapshot_root
        if not actual_dir.exists():
            issues.append(ValidationIssue(
                "error", str(manifest_path),
                f"stage_snapshot_root '{snapshot_root}' does not exist "
                f"(expected: {actual_dir})"))

    return issues


def _check_memory_timeline(path: Path,
                           schema_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    schema_path = schema_dir / "memory_timeline_entry.schema.json"

    data = _load_json(path)
    if data is None:
        issues.append(ValidationIssue(
            "error", str(path), "Cannot parse memory timeline JSON"))
        return issues

    if not isinstance(data, list):
        issues.append(ValidationIssue(
            "error", str(path),
            "Memory timeline must be a JSON array"))
        return issues

    if len(data) == 0:
        issues.append(ValidationIssue(
            "warning", str(path), "Memory timeline is empty"))
        return issues

    source_types: list[str] = []
    for i, entry in enumerate(data):
        label = f"{path}:entry[{i}]"
        if not isinstance(entry, dict):
            issues.append(ValidationIssue("error", label, "Not an object"))
            continue

        issues.extend(_validate_schema(entry, schema_path, label))

        st = entry.get("source_type")
        if not st:
            issues.append(ValidationIssue(
                "warning", label, "source_type not set"))
        else:
            source_types.append(st)

    # Detect all-canon distribution
    if source_types and all(t == "canon" for t in source_types):
        issues.append(ValidationIssue(
            "warning", str(path),
            f"All {len(source_types)} memory entries are 'canon' — "
            f"some subjective experiences should be 'inference'"))

    return issues


def _check_memory_digest(path: Path, stage_id: str,
                         schema_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    schema_path = schema_dir / "memory_digest_entry.schema.json"

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        issues.append(ValidationIssue(
            "warning", str(path), "memory_digest.jsonl is empty"))
        return issues

    # Auto-repair if needed
    if not all(_is_valid_json_line(line) for line in text.splitlines()):
        ok, desc = try_repair_jsonl_file(path)
        if ok:
            logger.info("Auto-repaired %s (%s)", path.name, desc)
            text = path.read_text(encoding="utf-8").strip()

    stage_entries = 0
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            issues.append(ValidationIssue(
                "error", f"{path}:line[{i}]",
                "Invalid JSON line in memory_digest"))
            continue

        issues.extend(_validate_schema(entry, schema_path,
                                       f"{path}:line[{i}]"))
        if entry.get("stage_id") == stage_id:
            stage_entries += 1

    if stage_entries == 0:
        issues.append(ValidationIssue(
            "warning", str(path),
            f"No digest entries found for stage '{stage_id}'"))

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

def _load_json(path: Path, *, auto_repair: bool = True) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        if auto_repair:
            ok, desc = try_repair_json_file(path)
            if ok:
                logger.info("Auto-repaired %s (%s)", path.name, desc)
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
        logger.warning("Cannot load %s (repair failed)", path)
        return None
    except OSError as e:
        logger.warning("Cannot load %s: %s", path, e)
        return None


def _is_valid_json_line(line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    try:
        json.loads(line)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


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
