"""Programmatic validator — Phase 2 baseline gate.

After Phase 2 produces baseline outputs (identity, manifest, world
foundation, and the skeleton voice/behavior/boundary/failure-mode files)
this validator checks that every file parses as JSON, matches its schema
and carries the required non-empty fields. It runs before Phase 3 starts
so baseline issues surface immediately rather than during stage
extraction.

Stage-level validation lives in ``repair_agent`` (L0–L3 checkers +
T0–T3 fixers), driven by ``orchestrator.run_stage_extraction``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .json_repair import try_repair_json_file

logger = logging.getLogger(__name__)

try:
    import jsonschema
except ImportError as _jsonschema_exc:  # pragma: no cover
    # jsonschema is declared as a required dependency in automation/pyproject.toml.
    # If import fails here, the environment is broken — fail loudly rather than
    # silently downgrade the gate. See requirements.md §11.4 "第一层：程序化
    # 校验（jsonschema 为硬依赖）".
    raise ImportError(
        "jsonschema is a required dependency of persona-extraction. "
        "Install it with `pip install jsonschema` (or install the automation "
        "package with its dependencies). See docs/requirements.md §11.4."
    ) from _jsonschema_exc


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


def load_importance_map(project_root: Path,
                        work_id: str) -> dict[str, str]:
    """Load character importance from candidate_characters.json.

    Returns ``{character_id: importance}`` (e.g. ``{"角色A": "主角"}``).
    Consumed by the repair agent's StructuralChecker to raise the
    minimum example count for main / important characters.
    """
    path = (project_root / "works" / work_id / "analysis"
            / "candidate_characters.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {c["character_id"]: c.get("importance", "")
                for c in data.get("candidates", [])
                if c.get("character_id")}
    except (json.JSONDecodeError, OSError, KeyError):
        return {}


_IMPORTANCE_RANK = {"主角": 3, "重要配角": 2}


def importance_for_target(
    target: str, importance_map: dict[str, str],
) -> str:
    """Resolve a ``target_type`` label to its canonical importance.

    Matches each ``character_id`` in ``importance_map`` as a substring of
    ``target`` so that annotated labels (``<character_a>（<phase_alias>）``) still
    map back to the base character. Among matches, picks the most
    important importance; ties broken by longer ``character_id`` so that
    a specific id wins over one that happens to be a substring of another
    (e.g. ``张三丰`` over ``张三`` when both would match).
    """
    if not isinstance(target, str) or not target or not importance_map:
        return "其他"
    best: tuple[int, int, str] | None = None  # (rank, id_len, importance)
    for char_id, importance in importance_map.items():
        if not char_id or char_id not in target:
            continue
        rank = _IMPORTANCE_RANK.get(importance, 1)
        score = (rank, len(char_id))
        if best is None or score > (best[0], best[1]):
            best = (rank, len(char_id), importance or "其他")
    if best is None:
        return "其他"
    return best[2]


def importance_min_examples(importance: str) -> int:
    """Minimum example count required for a given importance.

    主角 → 5, 重要配角 → 3, others → 1.  Shared by the L2 structural
    checker and the Phase 3.5 consistency checker so both enforce the
    same threshold.
    """
    if "主角" in importance:
        return 5
    if "重要" in importance:
        return 3
    return 1


def validate_baseline(
    project_root: Path,
    work_id: str,
    character_ids: list[str],
    schema_dir: Path | None = None,
) -> ValidationReport:
    """Validate Phase 2 baseline outputs (identity, manifest, foundation).

    Run after baseline production to catch issues early before Phase 3.
    """
    issues: list[ValidationIssue] = []
    schema_dir = schema_dir or (project_root / "schemas")
    work_dir = project_root / "works" / work_id

    # Works manifest (written programmatically at end of Phase 1.5)
    works_manifest_path = work_dir / "manifest.json"
    if not works_manifest_path.exists():
        issues.append(ValidationIssue(
            "error", str(works_manifest_path),
            "works manifest missing (should be written at Phase 1.5 end)"))
    else:
        try_repair_json_file(works_manifest_path)
        wm_data = _load_json(works_manifest_path)
        if wm_data is None:
            issues.append(ValidationIssue(
                "error", str(works_manifest_path), "Invalid JSON"))
        else:
            issues.extend(_validate_schema(
                wm_data,
                schema_dir / "work" / "works_manifest.schema.json",
                str(works_manifest_path)))

    # World manifest (written programmatically at end of Phase 2)
    world_manifest_path = work_dir / "world" / "manifest.json"
    if not world_manifest_path.exists():
        issues.append(ValidationIssue(
            "error", str(world_manifest_path),
            "world manifest missing (should be written at Phase 2 end)"))
    else:
        try_repair_json_file(world_manifest_path)
        wom_data = _load_json(world_manifest_path)
        if wom_data is None:
            issues.append(ValidationIssue(
                "error", str(world_manifest_path), "Invalid JSON"))
        else:
            issues.extend(_validate_schema(
                wom_data,
                schema_dir / "world" / "world_manifest.schema.json",
                str(world_manifest_path)))

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

    # fixed_relationships.json — required output of Phase 2
    fixed_rel_path = (work_dir / "world" / "foundation"
                      / "fixed_relationships.json")
    if not fixed_rel_path.exists():
        issues.append(ValidationIssue(
            "error", str(fixed_rel_path),
            "fixed_relationships.json not produced "
            "(Phase 2 must create)"))
    else:
        try_repair_json_file(fixed_rel_path)
        fr_data = _load_json(fixed_rel_path)
        if fr_data is None:
            issues.append(ValidationIssue(
                "error", str(fixed_rel_path), "Invalid JSON"))
        else:
            issues.extend(_validate_schema(
                fr_data,
                schema_dir / "world" / "fixed_relationships.schema.json",
                str(fixed_rel_path)))

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
                    identity, schema_dir / "character" / "identity.schema.json",
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
                    schema_dir / "character" / "character_manifest.schema.json",
                    str(manifest_path)))

        # target_baseline.json — required Phase 2 output, anchors phase 3
        # stage_snapshot target keys (target_voice_map / target_behavior_map
        # / relationships keys ⊆ targets[].target_character_id).
        tb_path = char_dir / "target_baseline.json"
        if not tb_path.exists():
            issues.append(ValidationIssue(
                "error", str(tb_path),
                "target_baseline.json missing (Phase 2 must produce)"))
        else:
            try_repair_json_file(tb_path)
            tb_data = _load_json(tb_path)
            if tb_data is None:
                issues.append(ValidationIssue(
                    "error", str(tb_path), "Invalid JSON"))
            else:
                issues.extend(_validate_schema(
                    tb_data,
                    schema_dir / "character" / "target_baseline.schema.json",
                    str(tb_path)))
                if tb_data.get("character_id") != char_id:
                    issues.append(ValidationIssue(
                        "error", str(tb_path),
                        f"character_id={tb_data.get('character_id')!r} "
                        f"does not match directory {char_id!r}"))

    passed = not any(i.severity == "error" for i in issues)
    return ValidationReport(passed=passed, issues=issues)


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


def _validate_schema(data: dict, schema_path: Path,
                     file_label: str) -> list[ValidationIssue]:
    """Validate data against a JSON Schema (jsonschema is a hard dependency)."""
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
