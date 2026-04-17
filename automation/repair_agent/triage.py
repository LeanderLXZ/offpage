"""Source-discrepancy triage — decides whether residual L3 issues are
source-inherent (author bugs) and should be accepted with notes.

Invoked at two points by the coordinator:
  round 1: before escalating remaining L3 issues to T3 (saves a T3 run
           when all residuals are source bugs)
  round 2: after T3 + L3 gate still has blocking issues (last chance
           before FAIL)

Batches all L3 issues of a single file into one LLM call. Each accepted
verdict must cite chapter_number + line_range + verbatim quote; the
program verifies the quote is a literal substring of that chapter's text
before converting to a SourceNote. Per-file accept cap is enforced here
too so the LLM cannot rationalize every issue away.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Callable

from .context_retriever import ContextRetriever
from .protocol import (
    DISCREPANCY_TYPES,
    Issue,
    SourceContext,
    SourceEvidence,
    SourceNote,
    TriageVerdict,
)

logger = logging.getLogger(__name__)

TRIAGE_SYSTEM = """\
You are a source-discrepancy triage tool for a novel-character extraction
pipeline. You will receive a list of L3 semantic issues found in ONE
extracted JSON file, plus the original chapter text from the source novel.

For EACH issue, decide one of:
  (A) source_inherent=true  — the issue is caused by a bug in the source
      novel itself (author's logic contradiction, typo, pronoun confusion,
      name mixup, world-rule conflict, etc.). The extraction is faithful
      to the source; there is nothing to "fix" without editorializing.
  (B) source_inherent=false — the issue is an extraction error. The
      source text is consistent; the extracted JSON misread or
      fabricated something.

HARD REQUIREMENTS for (A):
  1. You MUST cite chapter_number, line_range [start, end] (1-indexed,
     inclusive), and a verbatim quote (minLength 1) copied EXACTLY from
     that chapter's text. The quote must literally appear in the chapter
     text — no paraphrase, no ellipsis, no summary.
  2. You MUST pick discrepancy_type from this closed list:
     author_contradiction, typo, name_mixup, pronoun_confusion,
     title_drift, time_shift, space_conflict, duplicated_passage,
     world_rule_conflict, death_state_conflict, logic_jump, other.
  3. rationale MUST explain why this is a SOURCE bug, not an extraction
     bug — reference specific evidence in the chapter.
  4. extraction_choice MUST state what the extraction preserved (e.g.
     "kept the S002 name because it was repeated 3 times").

If you are not confident the source itself is buggy, answer (B).
Rationalization ("maybe the author meant...") is NOT acceptance.

Output format: ONE JSON object with a single "verdicts" array. Each
element has exactly these fields:
  issue_fingerprint (string, must match one of the input fingerprints)
  source_inherent (boolean)
  discrepancy_type (string, one of the enum; use "other" if inherent=false)
  chapter_number (integer or null)
  line_range ([int, int] or null)
  quote (string, "" when inherent=false)
  rationale (string)
  extraction_choice (string, "" when inherent=false)

Output ONLY the JSON object. No markdown fences, no commentary.
"""

def _extract_first_json_object(text: str) -> str | None:
    """Return the first balanced JSON object in ``text`` or None.

    Walks the string tracking brace depth and string/escape state so nested
    objects and braces inside string values don't fool it. A greedy
    ``\\{.*\\}`` regex would overshoot on multi-object responses.
    """
    depth = 0
    start = -1
    in_str = False
    escape = False
    for i, ch in enumerate(text):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start:i + 1]
    return None


class Triager:
    """Runs triage decisions and verifies quote anchoring."""

    def __init__(
        self,
        llm_call: Callable[..., str] | None,
        retriever: ContextRetriever | None = None,
    ) -> None:
        self._llm_call = llm_call
        self._retriever = retriever or ContextRetriever()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def triage_file(
        self,
        file_path: str,
        issues: list[Issue],
        source_ctx: SourceContext,
        accept_cap: int,
        fixer_candidates: dict[str, TriageVerdict] | None = None,
    ) -> list[TriageVerdict]:
        """Return the verdicts the coordinator should honor for this file.

        Merges any fixer self-reported candidates as priors (they still
        go through the same quote verification). Only verdicts with
        ``source_inherent=true`` and ``evidence_verified=true`` are
        returned, capped at ``accept_cap`` entries.
        """
        if not issues:
            return []

        stage_chapters = self._retriever.get_stage_chapters(source_ctx)
        if not stage_chapters:
            logger.warning("triage: stage %s has no chapters", source_ctx.stage_id)
            return []

        # Gather LLM verdicts (batched per file) + any fixer self-reports
        verdicts: dict[str, TriageVerdict] = {}

        llm_verdicts = self._call_llm(
            file_path, issues, source_ctx, stage_chapters)
        for v in llm_verdicts:
            verdicts[v.issue_fingerprint] = v

        if fixer_candidates:
            for fp, v in fixer_candidates.items():
                # Trust LLM output over self-report when both exist,
                # but keep self-reports for issues the LLM didn't cover.
                verdicts.setdefault(fp, v)

        # Verify quotes against chapter text
        accepted: list[TriageVerdict] = []
        for issue in issues:
            v = verdicts.get(issue.fingerprint)
            if v is None or not v.source_inherent:
                continue
            if v.discrepancy_type not in DISCREPANCY_TYPES:
                logger.warning(
                    "triage: %s rejected — bad discrepancy_type %r",
                    issue.fingerprint, v.discrepancy_type)
                continue
            if not self._verify_quote(v, source_ctx):
                logger.warning(
                    "triage: %s rejected — quote not found in chapter %s",
                    issue.fingerprint, v.chapter_number)
                continue
            v.evidence_verified = True
            accepted.append(v)
            if len(accepted) >= accept_cap:
                logger.info(
                    "triage: hit per-file cap %d for %s — %d remaining "
                    "source_inherent verdicts dropped",
                    accept_cap, file_path,
                    sum(1 for x in verdicts.values()
                        if x.source_inherent) - len(accepted))
                break

        logger.info(
            "triage: %s — %d issue(s), %d accepted",
            file_path, len(issues), len(accepted))
        return accepted

    def build_source_note(
        self,
        verdict: TriageVerdict,
        issue: Issue,
        source_ctx: SourceContext,
        note_id: str,
        accepted_at: str,
        triage_round: int,
    ) -> SourceNote | None:
        """Convert a verified verdict into a persistable SourceNote."""
        if not verdict.evidence_verified or verdict.chapter_number is None:
            return None
        # Schema hard constraint: issue_category enum is ["semantic"].
        # Reject anything else before it reaches notes_writer / disk.
        if issue.category != "semantic":
            logger.warning(
                "triage: refusing to build SourceNote for non-semantic "
                "issue %s (category=%s)", issue.fingerprint, issue.category)
            return None
        chapter_text = self._retriever.load_chapter_text(
            source_ctx, verdict.chapter_number)
        if not chapter_text:
            return None
        quote_sha = hashlib.sha256(
            verdict.quote.encode("utf-8")).hexdigest()
        chapter_sha = hashlib.sha256(
            chapter_text.encode("utf-8")).hexdigest()
        line_range = verdict.line_range or self._guess_line_range(
            chapter_text, verdict.quote)
        evidence = SourceEvidence(
            chapter_number=verdict.chapter_number,
            line_range=line_range,
            quote=verdict.quote,
            quote_sha256=quote_sha,
            chapter_sha256=chapter_sha,
        )
        return SourceNote(
            note_id=note_id,
            stage_id=source_ctx.stage_id,
            file=issue.file,
            json_path=issue.json_path,
            issue_fingerprint=issue.fingerprint,
            issue_category=issue.category,
            issue_rule=issue.rule,
            issue_severity=issue.severity,
            issue_message=issue.message,
            discrepancy_type=verdict.discrepancy_type,
            source_evidence=evidence,
            rationale=verdict.rationale,
            extraction_choice=verdict.extraction_choice,
            future_fixer_hint={},
            accepted_at=accepted_at,
            triage_round=triage_round,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        file_path: str,
        issues: list[Issue],
        source_ctx: SourceContext,
        stage_chapters: list[int],
    ) -> list[TriageVerdict]:
        if self._llm_call is None:
            return []

        # Load all stage chapters (cache-friendly; shared with T2/T3)
        chapter_blobs: list[str] = []
        for ch in stage_chapters:
            text = self._retriever.load_chapter_text(source_ctx, ch)
            if text:
                chapter_blobs.append(f"=== 第{ch}章 ===\n{text}")
        if not chapter_blobs:
            return []

        prompt = self._build_prompt(
            file_path, issues, "\n\n".join(chapter_blobs))

        try:
            response = self._llm_call(prompt, timeout=300)
        except Exception as exc:  # LLM transport errors — don't crash run
            logger.warning("triage LLM call failed for %s: %s", file_path, exc)
            return []

        return self._parse_response(response, issues)

    def _build_prompt(self, file_path: str, issues: list[Issue],
                      chapter_text: str) -> str:
        parts = [TRIAGE_SYSTEM]
        parts.append(f"\n--- FILE ---\n{file_path}")
        parts.append("\n--- ISSUES ---")
        for issue in issues:
            parts.append(
                f"fingerprint: {issue.fingerprint}\n"
                f"  json_path: {issue.json_path}\n"
                f"  rule: {issue.rule}\n"
                f"  severity: {issue.severity}\n"
                f"  message: {issue.message}"
            )
        parts.append(f"\n--- SOURCE TEXT ---\n{chapter_text}")
        return "\n".join(parts)

    def _parse_response(
        self, response: str, issues: list[Issue],
    ) -> list[TriageVerdict]:
        valid_fingerprints = {i.fingerprint for i in issues}

        try:
            data = json.loads(response.strip())
        except json.JSONDecodeError:
            extracted = _extract_first_json_object(response)
            if extracted is None:
                logger.warning("triage: could not parse LLM response")
                return []
            try:
                data = json.loads(extracted)
            except json.JSONDecodeError:
                logger.warning("triage: LLM response not valid JSON")
                return []

        raw_verdicts = data.get("verdicts") if isinstance(data, dict) else None
        if not isinstance(raw_verdicts, list):
            logger.warning("triage: LLM response missing 'verdicts' array")
            return []

        verdicts: list[TriageVerdict] = []
        for raw in raw_verdicts:
            if not isinstance(raw, dict):
                continue
            fp = raw.get("issue_fingerprint")
            if fp not in valid_fingerprints:
                continue
            line_range = raw.get("line_range")
            if (isinstance(line_range, list) and len(line_range) == 2
                    and all(isinstance(x, int) for x in line_range)):
                lr: tuple[int, int] | None = (line_range[0], line_range[1])
            else:
                lr = None
            verdicts.append(TriageVerdict(
                issue_fingerprint=fp,
                source_inherent=bool(raw.get("source_inherent", False)),
                discrepancy_type=str(raw.get("discrepancy_type", "other")),
                chapter_number=(raw.get("chapter_number")
                                if isinstance(raw.get("chapter_number"), int)
                                else None),
                line_range=lr,
                quote=str(raw.get("quote", "")),
                rationale=str(raw.get("rationale", "")),
                extraction_choice=str(raw.get("extraction_choice", "")),
                evidence_verified=False,
            ))
        return verdicts

    def _verify_quote(self, v: TriageVerdict,
                      source_ctx: SourceContext) -> bool:
        if not v.quote or v.chapter_number is None:
            return False
        chapter_text = self._retriever.load_chapter_text(
            source_ctx, v.chapter_number)
        if not chapter_text:
            return False
        return chapter_text.find(v.quote) >= 0

    @staticmethod
    def _guess_line_range(chapter_text: str, quote: str) -> tuple[int, int]:
        """Fallback when LLM omits line_range — derive from substring.

        1-indexed, inclusive. Returns (1, 1) if anything goes wrong.
        """
        idx = chapter_text.find(quote)
        if idx < 0:
            return (1, 1)
        before = chapter_text[:idx]
        start_line = before.count("\n") + 1
        end_line = start_line + quote.count("\n")
        return (start_line, end_line)
