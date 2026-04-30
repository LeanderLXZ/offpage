"""Coordinator — three-phase check → fix → verify orchestration.

Phase A: Full validation (L0–L3 if configured)
Phase B: Fix loop — escalate T0→T1→T2→T3 with scoped recheck and
         an embedded L3 gate (re-runs semantic checker on files that
         were modified this round AND had semantic issues in Phase A)
Phase C: Final confirmation — reuses the last L3 gate result instead of
         issuing a fresh semantic call when possible

Source-discrepancy triage (when ``config.triage_enabled``) hooks into
Phase B at two points:
  round 1 — pre-T3, to skip the expensive T3 regen when all residual
            L3 issues are author bugs in the source novel
  round 2 — post-L3-gate and pre-FAIL, to accept any remaining L3
            residuals that program-verify as source-inherent

Lifecycle reset:
  One file may walk at most ``config.max_lifecycles_per_file`` complete
  Phase A→B→C lifecycles. Lifecycle 1 may invoke T3; the moment T3 fires
  the lifecycle returns immediately (no post-T3 corruption check, no
  same-cycle L3 gate / Phase C) and the outer ``run()`` resets the state
  machine and enters lifecycle 2 with ``prior_attempt_context`` summarising
  what lifecycle 1 fixed and what still failed. Lifecycle 2 disables T3:
  any escalation that would call T3 returns ``T3_EXHAUSTED`` instead.
  Disk-side ``extraction_notes/{stage_id}.jsonl`` is append-only across
  lifecycles; lifecycle 2 reads back already-accepted fingerprints so the
  same issue is never written twice.

Public API:
    run(files, config, ...) → RepairResult
    validate_only(files, ...) → list[Issue]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

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
from .fixers.file_regen import FileRegenFixer
from .notes_writer import NotesWriter
from .recorder import RepairRecorder
from .protocol import (
    COVERAGE_SHORTAGE_MAX_TIER,
    COVERAGE_SHORTAGE_START_TIER,
    FileEntry,
    Issue,
    RepairAttempt,
    RepairConfig,
    RepairResult,
    SourceContext,
    SourceNote,
    START_TIER,
    TriageVerdict,
    is_coverage_shortage,
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
) -> CheckerPipeline:
    pipeline = CheckerPipeline()
    pipeline.register(JsonSyntaxChecker())
    pipeline.register(SchemaChecker())
    pipeline.register(StructuralChecker(importance_map=importance_map))
    pipeline.register(TargetsKeysEqBaselineChecker())
    pipeline.register(SemanticChecker(llm_call=llm_call))
    return pipeline


def _build_fixers(
    llm_call: Callable[..., str] | None = None,
    retriever: ContextRetriever | None = None,
) -> dict[int, object]:
    return {
        0: ProgrammaticFixer(),
        1: LocalPatchFixer(llm_call=llm_call),
        2: SourcePatchFixer(llm_call=llm_call, retriever=retriever),
        3: FileRegenFixer(llm_call=llm_call, retriever=retriever),
    }


def _tier_max(config: RepairConfig, tier: int) -> int:
    """Max retry attempts for a given tier."""
    return {
        0: config.retry_policy.t0_max,
        1: config.retry_policy.t1_max,
        2: config.retry_policy.t2_max,
        3: config.retry_policy.t3_max,
    }.get(tier, 1)


# ---------------------------------------------------------------------------
# Lifecycle outcome (one Phase A→B→C pass)
# ---------------------------------------------------------------------------

# Terminal reasons:
#   PASS           — Phase C confirmed no blocking issues
#   FAIL           — Phase C surfaced blocking issues; lifecycle done
#   T3_TRIGGERED   — lifecycle 1 invoked T3 and returns immediately so the
#                    outer loop can reset and run lifecycle 2
#   T3_EXHAUSTED   — lifecycle 2 wanted to escalate to T3; not allowed,
#                    lifecycle ends FAIL
_TERMINAL_TYPES = ("PASS", "FAIL", "T3_TRIGGERED", "T3_EXHAUSTED")


@dataclass
class _LifecycleOutcome:
    terminated_by: str
    final_issues: list[Issue] = field(default_factory=list)
    final_blocking: list[Issue] = field(default_factory=list)
    accepted_notes: list[SourceNote] = field(default_factory=list)
    tracker_history: dict[str, list[RepairAttempt]] = field(default_factory=dict)
    # Compact summaries fed into the next lifecycle's T3 prior-attempt
    # context. Each list entry is a single-line "path: rule" / "path:
    # rule (message)" string.
    resolved_summary: list[str] = field(default_factory=list)
    remaining_summary: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_only(
    files: list[FileEntry],
    llm_call: Callable[..., str] | None = None,
    run_semantic: bool = False,
    importance_map: dict[str, str] | None = None,
) -> list[Issue]:
    """Run all checkers without any repair. Returns issue list."""
    pipeline = _build_pipeline(
        llm_call=llm_call,
        importance_map=importance_map,
    )
    return pipeline.run(files, run_semantic=run_semantic)


def run(
    files: list[FileEntry],
    config: RepairConfig | None = None,
    source_context: SourceContext | None = None,
    llm_call: Callable[..., str] | None = None,
    importance_map: dict[str, str] | None = None,
    recorder: RepairRecorder | None = None,
) -> RepairResult:
    """Three-phase repair, possibly across two lifecycles.

    Args:
        importance_map: ``{character_id: importance}`` — raises the
            structural min-examples threshold for main / important
            characters (主角 → 5, 重要配角 → 3, others → 1).
        recorder: optional ``RepairRecorder`` that receives a structured
            JSONL event at each phase / round / issue / fix / triage /
            completion transition. ``None`` disables structured logging.
            Every event is tagged with ``cycle`` (0 = lifecycle 1,
            1 = lifecycle 2).
    """
    if config is None:
        config = RepairConfig()

    pipeline = _build_pipeline(
        llm_call=llm_call,
        importance_map=importance_map,
    )
    retriever = ContextRetriever()
    fixers = _build_fixers(llm_call=llm_call, retriever=retriever)

    triager: Triager | None = None
    notes_writer: NotesWriter | None = None
    if config.triage_enabled and source_context is not None:
        triager = Triager(llm_call=llm_call, retriever=retriever)
        notes_writer = NotesWriter(source_context.work_path)

    accepted_notes_total: list[SourceNote] = []
    aggregated_history: dict[str, list[RepairAttempt]] = {}
    last_outcome: _LifecycleOutcome | None = None
    prior_attempt_context: dict | None = None

    for cycle in range(max(1, config.max_lifecycles_per_file)):
        t3_disabled = cycle >= 1

        # Lifecycle 2: read back fingerprints already accepted on disk
        # so the same issue isn't written twice.
        existing_accepted_fps: set[str] = set()
        if t3_disabled and notes_writer is not None and source_context is not None:
            for f in files:
                existing_accepted_fps |= notes_writer.load_existing_fingerprints(
                    f.path, source_context.stage_id)

        outcome = _run_one_lifecycle(
            cycle=cycle,
            files=files,
            config=config,
            source_context=source_context,
            pipeline=pipeline,
            fixers=fixers,
            triager=triager,
            notes_writer=notes_writer,
            recorder=recorder,
            t3_disabled=t3_disabled,
            prior_attempt_context=prior_attempt_context,
            existing_accepted_fps=existing_accepted_fps,
        )

        accepted_notes_total.extend(outcome.accepted_notes)
        for fp, attempts in outcome.tracker_history.items():
            aggregated_history.setdefault(fp, []).extend(attempts)
        last_outcome = outcome

        if outcome.terminated_by == "T3_TRIGGERED":
            prior_attempt_context = {
                "resolved": list(outcome.resolved_summary),
                "remaining": list(outcome.remaining_summary),
            }
            continue
        break

    assert last_outcome is not None
    passed = last_outcome.terminated_by == "PASS"
    report_text = _build_report(
        last_outcome.final_issues,
        aggregated_history,
        passed,
        terminated_by=last_outcome.terminated_by,
        accepted_notes=accepted_notes_total,
    )

    return RepairResult(
        passed=passed,
        issues=last_outcome.final_issues,
        history=aggregated_history,
        report=report_text,
        accepted_notes=accepted_notes_total,
    )


# ---------------------------------------------------------------------------
# One lifecycle (one full Phase A → B → C pass)
# ---------------------------------------------------------------------------

def _run_one_lifecycle(
    *,
    cycle: int,
    files: list[FileEntry],
    config: RepairConfig,
    source_context: SourceContext | None,
    pipeline: CheckerPipeline,
    fixers: dict[int, object],
    triager: Triager | None,
    notes_writer: NotesWriter | None,
    recorder: RepairRecorder | None,
    t3_disabled: bool,
    prior_attempt_context: dict | None,
    existing_accepted_fps: set[str],
) -> _LifecycleOutcome:
    """Execute one complete Phase A → B → C pass.

    Returns a ``_LifecycleOutcome`` describing why the lifecycle ended
    and what state is needed by either the outer loop (for lifecycle 2
    setup) or the final ``RepairResult`` builder.
    """
    def _emit(event: str, **fields: Any) -> None:
        if recorder is not None:
            recorder.write(event, cycle=cycle, **fields)

    tracker = IssueTracker()
    accepted_notes: list[SourceNote] = []
    notes_per_file: dict[str, int] = {}

    # =================================================================
    # Phase A — Full check (L0–L3)
    # =================================================================
    logger.info("Phase A (lifecycle %d): full validation", cycle + 1)
    _emit("phase_start", phase="A",
          file_count=len(files), run_semantic=config.run_semantic)
    all_issues = pipeline.run(files, run_semantic=config.run_semantic)

    blocking = _filter_blocking(all_issues, config)

    # Lifecycle 2: drop issues already accepted on disk so they don't
    # cycle again (the underlying JSON wasn't modified — only the sidecar
    # note exists — so structural checks resurface them otherwise).
    if existing_accepted_fps:
        before = len(blocking)
        blocking = [
            i for i in blocking if i.fingerprint not in existing_accepted_fps
        ]
        dropped = before - len(blocking)
        if dropped:
            logger.info(
                "Lifecycle %d: dropped %d issue(s) already accepted on disk",
                cycle + 1, dropped)
            _emit("existing_notes_filtered", dropped=dropped)

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
        start_tier = (COVERAGE_SHORTAGE_START_TIER
                      if is_coverage_shortage(i)
                      else START_TIER.get(i.category, 0))
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
    lifecycle_signal = ""  # "" | "T3_TRIGGERED" | "T3_EXHAUSTED"

    for round_num in range(config.max_rounds):
        logger.info("Fix round %d — %d issues remaining",
                     round_num + 1, len(current_issues))
        _emit("round_start",
              round=round_num + 1, issues_remaining=len(current_issues))

        tier_groups = _group_by_start_tier(current_issues)

        modified_files: set[str] = set()
        round_t3_candidates: dict[str, TriageVerdict] = {}

        for tier in sorted(tier_groups.keys()):
            fixer = fixers.get(tier)
            if fixer is None:
                continue

            tier_issues = tier_groups[tier]
            tier_modified, tier_t3_cands, tier_signal = (
                _run_fixer_with_escalation(
                    fixer, fixers, tier, tier_issues, files,
                    source_context, config, tracker,
                    pipeline=pipeline,
                    triager=triager,
                    notes_writer=notes_writer,
                    accepted_notes=accepted_notes,
                    notes_per_file=notes_per_file,
                    t3_disabled=t3_disabled,
                    prior_attempt_context=prior_attempt_context,
                )
            )
            modified_files.update(tier_modified)
            round_t3_candidates.update(tier_t3_cands)
            if tier_signal:
                lifecycle_signal = tier_signal
                break

        # T3 fired (lifecycle 1) or was blocked (lifecycle 2). Skip the
        # rest of this round and let the outer loop decide whether to
        # reset into another lifecycle or finalise.
        if lifecycle_signal in ("T3_TRIGGERED", "T3_EXHAUSTED"):
            _emit("lifecycle_signal", round=round_num + 1,
                  signal=lifecycle_signal)
            return _build_signal_outcome(
                signal=lifecycle_signal,
                tracker=tracker,
                current_issues=current_issues,
                modified_files=modified_files,
                accepted_notes=accepted_notes,
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
        accepted_fps |= existing_accepted_fps
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
                    fixer_candidates=round_t3_candidates,
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
    accepted_fps |= existing_accepted_fps
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

    logger.info("Lifecycle %d complete: %s (%d issues remaining, %d note(s))",
                cycle + 1, "PASS" if passed else "FAIL",
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


def _build_signal_outcome(
    *,
    signal: str,
    tracker: IssueTracker,
    current_issues: list[Issue],
    modified_files: set[str],
    accepted_notes: list[SourceNote],
) -> _LifecycleOutcome:
    """Pack tracker state into summaries for the next lifecycle's T3 prompt."""
    history = tracker.get_history()
    resolved_summary: list[str] = []
    for fp, attempts in history.items():
        if any(a.result == "resolved" for a in attempts):
            # fingerprint format: file::json_path::rule
            resolved_summary.append(_format_fp_summary(fp))
    remaining_summary = [
        _format_issue_summary(i) for i in current_issues
    ]
    return _LifecycleOutcome(
        terminated_by=signal,
        final_issues=list(current_issues),
        final_blocking=list(current_issues),
        accepted_notes=accepted_notes,
        tracker_history=history,
        resolved_summary=resolved_summary,
        remaining_summary=remaining_summary,
    )


def _format_fp_summary(fp: str) -> str:
    """fingerprint = ``file::json_path::rule`` → ``json_path: rule``."""
    parts = fp.split("::", 2)
    if len(parts) == 3:
        _, jp, rule = parts
        return f"{jp}: {rule}"
    return fp


def _format_issue_summary(issue: Issue) -> str:
    msg = issue.message
    if len(msg) > 80:
        msg = msg[:80] + "…"
    return f"{issue.json_path}: {issue.rule} ({msg})"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _filter_blocking(issues: list[Issue],
                     config: RepairConfig) -> list[Issue]:
    """Issues that must be fixed or accepted before the stage can pass.

    Errors are always blocking. `coverage_shortage` warnings are also
    blocking: they carry a severity=warning demotion so they can't
    legitimately FAIL the stage, but they still need to enter the fix
    pipeline (START_TIER=T2) and then the 0-token triage fast path. If
    we dropped them here, they'd be silently ignored and leave the
    stage under the `importance_min_examples` floor.
    """
    if config.block_on == "all":
        return list(issues)
    return [i for i in issues
            if i.severity == "error" or is_coverage_shortage(i)]


def _group_by_start_tier(issues: list[Issue]) -> dict[int, list[Issue]]:
    groups: dict[int, list[Issue]] = {}
    for issue in issues:
        if is_coverage_shortage(issue):
            tier = COVERAGE_SHORTAGE_START_TIER
        else:
            tier = START_TIER.get(issue.category, 0)
        groups.setdefault(tier, []).append(issue)
    return groups


def _issue_max_tier(issue: Issue) -> int:
    """Highest fixer tier allowed for an issue.

    `coverage_shortage` issues cap at T2 — T3 can't add source material
    the novel doesn't contain, so escalation is pointless and just
    burns tokens. Everything else can escalate up to T3.
    """
    if is_coverage_shortage(issue):
        return COVERAGE_SHORTAGE_MAX_TIER
    return 3


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
    t3_disabled: bool,
    prior_attempt_context: dict | None,
) -> tuple[set[str], dict[str, TriageVerdict], str]:
    """Run a fixer tier; if retries exhausted, escalate to next tier.

    Returns ``(modified_files, t3_candidates, lifecycle_signal)``:
      * ``modified_files`` — file paths touched by at least one
        successful fix in this invocation (feeds the L3 gate).
      * ``t3_candidates`` — self-reported source_inherent verdicts
        emitted by T3 this round, carried forward to post-gate triage.
      * ``lifecycle_signal`` — ``""`` for normal completion,
        ``"T3_TRIGGERED"`` when T3 was invoked in lifecycle 1 (caller
        must abort the current lifecycle and reset),
        ``"T3_EXHAUSTED"`` when T3 was needed but disabled (lifecycle 2).
    """
    modified_files: set[str] = set()
    remaining = list(issues)
    tier = start_tier
    # T2 self-report verdicts — used as priors for pre-T3 triage.
    t2_self_report: dict[str, TriageVerdict] = {}
    t3_self_report: dict[str, TriageVerdict] = {}
    lifecycle_signal = ""

    while remaining and tier <= 3:
        fixer_obj = all_fixers.get(tier)
        if fixer_obj is None:
            tier += 1
            continue

        if tier == 3:
            # ---- Pre-T3 triage (round 1) ----
            if (triager is not None and notes_writer is not None
                    and source_context is not None):
                remaining = _run_triage_round(
                    triager=triager,
                    notes_writer=notes_writer,
                    config=config,
                    source_ctx=source_context,
                    issues=remaining,
                    triage_round=1,
                    accepted_notes=accepted_notes,
                    notes_per_file=notes_per_file,
                    fixer_candidates=t2_self_report,
                )
                if not remaining:
                    logger.info(
                        "T3 skipped: all residual L3 issues accepted "
                        "as source_inherent")
                    break

            # Lifecycle 2 forbids T3 entirely.
            if t3_disabled:
                logger.error(
                    "T3_EXHAUSTED: lifecycle 2 has %d residual issue(s) "
                    "that need T3 but T3 is disabled",
                    len(remaining))
                lifecycle_signal = "T3_EXHAUSTED"
                return modified_files, t3_self_report, lifecycle_signal

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
            fix_kwargs: dict[str, Any] = dict(
                files=files,
                issues=attempted,
                strategy="standard",
                source_context=source_context,
                attempt_num=attempt,
                max_attempts=max_retries,
            )
            if tier == 3 and prior_attempt_context is not None:
                fix_kwargs["prior_attempt_context"] = prior_attempt_context
            result = fixer_obj.fix(**fix_kwargs)

            # Capture fixer self-reports per tier
            if result.source_inherent_candidates:
                if tier == 2:
                    t2_self_report.update(result.source_inherent_candidates)
                elif tier == 3:
                    t3_self_report.update(result.source_inherent_candidates)

            fingerprint_to_file = {i.fingerprint: i.file for i in attempted}
            for fp in result.resolved_fingerprints:
                f_path = fingerprint_to_file.get(fp)
                if f_path:
                    modified_files.add(f_path)

            if tier == 3:
                # A T3 regen writes the file even when every remaining issue
                # is self-reported as source_inherent — `resolved_fingerprints`
                # alone would miss those files. Union with self-report
                # fingerprints so the lifecycle reset sees them as touched.
                t3_touched_fps = (
                    set(result.resolved_fingerprints)
                    | set(result.source_inherent_candidates.keys())
                )
                t3_files = {
                    fingerprint_to_file.get(fp)
                    for fp in t3_touched_fps
                    if fingerprint_to_file.get(fp)
                }
                for f_path in t3_files:
                    tracker.record_tier_use_on_file(f_path, 3)
                    modified_files.add(f_path)

            remaining = [
                i for i in remaining
                if i.fingerprint not in result.resolved_fingerprints
            ]

            for issue in attempted:
                status = ("resolved"
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
        # After T2 has had its one attempt at adding examples, any
        # remaining coverage_shortage issues are accepted via
        # program-constructed SourceNote. T3 would burn tokens rewriting
        # the whole file without adding source material the novel lacks.
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

        if tier == 3:
            # T3 fired; lifecycle 1 must end here so the outer loop
            # can reset the state machine and start lifecycle 2.
            lifecycle_signal = "T3_TRIGGERED"
            return modified_files, t3_self_report, lifecycle_signal

        if remaining:
            next_tier = tier + 1
            at_cap = [i for i in remaining
                      if _issue_max_tier(i) < next_tier]
            remaining = [i for i in remaining
                         if i.fingerprint not in {x.fingerprint for x in at_cap}]
            if at_cap:
                logger.info(
                    "Capping %d issue(s) at T%d (max_tier reached)",
                    len(at_cap), tier)
            if remaining:
                logger.info("Escalating %d issues from T%d to T%d",
                            len(remaining), tier, next_tier)
        tier += 1

    return modified_files, t3_self_report, lifecycle_signal


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

    ``triage_round`` is 1 for pre-T3 triage and 2 for any post-T3 /
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
    if terminated_by == "T3_EXHAUSTED":
        lines.append("Termination: T3_EXHAUSTED "
                     "(lifecycle 2 needed T3 but T3 is disabled)")
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
