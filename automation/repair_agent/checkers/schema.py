"""L1 — JSON Schema checker.

Validates file content against its JSON Schema definition.
Zero LLM tokens.  ``jsonschema`` is a hard dependency.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import BaseChecker
from ..protocol import FileEntry, Issue

try:
    import jsonschema as _jsonschema
except ImportError as _exc:
    raise ImportError(
        "jsonschema is a required dependency of repair_agent. "
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

            # For JSONL, validate each entry against the schema
            if Path(f.path).suffix == ".jsonl" and isinstance(content, list):
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
        validator = _jsonschema.Draft7Validator(schema)
        for error in sorted(validator.iter_errors(data),
                            key=lambda e: list(e.absolute_path)):
            path_parts = [str(p) for p in error.absolute_path]
            json_path = prefix + "." + ".".join(path_parts) if path_parts else prefix
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


def _safe_value(val):
    """Ensure context values are JSON-serializable."""
    if isinstance(val, (str, int, float, bool, type(None))):
        return val
    if isinstance(val, (list, tuple)):
        return val[:10]
    return str(val)[:200]
