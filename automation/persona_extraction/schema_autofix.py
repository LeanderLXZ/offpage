"""Schema-level autofix — programmatic repair for JSON Schema violations.

Complements ``json_repair.py`` (which handles JSON *syntax* errors).
This module handles structurally valid JSON that violates schema
constraints: extra properties, over-limit arrays, over-length strings,
missing required fields, and type mismatches.

Zero LLM tokens — all fixes are deterministic.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import jsonschema

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def attempt_schema_autofix(
    file_path: Path,
    schema_path: Path,
) -> tuple[bool, list[str]]:
    """Try to programmatically fix all schema violations in *file_path*.

    Returns ``(any_fix_applied, descriptions)`` where *descriptions*
    lists human-readable strings of what was fixed.  The caller should
    re-validate after this returns ``True``.
    """
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("schema_autofix: cannot load %s: %s", file_path, e)
        return False, [f"Cannot load file: {e}"]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("schema_autofix: cannot load schema %s: %s",
                        schema_path, e)
        return False, [f"Cannot load schema: {e}"]

    errors = _collect_all_errors(data, schema)
    if not errors:
        return False, []

    fixes: list[str] = []
    for err in errors:
        fixed = _apply_fix(data, schema, err)
        if fixed:
            fixes.append(fixed)

    if not fixes:
        return False, []

    # Write back
    file_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("schema_autofix: applied %d fix(es) to %s: %s",
                len(fixes), file_path.name, "; ".join(fixes))
    return True, fixes


# ---------------------------------------------------------------------------
# Collect all validation errors (not just the first)
# ---------------------------------------------------------------------------

def _collect_all_errors(
    data: dict,
    schema: dict,
) -> list[jsonschema.ValidationError]:
    """Return all schema validation errors, sorted deepest-path-first."""
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    errors = list(validator.iter_errors(data))
    # Sort deepest first so fixes to nested paths don't invalidate
    # parent paths processed later.
    errors.sort(key=lambda e: len(list(e.absolute_path)), reverse=True)
    return errors


# ---------------------------------------------------------------------------
# Fix dispatcher
# ---------------------------------------------------------------------------

def _apply_fix(
    data: dict,
    schema: dict,
    error: jsonschema.ValidationError,
) -> str | None:
    """Apply a single programmatic fix.  Returns description or None."""
    validator_type = error.validator

    if validator_type == "additionalProperties":
        return _fix_additional_properties(data, error)
    if validator_type == "maxItems":
        return _fix_max_items(data, error)
    if validator_type == "maxLength":
        return _fix_max_length(data, error)
    if validator_type == "minLength":
        return _fix_min_length(data, error)
    if validator_type == "type":
        return _fix_type(data, error)
    if validator_type == "required":
        return _fix_required(data, error)
    if validator_type == "enum":
        return _fix_enum(data, error)

    return None


# ---------------------------------------------------------------------------
# Individual fixers
# ---------------------------------------------------------------------------

def _navigate(data: dict, path: list) -> tuple:
    """Navigate to parent and return (parent, key, exists)."""
    node = data
    for i, segment in enumerate(path[:-1]):
        if isinstance(node, dict):
            node = node.get(segment)
        elif isinstance(node, list) and isinstance(segment, int):
            node = node[segment] if segment < len(node) else None
        else:
            return None, None, False
        if node is None:
            return None, None, False
    return node, path[-1] if path else None, True


def _fix_additional_properties(
    data: dict,
    error: jsonschema.ValidationError,
) -> str | None:
    """Remove properties not allowed by the schema."""
    path = list(error.absolute_path)
    # additionalProperties error points to the object containing the extra key.
    # error.message is like "Additional properties are not allowed ('foo' ...)"
    # The allowed keys come from the sub-schema's "properties".
    sub_schema = error.schema
    allowed = set(sub_schema.get("properties", {}).keys())
    if not allowed:
        return None

    # Navigate to the offending object
    if path:
        parent, key, ok = _navigate(data, path)
        if not ok or parent is None:
            return None
        try:
            obj = parent[key]
        except (KeyError, IndexError, TypeError):
            return None
    else:
        obj = data

    if not isinstance(obj, dict):
        return None

    extra = set(obj.keys()) - allowed
    # Also allow patternProperties keys
    if "patternProperties" in sub_schema:
        import re as _re
        for pattern in sub_schema["patternProperties"]:
            extra = {k for k in extra if not _re.match(pattern, k)}
    if not extra:
        return None

    for k in extra:
        del obj[k]
    return f"removed extra properties {extra} at /{'/'.join(str(p) for p in path)}"


def _fix_max_items(
    data: dict,
    error: jsonschema.ValidationError,
) -> str | None:
    """Truncate array to maxItems limit."""
    path = list(error.absolute_path)
    if not path:
        return None
    parent, key, ok = _navigate(data, path)
    if not ok or parent is None:
        return None

    arr = parent[key]
    if not isinstance(arr, list):
        return None

    limit = error.schema.get("maxItems")
    if limit is None or len(arr) <= limit:
        return None

    old_len = len(arr)
    parent[key] = arr[:limit]
    path_str = "/".join(str(p) for p in path)
    return f"truncated /{path_str} from {old_len} to {limit} items"


def _fix_max_length(
    data: dict,
    error: jsonschema.ValidationError,
) -> str | None:
    """Truncate string to maxLength."""
    path = list(error.absolute_path)
    if not path:
        return None
    parent, key, ok = _navigate(data, path)
    if not ok or parent is None:
        return None

    val = parent[key]
    if not isinstance(val, str):
        return None

    limit = error.schema.get("maxLength")
    if limit is None or len(val) <= limit:
        return None

    parent[key] = val[:limit]
    path_str = "/".join(str(p) for p in path)
    return f"truncated string at /{path_str} from {len(val)} to {limit} chars"


def _fix_min_length(
    data: dict,
    error: jsonschema.ValidationError,
) -> str | None:
    """Pad empty string to satisfy minLength (fill with placeholder)."""
    path = list(error.absolute_path)
    if not path:
        return None
    parent, key, ok = _navigate(data, path)
    if not ok or parent is None:
        return None

    val = parent[key]
    if not isinstance(val, str):
        return None

    limit = error.schema.get("minLength", 1)
    if len(val) >= limit:
        return None

    # Only fix empty/near-empty strings — don't fabricate content
    if len(val) > 5:
        return None

    parent[key] = val.ljust(limit, "…")
    path_str = "/".join(str(p) for p in path)
    return f"padded string at /{path_str} to meet minLength={limit}"


def _fix_type(
    data: dict,
    error: jsonschema.ValidationError,
) -> str | None:
    """Simple type coercions: string↔number, wrap scalar in array."""
    path = list(error.absolute_path)
    if not path:
        return None
    parent, key, ok = _navigate(data, path)
    if not ok or parent is None:
        return None

    val = parent[key]
    expected = error.schema.get("type")
    if not expected:
        return None

    path_str = "/".join(str(p) for p in path)

    # string expected, got number
    if expected == "string" and isinstance(val, (int, float)):
        parent[key] = str(val)
        return f"coerced number to string at /{path_str}"

    # integer expected, got string
    if expected == "integer" and isinstance(val, str):
        try:
            parent[key] = int(val)
            return f"coerced string to integer at /{path_str}"
        except ValueError:
            return None

    # array expected, got scalar — wrap in array
    if expected == "array" and not isinstance(val, list):
        parent[key] = [val]
        return f"wrapped scalar in array at /{path_str}"

    return None


def _fix_required(
    data: dict,
    error: jsonschema.ValidationError,
) -> str | None:
    """Add missing required fields with safe empty defaults."""
    path = list(error.absolute_path)

    # Navigate to the object that's missing the field
    if path:
        parent, key, ok = _navigate(data, path)
        if not ok or parent is None:
            return None
        try:
            obj = parent[key]
        except (KeyError, IndexError, TypeError):
            return None
    else:
        obj = data

    if not isinstance(obj, dict):
        return None

    # error.message is like "'foo' is a required property"
    required = error.schema.get("required", [])
    props_schema = error.schema.get("properties", {})
    added = []
    for field_name in required:
        if field_name not in obj:
            # Infer default from property schema type
            prop_schema = props_schema.get(field_name, {})
            prop_type = prop_schema.get("type", "string")
            if prop_type == "string":
                obj[field_name] = ""
            elif prop_type == "array":
                obj[field_name] = []
            elif prop_type == "object":
                obj[field_name] = {}
            elif prop_type == "integer":
                obj[field_name] = 0
            elif prop_type == "number":
                obj[field_name] = 0.0
            elif prop_type == "boolean":
                obj[field_name] = False
            else:
                obj[field_name] = ""
            added.append(field_name)

    if not added:
        return None
    path_str = "/".join(str(p) for p in path) if path else "(root)"
    return f"added missing required fields {added} at /{path_str}"


def _fix_enum(
    data: dict,
    error: jsonschema.ValidationError,
) -> str | None:
    """Fuzzy-match to closest enum value."""
    path = list(error.absolute_path)
    if not path:
        return None
    parent, key, ok = _navigate(data, path)
    if not ok or parent is None:
        return None

    val = parent[key]
    allowed = error.schema.get("enum", [])
    if not allowed or not isinstance(val, str):
        return None

    # Case-insensitive exact match first
    lower_map = {str(a).lower(): a for a in allowed}
    if isinstance(val, str) and val.lower() in lower_map:
        parent[key] = lower_map[val.lower()]
        path_str = "/".join(str(p) for p in path)
        return f"fixed enum case at /{path_str}: '{val}' → '{parent[key]}'"

    # No fuzzy match attempted — too risky for semantic correctness
    return None
