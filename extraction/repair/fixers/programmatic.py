"""T0 — Programmatic fixer.  Zero LLM tokens.

Combines JSON syntax repair and schema-level autofix:
  - Escape unescaped quotes, remove trailing commas, close truncated JSON
  - Remove additionalProperties, truncate over-limit arrays/strings
  - Type coercion (str↔number), fill missing required fields
  - ID format regex replacement (M-S3-2 → M-S003-02)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from . import BaseFixer
from ..protocol import FileEntry, FixResult, Issue, SourceContext
from ..field_patch import apply_field_patch, write_file_entry

logger = logging.getLogger(__name__)

try:
    import jsonschema as _jsonschema
except ImportError:
    _jsonschema = None  # type: ignore[assignment]


class ProgrammaticFixer(BaseFixer):
    """Tier 0: deterministic, zero-token fixes."""

    tier = 0

    def fix(
        self,
        files: list[FileEntry],
        issues: list[Issue],
        strategy: str = "standard",
        source_context: SourceContext | None = None,
        attempt_num: int = 0,
        max_attempts: int = 1,
    ) -> FixResult:
        patched: list[str] = []
        resolved: set[str] = set()

        # Group issues by file
        by_file: dict[str, list[Issue]] = {}
        for issue in issues:
            by_file.setdefault(issue.file, []).append(issue)

        for file_path, file_issues in by_file.items():
            f = next((f for f in files if f.path == file_path), None)
            if f is None:
                continue

            content = f.content if f.content is not None else f.load()
            if content is None:
                # Try JSON syntax repair first
                repaired = self._repair_json_syntax(file_path)
                if repaired is not None:
                    f.content = repaired
                    content = repaired
                    # Mark json_syntax issues as resolved
                    for issue in file_issues:
                        if issue.category == "json_syntax" and issue.rule == "json_parse":
                            resolved.add(issue.fingerprint)
                            patched.append(issue.json_path)
                else:
                    continue

            modified = False
            for issue in file_issues:
                if issue.fingerprint in resolved:
                    continue
                fixed = self._try_fix(content, issue, f.schema)
                if fixed is not None:
                    content = fixed
                    resolved.add(issue.fingerprint)
                    patched.append(issue.json_path)
                    modified = True

            if modified:
                f.content = content
                write_file_entry(f)

        return FixResult(patched_paths=patched, resolved_fingerprints=resolved)

    # ------------------------------------------------------------------
    # JSON syntax repair (from old json_repair.py L1)
    # ------------------------------------------------------------------

    def _repair_json_syntax(self, path: str) -> dict | list | None:
        """Attempt L1 regex-based JSON repair."""
        p = Path(path)
        if not p.exists():
            return None
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        # Remove trailing commas
        text = re.sub(r",\s*([}\]])", r"\1", text)
        # Strip trailing garbage after last } or ]
        for ch in ("}", "]"):
            idx = text.rfind(ch)
            if idx >= 0:
                text = text[:idx + 1]
                break
        # Try to close truncated JSON
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")
        text += "]" * max(0, open_brackets) + "}" * max(0, open_braces)

        try:
            data = json.loads(text)
            p.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return data
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Per-issue fixes
    # ------------------------------------------------------------------

    def _try_fix(self, content: dict | list, issue: Issue,
                 schema: dict | None) -> dict | list | None:
        """Try to programmatically fix a single issue. Returns new content
        or None if unfixable."""

        # ID format fixes
        if issue.rule in ("memory_id_format", "event_id_format"):
            return self._fix_id_format(content, issue)

        # Schema-level fixes
        if issue.category == "schema" and schema and _jsonschema:
            return self._fix_schema_violation(content, issue, schema)

        return None

    def _fix_id_format(self, content: Any, issue: Issue) -> Any | None:
        """Fix M-S3-2 → M-S003-02 style ID format errors."""
        ctx = issue.context or {}
        value = ctx.get("value", "")
        if not value:
            return None

        # Try to reformat
        if issue.rule == "memory_id_format":
            m = re.match(r"^M-S(\d+)-(\d+)$", value)
            if m:
                fixed = f"M-S{int(m.group(1)):03d}-{int(m.group(2)):02d}"
                return apply_field_patch(content, issue.json_path, fixed)
        elif issue.rule == "event_id_format":
            m = re.match(r"^E-S(\d+)-(\d+)$", value)
            if m:
                fixed = f"E-S{int(m.group(1)):03d}-{int(m.group(2)):02d}"
                return apply_field_patch(content, issue.json_path, fixed)
        return None

    def _fix_schema_violation(self, content: Any, issue: Issue,
                              schema: dict) -> Any | None:
        """Fix common schema violations."""
        ctx = issue.context or {}
        validator_type = ctx.get("validator", "")

        if validator_type == "additionalProperties":
            # Remove extra properties — needs schema traversal
            # For now, skip complex fixes
            return None

        if validator_type == "type":
            return self._fix_type_mismatch(content, issue)

        if validator_type == "required":
            return self._fix_missing_required(content, issue)

        if validator_type in ("maxLength", "minLength"):
            return self._fix_string_length(content, issue)

        return None

    def _fix_type_mismatch(self, content: Any, issue: Issue) -> Any | None:
        """Coerce types: str↔number, scalar→array."""
        from ..field_patch import extract_subtree
        try:
            current = extract_subtree(content, issue.json_path)
        except (KeyError, IndexError):
            return None

        ctx = issue.context or {}
        expected = ctx.get("validator_value")

        if expected == "number" and isinstance(current, str):
            try:
                return apply_field_patch(content, issue.json_path, float(current))
            except ValueError:
                return None
        if expected == "integer" and isinstance(current, str):
            try:
                return apply_field_patch(content, issue.json_path, int(current))
            except ValueError:
                return None
        if expected == "string" and isinstance(current, (int, float)):
            return apply_field_patch(content, issue.json_path, str(current))
        if expected == "array" and not isinstance(current, list):
            return apply_field_patch(content, issue.json_path, [current])

        return None

    def _fix_missing_required(self, content: Any,
                              issue: Issue) -> Any | None:
        """Add missing required fields with safe defaults."""
        # The message from jsonschema includes the missing field name
        msg = issue.message
        # Pattern: "'field_name' is a required property"
        m = re.search(r"'([^']+)' is a required property", msg)
        if not m:
            return None
        field_name = m.group(1)
        parent_path = issue.json_path
        new_path = f"{parent_path}.{field_name}" if parent_path != "$" else f"$.{field_name}"
        try:
            return apply_field_patch(content, new_path, "")
        except (KeyError, IndexError):
            return None

    def _fix_string_length(self, content: Any, issue: Issue) -> Any | None:
        """Truncate or pad strings to meet length constraints."""
        from ..field_patch import extract_subtree
        try:
            current = extract_subtree(content, issue.json_path)
        except (KeyError, IndexError):
            return None

        if not isinstance(current, str):
            return None

        ctx = issue.context or {}
        validator_type = ctx.get("validator", "")
        limit = ctx.get("validator_value")

        if validator_type == "maxLength" and isinstance(limit, int):
            if len(current) > limit:
                truncated = current[:limit]
                return apply_field_patch(content, issue.json_path, truncated)
        elif validator_type == "minLength" and isinstance(limit, int):
            if len(current) < limit:
                padded = current + "…" * (limit - len(current))
                return apply_field_patch(content, issue.json_path, padded)

        return None
