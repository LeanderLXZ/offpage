"""Phase 2 baseline gate.

After Phase 2 produces baseline outputs this validator checks that every
file parses as JSON, matches its schema, and carries the required non-
empty fields. Files validated (post-decision #54 + #58):

- `manifest.json` (works-level + world)
- `world/foundation/foundation.json` (phase 1 落 + phase 2 替换
  `major_factions[].key_figures` raw→character_id)
- `world/foundation/fixed_relationships.json`
- per-character `identity.json` + `target_baseline.json`

`stage_catalog.json` is NOT validated here — decision #58 made it a
phase-3 post_processing artifact (first stage's `upsert_stage_catalog`
initializes both world and character catalogs). `voice` / `behavior` /
`boundary` / `failure_modes` are no separate-file baselines (decision
#54 archive); their state lives inline in `stage_snapshot`.

It runs before Phase 3 starts so baseline issues surface immediately
rather than during stage extraction.

Stage-level validation lives in ``extraction.repair`` (L0–L3 checkers +
T0–T3 fixers), driven by ``orchestrator.run_stage_extraction``.

**L1/L2/L3 disambiguation** (see ``ai_context/decisions.md`` #25 + #40):
``extraction.repair``'s ``L0–L3`` here are the **checker hierarchy** for phase
3 stage extraction (L0=schema / L1=structural / L2=cross-check / L3=
semantic LLM). They are **not** the same as the phase 0 JSON-format
repair ``L1/L2/L3`` (regex / LLM-on-broken-JSON / full re-run) used only
inside ``orchestrator._summarize_chunk``. Same字面, different semantics;
互不依赖。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ...persona_extraction.core.json_repair import try_repair_json_file
from ...persona_extraction.core.schema_loader import load_schema
from ..shared.schema_tolerance import validate_with_length_tolerance
from ..types import ValidationIssue

logger = logging.getLogger(__name__)

try:
    import jsonschema
except ImportError as _jsonschema_exc:  # pragma: no cover
    raise ImportError(
        "jsonschema is a required dependency of persona-extraction. "
        "Install it with `pip install jsonschema` (or install the package "
        "with its dependencies). See docs/requirements.md §11.4."
    ) from _jsonschema_exc


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
    Consumed by the repair framework's StructuralChecker to raise the
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
    length_tolerance: float = 0.0,
) -> ValidationReport:
    """Validate Phase 2 baseline outputs (identity, manifest, foundation).

    Run after baseline production to catch issues early before Phase 3.

    ``length_tolerance > 0`` enables decision-#48 tolerance gate on every
    schema check (length-only failures within ±tolerance are accepted).
    Default 0.0 = pure strict validation. Callers should only set this on
    the terminal post-strict-retry path.
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
                str(works_manifest_path), length_tolerance=length_tolerance))

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
                str(world_manifest_path), length_tolerance=length_tolerance))

    # World foundation — phase 1 foundation lane 产出主体，phase 2 baseline 补齐
    # `major_factions[].key_figures`。schema validate 是 decision #54 显式要求
    # （character_id 合法性 + bound + 结构完整性都走 schema gate；fixed_relationships
    # / identity / target_baseline 同形态都走 _validate_schema）。
    foundation_path = work_dir / "world" / "foundation" / "foundation.json"
    if not foundation_path.exists():
        issues.append(ValidationIssue(
            "error", str(foundation_path), "foundation.json missing"))
    else:
        try_repair_json_file(foundation_path)
        data = _load_json(foundation_path)
        if data is None:
            issues.append(ValidationIssue(
                "error", str(foundation_path), "Invalid JSON"))
        elif not data.get("work_id"):
            issues.append(ValidationIssue(
                "error", str(foundation_path), "work_id is empty"))
        else:
            issues.extend(_validate_schema(
                data,
                schema_dir / "world" / "foundation.schema.json",
                str(foundation_path), length_tolerance=length_tolerance))

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
                str(fixed_rel_path), length_tolerance=length_tolerance))

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
                    str(id_path), length_tolerance=length_tolerance))
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
                    str(manifest_path), length_tolerance=length_tolerance))

        # target_baseline.json — required Phase 2 output, anchors phase 3
        # stage_snapshot target keys (set(三结构 keys) ==
        # set(targets[].target_character_id), enforced cross-file at the
        # phase 3 single-stage validate layer by repair's
        # TargetsKeysEqBaselineChecker; violations route into the
        # file-level repair lifecycle).
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
                    str(tb_path), length_tolerance=length_tolerance))
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

def _load_json(path: Path, *, auto_repair: bool = True) -> dict | None:
    """Load a JSON file expected to be an object.

    Every caller in this validator targets schemas whose root is an
    object; list-shaped or scalar JSON files are returned as ``None`` so
    they hit the "Invalid JSON" error branch alongside genuine parse
    failures. This keeps the error message uniform and lets the type
    checker prove `.get(...)` is safe at every callsite.
    """
    raw: object
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        if auto_repair:
            ok, desc = try_repair_json_file(path)
            if ok:
                logger.info("Auto-repaired %s (%s)", path.name, desc)
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    logger.warning("Cannot load %s (repair failed)", path)
                    return None
            else:
                logger.warning("Cannot load %s (repair failed)", path)
                return None
        else:
            logger.warning("Cannot load %s (repair failed)", path)
            return None
    except OSError as e:
        logger.warning("Cannot load %s: %s", path, e)
        return None
    if not isinstance(raw, dict):
        logger.warning(
            "Loaded %s but top-level is %s, expected object",
            path, type(raw).__name__)
        return None
    return raw


def _validate_schema(data: dict, schema_path: Path,
                     file_label: str,
                     length_tolerance: float = 0.0) -> list[ValidationIssue]:
    """Validate data against a JSON Schema (jsonschema is a hard dependency).

    ``length_tolerance > 0`` enables the decision-#48 tolerance gate: if
    strict validation fails *only* on ``minLength`` / ``maxLength`` and a
    relaxed schema (×0.9 floor / ×1.1 ceil at default 0.10) passes, no
    issues are returned. Non-zero tolerance is meant for the
    "strict-retry-budget exhausted" terminal path; callers that need a
    pure strict gate should leave the default 0.0.
    """
    if not schema_path.exists():
        return [ValidationIssue("warning", file_label,
                                f"Schema not found: {schema_path.name}")]

    try:
        schema = load_schema(schema_path)
    except (OSError, ValueError):
        return [ValidationIssue("warning", file_label,
                                f"Cannot load schema: {schema_path.name}")]

    if length_tolerance > 0.0:
        try:
            ok_tol, tol_issues = validate_with_length_tolerance(
                data, schema, tolerance=length_tolerance)
        except jsonschema.SchemaError as e:
            return [ValidationIssue(
                "warning", file_label,
                f"Schema itself is invalid: {e.message}")]
        if ok_tol:
            return []
        # Restamp issues with file_label (helper fills "(length_tolerance_gate)")
        return [ValidationIssue(i.severity, file_label, i.message)
                for i in tol_issues]

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
