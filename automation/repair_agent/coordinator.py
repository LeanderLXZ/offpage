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

A post-T3 scoped L0–L2 check fails the run immediately if T3 corrupted
the file structure (``T3_CORRUPTED``) — triage is skipped in that case
because mechanical corruption cannot be "source's fault".

Public API:
    run(files, config, ...) → RepairResult
    validate_only(files, ...) → list[Issue]
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from .checkers import CheckerPipeline
from .checkers.json_syntax import JsonSyntaxChecker
from .checkers.schema import SchemaChecker
from .checkers.structural import StructuralChecker
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
    """Three-phase repair: check → fix loop → verify.

    Args:
        importance_map: ``{character_id: importance}`` — raises the
            structural min-examples threshold for main / important
            characters (主角 → 5, 重要配角 → 3, others → 1).
        recorder: optional ``RepairRecorder`` that receives a structured
            JSONL event at each phase / round / issue / fix / triage /
            completion transition. ``None`` disables structured logging.
    """
    def _emit(event: str, **fields: Any) -> None:
        if recorder is not None:
            recorder.write(event, **fields)
    if config is None:
        config = RepairConfig()

    pipeline = _build_pipeline(
        llm_call=llm_call,
        importance_map=importance_map,
    )
    retriever = ContextRetriever()
    fixers = _build_fixers(llm_call=llm_call, retriever=retriever)
    tracker = IssueTracker()

    # Triage — optional, requires source_context to resolve chapters
    triager: Triager | None = None
    notes_writer: NotesWriter | None = None
    if config.triage_enabled and source_context is not None:
        triager = Triager(llm_call=llm_call, retriever=retriever)
        notes_writer = NotesWriter(source_context.work_path)
    accepted_notes: list[SourceNote] = []
    notes_per_file: dict[str, int] = {}

    # =================================================================
    # Phase A — Full check (L0–L3)
    # =================================================================
    logger.info("Phase A: full validation")
    _emit("phase_start", phase="A",
          file_count=len(files), run_semantic=config.run_semantic)
    all_issues = pipeline.run(
        files, run_semantic=config.run_semantic)

    blocking = _filter_blocking(all_issues, config)
    if not blocking:
        logger.info("Phase A: no blocking issues — pass")
        _emit("phase_a_result", blocking=0, total=len(all_issues))
        _emit("complete", status="PASS",
              resolved=0, persisting=0, issues_remaining=0)
        return RepairResult(passed=True, issues=all_issues,
                            report="No blocking issues found.")

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
    t3_corrupted = False

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
            tier_modified, tier_corrupted, tier_t3_cands = (
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
            round_t3_candidates.update(tier_t3_cands)
            if tier_corrupted:
                t3_corrupted = True
                break

        if t3_corrupted:
            logger.error(
                "T3_CORRUPTED — aborting Phase B without triage")
            _emit("t3_corrupted", round=round_num + 1)
            break

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
    # Drop any L0-L2 issue that was already accepted via SourceNote
    # (coverage_shortage). Structural rerun resurfaces them because the
    # JSON wasn't modified; leaving them in would FAIL the stage after
    # a successful accept.
    accepted_fps = {n.issue_fingerprint for n in accepted_notes}
    if accepted_fps:
        final_issues = [
            i for i in final_issues if i.fingerprint not in accepted_fps
        ]

    if t3_corrupted:
        # Already aborted — surface a synthetic marker so the report
        # explains why the run stopped.
        passed = False
        report_text = _build_report(
            final_issues, tracker, passed, t3_corrupted=True,
            accepted_notes=accepted_notes)
        _emit("complete", status="FAIL_T3_CORRUPTED",
              issues_remaining=len(_filter_blocking(final_issues, config)),
              accepted_notes=len(accepted_notes))
        return RepairResult(
            passed=passed,
            issues=final_issues,
            history=tracker.get_history(),
            report=report_text,
            accepted_notes=accepted_notes,
        )

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

    report_text = _build_report(
        final_issues, tracker, passed, t3_corrupted=False,
        accepted_notes=accepted_notes)
    logger.info("Repair complete: %s (%d issues remaining, %d note(s))",
                "PASS" if passed else "FAIL", len(final_blocking),
                len(accepted_notes))
    _emit("complete",
          status="PASS" if passed else "FAIL",
          issues_remaining=len(final_blocking),
          accepted_notes=len(accepted_notes))

    return RepairResult(
        passed=passed,
        issues=final_issues,
        history=tracker.get_history(),
        report=report_text,
        accepted_notes=accepted_notes,
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
) -> tuple[set[str], bool, dict[str, TriageVerdict]]:
    """Run a fixer tier; if retries exhausted, escalate to next tier.

    Returns ``(modified_files, t3_corrupted, t3_candidates)``:
      * ``modified_files`` — file paths touched by at least one
        successful fix in this invocation (feeds the L3 gate).
      * ``t3_corrupted`` — True if a post-T3 scoped L0–L2 check found
        errors. The caller MUST abort Phase B.
      * ``t3_candidates`` — self-reported source_inherent verdicts
        emitted by T3 this round, carried forward to post-gate triage.
    """
    modified_files: set[str] = set()
    remaining = list(issues)
    tier = start_tier
    # T2 self-report verdicts — used as priors for pre-T3 triage.
    t2_self_report: dict[str, TriageVerdict] = {}
    t3_self_report: dict[str, TriageVerdict] = {}
    t3_corrupted = False

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

            # Global T3 cap
            t3_cap = config.retry_policy.t3_max_per_file
            before = len(remaining)
            remaining = [
                i for i in remaining
                if tracker.tier_uses_on_file(i.file, 3) < t3_cap
            ]
            dropped = before - len(remaining)
            if dropped:
                logger.warning(
                    "T3 global cap reached — dropping %d issue(s)", dropped)
            if not remaining:
                break

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
                # alone would miss those files and let the T3 cap + corruption
                # check be bypassed. Union with self-report fingerprints.
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

                # ---- T3 corruption hard-stop ----
                if t3_files:
                    t3_entries = [f for f in files if f.path in t3_files]
                    scoped = pipeline.run_scoped(
                        t3_entries,
                        patched_paths=list(t3_files),
                        max_layer=2)
                    scoped_errors = [i for i in scoped
                                     if i.severity == "error"]
                    if scoped_errors:
                        logger.error(
                            "T3_CORRUPTED: %d L0-L2 error(s) after T3 "
                            "in %d file(s) — aborting",
                            len(scoped_errors), len(t3_files))
                        t3_corrupted = True
                        return (modified_files, t3_corrupted,
                                t3_self_report)

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

    return modified_files, t3_corrupted, t3_self_report


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


def _build_report(issues: list[Issue], tracker: IssueTracker,
                  passed: bool, *, t3_corrupted: bool = False,
                  accepted_notes: list[SourceNote] | None = None) -> str:
    lines = [f"Repair {'PASSED' if passed else 'FAILED'}"]
    if t3_corrupted:
        lines.append("Termination: T3_CORRUPTED "
                     "(post-T3 L0-L2 check found errors)")
    lines.append(f"Final issues: {len(issues)}")

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    lines.append(f"  errors: {len(errors)}, warnings: {len(warnings)}")

    if accepted_notes:
        lines.append(f"Accepted source_inherent notes: {len(accepted_notes)}")
        for n in accepted_notes:
            lines.append(f"  {n.note_id} [{n.discrepancy_type}] "
                         f"{n.file} {n.json_path}")

    history = tracker.get_history()
    if history:
        total_attempts = sum(len(v) for v in history.values())
        lines.append(f"Total repair attempts: {total_attempts}")

    if errors:
        lines.append("\nRemaining errors:")
        for i in errors:
            lines.append(f"  {i}")

    return "\n".join(lines)
