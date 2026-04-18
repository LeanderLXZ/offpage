"""T2 — Source patch fixer.  Field-level LLM repair WITH original chapter text.

Uses context_retriever to locate relevant chapters, then sends
the broken field + issue + chapter text to an LLM for repair.

Retry strategies (handled by context_retriever):
  attempt 0: top-3 chapters
  attempt 1: top-5 + adjacent chapters
  attempt 2: all stage chapters
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from . import BaseFixer
from ..context_retriever import ContextRetriever
from ..field_patch import apply_field_patch, extract_subtree, write_patched_file
from ..protocol import (
    FileEntry, FixResult, Issue, SourceContext, TriageVerdict,
)

logger = logging.getLogger(__name__)

SOURCE_PATCH_SYSTEM = """\
You are a precise JSON field repair tool.  You will receive:
1. A JSON field value that has a factual/content issue
2. A description of the issue
3. Original chapter text from the source novel as reference

Primary task: output ONLY the corrected JSON value for this field,
based on evidence from the source text.
Do not output anything else — no explanation, no markdown fences.
The output must be valid JSON that can replace the broken field directly.

Escape hatch — source_inherent report:
If, after reading the source text, you conclude that the issue is NOT a
mistake in the extracted JSON but rather a bug in the source novel itself
(author contradiction, typo, pronoun confusion, name mixup, etc.) and
therefore cannot be "fixed" without editorializing, output a JSON object
of exactly this shape INSTEAD of a corrected value:

  {"source_inherent": true,
   "discrepancy_type": "<one of: author_contradiction, typo, name_mixup,
        pronoun_confusion, title_drift, time_shift, space_conflict,
        duplicated_passage, world_rule_conflict, death_state_conflict,
        logic_jump, other>",
   "chapter_number": <int>,
   "line_range": [<int>, <int>],
   "quote": "<VERBATIM substring of that chapter>",
   "rationale": "<why this is a source bug, not an extraction bug>",
   "extraction_choice": "<what the extraction preserved and why>"}

The quote MUST be an exact substring of the chapter text — no paraphrase,
no ellipsis. A downstream program verifies this literally.
Use this channel only when you are confident; otherwise produce the
corrected value as normal.
"""


class SourcePatchFixer(BaseFixer):
    """Tier 2: field-level LLM patch with original chapter text."""

    tier = 2

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
        max_attempts: int = 3,
    ) -> FixResult:
        if self._llm_call is None:
            return FixResult()
        if source_context is None:
            logger.warning("T2: source_context is None — skipping %d issues",
                           len(issues))
            return FixResult()

        patched: list[str] = []
        resolved: set[str] = set()
        candidates: dict[str, TriageVerdict] = {}

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

            # Retrieve relevant chapter text
            chapter_text = self._retriever.retrieve(
                issue, source_context, attempt_num, max_attempts)
            if not chapter_text:
                logger.warning("T2: no chapter text retrieved for %s",
                               issue.fingerprint)
                continue

            prompt = self._build_prompt(issue, current_value, chapter_text)

            try:
                response = self._llm_call(prompt, timeout=600)
                parsed = json.loads(response.strip())
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("T2 fix failed for %s: %s",
                               issue.fingerprint, exc)
                continue

            # Self-report channel: LLM says this is a source bug
            verdict = _extract_self_report(parsed, issue.fingerprint)
            if verdict is not None:
                candidates[issue.fingerprint] = verdict
                continue

            try:
                new_content = apply_field_patch(content, issue.json_path,
                                                parsed)
                f.content = new_content
                write_patched_file(f.path, new_content)
                patched.append(issue.json_path)
                resolved.add(issue.fingerprint)
            except (KeyError, IndexError) as exc:
                logger.warning("T2 patch apply failed: %s", exc)

        return FixResult(
            patched_paths=patched,
            resolved_fingerprints=resolved,
            source_inherent_candidates=candidates,
        )

    def _build_prompt(self, issue: Issue, current_value: Any,
                      chapter_text: str) -> str:
        parts = [SOURCE_PATCH_SYSTEM]
        parts.append(f"\n--- FIELD PATH ---\n{issue.json_path}")
        parts.append(f"\n--- CURRENT VALUE ---\n{json.dumps(current_value, ensure_ascii=False, indent=2)}")
        parts.append(f"\n--- ISSUE ---\n[{issue.rule}] {issue.message}")

        if issue.context:
            parts.append(f"\n--- ISSUE CONTEXT ---\n{json.dumps(issue.context, ensure_ascii=False)}")

        parts.append(f"\n--- SOURCE TEXT (original chapters) ---\n{chapter_text}")

        return "\n".join(parts)


def _extract_self_report(parsed: Any,
                         fingerprint: str) -> TriageVerdict | None:
    """Detect a source_inherent escape-hatch object in an LLM response."""
    if not isinstance(parsed, dict):
        return None
    if not parsed.get("source_inherent"):
        return None
    lr = parsed.get("line_range")
    if (isinstance(lr, list) and len(lr) == 2
            and all(isinstance(x, int) for x in lr)):
        line_range: tuple[int, int] | None = (lr[0], lr[1])
    else:
        line_range = None
    ch = parsed.get("chapter_number")
    return TriageVerdict(
        issue_fingerprint=fingerprint,
        source_inherent=True,
        discrepancy_type=str(parsed.get("discrepancy_type", "other")),
        chapter_number=ch if isinstance(ch, int) else None,
        line_range=line_range,
        quote=str(parsed.get("quote", "")),
        rationale=str(parsed.get("rationale", "")),
        extraction_choice=str(parsed.get("extraction_choice", "")),
        evidence_verified=False,
    )
