"""T3 — Full file regeneration fixer.

Last resort: sends the entire file content + all unresolved issues +
original chapter text to an LLM and asks for a complete rewrite.

Only used when field-level patches (T1/T2) have failed repeatedly.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from . import BaseFixer
from ..context_retriever import ContextRetriever
from ..protocol import FileEntry, FixResult, Issue, SourceContext

logger = logging.getLogger(__name__)

REGEN_SYSTEM = """\
You are a JSON file regeneration tool for character extraction data.
The previous field-level repairs have failed — you must regenerate the
entire file content.

You will receive:
1. The current (broken) JSON content
2. A list of all remaining issues
3. Original chapter text from the source novel

Your task: output a COMPLETE, valid JSON object that fixes ALL listed
issues while preserving correct data that is not flagged.
Do not output anything else — no explanation, no markdown fences.
The output must be a single valid JSON object.
"""


class FileRegenFixer(BaseFixer):
    """Tier 3: full file regeneration via LLM."""

    tier = 3

    def __init__(self, llm_call: Callable[..., str] | None = None):
        self._llm_call = llm_call
        self._retriever = ContextRetriever()

    def fix(
        self,
        files: list[FileEntry],
        issues: list[Issue],
        strategy: str = "standard",
        source_context: SourceContext | None = None,
        attempt_num: int = 0,
        max_attempts: int = 1,
    ) -> FixResult:
        if self._llm_call is None:
            return FixResult()

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
                continue

            # Retrieve chapter text if source context available
            chapter_text = ""
            if source_context:
                chapter_text = self._retriever.retrieve_all_stage(
                    source_context)

            prompt = self._build_prompt(
                file_path, content, file_issues, chapter_text)

            try:
                response = self._llm_call(prompt, timeout=900)
                new_content = json.loads(response.strip())
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("T3 regen failed for %s: %s", file_path, exc)
                continue

            from ..field_patch import write_patched_file
            f.content = new_content
            write_patched_file(file_path, new_content)
            for issue in file_issues:
                patched.append(issue.json_path)
                resolved.add(issue.fingerprint)

        return FixResult(patched_paths=patched, resolved_fingerprints=resolved)

    def _build_prompt(self, file_path: str, content: Any,
                      issues: list[Issue], chapter_text: str) -> str:
        parts = [REGEN_SYSTEM]

        parts.append(f"\n--- FILE: {file_path} ---")
        content_str = json.dumps(content, ensure_ascii=False, indent=2)
        if len(content_str) > 80000:
            content_str = content_str[:80000] + "\n... (truncated)"
        parts.append(content_str)

        parts.append("\n--- ISSUES TO FIX ---")
        for issue in issues:
            parts.append(f"  [{issue.severity}] {issue.json_path}: "
                         f"[{issue.rule}] {issue.message}")

        if chapter_text:
            parts.append(
                f"\n--- SOURCE TEXT (original chapters) ---\n{chapter_text}")

        return "\n".join(parts)
