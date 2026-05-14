"""T1 — Local patch fixer.  Field-level LLM repair without source text.

Sends the broken field subtree + issue description to an LLM,
gets back a patched value.  No original chapters needed.

Retry strategies:
  attempt 0: standard prompt + issue description
  attempt 1: add related fields from same file as context
  attempt 2: add same field from previous stage as continuity reference
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from . import BaseFixer
from ..field_patch import apply_field_patch, extract_subtree, write_file_entry
from ..protocol import FileEntry, FixResult, Issue, SourceContext

logger = logging.getLogger(__name__)

PATCH_SYSTEM = """\
You are a precise JSON field repair tool.  You will receive:
1. A JSON field value that has an issue
2. A description of the issue
3. Optional context from the same file

Your task: output ONLY the corrected JSON value for this field.
Do not output anything else — no explanation, no markdown fences.
The output must be valid JSON that can replace the broken field directly.
"""


class LocalPatchFixer(BaseFixer):
    """Tier 1: field-level LLM patch without source text."""

    tier = 1

    def __init__(self, llm_call: Callable[..., str] | None = None):
        self._llm_call = llm_call

    def fix(
        self,
        files: list[FileEntry],
        issues: list[Issue],
        strategy: str = "standard",
        source_context: SourceContext | None = None,
        attempt_num: int = 0,
        max_attempts: int = 3,
    ) -> FixResult:
        if self._llm_call is None:
            return FixResult()

        patched: list[str] = []
        resolved: set[str] = set()

        for issue in issues:
            f = next((f for f in files if f.path == issue.file), None)
            if f is None:
                continue
            content = f.content if f.content is not None else f.load()
            if content is None:
                continue

            try:
                current_value = extract_subtree(content, issue.json_path)
            except (KeyError, IndexError):
                continue

            prompt = self._build_prompt(
                issue, current_value, content, attempt_num)

            try:
                response = self._llm_call(prompt, timeout=600)
                new_value = json.loads(response.strip())
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("T1 fix failed for %s: %s",
                               issue.fingerprint, exc)
                continue

            try:
                new_content = apply_field_patch(content, issue.json_path,
                                                new_value)
                f.content = new_content
                write_file_entry(f)
                patched.append(issue.json_path)
                resolved.add(issue.fingerprint)
            except (KeyError, IndexError) as exc:
                logger.warning("T1 patch apply failed: %s", exc)

        return FixResult(patched_paths=patched, resolved_fingerprints=resolved)

    def _build_prompt(self, issue: Issue, current_value: Any,
                      full_content: Any, attempt_num: int) -> str:
        parts = [PATCH_SYSTEM]
        parts.append(f"\n--- FIELD PATH ---\n{issue.json_path}")
        parts.append(f"\n--- CURRENT VALUE ---\n{json.dumps(current_value, ensure_ascii=False, indent=2)}")
        parts.append(f"\n--- ISSUE ---\n[{issue.rule}] {issue.message}")

        if issue.context:
            parts.append(f"\n--- ISSUE CONTEXT ---\n{json.dumps(issue.context, ensure_ascii=False)}")

        # Strategy variation by attempt
        if attempt_num >= 1 and isinstance(full_content, dict):
            # Add related fields from same file
            related = self._get_related_context(issue.json_path, full_content)
            if related:
                parts.append(f"\n--- RELATED FIELDS (same file) ---\n{json.dumps(related, ensure_ascii=False, indent=2)}")

        if attempt_num >= 2:
            parts.append("\n--- HINT ---\nThis is the 3rd attempt. "
                         "Consider the broader context of the character "
                         "and stage when generating the fix.")

        return "\n".join(parts)

    def _get_related_context(self, json_path: str,
                             content: dict) -> dict | None:
        """Extract related fields from the same file for context."""
        # If path is about relationships, include personality and mood
        if "relationships" in json_path:
            related = {}
            for key in ("personality", "mood", "stage_delta", "stage_events"):
                if key in content:
                    related[key] = content[key]
            return related if related else None

        # If path is about voice/behavior, include relationships
        if "voice_state" in json_path or "behavior_state" in json_path:
            related = {}
            for key in ("relationships", "personality", "mood"):
                if key in content:
                    related[key] = content[key]
            return related if related else None

        return None
