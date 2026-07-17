"""L3 — Semantic checker (LLM-based).

Calls an LLM to review content for factual correctness, inter-stage
continuity, and logical consistency.  Outputs structured Issue list.

This is the only checker that costs LLM tokens.

Failure semantics: an unavailable / failing semantic backend is NOT
silently treated as "no issues found" — it is converted to a blocking
``semantic_unavailable`` issue so the repair coordinator routes the
file through the standard L3 fix path. False-passes here would let
factually-wrong stage data through to commit. The orchestrator's
``_llm_call`` wrapper raises :class:`SemanticReviewLLMUnavailable`
when the upstream LLMResult has ``success=False``.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from . import BaseChecker
from ..protocol import FileEntry, Issue

logger = logging.getLogger(__name__)


class SemanticReviewLLMUnavailable(Exception):
    """Raised by ``llm_call`` wrappers when the underlying LLM call
    failed (e.g. token limit, retry budget exhausted, backend error).
    Signals that semantic review could not run, so the checker must
    surface this as a blocking issue instead of a clean pass.
    """

# Template for semantic review — instructs LLM to output structured issues.
SEMANTIC_REVIEW_SYSTEM = """\
You are a quality reviewer for character extraction data.
Review the provided JSON files for factual accuracy, inter-stage
continuity, and logical consistency.

Output ONLY a JSON array of issues found.  Each issue must have:
{
  "json_path": "$.field.path",
  "severity": "error" or "warning",
  "rule": "brief_rule_name",
  "message": "description of the problem"
}

`json_path` MUST anchor at the most specific offending LEAF field, never
at a large parent container. E.g. flag
`$.voice_state.target_voice_map[2].dialogue_examples[0]` or
`$.relationships[1].relationship_history_summary`, NOT `$.voice_state`
or `$.relationships`. A downstream repair patches exactly the subtree at
`json_path`, so a container anchor forces an expensive whole-subtree
rewrite.

If no issues found, output: []

Do NOT invent issues. Only flag clear factual errors, logical
contradictions, or significant continuity breaks.
"""


class SemanticChecker(BaseChecker):
    """Layer 3: LLM-based semantic review."""

    layer = 3

    def __init__(self, llm_call: Callable[..., str] | None = None):
        """
        Args:
            llm_call: A callable ``(prompt: str, timeout: int | None = None,
                effort: str | None = None) -> str`` that invokes an LLM and
                returns the raw text response. It MUST accept ``effort`` as a
                keyword on every path — this checker always passes it, sending
                ``effort=None`` on the Phase A full pass so that pass inherits
                the backend default. ``timeout`` MUST have a default: this
                checker never passes it, so the injector owns the budget
                (wired to ``[repair].semantic_timeout_s``). If None, semantic
                checking is a no-op.
        """
        self._llm_call = llm_call

    def check(self, files: list[FileEntry], effort: str | None = None,
              **kwargs) -> list[Issue]:
        """Full-file semantic review.

        ``effort`` is a per-call override the caller passes down; the Phase A
        full pass omits it and inherits the backend default, while the Phase B
        L3 gate passes ``medium`` (decision #65) — the gate re-reads a file
        whose issues are already known, so it needs less reasoning depth than
        the cold first pass.
        """
        if self._llm_call is None:
            logger.info("Semantic checker: no LLM backend configured, skipping")
            return []

        issues: list[Issue] = []
        for f in files:
            content = f.content if f.content is not None else f.load()
            if content is None:
                continue
            file_issues = self._review_file(f.path, content, effort=effort)
            issues.extend(file_issues)
        return issues

    def check_scoped(self, files: list[FileEntry], paths: list[str],
                     effort: str | None = None) -> list[Issue]:
        """Re-check only specific json_paths (for final verification)."""
        if self._llm_call is None:
            return []
        # For scoped review, include hint about which fields to focus on
        issues: list[Issue] = []
        for f in files:
            content = f.content if f.content is not None else f.load()
            if content is None:
                continue
            file_issues = self._review_file(
                f.path, content, focus_paths=paths, effort=effort)
            issues.extend(file_issues)
        return issues

    def _review_file(self, file_path: str, content: Any,
                     focus_paths: list[str] | None = None,
                     effort: str | None = None) -> list[Issue]:
        # Callers (`check` / `check_scoped`) guard with `_llm_call is None`
        # before invoking this method; assert reflects that contract for
        # the type checker, since narrowing doesn't cross method boundaries.
        assert self._llm_call is not None
        prompt_parts = [SEMANTIC_REVIEW_SYSTEM, "\n--- FILE ---\n"]

        content_str = json.dumps(content, ensure_ascii=False, indent=2)
        # Truncate very large files to stay within context limits. Log a
        # warning when we truncate so the tail of the file (where the LLM
        # might catch real semantic issues) isn't silently dropped.
        _SEMANTIC_MAX_CHARS = 50000
        if len(content_str) > _SEMANTIC_MAX_CHARS:
            logger.warning(
                "Semantic review truncated %s: %d chars → %d chars "
                "(tail dropped from review)",
                file_path, len(content_str), _SEMANTIC_MAX_CHARS)
            content_str = (content_str[:_SEMANTIC_MAX_CHARS]
                           + "\n... (truncated)")
        prompt_parts.append(content_str)

        if focus_paths:
            prompt_parts.append(
                f"\n\nFocus review on these paths: {', '.join(focus_paths)}")

        prompt = "\n".join(prompt_parts)

        try:
            # No explicit timeout: the injected ``llm_call`` owns that budget
            # (orchestrator wires it to ``[repair].semantic_timeout_s``).
            # Hardcoding it here would shadow the config — reviewing a whole
            # ~50k-char snapshot needs a budget the caller can tune per phase.
            # ``effort=None`` inherits the backend default (Phase A); the L3
            # gate passes it down explicitly.
            response = self._llm_call(prompt, effort=effort)
        except SemanticReviewLLMUnavailable as exc:
            # Backend reported failure. Treat as blocking so repair
            # coordinator does NOT mark the file PASS. Detail in message
            # for the recorder; rule fingerprint is what the gate keys on.
            logger.warning(
                "Semantic review LLM unavailable for %s: %s", file_path, exc)
            return [Issue(
                file=file_path,
                json_path="$",
                category="semantic",
                severity="error",
                rule="semantic_unavailable",
                message=(f"L3 semantic backend unavailable: {exc}. "
                         f"Re-run after backend recovers or disable "
                         f"[repair].run_semantic to skip L3."),
            )]
        except Exception as exc:
            # Anything else is also unsafe to silently pass — same
            # treatment, distinct rule fingerprint.
            logger.warning("Semantic review crashed for %s: %s", file_path, exc)
            return [Issue(
                file=file_path,
                json_path="$",
                category="semantic",
                severity="error",
                rule="semantic_check_crashed",
                message=f"Semantic checker raised: {exc!r}",
            )]

        return self._parse_response(file_path, response)

    def _parse_response(self, file_path: str,
                        response: str) -> list[Issue]:
        """Parse LLM response into Issue list. Empty / unparseable
        responses become a blocking ``semantic_unparseable`` issue —
        a missing review is not the same as a clean review.
        """
        text = response.strip()
        if text == "[]":
            return []
        if not text:
            logger.warning("Semantic review returned empty response for %s",
                           file_path)
            return [Issue(
                file=file_path,
                json_path="$",
                category="semantic",
                severity="error",
                rule="semantic_unparseable",
                message="L3 semantic backend returned empty output.",
            )]
        # Try to find JSON array in the response
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end < 0:
            logger.warning("Could not parse semantic review response for %s",
                           file_path)
            return [Issue(
                file=file_path,
                json_path="$",
                category="semantic",
                severity="error",
                rule="semantic_unparseable",
                message=(f"L3 semantic response had no JSON array; "
                         f"first 80 chars: {text[:80]!r}"),
            )]

        try:
            items = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in semantic review for %s", file_path)
            return [Issue(
                file=file_path,
                json_path="$",
                category="semantic",
                severity="error",
                rule="semantic_unparseable",
                message=f"L3 semantic JSON decode failed: {exc}",
            )]

        issues: list[Issue] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            issues.append(Issue(
                file=file_path,
                json_path=item.get("json_path", "$"),
                category="semantic",
                severity=item.get("severity", "warning"),
                rule=item.get("rule", "semantic_review"),
                message=item.get("message", ""),
            ))
        return issues
