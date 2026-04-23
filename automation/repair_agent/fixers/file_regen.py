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
from ..field_patch import write_file_entry
from ..protocol import (
    FileEntry, FixResult, Issue, SourceContext, TriageVerdict,
)

logger = logging.getLogger(__name__)

REGEN_SYSTEM = """\
You are a JSON file regeneration tool for character extraction data.
The previous field-level repairs have failed — you must regenerate the
entire file content.

You will receive:
1. The current (broken) JSON content
2. A list of all remaining issues
3. Original chapter text from the source novel

Primary task: output a COMPLETE, valid JSON object that fixes ALL listed
issues while preserving correct data that is not flagged.
Do not output anything else — no explanation, no markdown fences.
The output must be a single valid JSON object.

Optional escape hatch — source_inherent reports:
Some issues may be bugs in the SOURCE novel itself (author contradiction,
typo, name mixup, etc.) that you cannot truly fix without editorializing.
For any such issue, include it under a top-level ``__source_inherent__``
array on the regenerated object. Each entry MUST have exactly:

  {"issue_fingerprint": "<fingerprint from the ISSUES list above>",
   "discrepancy_type": "<author_contradiction | typo | name_mixup |
        pronoun_confusion | title_drift | time_shift | space_conflict |
        duplicated_passage | world_rule_conflict | death_state_conflict |
        logic_jump | other>",
   "chapter_number": <int>,
   "line_range": [<int>, <int>],
   "quote": "<VERBATIM substring of that chapter>",
   "rationale": "<why this is a source bug, not an extraction bug>",
   "extraction_choice": "<what you kept in the regenerated JSON and why>"}

A downstream program strips ``__source_inherent__`` before writing the
file, and verifies every quote as a literal substring of the chapter.
Do not fabricate — if uncertain, fix the field instead.
"""


class FileRegenFixer(BaseFixer):
    """Tier 3: full file regeneration via LLM."""

    tier = 3

    def __init__(self, llm_call: Callable[..., str] | None = None,
                 retriever: ContextRetriever | None = None):
        self._llm_call = llm_call
        self._retriever = retriever or ContextRetriever()

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
        candidates: dict[str, TriageVerdict] = {}

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

            # Strip self-report side-channel before writing the file.
            file_candidates = _extract_file_self_reports(
                new_content, file_issues)
            candidates.update(file_candidates)
            if isinstance(new_content, dict):
                new_content.pop("__source_inherent__", None)

            f.content = new_content
            write_file_entry(f)
            for issue in file_issues:
                if issue.fingerprint in file_candidates:
                    # Triage owns the decision — don't mark resolved.
                    continue
                patched.append(issue.json_path)
                resolved.add(issue.fingerprint)

        return FixResult(
            patched_paths=patched,
            resolved_fingerprints=resolved,
            source_inherent_candidates=candidates,
        )

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


def _extract_file_self_reports(
    new_content: Any, file_issues: list[Issue],
) -> dict[str, TriageVerdict]:
    """Pull ``__source_inherent__`` reports off a T3 regenerated object."""
    if not isinstance(new_content, dict):
        return {}
    raw = new_content.get("__source_inherent__")
    if not isinstance(raw, list):
        return {}
    valid = {i.fingerprint for i in file_issues}
    out: dict[str, TriageVerdict] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        fp = entry.get("issue_fingerprint")
        if fp not in valid:
            continue
        lr = entry.get("line_range")
        line_range: tuple[int, int] | None = (
            (lr[0], lr[1]) if isinstance(lr, list) and len(lr) == 2
            and all(isinstance(x, int) for x in lr) else None)
        ch = entry.get("chapter_number")
        out[fp] = TriageVerdict(
            issue_fingerprint=fp,
            source_inherent=True,
            discrepancy_type=str(entry.get("discrepancy_type", "other")),
            chapter_number=ch if isinstance(ch, int) else None,
            line_range=line_range,
            quote=str(entry.get("quote", "")),
            rationale=str(entry.get("rationale", "")),
            extraction_choice=str(entry.get("extraction_choice", "")),
            evidence_verified=False,
        )
    return out
