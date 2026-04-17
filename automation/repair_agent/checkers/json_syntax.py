"""L0 — JSON syntax checker.

Verifies files can be parsed as valid JSON/JSONL with UTF-8 encoding.
Zero LLM tokens.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import BaseChecker
from ..protocol import FileEntry, Issue


class JsonSyntaxChecker(BaseChecker):
    """Layer 0: check that files exist and parse as valid JSON."""

    layer = 0

    def check(self, files: list[FileEntry], **kwargs) -> list[Issue]:
        issues: list[Issue] = []
        for f in files:
            p = Path(f.path)
            if not p.exists():
                issues.append(Issue(
                    file=f.path, json_path="$", category="json_syntax",
                    severity="error", rule="file_exists",
                    message=f"File does not exist: {f.path}",
                ))
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                issues.append(Issue(
                    file=f.path, json_path="$", category="json_syntax",
                    severity="error", rule="file_readable",
                    message=f"Cannot read file: {exc}",
                ))
                continue
            if not text.strip():
                issues.append(Issue(
                    file=f.path, json_path="$", category="json_syntax",
                    severity="error", rule="file_non_empty",
                    message="File is empty",
                ))
                continue
            try:
                if p.suffix == ".jsonl":
                    entries = []
                    for i, line in enumerate(text.splitlines(), 1):
                        if line.strip():
                            entries.append(json.loads(line))
                    f.content = entries  # cache parsed JSONL entries
                else:
                    parsed = json.loads(text)
                    f.content = parsed  # cache for later checkers
            except json.JSONDecodeError as exc:
                issues.append(Issue(
                    file=f.path, json_path="$", category="json_syntax",
                    severity="error", rule="json_parse",
                    message=f"JSON parse error: {exc}",
                    context={"error": str(exc)},
                ))
        return issues
