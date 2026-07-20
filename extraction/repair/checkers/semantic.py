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

# Rules that signal the semantic review COULD NOT RUN (backend down, empty
# or unparseable output). They anchor at ``$`` and must survive scoped
# filtering — dropping them would turn "review never happened" into a
# silent clean pass, which is exactly the false-pass this checker exists to
# prevent (see module docstring). ``check_scoped`` keeps them unconditionally.
_BACKEND_FAILURE_RULES = frozenset({
    "semantic_unavailable",
    "semantic_check_crashed",
    "semantic_unparseable",
})


def _path_in_scope(json_path: str, scope_paths: list[str]) -> bool:
    """True when ``json_path`` is one of ``scope_paths`` or nested under one.

    The L3 gate scopes a re-check to a narrow per-file path set — see
    ``coordinator._gate_scope``: what a fix touched this round, plus the paths
    of semantic issues still open on that file. A fix patches the subtree at
    path ``P``; the re-review may re-anchor a new finding at a leaf UNDER
    ``P`` (e.g. patched ``$.a`` → finding at ``$.a.b``), which is still "a
    problem on the path I touched" and must be kept. Anything outside every
    scoped subtree is review jitter on an untouched field — dropped so the
    loop doesn't chase moving targets.
    """
    for p in scope_paths:
        if json_path == p or json_path.startswith(p + ".") \
                or json_path.startswith(p + "["):
            return True
    return False


def _decode_top_level_arrays(text: str) -> list[list]:
    """Decode every top-level JSON array in ``text``, in order.

    ``text`` starts at the first ``[``. The model is asked for exactly one
    array but has been observed emitting two (``[] [{...}]``), so a
    first-``[``-to-last-``]`` slice would splice them into invalid JSON.
    Decoding value by value handles that, while still tolerating the
    non-JSON tail the old slice absorbed (markdown fences, closing prose).

    Junk between arrays is skipped by seeking the next ``[``. A decode
    failure raises only when nothing has been decoded yet — once at least
    one array is in hand, trailing garbage is the model padding its answer,
    not a broken response.
    """
    decoder = json.JSONDecoder()
    arrays: list[list] = []
    pos = 0
    while True:
        pos = text.find("[", pos)
        if pos < 0:
            return arrays
        try:
            value, pos = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            if arrays:
                return arrays
            raise
        if isinstance(value, list):
            arrays.append(value)


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

    def __init__(self, llm_call: Callable[..., str] | None = None,
                 timeout_s: int = 900):
        """
        Args:
            llm_call: A callable ``(prompt: str, timeout: int,
                effort: str | None = None) -> str`` that invokes an LLM and
                returns the raw text response. It MUST accept ``effort`` as a
                keyword on every path — this checker always passes it, sending
                ``effort=None`` on the Phase A full pass so that pass inherits
                the backend default. If None, semantic checking is a no-op.
            timeout_s: hard timeout per review call, passed explicitly on
                every call (decision #68 — no injector-side default that a
                config change could be shadowed by). Wired from
                ``RepairConfig.semantic_timeout_s``.
        """
        self._llm_call = llm_call
        self._timeout_s = timeout_s

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
        """Re-check semantics restricted to ``paths`` — the caller's per-file
        gate scope (``coordinator._gate_scope``: touched this round ∪ paths of
        still-open semantic issues on that file).

        The prompt's ``Focus review on these paths`` line is a SOFT hint; the
        LLM may still report problems on fields it wasn't asked about. That is
        precisely the whack-a-mole failure this method guards against: an
        nondeterministic full-file re-review surfaces a different set of
        untouched-field nits every round, each a fresh fingerprint that the
        round diff counts as ``introduced``, so the loop never converges.

        So filtering here is a PROGRAM guarantee, not a request: only issues
        on (or nested under) a scoped path survive. Backend-failure issues
        (``$``-anchored, see ``_BACKEND_FAILURE_RULES``) are always kept —
        they mean the review couldn't run, and dropping them would be a
        false pass. An empty ``paths`` therefore keeps only backend failures.
        """
        if self._llm_call is None:
            return []
        issues: list[Issue] = []
        for f in files:
            content = f.content if f.content is not None else f.load()
            if content is None:
                continue
            file_issues = self._review_file(
                f.path, content, focus_paths=paths, effort=effort)
            for issue in file_issues:
                if (issue.rule in _BACKEND_FAILURE_RULES
                        or _path_in_scope(issue.json_path, paths)):
                    issues.append(issue)
        return issues

    def _review_file(self, file_path: str, content: Any,
                     focus_paths: list[str] | None = None,
                     effort: str | None = None) -> list[Issue]:
        # Callers (`check` / `check_scoped`) guard with `_llm_call is None`
        # before invoking this method; assert reflects that contract for
        # the type checker, since narrowing doesn't cross method boundaries.
        assert self._llm_call is not None
        prompt_parts = [SEMANTIC_REVIEW_SYSTEM, "\n--- FILE ---\n"]

        # The file goes in WHOLE — never truncated, and deliberately NOT a
        # tunable (decision #70). Phase A is the only full-file semantic pass
        # in the repair lifecycle, so whatever it does not see, nothing
        # downstream sees either. A file that overruns the context window
        # fails the call, which the handlers below turn into a blocking issue
        # — loud failure beats a silent partial review reporting PASS.
        prompt_parts.append(json.dumps(content, ensure_ascii=False, indent=2))

        if focus_paths:
            prompt_parts.append(
                f"\n\nFocus review on these paths: {', '.join(focus_paths)}")

        prompt = "\n".join(prompt_parts)

        try:
            # Timeout comes from the injected ``RepairConfig`` and is passed
            # explicitly (decision #68) — a literal here would shadow the
            # config, and an injector-side default would hide it from the
            # call site. ``effort=None`` inherits the backend default
            # (Phase A); the L3 gate passes it down explicitly.
            response = self._llm_call(
                prompt, timeout=self._timeout_s, effort=effort)
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
        start = text.find("[")
        if start < 0:
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
            arrays = _decode_top_level_arrays(text[start:])
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in semantic review for %s", file_path)
            return [Issue(
                file=file_path,
                json_path="$",
                category="semantic",
                severity="error",
                rule="semantic_unparseable",
                message=(f"L3 semantic JSON decode failed: {exc}; "
                         f"first 80 chars: {text[:80]!r}"),
            )]

        if len(arrays) > 1:
            # The model emitted more than one array (observed shape:
            # ``[] [{...}]`` — an empty one followed by the real findings).
            # Merging is the only safe read: taking just the first would
            # report a clean pass while the actual issues sat in the second.
            logger.warning(
                "Semantic review for %s returned %d top-level arrays; "
                "merged into one issue list", file_path, len(arrays))
        items = [item for arr in arrays for item in arr]

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
