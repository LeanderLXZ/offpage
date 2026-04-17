"""Programmatic validator — Phase 2.5 baseline gate.

After Phase 2.5 produces baseline outputs (identity, manifest, world
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

    # fixed_relationships.json — required output of Phase 2.5
    fixed_rel_path = (work_dir / "world" / "foundation"
                      / "fixed_relationships.json")
    if not fixed_rel_path.exists():
        issues.append(ValidationIssue(
            "error", str(fixed_rel_path),
            "fixed_relationships.json not produced "
            "(Phase 2.5 must create)"))
    else:
        try_repair_json_file(fixed_rel_path)
        fr_data = _load_json(fixed_rel_path)
        if fr_data is None:
            issues.append(ValidationIssue(
                "error", str(fixed_rel_path), "Invalid JSON"))
        else:
            issues.extend(_validate_schema(
                fr_data,
                schema_dir / "fixed_relationships.schema.json",
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

        # Skeleton baseline files (warn only — non-critical)
        _baseline_schemas = {
            "voice_rules.json": "voice_rules.schema.json",
            "behavior_rules.json": "behavior_rules.schema.json",
            "boundaries.json": "boundaries.schema.json",
            "failure_modes.json": "failure_modes.schema.json",
        }
        for fname, schema_name in _baseline_schemas.items():
            fpath = char_dir / fname
            if not fpath.exists():
                issues.append(ValidationIssue(
                    "warning", str(fpath),
                    f"{fname} not produced (Phase 2.5 should create)"))
            else:
                try_repair_json_file(fpath)
                data = _load_json(fpath)
                if data is None:
                    issues.append(ValidationIssue(
                        "error", str(fpath), "Invalid JSON"))
                else:
                    issues.extend(_validate_schema(
                        data, schema_dir / schema_name, str(fpath)))

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
