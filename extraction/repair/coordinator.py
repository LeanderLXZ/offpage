"""Coordinator — three-phase check → fix → verify orchestration.

Phase A: Full validation (L0–L3 if configured)
Phase B: Fix loop — escalate T0→T1→T2 (each tier capped at 2 attempts,
         routed per issue rule by ``protocol.route_tiers``) with a scoped
         L0–L2 recheck and an embedded L3 gate (re-runs the semantic
         checker on files modified this round AND that had semantic
         issues in Phase A). There is NO full-file regeneration tier —
         issues the capped tiers can't fix are left for Phase C to
         surface (and the caller to defer).
Phase C: Final confirmation — reuses the last L3 gate result instead of
         issuing a fresh semantic call when possible

Source-discrepancy triage (when ``config.triage_enabled``) hooks into
Phase B at two points:
  round 1 — post-capped-tiers, to accept residual L3 issues that are
            author bugs in the source novel as SourceNotes
  round 2 — post-L3-gate and pre-FAIL, to accept any remaining L3
            residuals that program-verify as source-inherent

A run is a single Phase A→B→C pass (no lifecycle reset — that machinery
existed only to host the removed T3 regen). Residual length-bound schema
misses are accepted via the decision #48 tolerance gate after the capped
tiers rather than hard-failing.

Public API:
    run(files, config, ...) → RepairResult
    validate_only(files, ...) → list[Issue]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from .checkers import CheckerPipeline
from .checkers.json_syntax import JsonSyntaxChecker
from .checkers.schema import SchemaChecker
from .checkers.structural import StructuralChecker
from .checkers.targets_keys_eq_baseline import TargetsKeysEqBaselineChecker
from .checkers.semantic import SemanticChecker
from .context_retriever import ContextRetriever
from .fixers.programmatic import ProgrammaticFixer
from .fixers.local_patch import LocalPatchFixer
from .fixers.source_patch import SourcePatchFixer
from .notes_writer import NotesWriter
from .recorder import RepairRecorder
from .protocol import (
    FileEntry,
    Issue,
    RepairAttempt,
    RepairConfig,
    RepairResult,
    SourceContext,
    SourceNote,
    TriageVerdict,
    is_coverage_shortage,
    issue_max_tier,
    issue_start_tier,
)
from .tracker import IssueTracker
from .triage import Triager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline & fixer factory
# ---------------------------------------------------------------------------

def _build_pipeline(
    llm_call: Callable[..., str] | None = None,
    importance_map: dict[str, str] | None = None,
    extra_checkers: list[Any] | None = None,
) -> CheckerPipeline:
    pipeline = CheckerPipeline()
    pipeline.register(JsonSyntaxChecker())
    pipeline.register(SchemaChecker())
    pipeline.register(StructuralChecker(importance_map=importance_map))
    pipeline.register(TargetsKeysEqBaselineChecker())
    pipeline.register(SemanticChecker(llm_call=llm_call))
    for checker in extra_checkers or []:
        pipeline.register(checker)
    return pipeline


# Hard cap on attempts per tier (T-REPAIR-NO-REEXTRACT): a tier tries at
# most twice; the 2nd attempt only re-targets fields the immediate
# re-verify still flags. Configured ``t*_max`` above this is clamped down.
_TIER_ATTEMPT_CAP = 2


def _build_fixers(
    llm_call: Callable[..., str] | None = None,
    retriever: ContextRetriever | None = None,
    pipeline: CheckerPipeline | None = None,
) -> dict[int, object]:
    # T1's immediate re-verify: scoped L0–L2 recheck (0 token) returning
    # the set of issue fingerprints still present after a patch.
    verify_fn: Callable[[list[FileEntry]], set[str]] | None = None
    if pipeline is not None:
        def verify_fn(files: list[FileEntry]) -> set[str]:
            issues = pipeline.run_scoped(files, patched_paths=[], max_layer=2)
            return {i.fingerprint for i in issues}

    return {
        0: ProgrammaticFixer(),
        1: LocalPatchFixer(llm_call=llm_call, verify_fn=verify_fn),
        2: SourcePatchFixer(llm_call=llm_call, retriever=retriever),
    }


def _tier_max(config: RepairConfig, tier: int) -> int:
    """Max retry attempts for a given tier (hard-capped at 2)."""
    configured = {
        0: config.retry_policy.t0_max,
        1: config.retry_policy.t1_max,
        2: config.retry_policy.t2_max,
    }.get(tier, 1)
    return min(configured, _TIER_ATTEMPT_CAP)


# ---------------------------------------------------------------------------
# Lifecycle outcome (one Phase A→B→C pass)
# ---------------------------------------------------------------------------

# Terminal reasons:
#   PASS — Phase C confirmed no blocking issues (or the decision #48
#          length-tolerance gate accepted the residual)
#   FAIL — Phase C surfaced blocking issues; run done
_TERMINAL_TYPES = ("PASS", "FAIL")


@dataclass
class _LifecycleOutcome:
    terminated_by: str
    final_issues: list[Issue] = field(default_factory=list)
    final_blocking: list[Issue] = field(default_factory=list)
    accepted_notes: list[SourceNote] = field(default_factory=list)
    tracker_history: dict[str, list[RepairAttempt]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_only(
    files: list[FileEntry],
    llm_call: Callable[..., str] | None = None,
    run_semantic: bool = False,
    importance_map: dict[str, str] | None = None,
    extra_checkers: list[Any] | None = None,
) -> list[Issue]:
    """Run all checkers without any repair. Returns issue list."""
    pipeline = _build_pipeline(
        llm_call=llm_call,
        importance_map=importance_map,
        extra_checkers=extra_checkers,
    )
    return pipeline.run(files, run_semantic=run_semantic)


def run(
    files: list[FileEntry],
    config: RepairConfig | None = None,
    source_context: SourceContext | None = None,
    llm_call: Callable[..., str] | None = None,
    importance_map: dict[str, str] | None = None,
    recorder: RepairRecorder | None = None,
    extra_checkers: list[Any] | None = None,
) -> RepairResult:
    """Single-pass three-phase repair (Phase A → B → C).

    Args:
        importance_map: ``{character_id: importance}`` — raises the
            structural min-examples threshold for main / important
            characters (主角 → 5, 重要配角 → 3, others → 1).
        recorder: optional ``RepairRecorder`` that receives a structured
            JSONL event at each phase / round / issue / fix / triage /
            completion transition. ``None`` disables structured logging.
        extra_checkers: optional additional ``BaseChecker`` instances
            registered on top of the built-in pipeline (decision #59 —
            phase 2 baseline reference checkers carry their hints via
            constructor injection, keeping ``FileEntry.content`` clean).
    """
    if config is None:
        config = RepairConfig()

    pipeline = _build_pipeline(
        llm_call=llm_call,
        importance_map=importance_map,
        extra_checkers=extra_checkers,
    )
    retriever = ContextRetriever()
    fixers = _build_fixers(
        llm_call=llm_call,
        retriever=retriever,
        pipeline=pipeline,
    )

    triager: Triager | None = None
    notes_writer: NotesWriter | None = None
    if config.triage_enabled and source_context is not None:
        triager = Triager(llm_call=llm_call, retriever=retriever)
        notes_writer = NotesWriter(source_context.work_path)

    outcome = _run_one_lifecycle(
        files=files,
        config=config,
        source_context=source_context,
        pipeline=pipeline,
        fixers=fixers,
        triager=triager,
        notes_writer=notes_writer,
        recorder=recorder,
    )

    passed = outcome.terminated_by == "PASS"
    report_text = _build_report(
        outcome.final_issues,
        outcome.tracker_history,
        passed,
        terminated_by=outcome.terminated_by,
        accepted_notes=outcome.accepted_notes,
    )

    return RepairResult(
        passed=passed,
        issues=outcome.final_issues,
        history=outcome.tracker_history,
        report=report_text,
        accepted_notes=outcome.accepted_notes,
    )


# ---------------------------------------------------------------------------
# One lifecycle (one full Phase A → B → C pass)
# ---------------------------------------------------------------------------

def _run_one_lifecycle(
    *,
    files: list[FileEntry],
    config: RepairConfig,
    source_context: SourceContext | None,
    pipeline: CheckerPipeline,
    fixers: dict[int, object],
    triager: Triager | None,
    notes_writer: NotesWriter | None,
    recorder: RepairRecorder | None,
) -> _LifecycleOutcome:
    """Execute one complete Phase A → B → C pass.

    Returns a ``_LifecycleOutcome`` describing why the run ended and the
    state the final ``RepairResult`` builder needs.
    """
    def _emit(event: str, **fields: Any) -> None:
        if recorder is not None:
            recorder.write(event, cycle=0, **fields)

    tracker = IssueTracker()
    accepted_notes: list[SourceNote] = []
    notes_per_file: dict[str, int] = {}

    # =================================================================
    # Phase A — Full check (L0–L3)
    # =================================================================
    logger.info("Phase A: full validation")
    _emit("phase_start", phase="A",
          file_count=len(files), run_semantic=config.run_semantic)
    all_issues = pipeline.run(files, run_semantic=config.run_semantic)

    blocking = _filter_blocking(all_issues, config)

    if not blocking:
        logger.info("Phase A: no blocking issues — pass")
        _emit("phase_a_result", blocking=0, total=len(all_issues))
        _emit("complete", status="PASS",
              resolved=0, persisting=0, issues_remaining=0)
        return _LifecycleOutcome(
            terminated_by="PASS",
            final_issues=all_issues,
            final_blocking=[],
            accepted_notes=accepted_notes,
            tracker_history=tracker.get_history(),
        )

    logger.info("Phase A: %d blocking issues found", len(blocking))
    _emit("phase_a_result", blocking=len(blocking), total=len(all_issues))
    for i in blocking:
        start_tier = issue_start_tier(i)
        _emit("issue",
              fingerprint=i.fingerprint,
              file=i.file,
              json_path=i.json_path,
              category=i.category,
              rule=i.rule,
              severity=i.severity,
              message=i.message,
              start_tier=start_tier)
    had_semantic = any(i.category == "semantic" for i in all_issues)
    l3_file_set: set[str] = {
        i.file for i in all_issues if i.category == "semantic"
    }

    # =================================================================
    # Phase B — Fix loop (with embedded L3 gate + triage hooks)
    # =================================================================
    logger.info("Phase B: entering fix loop")
    _emit("phase_start", phase="B")
    prev_report = None
    current_issues = list(blocking)
    last_gate_issues: list[Issue] | None = None
    gate_ever_ran = False
    lifecycle_signal = ""  # "" | "LENGTH_TOLERANCE_PASS"

    for round_num in range(config.max_rounds):
        logger.info("Fix round %d — %d issues remaining",
                     round_num + 1, len(current_issues))
        _emit("round_start",
              round=round_num + 1, issues_remaining=len(current_issues))

        tier_groups = _group_by_start_tier(current_issues)

        modified_files: set[str] = set()
        round_fixer_candidates: dict[str, TriageVerdict] = {}

        for tier in sorted(tier_groups.keys()):
            fixer = fixers.get(tier)
            if fixer is None:
                continue

            tier_issues = tier_groups[tier]
            tier_modified, tier_cands, tier_signal = (
                _run_fixer_with_escalation(
                    fixer, fixers, tier, tier_issues, files,
                    source_context, config, tracker,
                    pipeline=pipeline,
                    triager=triager,
                    notes_writer=notes_writer,
                    accepted_notes=accepted_notes,
                    notes_per_file=notes_per_file,
                )
            )
            modified_files.update(tier_modified)
            round_fixer_candidates.update(tier_cands)
            if tier_signal:
                lifecycle_signal = tier_signal
                break

        if lifecycle_signal == "LENGTH_TOLERANCE_PASS":
            # The length-bound tolerance gate accepted the residual
            # schema minLength/maxLength issues (decision #48). Terminate
            # as PASS without re-running Phase C — Phase C uses the strict
            # pipeline and would re-flag the same length issues we just
            # intentionally relaxed.
            logger.info(
                "Length-bound tolerance gate: PASS (decision #48)")
            _emit("complete", status="PASS",
                  issues_remaining=0,
                  accepted_notes=len(accepted_notes))
            return _LifecycleOutcome(
                terminated_by="PASS",
                final_issues=[],
                final_blocking=[],
                accepted_notes=accepted_notes,
                tracker_history=tracker.get_history(),
            )

        if not modified_files:
            logger.info("No patches applied in round %d — stopping",
                         round_num + 1)
            _emit("no_patches", round=round_num + 1)
            break
        _emit("round_patched",
              round=round_num + 1,
              modified_files=sorted(modified_files))

        # Scoped recheck (L0–L2 only, 0 token). Already-accepted
        # coverage_shortage issues resurface here because the note is
        # sidecar and the underlying JSON wasn't modified — drop them by
        # fingerprint so the loop doesn't spin.
        recheck_issues = pipeline.run_scoped(
            files, patched_paths=[], max_layer=2)
        accepted_fps = {n.issue_fingerprint for n in accepted_notes}
        recheck_blocking = [
            i for i in _filter_blocking(recheck_issues, config)
            if i.fingerprint not in accepted_fps
        ]

        # ---- L3 gate ----
        gate_blocking: list[Issue] = []
        gate_targets = l3_file_set & modified_files
        if (config.l3_gate_enabled and config.run_semantic
                and gate_targets):
            logger.info(
                "L3 gate: re-checking %d file(s) modified this round",
                len(gate_targets))
            gate_file_entries = [f for f in files if f.path in gate_targets]
            gate_issues = pipeline.run_layer(gate_file_entries, layer=3)
            gate_blocking = _filter_blocking(gate_issues, config)
            tracker.record_l3_gate(
                {i.fingerprint for i in gate_blocking})
            gate_ever_ran = True

            # ---- Post-gate triage (round 2) ----
            if gate_blocking and triager and notes_writer and source_context:
                gate_blocking = _run_triage_round(
                    triager=triager,
                    notes_writer=notes_writer,
                    config=config,
                    source_ctx=source_context,
                    issues=gate_blocking,
                    triage_round=2,
                    accepted_notes=accepted_notes,
                    notes_per_file=notes_per_file,
                    fixer_candidates=round_fixer_candidates,
                )

            last_gate_issues = gate_blocking
            logger.info(
                "L3 gate result: %d blocking semantic issue(s) remain",
                len(gate_blocking))
            _emit("l3_gate_result",
                  round=round_num + 1,
                  targets=sorted(gate_targets),
                  blocking=len(gate_blocking))

        combined_blocking = recheck_blocking + gate_blocking
        report = tracker.diff(current_issues, combined_blocking)
        logger.info(
            "Round %d result: resolved=%d, persisting=%d, introduced=%d",
            round_num + 1, len(report.resolved),
            len(report.persisting), len(report.introduced),
        )
        _emit("round_result",
              round=round_num + 1,
              resolved=len(report.resolved),
              persisting=len(report.persisting),
              introduced=len(report.introduced))

        # Safety valves
        if tracker.is_regression(report):
            logger.warning("Regression detected in round %d — stopping",
                           round_num + 1)
            break
        if tracker.is_stalled(prev_report, report):
            logger.warning("Stalled in round %d — stopping", round_num + 1)
            break
        if tracker.is_l3_gate_reemerge():
            logger.warning(
                "L3 gate reemerge in round %d — semantic layer not "
                "converging, stopping", round_num + 1)
            break

        prev_report = report
        current_issues = combined_blocking

        if not current_issues:
            logger.info("All blocking issues resolved after round %d",
                         round_num + 1)
            break

    # =================================================================
    # Phase C — Final confirmation
    # =================================================================
    final_issues = pipeline.run(files, max_layer=2, run_semantic=False)
    accepted_fps = {n.issue_fingerprint for n in accepted_notes}
    if accepted_fps:
        final_issues = [
            i for i in final_issues if i.fingerprint not in accepted_fps
        ]

    if had_semantic and config.run_semantic:
        if gate_ever_ran:
            logger.info(
                "Phase C: reusing last L3 gate result (%d issue(s))",
                len(last_gate_issues or []))
            _emit("phase_c", mode="gate_reuse",
                  carried=len(last_gate_issues or []))
            final_issues.extend(last_gate_issues or [])
        else:
            logger.info(
                "Phase C: fallback semantic verification (gate never ran)")
            _emit("phase_c", mode="fallback_l3")
            l3_fallback = pipeline.run_layer(files, layer=3)
            final_issues.extend(l3_fallback)

    final_blocking = _filter_blocking(final_issues, config)
    passed = len(final_blocking) == 0

    logger.info("Repair complete: %s (%d issues remaining, %d note(s))",
                "PASS" if passed else "FAIL",
                len(final_blocking), len(accepted_notes))
    _emit("complete",
          status="PASS" if passed else "FAIL",
          issues_remaining=len(final_blocking),
          accepted_notes=len(accepted_notes))

    return _LifecycleOutcome(
        terminated_by="PASS" if passed else "FAIL",
        final_issues=final_issues,
        final_blocking=final_blocking,
        accepted_notes=accepted_notes,
        tracker_history=tracker.get_history(),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _filter_blocking(issues: list[Issue],
                     config: RepairConfig) -> list[Issue]:
    """Issues that must be fixed or accepted before the stage can pass.

    Errors are always blocking. `coverage_shortage` warnings are also
    blocking: they carry a severity=warning demotion so they can't
    legitimately FAIL the stage, but they still need to enter the fix
    pipeline (start=T2) and then the 0-token triage fast path. If we
    dropped them here, they'd be silently ignored and leave the stage
    under the `importance_min_examples` floor.
    """
    if config.block_on == "all":
        return list(issues)
    return [i for i in issues
            if i.severity == "error" or is_coverage_shortage(i)]


def _group_by_start_tier(issues: list[Issue]) -> dict[int, list[Issue]]:
    groups: dict[int, list[Issue]] = {}
    for issue in issues:
        groups.setdefault(issue_start_tier(issue), []).append(issue)
    return groups


def _run_fixer_with_escalation(
    fixer,
    all_fixers: dict,
    start_tier: int,
    issues: list[Issue],
    files: list[FileEntry],
    source_context: SourceContext | None,
    config: RepairConfig,
    tracker: IssueTracker,
    *,
    pipeline: CheckerPipeline,
    triager: Triager | None,
    notes_writer: NotesWriter | None,
    accepted_notes: list[SourceNote],
    notes_per_file: dict[str, int],
) -> tuple[set[str], dict[str, TriageVerdict], str]:
    """Run a fixer tier; if attempts are exhausted, escalate to the next
    tier (capped per issue by ``protocol.route_tiers``; no tier > 2).

    Returns ``(modified_files, fixer_candidates, lifecycle_signal)``:
      * ``modified_files`` — file paths touched by at least one
        successful fix in this invocation (feeds the L3 gate).
      * ``fixer_candidates`` — T2 self-reported source_inherent verdicts,
        carried forward as priors for the post-gate triage.
      * ``lifecycle_signal`` — ``""`` for normal completion, or
        ``"LENGTH_TOLERANCE_PASS"`` when the residual issues were all
        pure ``minLength``/``maxLength`` schema misses that passed the
        relaxed (×0.9 floor / ×1.1 ceil) re-validation (decision #48) —
        the caller treats this as a terminal PASS.
    """
    modified_files: set[str] = set()
    remaining = list(issues)
    tier = start_tier
    # T2 self-report verdicts — used as priors for the residual triage.
    t2_self_report: dict[str, TriageVerdict] = {}
    # Issues that hit their per-issue max_tier without being fixed.
    capped_out: list[Issue] = []
    lifecycle_signal = ""

    while remaining and tier <= 2:
        fixer_obj = all_fixers.get(tier)
        if fixer_obj is None:
            tier += 1
            continue

        max_retries = _tier_max(config, tier)
        for attempt in range(max_retries):
            if not remaining:
                break

            # coverage_shortage issues only get ONE T2 attempt — the
            # novel either gains more examples on the first source_patch
            # or it doesn't. Retrying doesn't add source material.
            if attempt > 0 and tier == 2:
                remaining = [i for i in remaining
                             if not is_coverage_shortage(i)]
                if not remaining:
                    break

            attempted = list(remaining)
            result = fixer_obj.fix(
                files=files,
                issues=attempted,
                strategy="standard",
                source_context=source_context,
                attempt_num=attempt,
                max_attempts=max_retries,
            )

            # Capture T2 self-reports (source_inherent escape hatch).
            if result.source_inherent_candidates and tier == 2:
                t2_self_report.update(result.source_inherent_candidates)

            fingerprint_to_file = {i.fingerprint: i.file for i in attempted}
            for fp in result.resolved_fingerprints:
                f_path = fingerprint_to_file.get(fp)
                if f_path:
                    modified_files.add(f_path)

            remaining = [
                i for i in remaining
                if i.fingerprint not in result.resolved_fingerprints
            ]

            for issue in attempted:
                status: Literal["resolved", "persisting"] = (
                    "resolved"
                    if issue.fingerprint in result.resolved_fingerprints
                    else "persisting")
                tracker.record_attempt(RepairAttempt(
                    issue_fingerprint=issue.fingerprint,
                    tier=tier,
                    attempt_num=attempt,
                    strategy="standard",
                    result=status,
                ))

        # ---- coverage_shortage fast path (0 token, post-T2) ----
        # After T2's one attempt at adding examples, any remaining
        # coverage_shortage issues are accepted via a program-constructed
        # SourceNote — no source material can be invented.
        if (tier == 2 and triager is not None and notes_writer is not None
                and source_context is not None):
            cs_remaining = [i for i in remaining if is_coverage_shortage(i)]
            if cs_remaining:
                accepted_cs = _run_coverage_shortage_triage(
                    triager=triager,
                    notes_writer=notes_writer,
                    config=config,
                    source_ctx=source_context,
                    issues=cs_remaining,
                    accepted_notes=accepted_notes,
                    notes_per_file=notes_per_file,
                )
                if accepted_cs:
                    modified_files.update(i.file for i in accepted_cs)
                    accepted_fps = {i.fingerprint for i in accepted_cs}
                    remaining = [i for i in remaining
                                 if i.fingerprint not in accepted_fps]

        # ---- escalation / per-issue cap ----
        if remaining:
            next_tier = tier + 1
            at_cap = [i for i in remaining if issue_max_tier(i) < next_tier]
            if at_cap:
                capped_out.extend(at_cap)
                at_cap_fps = {x.fingerprint for x in at_cap}
                remaining = [i for i in remaining
                             if i.fingerprint not in at_cap_fps]
                logger.info("Capping %d issue(s) at T%d (max_tier reached)",
                            len(at_cap), tier)
            if remaining:
                logger.info("Escalating %d issues from T%d to T%d",
                            len(remaining), tier, next_tier)
        tier += 1

    # Anything the capped tiers couldn't fix.
    residual = capped_out + remaining

    # ---- Residual source_inherent triage (post-cap, before defer) ----
    # Accept residual L3 semantic issues that are author bugs in the
    # source novel as SourceNotes so they don't become blocking. Only
    # semantic issues are eligible; the rest fall through to Phase C
    # (and the caller's deferred-repair ledger).
    if (residual and triager is not None and notes_writer is not None
            and source_context is not None):
        residual = _run_triage_round(
            triager=triager,
            notes_writer=notes_writer,
            config=config,
            source_ctx=source_context,
            issues=residual,
            triage_round=1,
            accepted_notes=accepted_notes,
            notes_per_file=notes_per_file,
            fixer_candidates=t2_self_report,
        )

    # ---- Length-bound tolerance gate (decision #48) ----
    # When every residual issue is a pure minLength / maxLength schema
    # miss, re-validate the affected files with a relaxed schema (×0.9
    # floor / ×1.1 ceil); if they pass, accept them and signal a terminal
    # PASS instead of leaving them to fail Phase C.
    if residual and _all_length_only(residual):
        if _length_tolerance_pass(residual, files):
            logger.info(
                "Length-bound tolerance gate accepted %d residual "
                "issue(s) (decision #48).", len(residual))
            lifecycle_signal = "LENGTH_TOLERANCE_PASS"

    return modified_files, t2_self_report, lifecycle_signal


def _all_length_only(issues: list[Issue]) -> bool:
    """True when every issue is a pure minLength/maxLength schema miss."""
    return bool(issues) and all(
        i.category == "schema"
        and i.rule in ("schema_minLength", "schema_maxLength")
        for i in issues)


def _length_tolerance_pass(issues: list[Issue],
                           files: list[FileEntry]) -> bool:
    """Re-validate the files behind ``issues`` against a length-relaxed
    schema (decision #48). Returns True only when every affected file
    passes the ×0.9 floor / ×1.1 ceil re-check.
    """
    from extraction.validation.shared.schema_tolerance import (
        validate_with_length_tolerance)

    affected_paths = {i.file for i in issues}
    files_by_path = {f.path: f for f in files}
    for fp in affected_paths:
        fe = files_by_path.get(fp)
        if fe is None or fe.schema is None:
            return False
        content = fe.content if fe.content is not None else fe.load()
        if content is None:
            return False
        # JSONL files validate per-entry (mirrors SchemaChecker).
        entries = content if isinstance(content, list) else [content]
        for entry in entries:
            ok, _ = validate_with_length_tolerance(entry, fe.schema)
            if not ok:
                return False
    return True


def _run_triage_round(
    *,
    triager: Triager,
    notes_writer: NotesWriter,
    config: RepairConfig,
    source_ctx: SourceContext,
    issues: list[Issue],
    triage_round: int,
    accepted_notes: list[SourceNote],
    notes_per_file: dict[str, int],
    fixer_candidates: dict[str, TriageVerdict],
) -> list[Issue]:
    """Run one triage pass; persist accepted notes; return remaining issues.

    ``triage_round`` is 1 for the residual (post-cap) triage and 2 for
    post-gate triage. Enforces the per-file accept cap from config.
    """
    if not issues:
        return []

    # Only L3 `semantic` issues are eligible for accept_with_notes.
    # Mechanical errors (L0 syntax / L1 schema / L2 structural) can't be
    # "the source novel's fault" — keep them in the queue untouched.
    semantic_issues = [i for i in issues if i.category == "semantic"]
    non_semantic = [i for i in issues if i.category != "semantic"]
    if not semantic_issues:
        return list(issues)

    by_file: dict[str, list[Issue]] = {}
    for i in semantic_issues:
        by_file.setdefault(i.file, []).append(i)

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    round_notes: list[SourceNote] = []
    accepted_fps: set[str] = set()

    for file_path, file_issues in by_file.items():
        already = notes_per_file.get(file_path, 0)
        cap_remaining = config.accept_cap_per_file - already
        if cap_remaining <= 0:
            continue

        file_prior = {
            fp: v for fp, v in fixer_candidates.items()
            if any(i.fingerprint == fp for i in file_issues)
        }

        verdicts = triager.triage_file(
            file_path=file_path,
            issues=file_issues,
            source_ctx=source_ctx,
            accept_cap=cap_remaining,
            fixer_candidates=file_prior,
        )

        for v in verdicts:
            issue = next((i for i in file_issues
                          if i.fingerprint == v.issue_fingerprint), None)
            if issue is None:
                continue
            note_id = notes_writer.allocate_note_id(
                file_path, source_ctx.stage_id)
            note = triager.build_source_note(
                verdict=v,
                issue=issue,
                source_ctx=source_ctx,
                note_id=note_id,
                accepted_at=now_iso,
                triage_round=triage_round,
            )
            if note is None:
                continue
            round_notes.append(note)
            accepted_notes.append(note)
            accepted_fps.add(v.issue_fingerprint)
            notes_per_file[file_path] = (
                notes_per_file.get(file_path, 0) + 1)

    if round_notes:
        notes_writer.append(round_notes)
        logger.info(
            "triage round %d: accepted %d issue(s) as source_inherent",
            triage_round, len(round_notes))

    remaining_semantic = [
        i for i in semantic_issues if i.fingerprint not in accepted_fps
    ]
    return non_semantic + remaining_semantic


def _run_coverage_shortage_triage(
    *,
    triager: Triager,
    notes_writer: NotesWriter,
    config: RepairConfig,
    source_ctx: SourceContext,
    issues: list[Issue],
    accepted_notes: list[SourceNote],
    notes_per_file: dict[str, int],
) -> list[Issue]:
    """Accept L2 `min_examples` shortages via program-constructed
    SourceNotes (0 token). Returns the list of issues actually accepted.

    Shares ``accept_cap_per_file`` with the L3 source_inherent triage —
    overflow issues stay blocking and surface as warnings on the final
    report. ``triage_round=1`` (treated as first-pass acceptance) because
    coverage_shortage runs once per issue per stage.
    """
    if not issues:
        return []

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    accepted_issues: list[Issue] = []
    round_notes: list[SourceNote] = []

    by_file: dict[str, list[Issue]] = {}
    for i in issues:
        by_file.setdefault(i.file, []).append(i)

    for file_path, file_issues in by_file.items():
        already = notes_per_file.get(file_path, 0)
        cap_remaining = config.accept_cap_per_file - already
        if cap_remaining <= 0:
            logger.info(
                "coverage_shortage: %s — cap reached, %d issue(s) stay "
                "blocking", file_path, len(file_issues))
            continue

        taken = 0
        for issue in file_issues:
            if taken >= cap_remaining:
                logger.info(
                    "coverage_shortage: %s — per-file cap %d reached, "
                    "dropping %d remaining issue(s)",
                    file_path, config.accept_cap_per_file,
                    len(file_issues) - taken)
                break
            verdict = triager.build_coverage_shortage_verdict(
                issue, source_ctx)
            if verdict is None:
                continue
            note_id = notes_writer.allocate_note_id(
                file_path, source_ctx.stage_id)
            note = triager.build_source_note(
                verdict=verdict,
                issue=issue,
                source_ctx=source_ctx,
                note_id=note_id,
                accepted_at=now_iso,
                triage_round=1,
            )
            if note is None:
                continue
            round_notes.append(note)
            accepted_notes.append(note)
            accepted_issues.append(issue)
            notes_per_file[file_path] = (
                notes_per_file.get(file_path, 0) + 1)
            taken += 1

    if round_notes:
        notes_writer.append(round_notes)
        logger.info(
            "coverage_shortage: accepted %d issue(s) as 0-token SourceNote",
            len(round_notes))

    return accepted_issues


def _build_report(
    issues: list[Issue],
    history: dict[str, list[RepairAttempt]],
    passed: bool,
    *,
    terminated_by: str,
    accepted_notes: list[SourceNote] | None = None,
) -> str:
    lines = [f"Repair {'PASSED' if passed else 'FAILED'}"]
    lines.append(f"Final issues: {len(issues)}")

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    lines.append(f"  errors: {len(errors)}, warnings: {len(warnings)}")

    if accepted_notes:
        lines.append(f"Accepted source_inherent notes: {len(accepted_notes)}")
        for n in accepted_notes:
            lines.append(f"  {n.note_id} [{n.discrepancy_type}] "
                         f"{n.file} {n.json_path}")

    if history:
        total_attempts = sum(len(v) for v in history.values())
        lines.append(f"Total repair attempts: {total_attempts}")

    if errors:
        lines.append("\nRemaining errors:")
        for i in errors:
            lines.append(f"  {i}")

    return "\n".join(lines)
