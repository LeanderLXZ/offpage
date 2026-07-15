"""T1 — Local patch fixer.  Field-level LLM repair without source text.

Sends the broken field subtree(s) + issue description(s) to an LLM and
gets back the patched value(s).  No original chapters are ever loaded —
T1 is the cheap, no-source judgement tier (enum choices, clean length
rewrites, small schema/structural fixes that T0 couldn't finish).

Two behaviours matter for convergence:
  * Batch: all issues for the SAME file go in ONE LLM call (a json_path →
    corrected-value map) instead of one call per issue.
  * Immediate re-verify: after applying patches, a scoped L0–L2 recheck
    (0 token, injected by the coordinator) decides which issues are
    actually resolved. A field is only marked resolved when its issue
    fingerprint no longer surfaces — apply alone is NOT "resolved". This
    stops the "self-report resolved → blocks escalation → spin" failure
    and lets a 2nd attempt target only the fields still failing.
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
You are a precise JSON field repair tool.  You will receive one or more
fields from the SAME file, each with an issue to fix.

For EACH field you are given its json_path, current value, and the issue.

Output ONLY a single JSON object mapping each field's json_path (exactly
as given, verbatim) to its corrected JSON value:

  {"$.a.b": <corrected value>, "$.c[0]": <corrected value>}

Include every json_path you were given.  Do not output anything else —
no explanation, no markdown fences.  Each corrected value must be valid
JSON that can replace the broken field directly.
"""


class LocalPatchFixer(BaseFixer):
    """Tier 1: field-level LLM patch without source text."""

    tier = 1

    def __init__(
        self,
        llm_call: Callable[..., str] | None = None,
        verify_fn: Callable[[list[FileEntry]], set[str]] | None = None,
    ):
        self._llm_call = llm_call
        # Scoped L0–L2 re-verify injected by the coordinator. Given the
        # (possibly patched) file list it returns the set of issue
        # fingerprints still present. ``None`` falls back to the legacy
        # "apply == resolved" behaviour (used by tests / standalone).
        self._verify_fn = verify_fn

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
        applied_fps: set[str] = set()

        # Batch by file — one LLM call per file, all its issues together.
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

            # Collect issues whose current subtree can be extracted.
            targets: list[tuple[Issue, Any]] = []
            for issue in file_issues:
                try:
                    current_value = extract_subtree(content, issue.json_path)
                except (KeyError, IndexError):
                    continue
                targets.append((issue, current_value))
            if not targets:
                continue

            prompt = self._build_prompt(targets, content, attempt_num)
            try:
                response = self._llm_call(prompt, timeout=600)
                patch_map = self._parse_response(response, targets)
            except Exception as exc:  # noqa: BLE001
                logger.warning("T1 fix failed for %s: %s", file_path, exc)
                continue
            if not patch_map:
                continue

            file_modified = False
            for issue, _current in targets:
                if issue.json_path not in patch_map:
                    continue
                try:
                    content = apply_field_patch(
                        content, issue.json_path, patch_map[issue.json_path])
                    f.content = content
                    patched.append(issue.json_path)
                    applied_fps.add(issue.fingerprint)
                    file_modified = True
                except (KeyError, IndexError) as exc:
                    logger.warning("T1 patch apply failed: %s", exc)
            if file_modified:
                write_file_entry(f)

        # Immediate scoped re-verify (0 token): a field counts as resolved
        # only when its fingerprint no longer surfaces at L0–L2.
        if applied_fps and self._verify_fn is not None:
            try:
                remaining_fps = self._verify_fn(files)
            except Exception as exc:  # noqa: BLE001
                logger.warning("T1 re-verify failed, treating apply as "
                               "resolved: %s", exc)
                remaining_fps = set()
            resolved = {fp for fp in applied_fps if fp not in remaining_fps}
        else:
            resolved = set(applied_fps)

        return FixResult(patched_paths=patched, resolved_fingerprints=resolved)

    def _build_prompt(self, targets: list[tuple[Issue, Any]],
                      full_content: Any, attempt_num: int) -> str:
        parts = [PATCH_SYSTEM]
        for idx, (issue, current_value) in enumerate(targets):
            parts.append(f"\n=== FIELD {idx + 1} ===")
            parts.append(f"--- FIELD PATH ---\n{issue.json_path}")
            parts.append(
                f"--- CURRENT VALUE ---\n"
                f"{json.dumps(current_value, ensure_ascii=False, indent=2)}")
            parts.append(f"--- ISSUE ---\n[{issue.rule}] {issue.message}")
            if issue.context:
                parts.append(
                    f"--- ISSUE CONTEXT ---\n"
                    f"{json.dumps(issue.context, ensure_ascii=False)}")

        # Related same-file context is available from the FIRST attempt —
        # the LLM does better with siblings than with a bare field, and a
        # 2nd attempt only re-targets whatever the re-verify still flags.
        if isinstance(full_content, dict):
            related_seen: dict[str, Any] = {}
            for issue, _cv in targets:
                related = self._get_related_context(
                    issue.json_path, full_content)
                if related:
                    related_seen.update(related)
            if related_seen:
                parts.append(
                    f"\n--- RELATED FIELDS (same file) ---\n"
                    f"{json.dumps(related_seen, ensure_ascii=False, indent=2)}")

        if attempt_num >= 1:
            parts.append("\n--- HINT ---\nA previous attempt did not "
                         "resolve every field. Reconsider the broader "
                         "context of the character and stage.")

        return "\n".join(parts)

    def _parse_response(self, response: str,
                        targets: list[tuple[Issue, Any]]) -> dict[str, Any]:
        """Parse the LLM response into a ``{json_path: new_value}`` map.

        Accepts the batch object form, and — as a fallback when a single
        field was requested — a bare corrected value keyed to that field.
        """
        parsed = json.loads(response.strip())
        paths = {issue.json_path for issue, _ in targets}
        if isinstance(parsed, dict) and any(p in parsed for p in paths):
            return {p: v for p, v in parsed.items() if p in paths}
        if len(targets) == 1:
            # Single field, model returned the bare value.
            return {targets[0][0].json_path: parsed}
        return {}

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
