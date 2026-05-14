"""T3 — Full file regeneration fixer.

Last resort: sends the entire file content + all unresolved issues +
original chapter text to an LLM and asks for a complete rewrite.

Only used when field-level patches (T1/T2) have failed repeatedly.

Sub-lane regen hook (decision #55): when ``sub_lane_regen`` callback is
wired AND the target file is a character ``stage_snapshot.json``, T3
delegates regeneration to the orchestrator's 4-sub-lane parallel extract
+ merge path (replacing the default single-LLM-call full-file rewrite).
The callback receives the file entry + remaining issues +
``prior_attempt_context`` and returns the new content dict (or ``None``
to fall back to the default regen). The callback is responsible for
writing the resulting file to disk and clearing sub-lane ``.partial/``
scratch.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

from . import BaseFixer
from ..context_retriever import ContextRetriever
from ..field_patch import write_file_entry
from ..protocol import (
    FileEntry, FixResult, Issue, SourceContext, TriageVerdict,
)

logger = logging.getLogger(__name__)


# Decision #55 — callback signature for sub-lane-aware T3 regen.
# ``character_id`` / ``stage_id`` are parsed from the file path by the
# caller before invocation so the callback signature stays narrow.
# Return value: ``True`` means the callback handled the regen (wrote
# the file + cleaned partials) — the fixer will mark all attempted
# issues resolved; ``False`` means the callback chose not to handle
# this file (fall back to default regen); ``None`` means the callback
# failed and the fixer should NOT mark issues resolved (the lifecycle
# will surface them on the next pass).
SubLaneRegenCallback = Callable[
    [str, str, str, list[Issue], dict[str, list[str]] | None],
    bool | None,
]


_CHAR_SNAPSHOT_PATH_RE = re.compile(
    r"works/(?P<wid>[^/]+)/characters/(?P<cid>[^/]+)/canon/"
    r"stage_snapshots/(?P<sid>S[0-9]{3})\.json$"
)


def _parse_char_snapshot_path(file_path: str) -> tuple[str, str] | None:
    """Extract ``(character_id, stage_id)`` from a stage_snapshot path.

    Returns ``None`` if the path is not a character stage_snapshot file
    (e.g. world snapshot, memory_timeline, baseline). The sub-lane regen
    callback is only valid for character stage_snapshot files.
    """
    normalized = file_path.replace("\\", "/")
    m = _CHAR_SNAPSHOT_PATH_RE.search(normalized)
    if m is None:
        return None
    return m.group("cid"), m.group("sid")

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
                 retriever: ContextRetriever | None = None,
                 sub_lane_regen: SubLaneRegenCallback | None = None):
        self._llm_call = llm_call
        self._retriever = retriever or ContextRetriever()
        # Decision #55 — when set, T3 routes char_snapshot files through
        # the orchestrator's 4-sub-lane parallel re-extract + merge path
        # instead of the default single-LLM full-file regen.
        self._sub_lane_regen = sub_lane_regen

    def fix(
        self,
        files: list[FileEntry],
        issues: list[Issue],
        strategy: str = "standard",
        source_context: SourceContext | None = None,
        attempt_num: int = 0,
        max_attempts: int = 1,
        prior_attempt_context: dict | None = None,
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

            # Decision #55 — sub-lane-aware regen for char_snapshot
            # stage_snapshot files. The callback re-runs the 4-sub-lane
            # parallel extract + merge path with prior_attempt_context
            # injected, writes the merged file, and cleans .partial/
            # scratch. Returns True on success → mark every attempted
            # issue resolved (the merged file is the new ground truth).
            # Returns False (declined) → fall through to default regen.
            # Returns None (failure) → skip this file; lifecycle will
            # surface the issues on the next pass.
            if self._sub_lane_regen is not None:
                char_snapshot = _parse_char_snapshot_path(file_path)
                if char_snapshot is not None:
                    cid, sid = char_snapshot
                    verdict = self._sub_lane_regen(
                        file_path, cid, sid, file_issues,
                        prior_attempt_context,
                    )
                    if verdict is True:
                        # Re-load the merged file so f.content reflects
                        # the new ground truth for any downstream
                        # consumer that reuses the FileEntry object.
                        try:
                            with Path(file_path).open(
                                    "r", encoding="utf-8") as fh:
                                f.content = json.load(fh)
                        except (OSError, json.JSONDecodeError) as exc:
                            logger.warning(
                                "sub-lane regen claimed success but "
                                "merged file unreadable at %s: %s",
                                file_path, exc)
                            continue
                        for issue in file_issues:
                            patched.append(issue.json_path)
                            resolved.add(issue.fingerprint)
                        continue
                    if verdict is None:
                        # Sub-lane path failed — skip, do NOT mark
                        # issues resolved; do NOT fall back to default
                        # regen (would double-charge an already-failing
                        # extraction path).
                        logger.warning(
                            "sub-lane regen failed for %s; lifecycle "
                            "will re-surface remaining issues",
                            file_path)
                        continue
                    # verdict is False → callback declined; fall through

            content = f.content if f.content is not None else f.load()
            if content is None:
                continue

            # Retrieve chapter text if source context available
            chapter_text = ""
            if source_context:
                chapter_text = self._retriever.retrieve_all_stage(
                    source_context)

            prompt = self._build_prompt(
                file_path, content, file_issues, chapter_text,
                prior_attempt_context=prior_attempt_context)

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
                      issues: list[Issue], chapter_text: str,
                      *, prior_attempt_context: dict | None = None) -> str:
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

        if prior_attempt_context:
            parts.append(_format_prior_attempt_context(prior_attempt_context))

        if chapter_text:
            parts.append(
                f"\n--- SOURCE TEXT (original chapters) ---\n{chapter_text}")

        return "\n".join(parts)


_PRIOR_CONTEXT_CHAR_BUDGET = 600  # ~200 token CJK


def _format_prior_attempt_context(ctx: dict) -> str:
    """Render a compact summary of the previous lifecycle's attempts.

    Expected keys:
      ``resolved`` — list of "path: rule" strings (already-fixed issues)
      ``remaining`` — list of "path: rule (message)" strings (still failing)

    Truncated to ~200 token (`_PRIOR_CONTEXT_CHAR_BUDGET` chars total).
    """
    lines = ["\n--- PRIOR LIFECYCLE ATTEMPT ---"]
    resolved = ctx.get("resolved") or []
    remaining = ctx.get("remaining") or []
    if resolved:
        lines.append(f"Previously resolved ({len(resolved)}):")
        for s in resolved:
            lines.append(f"  + {s}")
    if remaining:
        lines.append(f"Still failing ({len(remaining)}):")
        for s in remaining:
            lines.append(f"  - {s}")
    text = "\n".join(lines)
    if len(text) > _PRIOR_CONTEXT_CHAR_BUDGET:
        text = text[:_PRIOR_CONTEXT_CHAR_BUDGET] + "\n... (truncated)"
    return text


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
