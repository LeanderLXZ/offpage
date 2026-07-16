"""L1 — JSON Schema checker.

Validates file content against its JSON Schema definition.
Zero LLM tokens.  ``jsonschema`` is a hard dependency.
"""

from __future__ import annotations

from . import BaseChecker
from ..protocol import FileEntry, Issue

try:
    import jsonschema as _jsonschema
except ImportError as _exc:
    raise ImportError(
        "jsonschema is a required dependency of the repair framework. "
        "Install it with `pip install jsonschema`."
    ) from _exc


class SchemaChecker(BaseChecker):
    """Layer 1: validate content against JSON Schema."""

    layer = 1

    def check(self, files: list[FileEntry], **kwargs) -> list[Issue]:
        issues: list[Issue] = []
        for f in files:
            if f.schema is None:
                continue
            content = f.content if f.content is not None else f.load()
            if content is None:
                continue

            # JSONL files decode to lists; some JSON files also hold arrays
            # of entries (e.g., memory_timeline/{stage_id}.json). In both
            # cases the schema describes a single entry, so iterate when
            # content is a list and validate per-entry.
            if isinstance(content, list):
                for idx, entry in enumerate(content):
                    issues.extend(
                        self._validate_one(entry, f.schema, f.path,
                                           prefix=f"$[{idx}]"))
            else:
                issues.extend(self._validate_one(content, f.schema, f.path))
        return issues

    def _validate_one(self, data: dict, schema: dict, file_path: str,
                      prefix: str = "$") -> list[Issue]:
        issues: list[Issue] = []
        validator = _jsonschema.Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(data),
                            key=lambda e: list(e.absolute_path)):
            json_path = _build_json_path(prefix, error.absolute_path)

            # additionalProperties anchors at the offending *container*;
            # extract_subtree on a container makes a downstream T1 patch
            # rewrite the whole subtree. Narrow to one issue per unexpected
            # key so the fixer targets that leaf (and T0 can delete it).
            if error.validator == "additionalProperties":
                extra = _unexpected_keys(error)
                if extra:
                    for key in extra:
                        issues.append(Issue(
                            file=file_path,
                            json_path=f"{json_path}.{key}",
                            category="schema",
                            severity="error",
                            rule="schema_additionalProperties",
                            message=(f"Unexpected property '{key}' not "
                                     f"allowed by schema"),
                            context={
                                "validator": "additionalProperties",
                                "extra_key": key,
                                "schema_path": list(error.schema_path),
                            },
                        ))
                    continue
                # Fall through to the generic container-level issue when
                # the extra keys can't be determined (e.g. patternProperties).

            issues.append(Issue(
                file=file_path,
                json_path=json_path,
                category="schema",
                severity="error",
                rule=f"schema_{error.validator}",
                message=error.message[:300],
                context={
                    "validator": error.validator,
                    "validator_value": _safe_value(error.validator_value),
                    "schema_path": list(error.schema_path),
                },
            ))
        return issues


def _build_json_path(prefix: str, absolute_path) -> str:
    """Render a jsonschema ``absolute_path`` as a ``field_patch`` json_path.

    Array indices arrive as ``int`` and MUST render as ``[i]``, not ``.i``:
    ``field_patch._parse_path`` reads a dot-token as a string key, so a
    ``$.relationships.1.attitude`` path makes ``_navigate`` try a str lookup
    on a list and raise ``KeyError`` — every tier then silently skips the
    issue. Bracket form matches what the structural / semantic checkers
    already emit.
    """
    path = prefix
    for part in absolute_path:
        if isinstance(part, int) and not isinstance(part, bool):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _unexpected_keys(error) -> list[str]:
    """Best-effort list of instance keys an additionalProperties error
    flags. Returns [] when it can't be determined cheaply (e.g. the
    subschema uses ``patternProperties``), so the caller keeps the
    generic container-level issue.
    """
    instance = error.instance
    subschema = error.schema
    if not isinstance(instance, dict) or not isinstance(subschema, dict):
        return []
    if subschema.get("patternProperties"):
        return []
    allowed = set(subschema.get("properties", {}).keys())
    return [k for k in instance if k not in allowed]


def _safe_value(val):
    """Ensure context values are JSON-serializable."""
    if isinstance(val, (str, int, float, bool, type(None))):
        return val
    if isinstance(val, (list, tuple)):
        return val[:10]
    return str(val)[:200]
