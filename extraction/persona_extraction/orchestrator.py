"""Main orchestrator — drives the full extraction pipeline.

Flow:
  1. Analysis phase (LLM)  → stage plan + candidate characters
  2. User confirmation      → select characters, confirm stage plan, set range
  3. Extraction loop        → for each stage (1+2N parallel):
       a. Git preflight
       b. World + char_snapshot + char_support extraction (1+2N LLM calls)
       c. Programmatic post-processing (memory_digest + stage_catalog)
       d. Repair framework (L0–L3 check → T0–T3 fix loop → final verify).
          Note: this `L0–L3` is the repair framework's checker hierarchy
          (decision #25), NOT the phase 0 JSON-format-repair三档 `L1/L2/L3`
          (decision #40 = regex / LLM-on-broken-JSON / full re-run, used
          only by `_summarize_chunk`). Same字面 L#, different semantics —
          see ai_context/decisions.md #25 + #40 disambiguation notes.
       e. Git commit
  3.5 Cross-stage consistency check (programmatic, zero tokens)
  4. Scene archive (per-chapter parallel, programmatic validation only)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from .core.config import get_config
from ..validation.gates.phase3_5_consistency import run_consistency_check, save_report
from .lifecycle.deferred_repair_log import (
    deferrable_issues,
    write_deferred_repairs,
)
from .lifecycle.failed_lane_log import write_failed_lane_log
from .core.git_utils import (
    branch_exists,
    checkout_main,
    commit_stage,
    create_extraction_branch,
    delete_branch,
    ensure_branch_from_main,
    git_gc_prune_now,
    preflight_check,
    reset_paths,
    squash_merge_to,
)
from .lifecycle.lane_output import (
    baseline_paths,
    expected_lane_dirty_paths,
    expected_lane_names,
    lane_product_path,
    prev_snapshot_slice_dir,
    prev_snapshot_slice_path,
    snapshot_partial_dir,
    snapshot_partial_path,
    verify_lane_output,
)
from .phases.snapshot_merge import (
    MergeError,
    SUB_LANE_NAMES,
    compute_fingerprint,
    derive_chapter_scope,
    merge_partials,
    slice_snapshot_for_lane,
)
from .lifecycle.manifests import (
    read_structure_mode,
    write_works_manifest,
    write_world_manifest,
)
from .core.llm_backend import LLMBackend, LLMResult, run_with_retry
from .phases.post_processing import run_stage_post_processing
from .core.process_guard import PidLock, fmt_memory, get_rss_mb
from .lifecycle.progress import (
    StageEntry,
    StageState,
    ChunkEntry,
    Phase0Progress,
    Phase3Progress,
    PipelineProgress,
    migrate_legacy_progress,
    PHASE_RUNNING,
    _atomic_write_json,
)
from .prompt_builder import (
    build_candidate_characters_prompt,
    build_char_snapshot_prompt,
    build_char_support_prompt,
    build_fixed_relationships_prompt,
    build_foundation_prompt,
    build_identity_prompt,
    build_key_figures_prompt,
    build_stage_plan_prompt,
    build_target_baseline_prompt,
    cleanup_phase1_lane_inputs,
    cleanup_phase2_lane_inputs,
    prepare_phase1_lane_inputs,
    prepare_phase2_lane_inputs,
    build_summarization_prompt,
    build_world_extraction_prompt,
)
from .core.json_repair import try_repair_json_file
from functools import lru_cache as _lru_cache
import jsonschema as _jsonschema


def _load_analysis_schema(name: str) -> _jsonschema.Draft202012Validator:
    from .core.schema_loader import load_schema as _load_schema_inlined
    schema_path = (Path(__file__).resolve().parents[2]
                   / "schemas/analysis" / name)
    schema = _load_schema_inlined(schema_path)
    return _jsonschema.Draft202012Validator(schema)


def _load_world_schema(name: str) -> _jsonschema.Draft202012Validator:
    from .core.schema_loader import load_schema as _load_schema_inlined
    schema_path = (Path(__file__).resolve().parents[2]
                   / "schemas/world" / name)
    schema = _load_schema_inlined(schema_path)
    return _jsonschema.Draft202012Validator(schema)


@_lru_cache(maxsize=1)
def _chunk_validator() -> _jsonschema.Draft202012Validator:
    """Lazy-load schemas/analysis/chapter_summary_chunk.schema.json once."""
    return _load_analysis_schema("chapter_summary_chunk.schema.json")


@_lru_cache(maxsize=1)
def _foundation_validator() -> _jsonschema.Draft202012Validator:
    """Lazy-load schemas/world/foundation.schema.json once (decision #54 —
    foundation 前移到 phase 1，schema 从 schemas/analysis/world_overview.schema.json
    迁移到 schemas/world/foundation.schema.json)."""
    return _load_world_schema("foundation.schema.json")


@_lru_cache(maxsize=1)
def _stage_plan_validator() -> _jsonschema.Draft202012Validator:
    """Lazy-load schemas/analysis/stage_plan.schema.json once."""
    return _load_analysis_schema("stage_plan.schema.json")


# Defensive fallback for `_stage_title_max_length()`. Only used if the
# schema path drifts and lookup fails; logs a WARN so the drift surfaces.
# Per `ai_context/decisions.md` §27b (Bounds-only-in-schema), schema is
# the single source of truth; this fallback exists purely so a malformed
# / missing schema does not crash Phase 1 — the WARN is the signal.
_STAGE_TITLE_FALLBACK_MAX = 80


@_lru_cache(maxsize=1)
def _stage_title_max_length() -> int:
    """Read `stage_title.maxLength` from `stage_plan.schema.json`.

    light_novel mode uses this cap to soft-truncate
    `_build_light_novel_stage_plan` output, preventing adversarial
    long volume_title × original_chapter_title combinations from
    tripping schema gate → infinite Phase 1 retry → FATAL.

    Schema is the authoritative single source per §27b
    (Bounds-only-in-schema); drift falls back to
    `_STAGE_TITLE_FALLBACK_MAX` with a WARN.
    """
    try:
        schema = _stage_plan_validator().schema
        cap = (schema["properties"]["stages"]["items"]
               ["properties"]["stage_title"]["maxLength"])
        if isinstance(cap, int) and cap > 1:
            return cap
        print(f"[WARN] stage_title.maxLength schema lookup returned "
              f"non-positive int {cap!r}; falling back to "
              f"{_STAGE_TITLE_FALLBACK_MAX}.")
    except (KeyError, TypeError, AttributeError) as exc:
        print(f"[WARN] stage_title.maxLength schema lookup failed "
              f"({exc!r}); falling back to {_STAGE_TITLE_FALLBACK_MAX}. "
              f"Check schemas/analysis/stage_plan.schema.json drift.")
    return _STAGE_TITLE_FALLBACK_MAX


@_lru_cache(maxsize=1)
def _candidate_characters_validator() -> _jsonschema.Draft202012Validator:
    """Lazy-load schemas/analysis/candidate_characters.schema.json once."""
    return _load_analysis_schema("candidate_characters.schema.json")


from .core.rate_limit import (
    RateLimitController,
    RateLimitHardStop,
    set_active as set_active_rl,
)
from .phases.scene_archive import run_scene_archive
from .core.run_metrics import set_phase as _set_run_phase
from ..validation.gates.phase2_baseline import (
    load_importance_map,
    validate_baseline,
)
from ..validation.shared.schema_tolerance import validate_with_length_tolerance
from ..repair import (
    FileEntry as RepairFileEntry,
    RepairConfig,
    RepairResult,
    RetryPolicy,
    SourceContext,
    run as run_repair,
)
from ..repair.checkers.phase2_baseline_refs import (
    FixedRelationshipsPartiesChecker,
    FoundationKeyFiguresChecker,
    TargetBaselineKeysChecker,
)
from ..repair.checkers.semantic import SemanticReviewLLMUnavailable
from ..repair.recorder import RepairRecorder

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Progress tracker
# ---------------------------------------------------------------------------

def _fmt_duration(seconds: float) -> str:
    """Format seconds as human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s"


def _phase3_committed_artifacts_present(
    project_root: Path, work_id: str,
) -> bool:
    """Return True iff phase 3 has produced committed stage artifacts.

    Detection signals (any one is sufficient):
      1. ``phase3_stages.json`` carries at least one stage in COMMITTED state
      2. World stage snapshot files exist on disk
      3. Any character stage snapshot files exist on disk

    A True result means a Phase 2 baseline rewrite would cascade-break the
    decision #13 set-equal contract on every existing stage snapshot. The
    caller MUST stop or get explicit confirmation before continuing.
    Decision #56.
    """
    phase3 = Phase3Progress.load(project_root, work_id)
    if phase3 is not None:
        for stage in phase3.stages:
            if stage.state == StageState.COMMITTED:
                return True
    work_dir = project_root / "works" / work_id
    world_snaps = work_dir / "world" / "stage_snapshots"
    if world_snaps.exists() and any(world_snaps.glob("S*.json")):
        return True
    characters_dir = work_dir / "characters"
    if characters_dir.exists():
        for char_dir in characters_dir.iterdir():
            if not char_dir.is_dir():
                continue
            snap_dir = char_dir / "canon" / "stage_snapshots"
            if snap_dir.exists() and any(snap_dir.glob("S*.json")):
                return True
    return False


def _guard_phase2_rewrite_against_phase3(
    project_root: Path, work_id: str, *, context: str,
) -> None:
    """Block phase 2 baseline rewrite when phase 3 committed artifacts exist.

    Phase 2 rewriting ``target_baseline.json`` mutates the target-character
    set that decision #13 set-equal-binds every phase 3 stage_snapshot to;
    silently continuing would leave the new baseline ↔ stale snapshots in
    cross-file hard-fail state on the next phase 3 cross-file validate.

    Daemon path (``sys.stdin.isatty()`` False) → hard stop ``sys.exit(1)``
    after printing the cleanup list. Foreground → same cleanup list plus
    ``input("Continue and overwrite phase 3 artifacts? [y/N]: ")``; any
    answer other than ``y`` exits 1. Decision #56.
    """
    if not _phase3_committed_artifacts_present(project_root, work_id):
        return
    work_root = project_root / "works" / work_id
    print(
        "\n[GUARD] Phase 2 baseline rewrite blocked — phase 3 committed "
        f"artifacts detected ({context}).\n"
        "  Decision #13 set-equal contract binds every existing phase 3 "
        "stage_snapshot to the current `target_baseline.targets[]` set; "
        "overwriting baseline now would leave them in cross-file hard-fail "
        "state.\n"
        "\n  Cleanup required before rerunning Phase 2 (decision #56):\n"
        f"    - {work_root}/world/stage_snapshots/\n"
        f"    - {work_root}/characters/*/canon/stage_snapshots/\n"
        f"    - {work_root}/characters/*/canon/memory_timeline/\n"
        f"    - {work_root}/characters/*/canon/memory_digest.jsonl\n"
        f"    - {work_root}/world/world_event_digest.jsonl\n"
        f"    - {work_root}/analysis/progress/phase3_stages.json\n"
        "  After cleanup, rerun with --resume.")
    if not sys.stdin.isatty():
        print("[GUARD] Daemon mode (non-interactive stdin) — hard stop.")
        sys.exit(1)
    try:
        answer = input(
            "Continue and overwrite phase 3 artifacts? [y/N]: "
        ).strip().lower()
    except EOFError:
        answer = ""
    if answer != "y":
        print("[GUARD] User declined — exiting without modifying baseline.")
        sys.exit(1)
    print("[GUARD] User confirmed — proceeding with baseline rewrite. "
          "Phase 3 cascade is now the user's responsibility.")


# stage_snapshot.schema.json::schema_version is a required string; the
# extractor LLM has historically written "1.0" so we keep the same shape
# when injecting the value during sub-lane merge (decision #55).
_SNAPSHOT_SCHEMA_VERSION = "1.0"

def _find_previous_committed_stage_for_sub_lanes(
    stages: list[StageEntry], current: StageEntry,
) -> StageEntry | None:
    """Mirror of ``prompt_builder._find_previous_committed_stage`` for use
    in ``_run_char_snapshot_sub_lanes`` (decision #55 — 4-lane prev
    slice). Kept local to avoid importing a private helper across modules;
    the logic is trivially 4 lines."""
    for b in reversed(stages):
        if b.stage_id == current.stage_id:
            continue
        if b.state.value == "committed":
            return b
    return None


def _repair_slug(file_path: str) -> str:
    """Compact filesystem-safe slug for a repair target path.

    Used in per-file JSONL filenames under progress/. Shape:
    ``<sanitized-last-2-segments>_<8-char-hash>``. The hash disambiguates
    paths whose segments collapse to the same ASCII skeleton (common for
    Chinese work_id / character_id where every non-ASCII char becomes
    ``_``); the readable prefix keeps the filename greppable.
    """
    import hashlib
    parts = [p for p in file_path.replace("\\", "/").split("/") if p]
    tail = "_".join(parts[-2:]) if parts else "file"
    safe = "".join(
        c if (c.isalnum() or c in "._-") else "_" for c in tail
    )[:60] or "file"
    digest = hashlib.md5(file_path.encode("utf-8")).hexdigest()[:8]
    return f"{safe}_{digest}"


class ProgressTracker:
    """Tracks timing and progress across the extraction loop."""

    # Step names used as keys for per-step duration tracking
    STEP_EXTRACTION = "extraction"
    STEP_VALIDATION = "validation"
    STEP_REVIEW = "review"
    STEP_FIX = "fix"
    STEP_COMMIT = "commit"

    def __init__(self, total_stages: int, completed_before: int):
        self.total = total_stages
        self.completed_before = completed_before
        self.completed_this_run = 0
        self.loop_start = time.monotonic()
        self.stage_start: float = 0.0
        self.step_start: float = 0.0
        self.stage_durations: list[float] = []
        # Per-step duration history (for step-level ETA)
        self.step_durations: dict[str, list[float]] = {
            self.STEP_EXTRACTION: [],
            self.STEP_VALIDATION: [],
            self.STEP_REVIEW: [],
            self.STEP_FIX: [],
            self.STEP_COMMIT: [],
        }

    @property
    def completed(self) -> int:
        return self.completed_before + self.completed_this_run

    @property
    def remaining(self) -> int:
        return self.total - self.completed

    @property
    def avg_stage_seconds(self) -> float:
        if not self.stage_durations:
            return 0.0
        return sum(self.stage_durations) / len(self.stage_durations)

    def avg_step_seconds(self, step_name: str) -> float:
        durations = self.step_durations.get(step_name, [])
        if not durations:
            return 0.0
        return sum(durations) / len(durations)

    def record_step(self, step_name: str) -> None:
        """Record the elapsed time of the current step under step_name."""
        duration = time.monotonic() - self.step_start
        if step_name in self.step_durations:
            self.step_durations[step_name].append(duration)

    def start_stage(self) -> None:
        self.stage_start = time.monotonic()

    def finish_stage(self) -> None:
        duration = time.monotonic() - self.stage_start
        self.stage_durations.append(duration)
        self.completed_this_run += 1

    def start_step(self) -> None:
        self.step_start = time.monotonic()

    def step_elapsed(self) -> str:
        return _fmt_duration(time.monotonic() - self.step_start)

    def print_stage_header(self, stage: Any) -> None:
        """Print stage header with overall and step-level progress."""
        n = self.completed + 1
        elapsed_total = time.monotonic() - self.loop_start
        avg = self.avg_stage_seconds

        print(f"\n{'━' * 60}")
        title_suffix = f" — {stage.stage_title}" if stage.stage_title else ""
        print(f"  [{n}/{self.total}] {stage.stage_id}{title_suffix}")
        print(f"  Chapters: {stage.chapters}  |  "
              f"State: {stage.state.value}")

        parts = [f"Elapsed: {_fmt_duration(elapsed_total)}"]
        if avg > 0:
            parts.append(f"Avg: {_fmt_duration(avg)}/stage")
            eta = avg * self.remaining
            parts.append(f"ETA: {_fmt_duration(eta)}")
        orch_mem = fmt_memory(get_rss_mb(os.getpid()))
        parts.append(f"Mem: {orch_mem}")
        print(f"  {' | '.join(parts)}")

        # Step-level estimates (only show if we have history)
        step_parts: list[str] = []
        for label, key in [("Extract", self.STEP_EXTRACTION),
                           ("Validate", self.STEP_VALIDATION),
                           ("Review", self.STEP_REVIEW),
                           ("Fix", self.STEP_FIX),
                           ("Commit", self.STEP_COMMIT)]:
            avg_s = self.avg_step_seconds(key)
            if avg_s > 0:
                step_parts.append(f"{label} ~{_fmt_duration(avg_s)}")
        if step_parts:
            print(f"  Step estimates: {' | '.join(step_parts)}")

        print(f"{'━' * 60}")

    def print_step(self, step: int, total: int, label: str) -> None:
        """Print step start."""
        print(f"  [{step}/{total}] {label}...")

    def print_step_done(self, step: int, total: int, label: str,
                        detail: str = "") -> None:
        """Print step completion with elapsed time."""
        elapsed = self.step_elapsed()
        suffix = f" ({detail})" if detail else ""
        print(f"  [{step}/{total}] {label} done  [{elapsed}]{suffix}")

    def print_summary(self) -> None:
        """Print final summary."""
        elapsed = time.monotonic() - self.loop_start
        print(f"\n{'=' * 60}")
        print("  Extraction Summary")
        print(f"{'=' * 60}")
        print(f"  Completed this run: {self.completed_this_run}")
        print(f"  Total completed: {self.completed}/{self.total}")
        print(f"  Total elapsed: {_fmt_duration(elapsed)}")
        if self.stage_durations:
            print(f"  Avg per stage: "
                  f"{_fmt_duration(self.avg_stage_seconds)}")
            fastest = min(self.stage_durations)
            slowest = max(self.stage_durations)
            print(f"  Fastest: {_fmt_duration(fastest)}  |  "
                  f"Slowest: {_fmt_duration(slowest)}")

        # Step breakdown
        step_lines: list[str] = []
        for label, key in [("Extraction", self.STEP_EXTRACTION),
                           ("Validation", self.STEP_VALIDATION),
                           ("Review", self.STEP_REVIEW),
                           ("Fix", self.STEP_FIX),
                           ("Commit", self.STEP_COMMIT)]:
            durations = self.step_durations.get(key, [])
            if durations:
                avg_s = sum(durations) / len(durations)
                step_lines.append(f"{label}: {_fmt_duration(avg_s)}")
        if step_lines:
            print(f"  Step avg: {' | '.join(step_lines)}")

        print(f"{'=' * 60}")


class ExtractionOrchestrator:
    """Drives the full automated extraction pipeline."""

    def __init__(
        self,
        project_root: Path,
        work_id: str,
        backend: LLMBackend,
        reviewer_backend: LLMBackend | None = None,
        chunk_size: int = 20,
        max_runtime_minutes: int = 0,
        start_phase: str = "auto",
        concurrency: int = 12,
        char_snapshot_sub_lanes: bool | None = None,
    ):
        self.project_root = project_root
        self.work_id = work_id
        self.backend = backend
        self.reviewer_backend = reviewer_backend or backend
        self.chunk_size = chunk_size
        self.max_runtime_minutes = max_runtime_minutes
        self.start_phase = start_phase
        self.concurrency = concurrency
        # ``None`` → inherit ``[phase3].char_snapshot_sub_lanes`` from
        # the loaded config; ``True`` / ``False`` → CLI override
        # (``--[no-]char-snapshot-sub-lanes``). Decision #55.
        self.char_snapshot_sub_lanes: bool = (
            char_snapshot_sub_lanes
            if char_snapshot_sub_lanes is not None
            else get_config().phase3.char_snapshot_sub_lanes
        )
        self.pipeline: PipelineProgress | None = None
        self.phase3: Phase3Progress | None = None
        self._interrupted = False
        self._start_time = time.monotonic()
        self._lock = PidLock(project_root, work_id)

        # Per-work rate-limit controller (§11.13). Installed as the
        # process-wide singleton so deeply-nested run_with_retry calls
        # (json_repair, scene_archive, repair framework) find it.
        work_root = project_root / "works" / work_id
        self._rate_limit = RateLimitController(work_root)
        set_active_rl(self._rate_limit)

        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum: int, frame: Any) -> None:
        logger.warning("Signal %d received. Saving progress and exiting...",
                       signum)
        self._interrupted = True
        if self.phase3:
            self.phase3.save(self.project_root)
        if self.pipeline:
            self.pipeline.save(self.project_root)
        self._lock.release()
        sys.exit(130)

    def _check_runtime_limit(self) -> bool:
        """Return True if max runtime exceeded.

        Time spent inside ``RateLimitController.wait_if_paused`` is excluded
        from the elapsed accounting (§11.13.7) so a long token-limit pause
        does not falsely trip the budget.
        """
        if self.max_runtime_minutes <= 0:
            return False
        elapsed_s = (time.monotonic() - self._start_time)
        elapsed_s -= self._rate_limit.paused_seconds_total
        elapsed_min = max(0.0, elapsed_s) / 60
        if elapsed_min >= self.max_runtime_minutes:
            print(f"\n[TIMEOUT] Max runtime ({self.max_runtime_minutes}min) "
                  f"exceeded after {elapsed_min:.0f}min "
                  f"(paused excluded: "
                  f"{self._rate_limit.paused_seconds_total / 60:.1f}min). "
                  f"Stopping gracefully.")
            return True
        return False

    def acquire_lock(self) -> bool:
        """Acquire PID lock. Prints error and returns False if held."""
        existing = self._lock.is_held()
        if existing:
            pid = existing.get("pid", "?")
            started = existing.get("started", "?")
            mem = fmt_memory(get_rss_mb(pid)) if isinstance(pid, int) else "?"
            print("[ERROR] Another extraction is already running:")
            print(f"  PID: {pid}  Started: {started}  Mem: {mem}")
            print("  If the process is dead, remove the lock:")
            print(f"  rm \"{self._lock.lock_path}\"")
            return False
        if not self._lock.acquire():
            print("[ERROR] Failed to acquire lock.")
            return False
        return True

    def release_lock(self) -> None:
        self._lock.release()

    # ------------------------------------------------------------------
    # Phase 0: Chapter summarization (chunk-based)
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk_passes_full_check(
        output_path: Path,
        expected: int,
        *,
        start_ch: int | None = None,
        end_ch: int | None = None,
    ) -> tuple[bool, str]:
        """Verify chunk file is structurally complete: exists + valid JSON
        + schema-passing + chapter set equal to the expected range.

        Strict equality (decision-#58 H3): the chapter set extracted from
        ``summaries[].chapter`` must equal exactly
        ``{f"C{i:04d}" for i in range(start_ch, end_ch + 1)}`` — neither
        under-count nor over-count nor wrong-chapter sneaks past. The chunk
        schema only enforces ``^C[0-9]{4}$`` on each item and has no
        uniqueness / range knowledge.

        When ``start_ch`` / ``end_ch`` are omitted (e.g. legacy callers),
        falls back to the previous ``count == expected`` check to stay
        backwards compatible.

        Single source of truth for "chunk done"; called from skip path,
        final gate, and reconcile_with_disk so a partial / stale file
        cannot pass any one of them.
        """
        if not output_path.exists():
            return False, "missing"
        data = _load_json(output_path)
        if data is None:
            return False, "json parse failed"
        errs = list(_chunk_validator().iter_errors(data))
        if errs:
            first = errs[0]
            err_path = "/".join(str(p) for p in first.absolute_path) or "<root>"
            return False, f"schema fail @ {err_path}: {first.message[:80]}"
        summaries = data.get("summaries", [])
        count = len(summaries)
        if count != expected:
            tag = "partial" if count < expected else "over"
            return False, f"{tag} {count}/{expected}"
        if start_ch is not None and end_ch is not None:
            expected_set = {f"C{i:04d}" for i in range(start_ch, end_ch + 1)}
            actual_set = {s.get("chapter", "") for s in summaries}
            if actual_set != expected_set:
                missing = sorted(expected_set - actual_set)
                extra = sorted(actual_set - expected_set)
                bits = []
                if missing:
                    bits.append(f"missing={missing[:5]}")
                if extra:
                    bits.append(f"extra={extra[:5]}")
                return False, "chapter set mismatch: " + " ".join(bits)
        return True, ""

    def _run_recovery_sweep(
        self,
        phase0: "Phase0Progress",
        summaries_dir: Path,
        total_chunks: int,
        chunks: list[tuple[int, int, int]],
    ) -> None:
        """Recovery sweep for chunks that hit timeout or max_turns
        (decision #49).

        Identifies failed chunks where the error matches ``'timed out'``
        or ``'error_max_turns'`` and ``recovery_attempted == False``,
        then reruns each via ``_summarize_chunk`` with
        ``_recovery_effort = [phase0].recovery_effort`` (default
        ``'high'``). Concurrency reuses ``self.concurrency`` (the same
        ThreadPool size as the main phase 0 pass). ``recovery_attempted``
        is set to True regardless of success — ``--resume`` skips
        already-swept chunks so we never救火-loop.

        ``chunks`` is the full ``(idx, start, end)`` list from
        ``run_summarization``; needed to map ``chunk_id`` → chapter
        range for ``_summarize_chunk``.
        """
        recovery_effort = get_config().phase0.recovery_effort

        # Filter candidates: failed + error matches timeout/max_turns
        # + not yet swept.
        candidates: list[tuple[int, int, int]] = []
        chunk_by_idx = {idx: (start, end) for idx, start, end in chunks}
        for chunk_id, entry in sorted(phase0.chunks.items()):
            if entry.state != "failed":
                continue
            if entry.recovery_attempted:
                continue
            err = (entry.error_message or "").lower()
            if "timed out" not in err and "error_max_turns" not in err:
                continue
            try:
                idx = int(chunk_id.split("_")[-1])
            except ValueError:
                continue
            rng = chunk_by_idx.get(idx)
            if rng is None:
                continue
            candidates.append((idx, rng[0], rng[1]))

        if not candidates:
            return

        print("\n" + "=" * 60)
        print(f"  Phase 0 Recovery Sweep "
              f"(effort={recovery_effort}, {len(candidates)} chunk(s))")
        print("=" * 60)

        sweep_completed = 0
        sweep_failed = 0
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {}
            for idx, start, end in candidates:
                future = executor.submit(
                    self._summarize_chunk,
                    idx, total_chunks, start, end, summaries_dir,
                    _recovery_effort=recovery_effort,
                )
                futures[future] = (idx, start, end)

            for future in as_completed(futures):
                idx, start, end = futures[future]
                chunk_id = f"chunk_{idx:03d}"
                try:
                    _, success, msg = future.result()
                except RateLimitHardStop:
                    # Cancel siblings so the implicit ``with`` exit
                    # ``shutdown(wait=True)`` doesn't block on still-
                    # sleeping recovery chunks.
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
                except Exception as exc:  # noqa: BLE001
                    success, msg = False, str(exc)

                entry = phase0.chunks.get(chunk_id)
                if entry is None:
                    continue
                # Mark recovery_attempted=True regardless of outcome —
                # this is the single-shot救火 contract.
                entry.recovery_attempted = True
                entry.retry_count += 1
                entry.last_updated = ""  # save() updates timestamp
                if success:
                    sweep_completed += 1
                    entry.state = "done"
                    entry.error_message = ""
                    print(f"    [OK] {chunk_id} "
                          f"(C{start:04d}-C{end:04d}) — recovery PASS  "
                          f"({sweep_completed}/{len(candidates)})")
                else:
                    sweep_failed += 1
                    entry.state = "failed"
                    entry.error_message = (
                        f"recovery (effort={recovery_effort}) failed: "
                        f"{(msg or 'unknown')[:400]}"
                    )
                    print(f"    [FAIL] {chunk_id}: {(msg or '')[:120]}")
                phase0.save(self.project_root)

        print(f"\n  Recovery sweep done: {sweep_completed}/{len(candidates)} "
              f"recovered, {sweep_failed} still failed")

    def _summarize_chunk(
        self,
        idx: int,
        total_chunks: int,
        start: int,
        end: int,
        summaries_dir: Path,
        *,
        _is_l3_retry: bool = False,
        _prior_error: str = "",
        _recovery_effort: str | None = None,
    ) -> tuple[int, bool, str]:
        """Process a single summarization chunk.

        Returns (chunk_index, success, message).

        If L1+L2 JSON repair fails or schema validation fails, and this is
        not already an L3 retry, the chunk is automatically re-run once from
        scratch (L3) with the previous error injected as ``prior_error`` so
        the LLM is told what to fix.

        ``_recovery_effort`` (decision #49): per-call effort override
        propagated to ``run_with_retry`` → ``LLMBackend.run`` → claude -p
        ``--effort``. Used by ``_run_recovery_sweep`` to retry timed-out
        chunks with effort=high without swapping the backend instance.
        ``None`` = use backend default. Also propagates into the L3 retry
        recursive call so both attempts within the sweep use the same
        downgraded effort.
        """
        output_path = summaries_dir / f"chunk_{idx:03d}.json"

        prompt = build_summarization_prompt(
            self.project_root, self.work_id,
            idx, total_chunks, start, end,
            prior_error=_prior_error)

        result = run_with_retry(
            self.backend, prompt,
            timeout_seconds=get_config().phase0.summarize_timeout_s,
            lane_name=f"summarize[chunk_{idx:03d}]",
            effort=_recovery_effort,
        )

        if not result.success:
            return idx, False, result.error or "LLM call failed"

        # Verify output was written
        if not output_path.exists():
            return idx, False, "Output file not created"

        data = _load_json(output_path)
        if data is None:
            # Try L1 + L2 repair
            ok, desc = try_repair_json_file(
                output_path,
                backend=self.backend,
                expected_key="summaries",
            )
            if ok:
                data = _load_json(output_path)
            else:
                output_path.unlink(missing_ok=True)
                # L3: full re-run (once) with prior_error injected
                if not _is_l3_retry:
                    logger.info("L3 full re-run for chunk_%03d (json fail: %s)",
                                idx, desc)
                    return self._summarize_chunk(
                        idx, total_chunks, start, end, summaries_dir,
                        _is_l3_retry=True,
                        _prior_error=f"JSON 解析失败: {desc}",
                        _recovery_effort=_recovery_effort,
                    )
                return idx, False, f"JSON repair failed (L3 also failed): {desc}"

        # JSON Schema gate (schemas/analysis/chapter_summary_chunk.schema.json)
        # Schema enforces all bounds + additionalProperties=false; exact
        # numbers live in the schema. Fail → L3 retry with prior_error.
        schema_errs = list(_chunk_validator().iter_errors(data))
        if schema_errs:
            first = schema_errs[0]
            err_path = "/".join(str(p) for p in first.absolute_path) or "<root>"
            err_summary = f"{err_path}: {first.message[:120]}"
            if not _is_l3_retry:
                output_path.unlink(missing_ok=True)
                logger.info("L3 full re-run for chunk_%03d (schema fail: %s)",
                            idx, err_summary)
                return self._summarize_chunk(
                    idx, total_chunks, start, end, summaries_dir,
                    _is_l3_retry=True,
                    _prior_error=(f"Schema 校验失败（共 {len(schema_errs)} 处，"
                                  f"首条：{err_summary}）"),
                    _recovery_effort=_recovery_effort,
                )
            # L3 strict retry exhausted — try length-bound tolerance gate
            # (decision #48) before declaring failure. Accept ONLY if all
            # surviving violations are minLength/maxLength.
            ok_tol, _tol_errs = validate_with_length_tolerance(
                data, _chunk_validator().schema)
            if ok_tol:
                logger.info(
                    "Length-bound tolerance gate accepted chunk_%03d "
                    "(strict-fail-only-on-length): %s", idx, err_summary)
                return idx, True, ""
            output_path.unlink(missing_ok=True)
            return idx, False, (f"Schema validation failed (L3 also failed): "
                                f"{err_summary}")

        count = len(data.get("summaries", [])) if data else 0
        expected = end - start + 1
        if count < expected:
            output_path.unlink(missing_ok=True)
            if not _is_l3_retry:
                logger.info("L3 full re-run for chunk_%03d (partial: %d/%d)",
                            idx, count, expected)
                return self._summarize_chunk(
                    idx, total_chunks, start, end, summaries_dir,
                    _is_l3_retry=True,
                    _prior_error=(f"章节摘要不完整（{count}/{expected}）。"
                                  f"必须为 chapter C{start:04d}-C{end:04d} 的"
                                  f"每一章都生成一条 summaries[] 条目，"
                                  f"不得跳过任何章节。"),
                    _recovery_effort=_recovery_effort,
                )
            return idx, False, (f"Partial chunk (L3 also failed): "
                                f"{count}/{expected} summaries")

        return idx, True, ""

    def _run_char_snapshot_sub_lanes(
        self,
        *,
        pipeline: PipelineProgress,
        stage: StageEntry,
        stages: list[StageEntry] | None,
        character_id: str,
        work_root: Path,
        feedback: str = "",
        log_lane_failure: Callable[[str, str, int],
                                   Callable[[LLMResult, int], None]]
                          | None = None,
    ) -> LLMResult:
        """Run 4 parallel sub-lane LLM calls for one character snapshot +
        merge programmatically (decision #55).

        Writes ``.partial/{stage_id}_{sub_lane}.json`` files via the
        sub-lane prompts (each one's ``output_relative_path`` placeholder
        points to its own partial), then loads the four partials and
        calls ``snapshot_merge.merge_partials`` to weld them into a
        single ``stage_snapshots/{stage_id}.json``. On success returns a
        positive ``LLMResult`` whose ``text`` field carries the
        file-level fingerprint (used by callers that wire it into the
        repair framework accept list); on failure returns a negative
        ``LLMResult`` with ``error`` describing which gate tripped.

        ``log_lane_failure`` may
        be ``None`` (repair path) or the closure-built
        ``_log_lane_failure`` (extraction path); each sub-lane uses its
        own ``f"char_snapshot:{cid}:{sub_lane}"`` lane name for failure
        logging so the per-sub-lane stdout / stderr is recoverable.
        """
        partial_dir = snapshot_partial_dir(work_root, character_id)
        partial_dir.mkdir(parents=True, exist_ok=True)

        # R3 .partial 残留清理 — drop any pre-existing partials for this
        # stage before the new attempt so a half-written ``.partial`` file
        # from a previous run can't bleed into the merge.
        self._clear_snapshot_partials(work_root, character_id, stage.stage_id)

        # Prev snapshot 4-way slice (decision #55): R3 pre-clear + fresh
        # write so each sub-lane reads only its allocated field projection
        # of the prev stage's snapshot, not the full ~30 KB file. Re-runs
        # within one stage (repair-triggered sub-lane regen) re-derive the
        # slices from whatever prev snapshot is on disk now — so a
        # repair framework rewrite of prev is reflected the next time we
        # re-extract.
        prev_stage = _find_previous_committed_stage_for_sub_lanes(
            stages or [], stage)
        if prev_stage is not None:
            self._clear_prev_snapshot_slices(
                work_root, character_id, prev_stage.stage_id)
            self._write_prev_snapshot_slices(
                work_root, character_id, prev_stage.stage_id)

        combined_feedback = feedback

        sub_lane_results: dict[str, LLMResult] = {}
        sub_lane_errors: dict[str, str] = {}
        hard_stop: RateLimitHardStop | None = None

        def _run_one_sub_lane(sub_lane: str) -> tuple[str, LLMResult]:
            prompt = build_char_snapshot_prompt(
                self.project_root, pipeline, stage, character_id,
                stages=stages,
                reviewer_feedback=combined_feedback,
                lane_scope=sub_lane,
            )
            lane_name = f"char_snapshot:{character_id}:{sub_lane}"
            on_failure = (
                log_lane_failure(
                    "char_snapshot",
                    f"{character_id}:{sub_lane}",
                    len(prompt))
                if log_lane_failure is not None else None
            )
            res = run_with_retry(
                self.backend, prompt,
                timeout_seconds=get_config().phase3.extraction_timeout_s,
                lane_name=lane_name,
                on_failure=on_failure,
            )
            return sub_lane, res

        # Pre-launch token-limit gate — block here if the controller
        # already recorded a pause (mirrors the parent extraction pool).
        self._rate_limit.wait_if_paused()

        with ThreadPoolExecutor(max_workers=len(SUB_LANE_NAMES)) as pool:
            futures = {
                pool.submit(_run_one_sub_lane, name): name
                for name in SUB_LANE_NAMES
            }
            try:
                for fut in as_completed(futures):
                    sub_lane, res = fut.result()
                    if res.success:
                        sub_lane_results[sub_lane] = res
                    else:
                        sub_lane_errors[sub_lane] = (
                            res.error or "unknown")
            except RateLimitHardStop as exc:
                # R2 — cancel sibling sub-lanes, re-raise so the outer
                # pool / CLI propagates exit 2. Partial files on disk are
                # preserved for the next ``--resume`` (the next sub-lane
                # batch starts with ``_clear_snapshot_partials`` so stale
                # partials cannot bleed into the fresh attempt).
                hard_stop = exc
                pool.shutdown(wait=False, cancel_futures=True)

        if hard_stop is not None:
            raise hard_stop

        def _on_failure_cleanup() -> None:
            """Clear .partial/ + .partial_prev/ for this (char, stage)
            on any sub-lane / merge failure path. ``prev_stage`` is
            captured from the enclosing scope; no-op when there is no
            committed prev stage (S001). Slices on hard-stop paths are
            intentionally NOT cleared (next ``--resume`` regenerates)."""
            self._clear_snapshot_partials(
                work_root, character_id, stage.stage_id)
            if prev_stage is not None:
                self._clear_prev_snapshot_slices(
                    work_root, character_id, prev_stage.stage_id)

        if sub_lane_errors:
            _on_failure_cleanup()
            joined = "; ".join(
                f"{name}: {msg}" for name, msg in sub_lane_errors.items())
            if len(joined) > 2000:
                joined = joined[:2000] + "...[truncated]"
            return LLMResult(
                success=False,
                text="",
                error=f"sub-lane extraction failed — {joined}",
            )

        # All sub-lane LLM calls succeeded; load partials + merge.
        partials: dict[str, dict[str, Any]] = {}
        for sub_lane in SUB_LANE_NAMES:
            path = snapshot_partial_path(
                work_root, character_id, stage.stage_id, sub_lane)
            if not path.exists():
                _on_failure_cleanup()
                return LLMResult(
                    success=False, text="",
                    error=(
                        f"sub-lane {sub_lane}: partial output file "
                        f"missing at {path}"),
                )
            try:
                partials[sub_lane] = json.loads(
                    path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                _on_failure_cleanup()
                return LLMResult(
                    success=False, text="",
                    error=(
                        f"sub-lane {sub_lane}: partial JSON unreadable "
                        f"at {path}: {exc}"),
                )

        baseline_keys = self._load_baseline_keys(work_root, character_id)
        if baseline_keys is None:
            logger.error(
                "sub-lane merge aborted for %s/%s: target_baseline.json "
                "missing or unreadable (phase 2 should have produced it; "
                "check works/%s/characters/%s/canon/target_baseline.json)",
                character_id, stage.stage_id, pipeline.work_id, character_id)
            _on_failure_cleanup()
            return LLMResult(
                success=False, text="",
                error=(
                    f"target_baseline.json missing or unreadable for "
                    f"{character_id}; cannot run sub-lane merge D4 "
                    f"pre-flight (decision #13)"),
            )

        try:
            merged = merge_partials(
                partials,
                schema_version=_SNAPSHOT_SCHEMA_VERSION,
                work_id=pipeline.work_id,
                character_id=character_id,
                stage_id=stage.stage_id,
                stage_title=stage.stage_title or stage.stage_id,
                chapter_scope=derive_chapter_scope(stage.chapters),
                baseline_keys=baseline_keys,
            )
        except MergeError as exc:
            _on_failure_cleanup()
            return LLMResult(
                success=False, text="",
                error=f"sub-lane merge failed: {exc}",
            )

        final_path = lane_product_path(
            work_root, stage.stage_id, f"snapshot:{character_id}")
        _atomic_write_json(final_path, merged)

        # Cleanup partials after a successful merge — they are no longer
        # needed; the final file is the canonical artifact.
        self._clear_snapshot_partials(
            work_root, character_id, stage.stage_id)

        fingerprint = compute_fingerprint(merged)
        logger.info(
            "char_snapshot sub-lane merge complete: %s/%s fingerprint=%s",
            character_id, stage.stage_id, fingerprint[:16])
        return LLMResult(success=True, text=fingerprint, error="")

    def _clear_snapshot_partials(
        self,
        work_root: Path,
        character_id: str,
        stage_id: str,
    ) -> None:
        """Delete ``.partial/{stage_id}_*.json`` for one (character, stage).

        Used (1) before launching a fresh sub-lane batch, (2) after a
        successful merge (cleanup), and (3) on any sub-lane / merge
        failure (R3). Idempotent — missing files are silently OK.
        """
        partial_dir = snapshot_partial_dir(work_root, character_id)
        if not partial_dir.exists():
            return
        for name in SUB_LANE_NAMES:
            p = snapshot_partial_path(
                work_root, character_id, stage_id, name)
            # ``missing_ok=True`` already absorbs the FileNotFoundError
            # idempotent case; remaining OSError = permission / read-only
            # mount / IO error → fail loudly so the caller sees the real
            # cause instead of silently moving on to the next attempt.
            p.unlink(missing_ok=True)

    def _write_prev_snapshot_slices(
        self,
        work_root: Path,
        character_id: str,
        prev_stage_id: str,
    ) -> None:
        """Slice the previous stage's snapshot into per-lane slice files
        for sub-lane consumption (decision #55 — 4-lane prev slice).

        Writes ``.partial_prev/{char_id}/{prev_stage_id}_{sub_lane}.json``
        for each sub-lane via ``slice_snapshot_for_lane`` — unconditional
        overwrite (R3 pre-clear runs first; this method assumes the dir
        has been cleared so the freshly written slices stay in sync with
        the on-disk prev snapshot, even if repair framework rewrote the prev
        file since the previous slice run).

        No-op when the prev snapshot file is missing (S001 has no prev →
        prompt_builder treats missing slice as "no delta reference",
        same as today's missing prev file).
        """
        prev_snapshot_path = (work_root / "characters" / character_id
                              / "canon" / "stage_snapshots"
                              / f"{prev_stage_id}.json")
        if not prev_snapshot_path.exists():
            return
        try:
            full = json.loads(prev_snapshot_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "prev snapshot slice skipped for %s/%s: cannot read %s (%s); "
                "sub-lanes will run without prev reference for this stage",
                character_id, prev_stage_id, prev_snapshot_path, exc)
            return

        slice_dir = prev_snapshot_slice_dir(work_root, character_id)
        try:
            slice_dir.mkdir(parents=True, exist_ok=True)
            for name in SUB_LANE_NAMES:
                projected = slice_snapshot_for_lane(full, name)
                path = prev_snapshot_slice_path(
                    work_root, character_id, prev_stage_id, name)
                path.write_text(
                    json.dumps(projected, ensure_ascii=False, indent=2),
                    encoding="utf-8")
        except OSError as exc:
            # permission denied / disk full / read-only mount — degrade
            # gracefully (mirrors the prev snapshot read-failure path
            # above, line 1254-1261): warning + return so sub-lanes can
            # still run, falling back to the full prev snapshot via
            # ``_format_prev_char_snapshot_reference`` /
            # ``_build_char_snapshot_read_list`` (which detect the
            # missing slice files and revert to the full prev path).
            logger.warning(
                "prev snapshot slice write failed for %s/%s under %s "
                "(%s); sub-lanes will fall back to the full prev "
                "snapshot for this stage",
                character_id, prev_stage_id, slice_dir, exc)

    def _clear_prev_snapshot_slices(
        self,
        work_root: Path,
        character_id: str,
        prev_stage_id: str,
    ) -> None:
        """Delete ``.partial_prev/{char_id}/{prev_stage_id}_*.json`` for
        one (character, prev_stage) pair (decision #55).

        Used (1) before writing a fresh slice batch (R3 pre-clear), (2)
        after repair completes + before ``[5/5] Git commit`` (slice is
        ephemeral, no debugging value once stage commits — prev snapshot
        is already in git history), and (3) on any sub-lane / merge
        failure path. Idempotent — missing files are silently OK.
        """
        slice_dir = prev_snapshot_slice_dir(work_root, character_id)
        if not slice_dir.exists():
            return
        for name in SUB_LANE_NAMES:
            p = prev_snapshot_slice_path(
                work_root, character_id, prev_stage_id, name)
            p.unlink(missing_ok=True)

    def _load_baseline_keys(
        self,
        work_root: Path,
        character_id: str,
    ) -> set[str] | None:
        """Read ``target_baseline.targets[].target_character_id`` as a set.

        Returns ``None`` when the file is missing or unparseable — caller
        treats this as a hard merge-time failure (decision #13).
        """
        path = (work_root / "characters" / character_id / "canon"
                / "target_baseline.json")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        targets = data.get("targets") if isinstance(data, dict) else None
        if not isinstance(targets, list):
            return None
        keys: set[str] = set()
        for entry in targets:
            if isinstance(entry, dict):
                cid = entry.get("target_character_id")
                if isinstance(cid, str) and cid:
                    keys.add(cid)
        return keys

    def _extraction_output_exists(
        self,
        target_characters: list[str],
        stage: StageEntry,
    ) -> bool:
        """Check if extraction output is fully present and parseable for a stage.

        Returns True iff **every** lane's per-stage product file exists and
        parses as JSON. Missing or corrupt files mean extraction is
        incomplete — skipping to post-processing would silently drop the
        absent lane.
        """
        work_dir = self.project_root / "works" / self.work_id
        for lane_name in expected_lane_names(target_characters):
            ok, _why = verify_lane_output(work_dir, stage.stage_id, lane_name)
            if not ok:
                return False
        return True

    def _collect_stage_files(
        self,
        work_dir: Path,
        stage_id: str,
        stage_num: int,
        target_characters: list[str],
    ) -> list[RepairFileEntry]:
        """Build the file list for repair agent validation.

        Only primary LLM outputs enter repair: world / character
        stage_snapshots and memory_timeline. Derived files
        (memory_digest.jsonl, world_event_digest.jsonl) are NOT included —
        they are 1:1 code projections of the primaries, regenerated
        deterministically by post-processing and guarded by the
        phase3_5_consistency §32/§33 gate. Letting repair (esp. T3 full-
        file LLM rewrite) mutate a derived file corrupts it and directly
        contradicts that gate. See decisions.md and
        logs/change_logs/2026-07-15_134148_digest-derived-no-repair.md.
        """
        from .core.schema_loader import load_schema as _load_schema_inlined
        schema_dir = self.project_root / "schemas"
        files: list[RepairFileEntry] = []

        def _load_schema(schema_name: str) -> dict | None:
            schema_path = schema_dir / schema_name
            if not schema_path.exists():
                return None
            try:
                return _load_schema_inlined(schema_path)
            except (ValueError, OSError):
                return None

        def _entry(path: Path, schema_name: str) -> RepairFileEntry | None:
            if not path.exists():
                return None
            return RepairFileEntry(
                path=str(path), schema=_load_schema(schema_name))

        # World stage snapshot
        world_ss = work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"
        e = _entry(world_ss, "world/world_stage_snapshot.schema.json")
        if e:
            files.append(e)

        # World stage catalog (accumulated; schema validates the whole
        # catalog shape and monotonic ordering across stages)
        e = _entry(
            work_dir / "world" / "stage_catalog.json",
            "world/world_stage_catalog.schema.json")
        if e:
            files.append(e)

        for char_id in target_characters:
            char_dir = work_dir / "characters" / char_id / "canon"

            # Character stage snapshot
            e = _entry(
                char_dir / "stage_snapshots" / f"{stage_id}.json",
                "character/stage_snapshot.schema.json")
            if e:
                files.append(e)

            # Memory timeline (JSON array; schema is per-entry — checker
            # iterates lists regardless of suffix)
            e = _entry(
                char_dir / "memory_timeline" / f"{stage_id}.json",
                "character/memory_timeline_entry.schema.json")
            if e:
                files.append(e)

            # Stage catalog
            e = _entry(
                char_dir / "stage_catalog.json",
                "character/stage_catalog.schema.json")
            if e:
                files.append(e)

        return files

    def run_summarization(self) -> Path:
        """Summarize all chapters in chunks, return summaries directory."""
        _set_run_phase("phase0")
        structure_mode = read_structure_mode(self.project_root, self.work_id)
        is_light_novel = structure_mode == "light_novel"

        print("\n" + "=" * 60)
        print(f"  Phase 0: Chapter Summarization "
              f"(structure_mode={structure_mode})")
        print("=" * 60 + "\n")

        source_dir = (self.project_root / "sources" / "works"
                      / self.work_id)
        chapters_dir = source_dir / "chapters"
        chapter_files = sorted(chapters_dir.glob("*.txt"))
        total_chapters = len(chapter_files)

        if total_chapters == 0:
            print("[ERROR] No chapter files found.")
            sys.exit(1)

        summaries_dir = (self.project_root / "works" / self.work_id
                         / "analysis" / "chapter_summaries")
        summaries_dir.mkdir(parents=True, exist_ok=True)

        # Build chunk list: (idx, start, end) all 1-based.
        # light_novel: 1 sub-section = 1 chunk = 1 chapter — degenerate
        # single-element chunks bypass token-budget batching but reuse the
        # same downstream chunk_summary schema / path / parallel runner.
        chunks: list[tuple[int, int, int]] = []
        if is_light_novel:
            for i in range(total_chapters):
                chunks.append((i + 1, i + 1, i + 1))
        else:
            for i in range(0, total_chapters, self.chunk_size):
                start = i + 1
                end = min(i + self.chunk_size, total_chapters)
                idx = i // self.chunk_size + 1
                chunks.append((idx, start, end))

        total_chunks = len(chunks)

        # Load or create Phase 0 progress
        phase0 = Phase0Progress.load(
            self.project_root, self.work_id)
        if phase0 is None:
            phase0 = Phase0Progress(
                work_id=self.work_id,
                total_chapters=total_chapters,
                chunk_size=self.chunk_size,
                total_chunks=total_chunks,
            )
        else:
            rec = phase0.reconcile_with_disk(self.project_root)
            if rec["reverted"] or rec["purged"]:
                print(f"  Reconciled with disk: reverted {rec['reverted']} "
                      f"chunk(s) to pending, purged {rec['purged']} stale "
                      f"summary file(s)")
        # Ensure all chunks are tracked
        for idx, start, end in chunks:
            chunk_id = f"chunk_{idx:03d}"
            if chunk_id not in phase0.chunks:
                phase0.chunks[chunk_id] = ChunkEntry(
                    chunk_id=chunk_id,
                    chapters=f"C{start:04d}-C{end:04d}",
                )
        phase0.save(self.project_root)

        print(f"  Total chapters: {total_chapters}")
        if is_light_novel:
            print(f"  Chunk size: 1 (light_novel mode)")
        else:
            print(f"  Chunk size: {self.chunk_size}")
        print(f"  Total chunks: {total_chunks}")

        # Filter out already-completed chunks. Skip judgement is
        # *schema-gated*: file existence alone is not enough — partial /
        # stale / corrupt files must re-run, otherwise Phase 1 will fan
        # out on a missing-chapter foundation.
        pending: list[tuple[int, int, int]] = []
        for idx, start, end in chunks:
            chunk_id = f"chunk_{idx:03d}"
            entry = phase0.chunks.get(chunk_id)
            output_path = summaries_dir / f"{chunk_id}.json"
            expected = end - start + 1

            ok, why = self._chunk_passes_full_check(
                output_path, expected, start_ch=start, end_ch=end)

            if not ok and output_path.exists() and "json parse" in why:
                # L1+L2 JSON repair attempt; re-check after repair
                repaired, desc = try_repair_json_file(
                    output_path,
                    backend=self.backend,
                    expected_key="summaries",
                )
                if repaired:
                    ok, why = self._chunk_passes_full_check(
                        output_path, expected,
                        start_ch=start, end_ch=end)
                    if ok:
                        print(f"  [{idx}/{total_chunks}] {chunk_id} "
                              f"(C{start:04d}-C{end:04d}) — repaired "
                              f"({desc}), skipping")

            if ok:
                if not entry or entry.state != "done":
                    if entry:
                        entry.state = "done"
                    phase0.save(self.project_root)
                if entry and entry.state == "done":
                    print(f"  [{idx}/{total_chunks}] {chunk_id} "
                          f"(C{start:04d}-C{end:04d}) — already done, "
                          f"skipping")
                continue

            # Re-extract: drop any partial / unrepairable file and reset
            # progress to pending so worker pool re-runs it cleanly.
            if output_path.exists():
                output_path.unlink(missing_ok=True)
                if entry:
                    entry.state = "pending"
                    entry.error_message = f"reset by gate: {why}"
                    phase0.save(self.project_root)
                print(f"  [{idx}/{total_chunks}] {chunk_id} "
                      f"(C{start:04d}-C{end:04d}) — re-extract ({why})")
            pending.append((idx, start, end))

        if not pending:
            print(f"\n[OK] All {total_chunks} chunks already complete.")
            # Mark pipeline phase_0 done
            if self.pipeline:
                self.pipeline.mark_done("phase_0")
                self.pipeline.save(self.project_root)
            return summaries_dir

        print(f"  To process: {len(pending)}")
        print(f"  Concurrency: {self.concurrency}")
        print("=" * 60)

        # Parallel processing
        start_time = time.monotonic()
        completed = 0
        failed = 0
        total_pending = len(pending)

        print(f"\n  Processing {total_pending} chunks "
              f"with {self.concurrency} workers...\n")

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {}
            for idx, start, end in pending:
                future = executor.submit(
                    self._summarize_chunk,
                    idx, total_chunks, start, end, summaries_dir,
                )
                futures[future] = (idx, start, end)

            for future in as_completed(futures):
                idx, start, end = futures[future]
                chunk_id = f"chunk_{idx:03d}"
                try:
                    _, success, msg = future.result()
                except RateLimitHardStop:
                    # Hard stop must propagate to the main thread (and
                    # then to CLI) per docs/requirements.md §11.13;
                    # never demote it to a per-chunk failure. Cancel
                    # siblings so the implicit ``with`` exit
                    # ``shutdown(wait=True)`` doesn't block on still-
                    # sleeping chunks (decision #55 R2 pattern).
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
                except Exception as exc:
                    success, msg = False, str(exc)

                entry = phase0.chunks.get(chunk_id)
                if success:
                    completed += 1
                    if entry:
                        entry.state = "done"
                        entry.last_updated = ""  # save() updates timestamp
                    phase0.save(self.project_root)
                    if msg:  # partial
                        print(f"    [WARN] {chunk_id} "
                              f"(C{start:04d}-C{end:04d}): {msg}  "
                              f"({completed}/{total_pending})")
                    else:
                        print(f"    [OK] {chunk_id} "
                              f"(C{start:04d}-C{end:04d})  "
                              f"({completed}/{total_pending})")
                else:
                    failed += 1
                    if entry:
                        entry.state = "failed"
                        entry.error_message = msg[:500]
                        entry.retry_count += 1
                    phase0.save(self.project_root)
                    print(f"    [FAIL] {chunk_id}: {msg[:120]}")

        elapsed = time.monotonic() - start_time
        print(f"\n  Completed: {completed}/{total_pending}  "
              f"Failed: {failed}  "
              f"Elapsed: {_fmt_duration(elapsed)}")
        if completed > 0:
            print(f"  Avg: {_fmt_duration(elapsed / completed)}/chunk")

        # Recovery sweep (decision #49) — for chunks that timed out or hit
        # max_turns, retry once with downgraded effort (default high). The
        # full L1/L2/L3 + tolerance pipeline runs inside _summarize_chunk;
        # only the per-call effort is changed via run_with_retry's effort
        # kwarg. Marks recovery_attempted=True regardless so subsequent
        # --resume skips already-swept chunks (no infinite救火 loop).
        self._run_recovery_sweep(phase0, summaries_dir, total_chunks, chunks)

        # Verify all chunks completed — gate for Phase 1. Schema-gated:
        # file existence alone is not enough; the file must parse, pass
        # schema, and cover every chapter in its range.
        gate_failures: list[str] = []
        for idx, start, end in chunks:
            output_path = summaries_dir / f"chunk_{idx:03d}.json"
            expected = end - start + 1
            ok, why = self._chunk_passes_full_check(
                output_path, expected, start_ch=start, end_ch=end)
            if not ok:
                gate_failures.append(f"chunk_{idx:03d} ({why})")

        if gate_failures:
            print(f"\n[ERROR] Summarization gate failed: "
                  f"{len(gate_failures)}/{total_chunks} chunks incomplete")
            for f in gate_failures[:10]:
                print(f"  - {f}")
            if len(gate_failures) > 10:
                print(f"  ... and {len(gate_failures) - 10} more")
            print("  Re-run to fill gaps (passing chunks will be skipped).")
            sys.exit(1)

        print(f"\n[OK] Summarization: {total_chunks}/{total_chunks} chunks")

        # Mark pipeline phase_0 done
        if self.pipeline:
            self.pipeline.mark_done("phase_0")
            self.pipeline.save(self.project_root)

        return summaries_dir

    # ------------------------------------------------------------------
    # Phase 1: Analysis (from summaries)
    # ------------------------------------------------------------------

    def _build_light_novel_stage_plan(self) -> dict[str, Any]:
        """Programmatically derive stage_plan 1:1 from chapter_index.

        light_novel mode: 1 sub-section = 1 phase 0 chunk = 1 phase 1
        stage. The LLM analysis call still runs (for foundation +
        candidate_characters lanes), but stage_plan is derived
        programmatically here without an LLM call.
        """
        chapter_index = _load_json(
            self.project_root / "sources" / "works" / self.work_id
            / "metadata" / "chapter_index.json")
        if not isinstance(chapter_index, list) or not chapter_index:
            print("[ERROR] light_novel stage_plan derivation: "
                  "chapter_index.json missing or empty.")
            sys.exit(1)

        stages: list[dict[str, Any]] = []
        for i, entry in enumerate(chapter_index, start=1):
            if not isinstance(entry, dict):
                print(f"[ERROR] chapter_index entry #{i} is not an object.")
                sys.exit(1)
            try:
                chapter_id = entry["chapter_id"]
                title = entry["title"]
            except (KeyError, TypeError) as exc:
                print(f"[ERROR] chapter_index entry #{i} missing "
                      f"required field: {exc}")
                sys.exit(1)
            # Soft-truncate to schema's `stage_title.maxLength` cap
            # (read dynamically per §27b Bounds-only-in-schema) +
            # `…` ellipsis, preventing adversarial long volume_title
            # × original_chapter_title combinations from triggering
            # schema gate fail → infinite Phase 1 retry → FATAL.
            title_cap = _stage_title_max_length()
            if len(title) > title_cap:
                title = title[: title_cap - 1] + "…"
            # `chapters` reuses the C####-C#### degenerate-range format
            # (start == end) so downstream phase 2/3/4 consumers
            # (prompt_builder._parse_chapter_range, scene_archive,
            # extraction.repair.context_retriever, post_processing._parse_chapter_scope)
            # work unchanged. Volume / printed-chapter display info lives
            # on the chapter_index profile-B fields, which already feed
            # `title` here via the normalization-derived formula.
            stages.append({
                "stage_id": f"S{i:03d}",
                "stage_title": title,
                "chapters": f"{chapter_id}-{chapter_id}",
                "chapter_count": 1,
                "boundary_reason": (
                    "light_novel: 1 sub-section = 1 stage"
                ),
            })

        return {
            "work_id": self.work_id,
            "total_chapters": len(chapter_index),
            "stages": stages,
        }

    def run_analysis(self) -> dict[str, Any]:
        """Run analysis phase as per-lane fan-out (decision #52).

        Lanes run in parallel, each = one ``claude -p`` + a narrow projection
        of the chunk JSON inputs (staged at
        ``works/{work_id}/analysis/.phase1_lane_inputs/{lane}/``) + per-lane
        schema gate + per-lane ``prior_error``-style retry budget
        (``[phase1].exit_validation_max_retry`` is per-lane independent —
        no shared pool). Strict-retry budget exhaustion falls through to
        length-bound tolerance gate (decision #48); only then FATAL.

        Lane sets (decision #54 — foundation lane output:
        `world/foundation/foundation.json`):
        - **monolithic**: foundation + stage_plan + candidate_characters
        - **light_novel**: foundation + candidate_characters (stage_plan
          is derived programmatically from chapter_index by
          ``_build_light_novel_stage_plan``, no LLM call — STAGE_MIN/MAX
          bypassed since 1:1 derivation always = 1 chapter per stage)

        ``--resume`` skip semantics: any lane whose output is already on disk
        AND passes its schema gate (and stage-limit check, for stage_plan
        monolithic) is skipped without rebuilding tmpdir inputs for it.
        """
        _set_run_phase("phase1")
        structure_mode = read_structure_mode(self.project_root, self.work_id)
        is_light_novel = structure_mode == "light_novel"

        cfg = get_config()
        MAX_RETRIES_PER_LANE = cfg.phase1.exit_validation_max_retry
        STAGE_MIN = cfg.stage.min_chapter_count
        STAGE_MAX = cfg.stage.max_chapter_count
        LANE_CONCURRENCY = max(1, cfg.phase1.lane_concurrency)
        work_dir = self.project_root / "works" / self.work_id
        inc_dir = work_dir / "analysis"

        # Lane definitions: (name, output_relpath, validator_fn, builder_fn)
        # — output_relpath is relative to work_dir (e.g. "analysis/stage_plan.json"
        # for analysis-layer lanes; "world/foundation/foundation.json" for the
        # foundation lane after decision #54 moved foundation production to
        # phase 1). stage_plan lane is included only in monolithic — light_novel
        # derives stage_plan programmatically (no LLM lane).
        lanes: list[tuple[str, str, Any, Any]] = [
            ("foundation", "world/foundation/foundation.json",
             _foundation_validator, build_foundation_prompt),
        ]
        if not is_light_novel:
            lanes.append((
                "stage_plan", "analysis/stage_plan.json",
                _stage_plan_validator, build_stage_plan_prompt,
            ))
        lanes.append((
            "candidate_characters", "analysis/candidate_characters.json",
            _candidate_characters_validator, build_candidate_characters_prompt,
        ))

        def _lane_passes_skip(name: str, relpath: str,
                              validator_fn: Any) -> bool:
            existing = _load_json(work_dir / relpath)
            if existing is None:
                return False
            if list(validator_fn().iter_errors(existing)):
                return False
            if name == "stage_plan" and not is_light_novel:
                if _check_stage_plan_limits(
                        existing,
                        max_stage_size=STAGE_MAX,
                        min_stage_size=STAGE_MIN):
                    return False
            return True

        # Decide which lanes to run vs skip (resume-aware).
        skip_set: set[str] = set()
        pending: list[tuple[str, str, Any, Any]] = []
        for lane in lanes:
            name, relpath, validator_fn, _ = lane
            if _lane_passes_skip(name, relpath, validator_fn):
                skip_set.add(name)
            else:
                pending.append(lane)

        print("\n" + "=" * 60)
        print(f"  Phase 1: Analysis [structure_mode={structure_mode}]")
        print("=" * 60)
        for name, relpath, _, _ in lanes:
            mark = ("[SKIP — schema-valid on disk]"
                    if name in skip_set else "[run]")
            print(f"  {mark} {name} → {relpath}")
        if is_light_novel:
            print("  [run] stage_plan → analysis/stage_plan.json "
                  "(programmatic derivation, no LLM)")
        if pending:
            print(f"  Lane concurrency: {LANE_CONCURRENCY}")

        # light_novel stage_plan is derived BEFORE the LLM lanes run so
        # downstream phases that read stage_plan (none in this method,
        # but kept for fail-safety on partial outcomes) always see it.
        if is_light_novel:
            derived = self._build_light_novel_stage_plan()
            _write_json(inc_dir / "stage_plan.json", derived)
            print(f"  [OK] light_novel stage_plan derived: "
                  f"{len(derived['stages'])} stages "
                  f"(1 sub-section = 1 stage)")

        # Per-lane retry loop. ``prior_error`` injection is per-lane
        # (decision #52) — same pattern as Phase 0 chunk-level / Phase 4
        # chapter-level prior_error retry; not shared across lanes.
        # Map lane name → schema reference path (for prior_error messages).
        # foundation lane lives under schemas/world/; the other two under
        # schemas/analysis/ (decision #54 — foundation schema migrated from
        # schemas/analysis/world_overview.schema.json to
        # schemas/world/foundation.schema.json).
        _LANE_SCHEMA_REF = {
            "foundation": "schemas/world/foundation.schema.json",
            "stage_plan": "schemas/analysis/stage_plan.schema.json",
            "candidate_characters":
                "schemas/analysis/candidate_characters.schema.json",
        }

        def _run_one_lane(
            lane: tuple[str, str, Any, Any],
            lane_dir: Path,
        ) -> tuple[str, str, str | None]:
            name, relpath, validator_fn, builder_fn = lane
            target_path = work_dir / relpath
            # Ensure parent dir exists (foundation lane writes into
            # works/{work_id}/world/foundation/ which may not exist yet).
            target_path.parent.mkdir(parents=True, exist_ok=True)
            prior_error = ""

            for attempt in range(1, MAX_RETRIES_PER_LANE + 2):
                if attempt > 1:
                    print(f"  [RETRY {attempt - 1}/{MAX_RETRIES_PER_LANE}] "
                          f"phase1 lane {name}: re-running with prior_error")

                prompt = builder_fn(
                    self.project_root, self.work_id, lane_dir,
                    prior_error=prior_error,
                )
                result = run_with_retry(
                    self.backend, prompt,
                    timeout_seconds=cfg.phase3.extraction_timeout_s,
                    lane_name=f"phase1_{name}",
                )
                if not result.success:
                    return name, "lane_failed", (
                        f"claude -p failed: {result.error or 'unknown'}")

                produced = _load_json(target_path)
                if produced is None:
                    # Disambiguate file-missing vs json-bad — `_load_json`
                    # swallows both and returns None, but the LLM needs
                    # a precise error to fix. Probe the file directly:
                    # exists() True + json.loads raise → bad JSON; not
                    # exists → never written. Single read attempt; we
                    # already know `_load_json` failed, so any exception
                    # here is the same root cause we want to surface.
                    if target_path.exists():
                        try:
                            json.loads(target_path.read_text(encoding="utf-8"))
                        except (json.JSONDecodeError, OSError) as exc:
                            prior_error = (
                                f"输出文件 `{relpath}` 已落盘但 JSON 解析失败："
                                f"`{exc}`。请检查格式（缺逗号 / 引号未闭合 / "
                                f"尾随非法字符等）后重写本 lane 输出。"
                            )
                        else:
                            # File parsed fine on direct read but `_load_json`
                            # returned None — should not happen unless the
                            # file content is JSON null / empty after parse.
                            prior_error = (
                                f"输出文件 `{relpath}` 解析为空 (null / 空容器)，"
                                f"请按 prompt 要求生成实质内容。"
                            )
                    else:
                        prior_error = (
                            f"输出文件 `{relpath}` 未生成，请按 prompt 要求"
                            f"将产物写入 `{target_path}`。"
                        )
                    if attempt > MAX_RETRIES_PER_LANE:
                        return name, "lane_failed", (
                            f"output `{relpath}` failed to load after "
                            f"{MAX_RETRIES_PER_LANE} retries: {prior_error[:120]}")
                    continue

                errs = list(validator_fn().iter_errors(produced))
                violating: list[dict[str, Any]] = []
                if name == "stage_plan" and not is_light_novel:
                    violating = _check_stage_plan_limits(
                        produced,
                        max_stage_size=STAGE_MAX,
                        min_stage_size=STAGE_MIN,
                    )
                if not errs and not violating:
                    return name, "ok", None

                lines: list[str] = []
                if errs:
                    first = errs[0]
                    err_path = "/".join(
                        str(p) for p in first.absolute_path) or "<root>"
                    lines.append(
                        f"Schema 校验失败：`{relpath}` 共 {len(errs)} 处违反，"
                        f"首条 `{err_path}`: {first.message[:120]}"
                    )
                if violating:
                    details = "; ".join(
                        f"{b.get('stage_id', '?')}={b.get('chapter_count')}章"
                        for b in violating)
                    lines.append(
                        f"stage_plan 中有 {len(violating)} 个 stage "
                        f"不满足 {STAGE_MIN}-{STAGE_MAX} 章限制：{details}。"
                        "对于跨度大的故事弧，必须拆分为多个 stage；"
                        "对于过短的 stage，应合并到相邻 stage。"
                    )

                if attempt <= MAX_RETRIES_PER_LANE:
                    schema_ref = _LANE_SCHEMA_REF.get(
                        name,
                        f"schemas/analysis/{Path(relpath).name.replace('.json', '.schema.json')}",
                    )
                    prior_error = (
                        "\n".join(lines)
                        + "\n\nschema 契约见 "
                        f"`{schema_ref}`。"
                        "请重新生成本 lane 输出以满足 schema + stage 限制。"
                    )
                    target_path.unlink(missing_ok=True)
                    continue

                # Strict-retry budget exhausted — try length-bound tolerance
                # gate (decision #48). Only schema bound violations are
                # tolerable (stage-limit violations are not length-bound).
                if errs and not violating:
                    ok_tol, _ = validate_with_length_tolerance(
                        produced, validator_fn().schema)
                    if ok_tol:
                        print(
                            f"  [LENGTH-TOLERANCE] phase1 lane {name} "
                            f"accepted by length-bound tolerance gate "
                            f"after {MAX_RETRIES_PER_LANE} strict retries "
                            f"(decision #48)")
                        return name, "ok_tolerance", None

                return name, "lane_failed", (
                    f"strict-retry exhausted ({MAX_RETRIES_PER_LANE}) + "
                    f"tolerance gate not applicable: {'; '.join(lines)}")

            return name, "lane_failed", "loop fell through (should not happen)"

        # Project chunks into per-lane tmpdirs (only for pending lanes —
        # skipped lanes already have valid output). Wrapped in try/finally
        # so the tmpdir tree is cleaned regardless of success / fatal /
        # SIGTERM (decision #52 (6)).
        results: dict[str, tuple[str, str | None]] = {}
        try:
            lane_dirs: dict[str, Path] = {}
            if pending:
                lane_dirs = prepare_phase1_lane_inputs(
                    self.project_root, self.work_id,
                    lanes=tuple(l[0] for l in pending),
                )

            if pending:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(
                        max_workers=LANE_CONCURRENCY) as pool:
                    futures = {
                        pool.submit(_run_one_lane, lane, lane_dirs[lane[0]]):
                            lane[0]
                        for lane in pending
                    }
                    for fut in as_completed(futures):
                        try:
                            name, status, err = fut.result()
                        except RateLimitHardStop:
                            # Cancel siblings so the implicit ``with``
                            # exit doesn't block on still-sleeping
                            # lanes (decision #55 R2 pattern).
                            pool.shutdown(wait=False, cancel_futures=True)
                            raise
                        results[name] = (status, err)
                        msg = f"  [{status.upper()}] phase 1 lane: {name}"
                        if err:
                            msg += f" — {err}"
                        print(msg)

            failed_lanes = [
                n for n, (s, _) in results.items() if s == "lane_failed"]
            if failed_lanes:
                print(f"\n[FATAL] Phase 1 failed lanes: "
                      f"{', '.join(failed_lanes)}. Aborting.")
                sys.exit(1)
        finally:
            cleanup_phase1_lane_inputs(self.project_root, self.work_id)

        # Final guard: defense in depth — abort if any of the three trio
        # files is missing (covers a future code-edit that drops a lane
        # from the loop without removing the trio guarantee). foundation
        # lives under world/foundation/ (decision #54); stage_plan +
        # candidate_characters under analysis/.
        trio_relpaths = (
            "analysis/stage_plan.json",
            "world/foundation/foundation.json",
            "analysis/candidate_characters.json",
        )
        for relpath in trio_relpaths:
            if not (work_dir / relpath).exists():
                print(f"[FATAL] Phase 1 marked complete but `{relpath}` "
                      f"missing on disk. Aborting.")
                sys.exit(1)

        stage_plan = _load_json(work_dir / "analysis" / "stage_plan.json")
        candidates = _load_json(
            work_dir / "analysis" / "candidate_characters.json")
        foundation = _load_json(
            work_dir / "world" / "foundation" / "foundation.json")

        # Mark pipeline phase_1 done
        if self.pipeline:
            self.pipeline.mark_done("phase_1")
            self.pipeline.save(self.project_root)

        return {
            "stage_plan": stage_plan,
            "candidates": candidates,
            "foundation": foundation,
            "raw_output": "",  # no single raw_output anymore (3 lanes)
        }

    # ------------------------------------------------------------------
    # Phase 2: Baseline production
    # ------------------------------------------------------------------

    def run_baseline_production(
        self, target_characters: list[str]
    ) -> None:
        """Produce phase 2 baseline as a 2+2N lane fan-out (decision #59;
        artifact set per decision #54 + #58):

        - **lane A (key_figures, runs FIRST, serialized)**：foundation.
          major_factions[].key_figures raw 名 → character_id 替换（in-place
          edit of foundation.json — 先行跑完再放其余 lane，避免同文件
          读写并发）
        - **lane B (fixed_relationships)**：world/foundation/
          fixed_relationships.json
        - **identity lane ×N**（每目标角色一个）：canon/identity.json +
          manifest.json
        - **target_baseline lane ×N**：canon/target_baseline.json

        lane B 与全部 per-char lanes 并行（``[phase2].lane_concurrency``）。
        每 lane：独立 prompt（chunk 输入按 lane 投影裁剪，同 phase 1
        projector 模式）→ 输出落盘 → per-file repair 缩水版（决策 #59：
        T0/T1 + schema/程序 checker；L3 语义 checker / T2 source_patch /
        triage 不开——``source_context=None``；无全文/lane 重跑层，仍不平
        的残留交终点 gate）。``[phase2].repair_enabled = false``
        时跳过 per-lane repair，仅靠终点 ``validate_baseline`` gate。

        foundation.json 主体由 phase 1 foundation lane 直接产出，phase 2
        不再二次综合 foundation。stage_catalog 不再由 phase 2 LLM 写空占位
        ——决策 #58 把 stage_catalog 初始化前移到 phase 3 第一个 stage 的
        post_processing.upsert_stage_catalog 程序级首次落盘。

        ⚠️ **Phase 3 cascade warning (decision #54 + #13)**：本函数重跑
        会改写 ``target_baseline.json``（决策 #54 的 dialogue/action 准入
        门槛使 baseline.targets 集合可能缩水）。决策 #13 双向 set-equal
        约束要求 phase 3 stage_snapshot 的三结构 keys 必须等于
        ``baseline.targets[].target_character_id`` 全集——baseline 一旦
        变化，**所有已落盘的 phase 3 stage_snapshot 都将与新 baseline
        集合不一致**，下一次 phase 3 跑 cross-file validate 会硬 fail。

        所以**重跑 phase 2 必须配套清空所有 phase 3 产物**：
        ``works/{work_id}/world/stage_snapshots/`` +
        ``works/{work_id}/characters/*/canon/stage_snapshots/`` +
        ``memory_timeline/`` + ``memory_digest.jsonl`` +
        ``world_event_digest.jsonl`` + ``analysis/progress/phase3_stages.json``。
        清空后从 phase 3 stage 1 重抽。

        本函数不自动清理 phase 3 产物——清理是破坏性动作，需用户
        显式执行（例如 ``rm -rf`` + ``git rm``）。
        """
        _set_run_phase("phase2")
        from .core.schema_loader import load_schema as _load_schema_inlined

        # Dedupe while preserving order — a duplicate id from the phase
        # 1.5 manual input would spawn two same-slug per-char lanes
        # writing the same files concurrently.
        target_characters = list(dict.fromkeys(target_characters))

        cfg = get_config()
        work_dir = self.project_root / "works" / self.work_id
        schemas_dir = self.project_root / "schemas"
        foundation_path = work_dir / "world" / "foundation" / "foundation.json"

        print("\n" + "=" * 60)
        print("  Phase 2: Baseline Production [2+2N lane fan-out]")
        print("=" * 60 + "\n")
        print(f"  Characters: {target_characters}")

        # Pre-check: foundation.json must exist (phase 1 foundation lane
        # output). Phase 2 reads + 补齐 key_figures, never re-creates the
        # file from scratch (decision #54). If missing, phase 1 must be
        # re-run before phase 2 can proceed.
        if not foundation_path.exists():
            print(f"[ERROR] phase 1 foundation lane output missing: "
                  f"{foundation_path}.")
            print("  Phase 2 cannot run baseline production without "
                  "phase 1 foundation.json (decision #54).")
            print("  Re-run with --resume to retry phase 1 foundation lane.")
            sys.exit(1)

        # Legal character_id set — replacement lookup for lane A and the
        # anchor every phase-2 reference checker validates against
        # (decision #59: checkers compare only against this immutable
        # shared input; no cross-artifact merge checker).
        candidates_data = _load_json(
            work_dir / "analysis" / "candidate_characters.json")
        legal_ids = {
            c["character_id"]
            for c in (candidates_data or {}).get("candidates", [])
            if isinstance(c, dict) and c.get("character_id")
        }
        if not legal_ids:
            print("[ERROR] candidate_characters.json missing or empty — "
                  "phase 2 lanes need the legal character_id set. "
                  "Re-run with --resume to retry phase 1.")
            sys.exit(1)

        # Lane A checker hint: pre-lane key_figures state ("不新增" 契约
        # 的对照基线)。Loaded BEFORE lane A mutates the file.
        pre_foundation = _load_json(foundation_path) or {}
        pre_key_figures: dict[str, list[str]] = {}
        for fac in pre_foundation.get("major_factions") or []:
            if isinstance(fac, dict):
                pre_key_figures[fac.get("name", "")] = [
                    e for e in (fac.get("key_figures") or [])
                    if isinstance(e, str)
                ]

        # --- repair plumbing (shared by every lane) ---
        repair_enabled = cfg.phase2.repair_enabled
        ra_cfg = cfg.repair
        repair_logs_dir = work_dir / "analysis" / "progress" / "repair_logs"
        if repair_enabled:
            repair_logs_dir.mkdir(parents=True, exist_ok=True)

        default_review_timeout = cfg.phase3.review_timeout_s

        def _llm_call(prompt: str, timeout: int | None = None) -> str:
            result = run_with_retry(
                self.reviewer_backend or self.backend,
                prompt,
                timeout_seconds=timeout or default_review_timeout,
                lane_name="repair[phase2]",
            )
            if not result.success:
                raise SemanticReviewLLMUnavailable(
                    result.error or "LLM call failed")
            return result.text

        def _phase2_repair_cfg() -> RepairConfig:
            # 缩水版（决策 #59）：run_semantic / l3_gate / triage 全关
            # （无失败样本 + phase 2 输入契约是摘要，语义层不适用）；
            # t2_max=0 跳过 T2 source_patch（phase 2 产物不该拿原文修）。
            return RepairConfig(
                max_rounds=ra_cfg.total_round_limit,
                run_semantic=False,
                l3_gate_enabled=False,
                triage_enabled=False,
                retry_policy=RetryPolicy(
                    t0_max=ra_cfg.t0_retry,
                    t1_max=ra_cfg.t1_retry,
                    t2_max=0,
                    max_total_rounds=ra_cfg.total_round_limit,
                ),
            )

        # --- lane table -------------------------------------------------
        # Each lane: slug / outputs [(path, schema_path)] / builder
        # (prior_error -> prompt) / extra checker factory. Builders close
        # over lane_dirs, which is populated before any lane runs.
        lane_dirs: dict[str, Path] = {}

        def _lane_a_builder(prior_error: str) -> str:
            return build_key_figures_prompt(
                self.project_root, self.work_id, prior_error=prior_error)

        lane_a: dict[str, Any] = {
            "slug": "key_figures",
            "outputs": [(foundation_path,
                         schemas_dir / "world" / "foundation.schema.json")],
            "builder": _lane_a_builder,
            "checkers": lambda: [FoundationKeyFiguresChecker(
                legal_ids, pre_key_figures)],
        }

        def _make_fixed_rel_lane() -> dict[str, Any]:
            def _builder(prior_error: str) -> str:
                return build_fixed_relationships_prompt(
                    self.project_root, self.work_id, target_characters,
                    lane_dirs["fixed_relationships"],
                    prior_error=prior_error)
            return {
                "slug": "fixed_relationships",
                "outputs": [(
                    work_dir / "world" / "foundation"
                    / "fixed_relationships.json",
                    schemas_dir / "world"
                    / "fixed_relationships.schema.json")],
                "builder": _builder,
                "checkers": lambda: [
                    FixedRelationshipsPartiesChecker(legal_ids)],
            }

        def _make_identity_lane(cid: str) -> dict[str, Any]:
            def _builder(prior_error: str) -> str:
                return build_identity_prompt(
                    self.project_root, self.work_id, cid,
                    lane_dirs["identity"], prior_error=prior_error)
            char_dir = work_dir / "characters" / cid
            return {
                "slug": f"identity_{cid}",
                "outputs": [
                    (char_dir / "canon" / "identity.json",
                     schemas_dir / "character" / "identity.schema.json"),
                    (char_dir / "manifest.json",
                     schemas_dir / "character"
                     / "character_manifest.schema.json"),
                ],
                "builder": _builder,
                "checkers": lambda: [],
            }

        def _make_target_baseline_lane(cid: str) -> dict[str, Any]:
            def _builder(prior_error: str) -> str:
                return build_target_baseline_prompt(
                    self.project_root, self.work_id, cid,
                    lane_dirs["target_baseline"], prior_error=prior_error)
            return {
                "slug": f"target_baseline_{cid}",
                "outputs": [(
                    work_dir / "characters" / cid / "canon"
                    / "target_baseline.json",
                    schemas_dir / "character"
                    / "target_baseline.schema.json")],
                "builder": _builder,
                "checkers": lambda: [
                    TargetBaselineKeysChecker(legal_ids, cid)],
            }

        parallel_lanes: list[dict[str, Any]] = [_make_fixed_rel_lane()]
        for cid in target_characters:
            parallel_lanes.append(_make_identity_lane(cid))
            parallel_lanes.append(_make_target_baseline_lane(cid))

        # --- resume skip: parallel lanes with valid outputs on disk are
        # skipped (same semantics as phase 1). "Valid" = schema pass AND
        # the lane's phase-2 reference checkers report no error — the
        # skip criterion must be at least as strict as the lane's own
        # pass criterion, otherwise a repair-FAIL run that left a
        # schema-legal but reference-illegal file on disk would be
        # silently skipped on --resume and reach phase 3. Lane A always
        # runs — replacement is idempotent (already-replaced ids match
        # themselves via exact character_id lookup) and "已替换" 无法从
        # schema 判定（raw 名残留合法）。
        def _outputs_valid(lane: dict[str, Any]) -> bool:
            entries: list[RepairFileEntry] = []
            for path, schema_path in lane["outputs"]:
                data = _load_json(path)
                if data is None:
                    return False
                try:
                    schema = _load_schema_inlined(schema_path)
                except (OSError, ValueError):
                    return False
                if list(_jsonschema.Draft202012Validator(
                        schema).iter_errors(data)):
                    return False
                entries.append(RepairFileEntry(path=str(path), content=data))
            for checker in lane["checkers"]():
                if any(i.severity == "error"
                       for i in checker.check(entries)):
                    return False
            return True

        pending = [l for l in parallel_lanes if not _outputs_valid(l)]
        pending_slugs = {l["slug"] for l in pending}
        skipped = [l["slug"] for l in parallel_lanes
                   if l["slug"] not in pending_slugs]

        print("  [run] key_figures → world/foundation/foundation.json "
              "(lane A, serialized)")
        for lane in parallel_lanes:
            mark = ("[SKIP — valid on disk (schema + ref checks)]"
                    if lane["slug"] in skipped else "[run]")
            print(f"  {mark} {lane['slug']}")
        lane_concurrency = max(1, cfg.phase2.lane_concurrency)
        if pending:
            print(f"  Lane concurrency: {lane_concurrency} "
                  f"(after lane A)")
        print(f"  Per-lane repair: "
              f"{'enabled (T0/T1, 决策 #59 缩水版)' if repair_enabled else 'disabled'}\n")

        # --- single-lane runner ------------------------------------------
        def _run_phase2_lane(
                lane: dict[str, Any]) -> tuple[str, str, str | None]:
            slug = lane["slug"]
            outputs: list[tuple[Path, Path]] = lane["outputs"]
            for path, _ in outputs:
                path.parent.mkdir(parents=True, exist_ok=True)

            prior_error = ""
            missing: list[str] = []
            missing_retry_budget = max(0, cfg.phase2.output_missing_max_retry)
            for attempt in range(missing_retry_budget + 1):
                if attempt > 0:
                    print(f"  [RETRY {attempt}/{missing_retry_budget}] "
                          f"phase2 lane {slug}: output missing, re-running")
                prompt = lane["builder"](prior_error)
                result = run_with_retry(
                    self.backend, prompt,
                    timeout_seconds=cfg.phase3.extraction_timeout_s,
                    lane_name=f"phase2_{slug}",
                )
                if not result.success:
                    return slug, "lane_failed", (
                        f"claude -p failed: {result.error or 'unknown'}")
                missing = [str(p) for p, _ in outputs if not p.exists()]
                if not missing:
                    break
                prior_error = (
                    f"上一次运行后输出文件未生成：{missing}。"
                    f"请按 prompt 要求把产物写入声明的路径。")
            else:
                return slug, "lane_failed", (
                    f"outputs missing after "
                    f"{missing_retry_budget} retries: {missing}")

            if not repair_enabled:
                return slug, "ok", None

            # Schema load failures degrade to schema=None (SchemaChecker
            # skips such entries; reference checkers still run) — same
            # posture as phase 3's _collect_stage_files. Raising here
            # would burn the whole pool after the lane's LLM tokens are
            # already spent.
            def _safe_schema(sp: Path) -> dict | None:
                try:
                    return _load_schema_inlined(sp)
                except (OSError, ValueError) as exc:
                    logger.warning(
                        "phase2 lane %s: cannot load schema %s (%s); "
                        "schema check skipped for this file", slug, sp, exc)
                    return None

            files = [
                RepairFileEntry(path=str(p), schema=_safe_schema(sp))
                for p, sp in outputs
            ]

            # phase 2 repair is capped-tier only (T0/T1); there is no
            # full-file / lane regeneration tier. Residual issues surface
            # via the terminal ``validate_baseline`` gate.
            rec_path = repair_logs_dir / f"repair_phase2_{slug}.jsonl"
            with RepairRecorder(rec_path) as recorder:
                repair_result = run_repair(
                    files=files,
                    config=_phase2_repair_cfg(),
                    source_context=None,
                    llm_call=_llm_call,
                    recorder=recorder,
                    extra_checkers=lane["checkers"](),
                )
            if not repair_result.passed:
                return slug, "lane_failed", (
                    f"repair FAIL: {repair_result.report[:300]}")
            return slug, "ok", None

        # --- execution: lane A first (serialized), then the rest ---------
        failed: list[tuple[str, str]] = []
        try:
            needed_kinds = set()
            for lane in pending:
                if lane["slug"] == "fixed_relationships":
                    needed_kinds.add("fixed_relationships")
                elif lane["slug"].startswith("identity_"):
                    needed_kinds.add("identity")
                elif lane["slug"].startswith("target_baseline_"):
                    needed_kinds.add("target_baseline")
            if needed_kinds:
                lane_dirs.update(prepare_phase2_lane_inputs(
                    self.project_root, self.work_id,
                    lanes=tuple(sorted(needed_kinds)),
                ))

            name, status, err = _run_phase2_lane(lane_a)
            msg = f"  [{status.upper()}] phase 2 lane: {name}"
            if err:
                msg += f" — {err}"
            print(msg)
            if status != "ok":
                print("\n[FATAL] Phase 2 lane A (key_figures) failed. "
                      "Aborting before parallel lanes.")
                sys.exit(1)

            if pending:
                with ThreadPoolExecutor(
                        max_workers=lane_concurrency) as pool:
                    futures = {
                        pool.submit(_run_phase2_lane, lane): lane["slug"]
                        for lane in pending
                    }
                    for fut in as_completed(futures):
                        submitted = futures[fut]
                        try:
                            name, status, err = fut.result()
                        except RateLimitHardStop:
                            # Cancel siblings so the implicit ``with``
                            # exit doesn't block on still-sleeping lanes
                            # (decision #55 R2 pattern).
                            pool.shutdown(wait=False, cancel_futures=True)
                            raise
                        except Exception as exc:  # noqa: BLE001
                            # Worker raised (unreadable file, unexpected
                            # bug). Don't abort the pool — mark this lane
                            # failed and let siblings finish (same
                            # posture as the phase 3 repair pool).
                            logger.exception(
                                "phase 2 lane worker raised for %s",
                                submitted)
                            name, status, err = (
                                submitted, "lane_failed",
                                f"worker exception: {exc!r}")
                        msg = f"  [{status.upper()}] phase 2 lane: {name}"
                        if err:
                            msg += f" — {err}"
                        print(msg)
                        if status != "ok":
                            failed.append((name, err or ""))
        finally:
            cleanup_phase2_lane_inputs(self.project_root, self.work_id)

        if failed:
            print(f"\n[FATAL] Phase 2 failed lanes: "
                  f"{', '.join(n for n, _ in failed)}. Aborting.")
            sys.exit(1)

        # Write world manifest programmatically now that foundation exists.
        world_manifest_path = write_world_manifest(
            self.project_root, self.work_id)
        print(f"  [OK] Wrote world manifest: {world_manifest_path}")

        # Phase 2 exit validation — catch schema/field errors early
        print("\n--- Phase 2 Validation ---")
        baseline_report = validate_baseline(
            self.project_root, self.work_id, target_characters)
        print(baseline_report.summary())
        if not baseline_report.passed:
            # Strict validation failed. Phase 2 has no LLM-level retry
            # budget here (Phase 2 LLM extraction itself happened above);
            # this is the terminal gate. Try length-bound tolerance
            # (decision #48): re-validate with each minLength × 0.9 /
            # maxLength × 1.1 — if every schema failure is purely a
            # length-bound miss within ±10%, accept; else fatal.
            tolerance_report = validate_baseline(
                self.project_root, self.work_id, target_characters,
                length_tolerance=0.10)
            if tolerance_report.passed:
                print("\n[LENGTH-TOLERANCE] Baseline accepted by "
                      "length-bound tolerance gate (decision #48): all "
                      "schema failures were minLength/maxLength within "
                      "±10%.")
            else:
                print("\n[ERROR] Baseline validation failed. "
                      "Fix the errors above before proceeding.")
                sys.exit(1)

        # Phase_2 progress is marked done by the caller AFTER commit_stage
        # succeeds (decision #58 / M3) — marking done here would let a
        # failed commit slip past while Phase 3 starts on a still-dirty
        # baseline. The caller pattern: run_baseline_production(...) →
        # commit_stage(...) → if sha is None: sys.exit(1) → mark_done.
        print("\n[OK] Baseline production complete.")

    # ------------------------------------------------------------------
    # Phase 1.5: User confirmation
    # ------------------------------------------------------------------

    def confirm_with_user(
        self,
        analysis: dict[str, Any],
        *,
        preset_characters: list[str] | None = None,
        preset_end_stage: int | None = None,
    ) -> tuple[PipelineProgress, Phase3Progress]:
        """Interactive user confirmation of characters and parameters."""
        print("\n" + "=" * 60)
        print("  Phase 1.5: User Confirmation")
        print("=" * 60 + "\n")

        candidates = analysis.get("candidates") or {}
        stage_plan = analysis.get("stage_plan") or {}

        # Show candidates. RECOMMENDED label = importance == "主角" (rule-based;
        # decision #53 replaced the LLM-self-reported `recommended` boolean).
        recommended_ids: list[str] = []
        if candidates and candidates.get("candidates"):
            print("Candidate characters:\n")
            for i, c in enumerate(candidates["candidates"], 1):
                is_recommended = c.get("importance") == "主角"
                rec = "RECOMMENDED" if is_recommended else ""
                if is_recommended:
                    recommended_ids.append(c["character_id"])
                print(f"  {i}. {c['character_id']} — {c.get('description', '')}")
                print(f"     Frequency: {c.get('frequency', '?')}, "
                      f"Importance: {c.get('importance', '?')} {rec}")
            print()
            if recommended_ids:
                print(f"Default selection (importance=主角): "
                      f"{', '.join(recommended_ids)}")
                print("(Press Enter to accept default, or type IDs to "
                      "override / extend.)\n")

        # Select characters
        if preset_characters:
            selected = preset_characters
            print(f"Pre-selected characters: {selected}")
        else:
            try:
                raw = input("Enter character IDs to extract (comma-separated, "
                            "empty = default): ")
            except EOFError:
                # Daemon path with stdin=DEVNULL — cli.py background validator
                # requires --characters preset on phase_1_5-pending path so
                # we shouldn't reach here, but defend in depth: empty falls
                # through to recommended_ids default below (or sys.exit(1)
                # if no recommended_ids).
                raw = ""
            typed = [c.strip() for c in raw.split(",") if c.strip()]
            selected = typed if typed else recommended_ids

        if not selected:
            print("[ERROR] No characters selected.")
            print("       No candidates have importance=='主角' — phase 1 "
                  "LLM produced no main-tier candidates, so empty input "
                  "had no default to fall back to. Re-run with "
                  "--characters <id> [<id> ...] to manually pick from the "
                  "list above.")
            sys.exit(1)

        # Show stage plan summary
        stages_data = stage_plan.get("stages", [])
        total_stages = len(stages_data)
        if stages_data:
            print(f"\nStage plan ({total_stages} stages, "
                  f"split by story boundaries):\n")
            for b in stages_data:
                print(f"  {b['stage_id']}: {b.get('stage_id', '?')} "
                      f"({b['chapters']}, {b.get('chapter_count', '?')} ch) "
                      f"— {b.get('boundary_reason', '')}")
            print()

        # --end-stage is a runtime limit only; progress always contains
        # the full stage plan (same pattern as Phase 4). Decision #56:
        # empty input → None = no limit (run all stages), aligned with
        # the `--end-stage` flag's "omit = all" design and the
        # `run_extraction_loop(max_stages=None)` "no limit" semantics.
        if preset_end_stage is None:
            try:
                raw = input(
                    f"Extract up to stage N (total {total_stages}; "
                    f"empty = all (no limit), 0 = baseline only): "
                ).strip()
            except EOFError:
                # Daemon path with stdin=DEVNULL — fall through to empty,
                # which decision #56 maps to None (= run all stages).
                # Daemon operators who want a runtime cap pass --end-stage
                # explicitly; omitting it is a legitimate "no limit"
                # request, not an error.
                raw = ""
            try:
                preset_end_stage = int(raw) if raw else None
            except ValueError:
                # Non-numeric input (e.g. user typed "abc") — fall back to
                # None = all stages with a one-line notice. Avoids a
                # traceback on a fat-finger; the operator can --end-stage
                # explicitly if they want a different limit.
                print(f"  [WARN] '{raw}' is not a number — defaulting to "
                      f"all stages (no limit).")
                preset_end_stage = None

        pipeline = PipelineProgress(
            work_id=self.work_id,
            extraction_branch=(
                f"{get_config().git.extraction_branch_prefix}{self.work_id}"),
            target_characters=selected,
        )
        pipeline.mark_done("phase_1")
        pipeline.mark_done("phase_1_5")
        pipeline.save(self.project_root)

        # Write works manifest now that characters + stages are confirmed.
        works_manifest_path = write_works_manifest(
            self.project_root, self.work_id, selected)
        print(f"  [OK] Wrote works manifest: {works_manifest_path}")

        phase3 = Phase3Progress(
            work_id=self.work_id,
            stages=[
                StageEntry(
                    stage_id=b["stage_id"],
                    chapters=b["chapters"],
                    chapter_count=b.get("chapter_count", 10),
                    stage_title=b.get("stage_title", ""),
                )
                for b in stages_data  # full plan, not truncated
            ],
        )
        phase3.save(self.project_root)

        self.pipeline = pipeline
        self.phase3 = phase3

        # None → "all" (no limit), 0 → "baseline only", positive → "first N"
        if preset_end_stage is None:
            run_label = "all"
        elif preset_end_stage == 0:
            run_label = "baseline only"
        else:
            run_label = f"first {preset_end_stage}"
        print("\n[OK] Configuration saved.")
        print(f"     Characters: {selected}")
        print(f"     Stages: {len(phase3.stages)} total "
              f"(this run: {run_label})")
        print(f"     Branch: {pipeline.extraction_branch}")
        return pipeline, phase3

    # ------------------------------------------------------------------
    # Phase 3: Extraction loop
    # ------------------------------------------------------------------

    def run_extraction_loop(
        self,
        pipeline: PipelineProgress | None = None,
        phase3: Phase3Progress | None = None,
        *,
        max_stages: int | None = None,
    ) -> None:
        """Main extraction loop: iterate through stages.

        Args:
            pipeline: Pipeline progress (uses self.pipeline if None).
            phase3: Phase 3 stage progress (uses self.phase3 if None).
            max_stages: Stop after this many stages complete.
                         None = all, 0 = baseline only.
        """
        _set_run_phase("phase3")
        pipeline = pipeline or self.pipeline
        phase3 = phase3 or self.phase3
        if not pipeline or not phase3:
            print("[ERROR] No progress loaded. Run analysis first.")
            sys.exit(1)

        self.pipeline = pipeline
        self.phase3 = phase3

        # Expand stages from stage plan if --end-stage increased
        self._ensure_stages_from_plan(phase3, max_stages)

        # Force baseline only when --start-phase 2 is explicitly requested.
        # --end-stage 0 ("baseline only, stop") is handled by the [STOP]
        # branch below — it must NOT force-rerun an already-validated
        # baseline that the fresh-start path's run_baseline_production just
        # produced + committed (would waste a full LLM call + emit a
        # redundant "Phase 2 baseline (recovery)" commit). When phase_2 is
        # genuinely incomplete on resume, the line 1760 `not is_done`
        # check still triggers the recovery path with force_baseline=False,
        # which routes through the "files present, validating" branch.
        force_baseline = self.start_phase == "2"

        # Force baseline if --start-phase 2
        if force_baseline:
            pipeline.set_phase("phase_2", PHASE_RUNNING)
            pipeline.save(self.project_root)

        # Enter the extraction branch FIRST, then run baseline rerun +
        # loop inside ``try`` — ``finally`` below guarantees the working
        # tree returns to ``main`` on every exit path (normal completion,
        # BLOCKED, --end-stage stop, keyboard interrupt, exception, or
        # ``sys.exit`` from branch creation failure). Baseline rerun
        # commits land on the extraction branch, not main, honoring the
        # "extraction data only on extraction branch" rule. See
        # ai_context/architecture.md §Git Branch Model.
        try:
            # Create extraction branch
            if pipeline.extraction_branch:
                if not create_extraction_branch(self.project_root,
                                                pipeline.extraction_branch):
                    print("[ERROR] Cannot create extraction branch.")
                    sys.exit(1)

            # Check if baseline production was completed — if not, run it now
            work_dir = self.project_root / "works" / pipeline.work_id
            fixed_rel = (work_dir / "world" / "foundation"
                         / "fixed_relationships.json")
            if not pipeline.is_done("phase_2") or (
                    force_baseline and not fixed_rel.exists()):
                foundation = (work_dir / "world" / "foundation"
                              / "foundation.json")
                identities_ok = all(
                    (work_dir / "characters" / c / "canon" / "identity.json"
                     ).exists()
                    for c in pipeline.target_characters
                )
                if (foundation.exists() and identities_ok
                        and fixed_rel.exists() and not force_baseline):
                    # Files exist from a prior partial run — still must pass
                    # Phase 2 exit validation before marking done. File
                    # presence alone does not guarantee schema / required-
                    # field correctness; external damage or stale baseline
                    # formats must be caught here rather than silently
                    # slipping into Phase 3. See requirements.md §11.7
                    # "Baseline 恢复".
                    print("  [OK] Baseline files already present — validating.")
                    baseline_report = validate_baseline(
                        self.project_root, self.work_id,
                        pipeline.target_characters)
                    print(baseline_report.summary())
                    accept = baseline_report.passed
                    if not accept:
                        # Length-bound tolerance gate (decision #48).
                        # Existing baseline may have been written by a
                        # tolerance-accepted Phase 2 run; re-validate
                        # with relaxed schema before deciding to re-run.
                        tolerance_report = validate_baseline(
                            self.project_root, self.work_id,
                            pipeline.target_characters,
                            length_tolerance=0.10)
                        if tolerance_report.passed:
                            print("  [LENGTH-TOLERANCE] Existing "
                                  "baseline accepted by length-bound "
                                  "tolerance gate (decision #48).")
                            accept = True
                    if not accept:
                        print("  [WARN] Existing baseline failed validation. "
                              "Re-running Phase 2 to repair.")
                        _guard_phase2_rewrite_against_phase3(
                            self.project_root, pipeline.work_id,
                            context="validation-triggered recovery")
                        self.run_baseline_production(pipeline.target_characters)
                        sha = commit_stage(
                            self.project_root, "baseline",
                            work_id=pipeline.work_id,
                            message="Phase 2 baseline (validation-triggered "
                                    "recovery)")
                        if sha is None:
                            print(
                                "\n[ERROR] Baseline validation-triggered "
                                "recovery produced no commit SHA (commit "
                                "failed or empty status). Refusing to "
                                "proceed to Phase 3 with a dirty / "
                                "uncommitted baseline (decision #58 / M3).")
                            sys.exit(1)
                        print(f"  [OK] Baseline committed as {sha}")
                        pipeline.mark_done("phase_2")
                        pipeline.save(self.project_root)
                    else:
                        pipeline.mark_done("phase_2")
                        pipeline.save(self.project_root)
                else:
                    print("  [WARN] Baseline not completed. Running Phase 2...")
                    # Decision #56: covers --start-phase 2 force_baseline path
                    # too. When phase 2 is genuinely first-time (force_baseline
                    # False and files missing), the guard helper is a no-op
                    # because phase 3 cannot have committed artifacts yet.
                    _guard_phase2_rewrite_against_phase3(
                        self.project_root, pipeline.work_id,
                        context=("--start-phase 2 force_baseline"
                                 if force_baseline
                                 else "baseline files missing on resume"))
                    self.run_baseline_production(pipeline.target_characters)
                    # Commit baseline so extraction starts with clean tree
                    sha = commit_stage(self.project_root, "baseline",
                                       work_id=pipeline.work_id,
                                       message="Phase 2 baseline (recovery)")
                    if sha is None:
                        print(
                            "\n[ERROR] Baseline recovery commit produced "
                            "no SHA (commit failed or empty status). "
                            "Refusing to proceed to Phase 3 with a dirty "
                            "/ uncommitted baseline (decision #58 / M3).")
                        sys.exit(1)
                    print(f"  [OK] Baseline committed as {sha}")
                    pipeline.mark_done("phase_2")
                    pipeline.save(self.project_root)

            # --end-stage 0: baseline only, stop here
            if max_stages is not None and max_stages == 0:
                print("\n[STOP] --end-stage 0: baseline only, skipping "
                      "extraction loop.")
                return

            # Auto-reset ERROR stages on resume — user chose to retry.
            # FAILED transitions to ERROR first, then ERROR → PENDING.
            for b in phase3.stages:
                if b.state == StageState.FAILED:
                    b.transition(StageState.ERROR)
                if b.state == StageState.ERROR:
                    print(f"  [RESET] {b.stage_id} was in ERROR state, "
                          f"resetting to PENDING.")
                    b.transition(StageState.PENDING)
                    b.error_message = ""
                    b.last_reviewer_feedback = ""
                    b.fail_source = ""
                    phase3.save(self.project_root)

            completed_before = phase3.completed_stage_count()
            tracker = ProgressTracker(len(phase3.stages), completed_before)

            print(f"\n{'=' * 60}")
            print("  Phase 3: Extraction Loop")
            print(f"{'=' * 60}")
            print(f"  Work: {pipeline.work_id}")
            print(f"  Characters: {pipeline.target_characters}")
            print(f"  Total stages: {tracker.total}")
            print(f"  Completed: {completed_before}")
            if max_stages is not None and max_stages > 0:
                to_run = max(0, max_stages - completed_before)
                print(f"  Target: {max_stages} (up to {to_run} this run)")
            else:
                print(f"  Target: all ({tracker.remaining} remaining)")
            print(f"{'=' * 60}")

            stopped_by_limit = False   # --end-stage 前缀试跑命中
            all_done = False           # 全部 stage 均已 COMMITTED

            while True:
                if self._interrupted:
                    break

                if self._check_runtime_limit():
                    break

                if (max_stages is not None and max_stages > 0
                        and tracker.completed >= max_stages):
                    print(f"\n[STOP] Reached max_stages limit "
                          f"({tracker.completed}/{max_stages}).")
                    stopped_by_limit = True
                    break

                stage = phase3.next_pending_stage()
                if stage is None:
                    if phase3.all_committed():
                        print("\n[DONE] All stages completed!")
                        all_done = True
                    else:
                        print("\n[BLOCKED] No actionable stages. "
                              "Check progress for blocked/error stages.")
                    break

                self._process_stage(phase3, pipeline, stage, tracker)

            # Post-loop: Phase 3.5 / squash-merge / Phase 4 only when all
            # stages are COMMITTED. A --end-stage prefix run stops short
            # and skips every finalization step — the user must re-run
            # without --end-stage. See requirements.md §11.5.
            if all_done:
                consistency_ok = self._run_consistency_check()
                self._offer_squash_merge()
                if consistency_ok:
                    self._run_scene_archive(end_stage=0, resume=True)
                else:
                    print("\n  Phase 4 skipped — fix consistency errors "
                          "first, then re-run with --resume.")
            elif stopped_by_limit:
                remaining = sum(
                    1 for s in phase3.stages
                    if s.state != StageState.COMMITTED
                )
                print(f"\n  [PREFIX-RUN] Stopped at --end-stage limit with "
                      f"{remaining} stage(s) remaining.")
                print("  Phase 3.5 / squash-merge / Phase 4 are skipped "
                      "until all stages commit.")
                print("  Re-run without --end-stage (or with a larger "
                      "value) to finalize.")

            tracker.print_summary()
        finally:
            if pipeline.extraction_branch:
                checkout_main(
                    self.project_root,
                    scope_paths=[f"works/{pipeline.work_id}/"])

    def _process_stage(self, phase3: Phase3Progress,
                       pipeline: PipelineProgress,
                       stage: StageEntry,
                       tracker: ProgressTracker) -> None:
        """Process a single stage through the full pipeline."""
        tracker.start_stage()
        tracker.print_stage_header(stage)

        work_root = self.project_root / "works" / pipeline.work_id

        def _log_lane_failure(lane_type: str, lane_id: str,
                              prompt_length: int):
            def _cb(result: LLMResult, _attempt: int) -> None:
                try:
                    path = write_failed_lane_log(
                        work_root, stage.stage_id, lane_type, lane_id,
                        result, prompt_length)
                    if path is not None:
                        print(f"    [LOG] {lane_type}:{lane_id} failure → "
                              f"{path.relative_to(self.project_root)}")
                except Exception:  # noqa: BLE001
                    logger.exception("failed to write lane failure log")
            return _cb

        def _verify_lane(lane_name: str, result: LLMResult) -> LLMResult:
            """On subprocess success, verify the lane's product JSON parses.
            A missing or unparseable product downgrades the result to a
            failure so the caller tags the lane as incomplete in
            `lane_states`."""
            if not result.success:
                return result
            ok, why = verify_lane_output(
                work_root, stage.stage_id, lane_name)
            if not ok:
                result.success = False
                result.error = f"output verify failed: {why}"
            return result

        # Per-process extraction closures — used by the parallel
        # extraction (Step 2). Each accepts an optional reviewer feedback
        # string (passed on resume after a repair-agent FAIL). Each
        # returns (process_type, process_id, result) where result.success
        # is set only after subprocess success AND product JSON parse.
        def _extract_world(
            feedback: str = "",
        ) -> tuple[str, str, LLMResult]:
            prompt = build_world_extraction_prompt(
                self.project_root, pipeline, stage,
                stages=phase3.stages,
                reviewer_feedback=feedback)
            result = run_with_retry(
                self.backend, prompt,
                timeout_seconds=get_config().phase3.extraction_timeout_s,
                lane_name="world",
                on_failure=_log_lane_failure("world", "world", len(prompt)))
            result = _verify_lane("world", result)
            return "world", "world", result

        def _extract_char_snapshot(
            char_id: str,
            feedback: str = "",
        ) -> tuple[str, str, LLMResult]:
            if self.char_snapshot_sub_lanes:
                result = self._run_char_snapshot_sub_lanes(
                    pipeline=pipeline,
                    stage=stage,
                    stages=phase3.stages,
                    character_id=char_id,
                    work_root=work_root,
                    feedback=feedback,
                    log_lane_failure=_log_lane_failure,
                )
                result = _verify_lane(f"snapshot:{char_id}", result)
                return "char_snapshot", char_id, result
            prompt = build_char_snapshot_prompt(
                self.project_root, pipeline, stage, char_id,
                stages=phase3.stages,
                reviewer_feedback=feedback)
            result = run_with_retry(
                self.backend, prompt,
                timeout_seconds=get_config().phase3.extraction_timeout_s,
                lane_name=f"char_snapshot:{char_id}",
                on_failure=_log_lane_failure(
                    "char_snapshot", char_id, len(prompt)))
            result = _verify_lane(f"snapshot:{char_id}", result)
            return "char_snapshot", char_id, result

        def _extract_char_support(
            char_id: str,
            feedback: str = "",
        ) -> tuple[str, str, LLMResult]:
            prompt = build_char_support_prompt(
                self.project_root, pipeline, stage, char_id,
                stages=phase3.stages,
                reviewer_feedback=feedback)
            result = run_with_retry(
                self.backend, prompt,
                timeout_seconds=get_config().phase3.extraction_timeout_s,
                lane_name=f"char_support:{char_id}",
                on_failure=_log_lane_failure(
                    "char_support", char_id, len(prompt)))
            result = _verify_lane(f"support:{char_id}", result)
            return "char_support", char_id, result

        def _lane_key(proc_type: str, proc_id: str) -> str:
            """Map closure-return identifiers to lane_states keys."""
            if proc_type == "world":
                return "world"
            if proc_type == "char_snapshot":
                return f"snapshot:{proc_id}"
            if proc_type == "char_support":
                return f"support:{proc_id}"
            raise ValueError(f"unknown proc_type: {proc_type}")

        # Handle state resumption — reset interrupted states.
        # No stage-level retry: FAILED/ERROR are terminal within a run.
        # --resume resets ERROR → PENDING (handled in run_extraction_loop).
        if stage.state in (StageState.FAILED, StageState.ERROR):
            print(f"  [BLOCKED] {stage.stage_id} in {stage.state.value} "
                  f"state. Use --resume to reset.")
            return

        if stage.state == StageState.EXTRACTING:
            # Partial-resume path: do not rollback. Completed lanes (if any)
            # live in stage.lane_states; their products stay on disk. The
            # PENDING branch below rebuilds the missing-lane set.
            print("  [RESUME] Interrupted during extraction, "
                  "preserving completed lanes and resuming...")
            stage.force_reset_to_pending(
                "resume from interrupted EXTRACTING")
            phase3.save(self.project_root)

        if stage.state == StageState.PASSED:
            # Interrupted after lanes + gate PASS but before git commit.
            # Before jumping to the git-commit step, verify the 1+2N
            # per-stage products still exist on disk. If any file was
            # deleted externally between PASSED and COMMITTED, a blind
            # ``git add -A works/`` would stage the deletions and poison
            # the extraction branch — escalate to FAILED → ERROR instead
            # so the operator can restore the files (or decide next step)
            # before resuming.
            if not self._extraction_output_exists(
                    pipeline.target_characters, stage):
                print("  [RESUME] PASSED stage missing on-disk products; "
                      "escalating to FAILED (operator must restore files "
                      "or run --resume after replacing them).")
                stage.error_message = (
                    "stage products missing after gate PASS — refusing to "
                    "commit deletions")
                stage.fail_source = "external_delete"
                stage.transition(StageState.FAILED)
                stage.transition(StageState.ERROR)
                phase3.save(self.project_root)
                return
            print("  [RESUME] Interrupted after gate PASS, "
                  "jumping to git commit step.")

        if stage.state == StageState.PENDING:
            # Reconcile lane_states with disk before deciding what to run:
            # a marker whose product file vanished (external delete, manual
            # cleanup) must not be trusted.
            for lane_name in list(stage.lane_states.keys()):
                ok, _why = verify_lane_output(
                    work_root, stage.stage_id, lane_name)
                if not ok:
                    stage.reset_lane(lane_name)
            if stage.lane_states:
                phase3.save(self.project_root)

            is_partial_resume = bool(stage.lane_states)

            # --- Step 1: Git preflight ---
            tracker.start_step()
            tracker.print_step(1, 5, "Git preflight")
            ignore_patterns = ["extraction_progress.json",
                               "pipeline.json", "phase3_stages.json",
                               "__pycache__"]
            if is_partial_resume:
                # Already-completed lane products are legitimate dirty
                # files during a partial resume; so are baseline files
                # that an incomplete support lane may have partially
                # touched (we reset them to HEAD before re-running).
                ignore_patterns.extend(expected_lane_dirty_paths(
                    work_root, stage.stage_id,
                    pipeline.target_characters))
            problems = preflight_check(
                self.project_root, pipeline.extraction_branch or None,
                ignore_patterns=ignore_patterns,
                scope_paths=[f"works/{pipeline.work_id}/"])
            if problems:
                for p in problems:
                    print(f"    [PROBLEM] {p}")
                stage.transition(StageState.ERROR)
                stage.error_message = "; ".join(problems)
                phase3.save(self.project_root)
                return
            tracker.print_step_done(1, 5, "Git preflight")

            # --- Smart skip: if all lane products on disk AND parse ---
            # `_extraction_output_exists` runs verify_lane_output on every
            # expected lane. When it returns True, the files are legitimate
            # lane output — auto-backfill any missing lane_states markers
            # so partial-resume logic stays consistent for older progress
            # files written before T-RESUME.
            if self._extraction_output_exists(
                    pipeline.target_characters, stage):
                print(f"  [SKIP] All lane outputs present for "
                      f"{stage.stage_id}, jumping to post-processing")
                for n in expected_lane_names(pipeline.target_characters):
                    if not stage.is_lane_complete(n):
                        stage.mark_lane_complete(n)
                stage.transition(StageState.EXTRACTED)
                phase3.save(self.project_root)
            else:
                # --- Step 2: Extract only missing lanes ---
                lanes_to_run = stage.missing_lanes(
                    pipeline.target_characters)
                n_chars = len(pipeline.target_characters)
                # Outer lanes (world / snapshot:* / support:*) all run
                # in parallel. sub-lane fan-out only expands inside
                # snapshot:* lanes; peak LLM concurrency is
                # 1 + N_chars*4 + N_chars when sub-lanes on, 1+2*N_chars
                # when off — decision #55 4-sub-lane topology, cap = 12
                # (raised from 10 in the 3-sub-lane era).
                n_workers = max(1, len(lanes_to_run))
                tracker.start_step()
                if is_partial_resume:
                    skipped = [n for n in expected_lane_names(
                        pipeline.target_characters)
                        if n not in lanes_to_run]
                    tracker.print_step(
                        2, 5,
                        f"Extraction (partial resume: "
                        f"{len(lanes_to_run)}/{1 + 2 * n_chars} lanes; "
                        f"skipping {len(skipped)} complete)")
                else:
                    tracker.print_step(2, 5,
                                       f"Extraction (1 world + "
                                       f"{n_chars} snapshot + "
                                       f"{n_chars} support parallel)")
                stage.transition(StageState.EXTRACTING)
                phase3.save(self.project_root)

                # Before re-running a support lane, restore that
                # character's 5 cumulative baseline files to HEAD so any
                # partial write from the prior interrupted attempt is
                # undone. No-op when the support lane is a fresh run
                # (HEAD already reflects the last committed baseline).
                for lane_name in lanes_to_run:
                    if lane_name.startswith("support:"):
                        char_id = lane_name[len("support:"):]
                        reset_paths(
                            self.project_root,
                            baseline_paths(work_root, char_id))

                extraction_errors: list[str] = []

                # Pre-launch token-limit gate (§11.13.2): block here if
                # another lane already recorded a pause. Lanes that hit
                # the limit mid-flight pause inside run_with_retry; this
                # gate prevents a fresh batch from launching during an
                # active pause window.
                self._rate_limit.wait_if_paused()

                with ThreadPoolExecutor(
                        max_workers=n_workers) as executor:
                    futures = []
                    for lane_name in lanes_to_run:
                        if lane_name == "world":
                            futures.append(
                                executor.submit(_extract_world))
                        elif lane_name.startswith("snapshot:"):
                            c = lane_name[len("snapshot:"):]
                            futures.append(executor.submit(
                                _extract_char_snapshot, c))
                        elif lane_name.startswith("support:"):
                            c = lane_name[len("support:"):]
                            futures.append(executor.submit(
                                _extract_char_support, c))
                    for future in as_completed(futures):
                        try:
                            proc_type, proc_id, result = future.result()
                        except RateLimitHardStop:
                            # Cancel siblings (1+2N lanes at N-char peak)
                            # so the implicit ``with`` exit doesn't block
                            # on still-sleeping lanes (decision #55 R2).
                            executor.shutdown(
                                wait=False, cancel_futures=True)
                            raise
                        lane_key = _lane_key(proc_type, proc_id)
                        if result.success:
                            stage.mark_lane_complete(lane_key)
                            phase3.save(self.project_root)
                        else:
                            extraction_errors.append(
                                f"{proc_type}:{proc_id}: "
                                f"{result.error or 'unknown'}")
                            print(f"    [ERROR] {proc_type}:{proc_id} "
                                  f"extraction failed: {result.error}")

                if not stage.all_lanes_complete(
                        pipeline.target_characters):
                    # Any lane still missing → stage ERROR, but
                    # successful lane products + lane_states are
                    # preserved for --resume.
                    stage.transition(StageState.ERROR)
                    stage.error_message = "; ".join(extraction_errors)
                    phase3.save(self.project_root)
                    return

                tracker.record_step(ProgressTracker.STEP_EXTRACTION)
                tracker.print_step_done(2, 5,
                                        f"Extraction "
                                        f"(1+{2 * n_chars} parallel)")

                stage.transition(StageState.EXTRACTED)
                phase3.save(self.project_root)

        # --- Step 3: Programmatic post-processing ---
        if stage.state in (StageState.EXTRACTED, StageState.POST_PROCESSING):
            if stage.state == StageState.EXTRACTED:
                stage.transition(StageState.POST_PROCESSING)
                phase3.save(self.project_root)

            tracker.start_step()
            tracker.print_step(3, 5, "Post-processing (digest + catalog)")

            pp_errors, pp_warnings = run_stage_post_processing(
                project_root=self.project_root,
                work_id=pipeline.work_id,
                stage_id=stage.stage_id,
                character_ids=pipeline.target_characters,
                chapter_range=stage.chapters,
            )

            for w in pp_warnings:
                print(f"    [WARN] {w}")

            if pp_errors:
                # Missing or unparsable extraction output — the repair
                # gate cannot meaningfully inspect absent files, so treat
                # as stage FAIL → ERROR. Products are preserved on disk
                # per §11.5 contract; --resume re-attempts the stage.
                for e in pp_errors:
                    print(f"    [ERROR] {e}")
                tracker.record_step(ProgressTracker.STEP_VALIDATION)
                tracker.print_step_done(
                    3, 5, "Post-processing",
                    f"{len(pp_errors)} errors, {len(pp_warnings)} warnings")
                stage.error_message = (
                    "post-processing blocked: "
                    + "; ".join(pp_errors)[:500])
                stage.transition(StageState.REVIEWING)
                stage.transition(StageState.FAILED)
                stage.transition(StageState.ERROR)
                phase3.save(self.project_root)
                return

            tracker.record_step(ProgressTracker.STEP_VALIDATION)
            tracker.print_step_done(
                3, 5, "Post-processing",
                f"{len(pp_warnings)} warnings")

            stage.transition(StageState.REVIEWING)
            phase3.save(self.project_root)

        # --- Step 4: Repair agent (check → fix → verify) ---
        if stage.state == StageState.REVIEWING:
            # Safety check: every 1+2N per-stage product (world snapshot +
            # each char's stage_snapshot and memory_timeline) must be
            # present and JSON-parseable. The prior directory-only check
            # could let a missing current-stage file slip through and
            # reach the repair framework with an incomplete file list.
            work_dir = self.project_root / "works" / pipeline.work_id
            if not self._extraction_output_exists(
                    pipeline.target_characters, stage):
                print("  [RESUME] Extraction output missing for REVIEWING "
                      "stage, clearing lane_states and restarting...")
                stage.clear_lane_states()
                stage.force_reset_to_pending(
                    "resume from REVIEWING without on-disk output")
                phase3.save(self.project_root)
                return

            tracker.start_step()
            tracker.print_step(4, 5, "Repair agent")

            # Build file list for repair agent. Stage number is the
            # 1-indexed position of this stage in the plan, used to filter
            # accumulated digest files (IDs carry S{stage_num:03d} segment).
            stage_num = next(
                (i + 1 for i, b in enumerate(phase3.stages)
                 if b.stage_id == stage.stage_id), 1)
            repair_files = self._collect_stage_files(
                work_dir, stage.stage_id, stage_num,
                pipeline.target_characters)

            # Build source context for T2/T3 fixes
            source_ctx = SourceContext(
                work_path=str(work_dir),
                stage_id=stage.stage_id,
                chapter_summaries_dir=str(
                    work_dir / "analysis" / "chapter_summaries"),
                chapters_dir=str(
                    self.project_root / "sources" / "works"
                    / pipeline.work_id / "chapters"),
            )

            # LLM callable for semantic checker + T1/T2/T3 fixers.
            # On backend failure (token limit, retry exhausted, etc.) we
            # raise SemanticReviewLLMUnavailable so the L3 checker turns
            # it into a blocking issue instead of a silent pass. Other
            # call sites (T1/T2/T3 fixers) likewise see a hard error
            # rather than an empty string.
            default_timeout = get_config().phase3.review_timeout_s

            def _llm_call(prompt: str, timeout: int | None = None) -> str:
                result = run_with_retry(
                    self.reviewer_backend or self.backend,
                    prompt,
                    timeout_seconds=timeout or default_timeout,
                    lane_name=f"repair[{stage.stage_id}]",
                )
                if not result.success:
                    raise SemanticReviewLLMUnavailable(
                        result.error or "LLM call failed")
                return result.text

            importance_map = load_importance_map(
                self.project_root, pipeline.work_id)

            ra_cfg = get_config().repair

            # Per-file parallel repair (E1). Each file becomes an
            # independent repair transaction with its own coordinator.run
            # invocation, recorder, and tracker. Files are dispatched to a
            # ThreadPoolExecutor sized by [repair].repair_concurrency.
            # coordinator.run is untouched — it's already pure per-file
            # logic; we just call it N times in parallel instead of once
            # with N files. See docs/architecture/extraction_workflow.md
            # repair section for the wider picture.
            progress_dir = work_root / "analysis" / "progress"

            def _repair_cfg() -> RepairConfig:
                return RepairConfig(
                    max_rounds=ra_cfg.total_round_limit,
                    run_semantic=True,
                    triage_enabled=ra_cfg.triage_enabled,
                    accept_cap_per_file=ra_cfg.triage_accept_cap_per_file,
                    retry_policy=RetryPolicy(
                        t0_max=ra_cfg.t0_retry,
                        t1_max=ra_cfg.t1_retry,
                        t2_max=ra_cfg.t2_retry,
                        max_total_rounds=ra_cfg.total_round_limit,
                    ),
                )

            repair_logs_dir = progress_dir / "repair_logs"
            repair_logs_dir.mkdir(parents=True, exist_ok=True)

            def _repair_one(f: RepairFileEntry) -> tuple[
                    RepairFileEntry, RepairResult]:
                rec_path = repair_logs_dir / (
                    f"repair_{stage.stage_id}_"
                    f"{_repair_slug(f.path)}.jsonl")
                with RepairRecorder(rec_path) as recorder:
                    result = run_repair(
                        files=[f],
                        config=_repair_cfg(),
                        source_context=source_ctx,
                        llm_call=_llm_call,
                        importance_map=importance_map,
                        recorder=recorder,
                    )
                return f, result

            repair_concurrency = max(1, ra_cfg.repair_concurrency)
            print(f"  [4/5] Repair agent ({len(repair_files)} files, "
                  f"up to {repair_concurrency} parallel)...")
            per_file_results: list[tuple[RepairFileEntry, RepairResult]] = []
            with ThreadPoolExecutor(
                    max_workers=repair_concurrency) as pool:
                repair_futures: dict[Future, RepairFileEntry] = {
                    pool.submit(_repair_one, f): f for f in repair_files
                }
                for fut in as_completed(repair_futures):
                    submitted = repair_futures[fut]
                    try:
                        per_file_results.append(fut.result())
                    except RateLimitHardStop:
                        # Propagate hard stop to the main thread; CLI
                        # exit-2 contract per docs/requirements.md §11.13.
                        # Cancel siblings so the implicit ``with`` exit
                        # doesn't block on still-sleeping repair workers
                        # (decision #55 R2 pattern).
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise
                    except Exception as exc:  # noqa: BLE001
                        # Worker raised (e.g. context_retriever ERR,
                        # unreadable file). Don't abort the whole pool —
                        # mark this file failed and let siblings finish.
                        logger.exception(
                            "Repair worker raised for %s", submitted.path)
                        synthetic = RepairResult(
                            passed=False,
                            issues=[],
                            report=f"worker exception: {exc!r}",
                        )
                        per_file_results.append((submitted, synthetic))

            all_pass = all(r.passed for _, r in per_file_results)
            failed_entries = [
                (f, r) for f, r in per_file_results if not r.passed]
            merged_issues = [
                i for _, r in per_file_results for i in r.issues]

            tracker.record_step(ProgressTracker.STEP_REVIEW)

            # Record-and-continue gate (decision #60, extended by
            # T-REPAIR-NO-REEXTRACT). When enabled and every remaining
            # error issue is deferrable (semantic / schema / structural /
            # cross_file — anything the capped tiers couldn't fix), defer
            # them to a durable ledger and let the stage commit instead of
            # failing; a later Phase 3.5 fix pass repairs them precisely
            # without re-extracting. A json_syntax error (unparseable file)
            # or a repair worker exception (no error issues) still forces
            # ERROR — those break downstream reads.
            deferrable: list | None = None
            if (not all_pass
                    and get_config().repair.defer_unresolved_semantic):
                deferrable = deferrable_issues(failed_entries)

            if all_pass:
                tracker.print_step_done(
                    4, 5, "Repair agent", "PASS")
            elif deferrable:
                write_deferred_repairs(
                    work_root, stage.stage_id, deferrable)
                tracker.print_step_done(
                    4, 5, "Repair agent",
                    f"DEFER — {len(deferrable)} issue(s) recorded "
                    f"to deferred_repairs/{stage.stage_id}.jsonl")
                for f, r in failed_entries:
                    print(f"    [DEFER] {f.path}")
                # Deferred issues are not a stage failure: clear any prior
                # error_message and fall through to the PASS path (post-
                # repair PP rerun → PASSED → commit).
                stage.error_message = ""
            else:
                n_errors = sum(
                    1 for i in merged_issues if i.severity == "error")
                tracker.print_step_done(
                    4, 5, "Repair agent",
                    f"FAIL — {len(failed_entries)} file(s), "
                    f"{n_errors} error(s) remaining")
                for f, r in failed_entries:
                    print(f"    [FAIL] {f.path}")
                    if r.report:
                        print(r.report)
                # Per requirements §11.5: repair FAIL does NOT roll back
                # extraction output. Artifacts stay on disk for human
                # inspection; --resume re-runs the repair loop (smart
                # skip bypasses extraction if files are already present).
                stage.error_message = "; ".join(
                    f"{f.path}: {(r.report or '').splitlines()[0][:80]}"
                    for f, r in failed_entries
                )[:2000]
                stage.transition(StageState.FAILED)
                stage.transition(StageState.ERROR)
                phase3.save(self.project_root)
                return

            # Post-repair post-processing rerun — MUST run before the
            # PASSED transition. Repair may have rewritten source fields
            # that post-processing already consumed
            # (memory_timeline.digest_summary, world stage_events,
            # character stage_events); re-running the idempotent 0-token
            # pass refreshes memory_digest.jsonl /
            # world_event_digest.jsonl / stage_catalog.json so derived
            # digests stay 1:1 with the repaired source. Placing it
            # before transition(PASSED) keeps the state invariant tight:
            # PASSED means "repair passed AND PP is synchronised". A
            # SIGKILL mid-rerun leaves state=REVIEWING, so --resume
            # re-enters Step 4 (repair is idempotent) and reruns PP —
            # the PASSED-resume branch never sees a half-synced state.
            pp2_errors, pp2_warnings = run_stage_post_processing(
                project_root=self.project_root,
                work_id=pipeline.work_id,
                stage_id=stage.stage_id,
                character_ids=pipeline.target_characters,
                chapter_range=stage.chapters,
            )
            for w in pp2_warnings:
                print(f"    [WARN] post-repair PP: {w}")
            if pp2_errors:
                for e in pp2_errors:
                    print(f"    [ERROR] post-repair PP: {e}")
                stage.error_message = (
                    "post-repair PP: " + "; ".join(pp2_errors)[:1980]
                    if pp2_errors
                    else "post-repair post-processing failed")
                stage.transition(StageState.FAILED)
                stage.transition(StageState.ERROR)
                phase3.save(self.project_root)
                return

            stage.transition(StageState.PASSED)
            phase3.save(self.project_root)

            # Prev snapshot slice cleanup (decision #55) — repair has
            # finished consuming the slices via any repair-triggered
            # sub-lane re-extraction, and the upcoming commit will baseline
            # the new snapshot.
            # Keeping slices past commit has no debug value (prev snapshot
            # is in git history + slice is a deterministic projection),
            # so wipe them per-char before the commit step.
            if self.char_snapshot_sub_lanes:
                prev_stage_for_slice = (
                    _find_previous_committed_stage_for_sub_lanes(
                        phase3.stages, stage))
                if prev_stage_for_slice is not None:
                    for char_id in pipeline.target_characters:
                        self._clear_prev_snapshot_slices(
                            work_root, char_id,
                            prev_stage_for_slice.stage_id)


        # --- Step 5: Git commit ---
        if stage.state == StageState.PASSED:
            tracker.start_step()
            tracker.print_step(5, 5, "Git commit")

            # Attempt the git commit first. Only after a real SHA comes back
            # do we transition to COMMITTED. If commit_stage returns None
            # (empty diff or commit failure), treat the stage as FAILED and
            # preserve the progress file so the next resume can retry.
            # See requirements.md §11.4b "提交顺序契约".
            sha = commit_stage(
                self.project_root, stage.stage_id,
                work_id=pipeline.work_id)
            tracker.record_step(ProgressTracker.STEP_COMMIT)

            if not sha:
                print("    [FAIL] Git commit returned no SHA "
                      "(empty diff or commit failure).")
                stage.transition(StageState.FAILED)
                stage.error_message = (
                    "git commit produced no object — aborting COMMITTED "
                    "transition")
                phase3.save(self.project_root)
                tracker.print_step_done(5, 5, "Git commit", "no-op/failed")
                return

            # Commit succeeded — close the crash window by saving the SHA
            # before the COMMITTED transition. If we die between the two
            # saves, reconcile_with_disk() sees state∈terminal ∧ committed_sha
            # present ∧ sha exists in git → auto-promote to COMMITTED.
            stage.committed_sha = sha
            stage.last_reviewer_feedback = ""
            stage.error_message = ""
            stage.fail_source = ""
            phase3.save(self.project_root)
            stage.transition(StageState.COMMITTED)
            phase3.save(self.project_root)

            tracker.print_step_done(5, 5, "Git commit", sha)
            tracker.finish_stage()

    def _run_consistency_check(self) -> bool:
        """Run Phase 3.5 cross-stage consistency check.

        Returns True if no error-level issues found (safe to proceed).
        Returns False if errors exist (should block Phase 4).

        The generated ``consistency_report.json`` is committed to the
        extraction branch before returning — regardless of pass/fail.
        Committing on both paths keeps ``checkout_main`` clean (report
        sits in the work scope) and ensures the squash-merge includes
        the report as documented in current_status.md.
        """
        assert self.pipeline and self.phase3
        print("\n--- Phase 3.5: Cross-stage consistency check ---")
        stage_ids = [b.stage_id for b in self.phase3.stages
                     if b.state.value == "committed"]
        char_ids = self.pipeline.target_characters or []

        report = run_consistency_check(
            self.project_root, self.pipeline.work_id, char_ids, stage_ids)

        # Save + commit the report on the extraction branch. Commit is
        # best-effort — the report save itself is authoritative, the
        # commit is so the file doesn't linger as uncommitted dirt when
        # the orchestrator later attempts checkout_main().
        save_report(report, self.project_root, self.pipeline.work_id)
        self._commit_consistency_report(stage_ids)

        # Print summary
        errors = sum(1 for i in report.issues if i.severity == "error")
        warnings = sum(1 for i in report.issues if i.severity == "warning")
        print(f"  Results: {errors} errors, {warnings} warnings, "
              f"{len(report.issues) - errors - warnings} info")

        if errors > 0:
            print("  [BLOCKED] Errors found — Phase 4 blocked. "
                  "Review consistency_report.json and fix before retrying.")
            for issue in report.issues:
                if issue.severity == "error":
                    print(f"    [ERROR] [{issue.category}] {issue.location}: "
                          f"{issue.message}")
            return False

        print("  [OK] No blocking issues found.")
        return True

    def _commit_consistency_report(self, stage_ids: list[str]) -> None:
        """Commit consistency_report.json on the extraction branch.

        Called right after ``save_report`` in ``_run_consistency_check``.
        A missing commit here would leave the tracked report as
        uncommitted dirt, blocking the final ``checkout_main`` under
        the work scope (see gpt-5 H4).
        """
        assert self.pipeline
        rel = (
            f"works/{self.pipeline.work_id}/analysis/consistency_report.json")
        stage_span = (
            f"{stage_ids[0]}..{stage_ids[-1]}"
            if stage_ids else "no-stages")
        message = (
            f"phase3.5: consistency_report {stage_span}\n\n"
            f"Cross-stage consistency check output.\n"
            f"Automated by persona-extraction orchestrator.")
        try:
            sha = commit_stage(
                self.project_root, "phase3.5",
                work_id=self.pipeline.work_id,
                message=message, files=[rel])
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Consistency report commit raised (non-fatal): %s", exc)
            return
        if sha:
            print(f"  [git] Committed consistency_report as {sha}")
        else:
            # commit_stage returns None when the diff is empty — the
            # report was already committed or the file is unchanged.
            logger.info(
                "Consistency report commit no-op (nothing to commit).")

    def _run_scene_archive(self, *, end_stage: int = 0,
                           resume: bool = True) -> None:
        """Run Phase 4: scene archive generation."""
        _set_run_phase("phase4")
        run_scene_archive(
            self.project_root, self.work_id, self.backend,
            concurrency=self.concurrency,
            end_stage=end_stage,
            resume=resume,
        )

    def _offer_squash_merge(self) -> None:
        """After all stages complete, offer to squash-merge to the
        archive branch (default ``library`` — see ``[git].squash_merge_target``).

        Three-branch model: main is framework-only and never receives
        extraction artefacts; library is the local archive of completed
        works.
        """
        assert self.pipeline and self.phase3
        branch = self.pipeline.extraction_branch
        if not branch:
            return

        target = get_config().git.squash_merge_target

        # Lazy idempotent creation: library is local-only and does not exist
        # in fresh clones, so create it from main on first use.
        existed = branch_exists(self.project_root, target)
        if not ensure_branch_from_main(self.project_root, target):
            print(f"  [ERROR] Cannot ensure target branch '{target}' "
                  f"exists. Squash-merge skipped — create it manually "
                  f"with: git branch {target} main")
            return
        if not existed:
            print(f"  [setup] target branch '{target}' created from main.")

        print(f"\n  All stages committed on branch '{branch}'.")
        print(f"  Squash-merge to '{target}' will consolidate all extraction")
        print("  commits into a single clean commit.")

        if get_config().git.auto_squash_merge:
            print("  [auto] [git].auto_squash_merge = true; merging.")
            answer = "y"
        else:
            try:
                answer = input(
                    f"  Squash-merge to '{target}' now? [Y/n]: "
                ).strip()
            except EOFError:
                answer = "n"

        if answer.lower() == "n":
            print(f"  Skipped. You can manually merge later:\n"
                  f"    git checkout {target} && "
                  f"git merge --squash {branch} && "
                  f"git commit")
            return

        chars = ", ".join(self.pipeline.target_characters)
        n = len(self.phase3.stages)
        message = (f"Extraction complete: {self.pipeline.work_id} "
                   f"({n} stages, {chars})\n\n"
                   f"Squash-merged from {branch}.\n"
                   f"Automated extraction via persona-extraction orchestrator.")

        sha = squash_merge_to(self.project_root, target, branch, message)
        if not sha:
            print(f"  [ERROR] Squash-merge failed. "
                  f"Merge manually from '{branch}'.")
            return

        print(f"  [OK] Squash-merged to '{target}' as {sha}")

        # Branch dispose is destructive — always interactive, even when
        # auto_squash_merge=true. Default N so the user must explicitly opt in.
        try:
            answer = input(
                f"  Delete extraction branch '{branch}' and run "
                f"'git gc --prune=now'? [y/N]: "
            ).strip()
        except EOFError:
            answer = "n"

        if answer.lower() != "y":
            print(f"  Extraction branch '{branch}' preserved. "
                  f"Delete later with: git branch -D {branch} && "
                  f"git gc --prune=now")
            return

        ok, err = delete_branch(self.project_root, branch)
        if not ok:
            print(f"  [ERROR] Cannot delete branch '{branch}': {err}")
            return
        print(f"  [OK] Deleted branch '{branch}'.")

        ok, err = git_gc_prune_now(self.project_root)
        if not ok:
            print(f"  [WARN] git gc reported error: {err}")
        else:
            print("  [OK] Reclaimed unreachable objects via git gc.")

    # ------------------------------------------------------------------
    # Stage expansion (like Phase 4: always derive targets from plan)
    # ------------------------------------------------------------------

    def _ensure_stages_from_plan(
        self,
        phase3: Phase3Progress,
        max_stages: int | None = None,
    ) -> None:
        """Ensure progress contains all target stages from the stage plan.

        Like Phase 4's chapter expansion pattern: every run re-reads the
        stage plan and appends any stages not yet tracked.  Existing
        stage states are preserved.

        Drift protection: the existing phase3 progress must be a prefix of
        the plan (stage_ids must match position-for-position up to the
        length of phase3.stages). If the user edited stage_plan.json in a
        way that renames or removes an already-tracked stage, we abort
        rather than silently append a divergent tail. The fix is to
        restore the plan or to restart Phase 3 explicitly.
        """
        plan_path = (self.project_root / "works" / self.work_id
                     / "analysis" / "stage_plan.json")
        if not plan_path.exists():
            return

        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        full_stages = plan.get("stages", [])
        plan_ids = [b.get("stage_id") for b in full_stages]

        # --- Drift detection: plan must match existing phase3 prefix ---
        existing_ids = [b.stage_id for b in phase3.stages]
        limit = min(len(existing_ids), len(plan_ids))
        mismatches: list[tuple[int, str, str]] = []
        for i in range(limit):
            if existing_ids[i] != plan_ids[i]:
                mismatches.append((i, existing_ids[i], plan_ids[i]))

        missing_from_plan = [
            sid for sid in existing_ids if sid not in plan_ids]

        if mismatches or missing_from_plan:
            lines = ["[ERROR] stage_plan.json diverges from phase3 progress."]
            for i, old, new in mismatches:
                lines.append(f"  position {i}: progress='{old}' plan='{new}'")
            for sid in missing_from_plan:
                lines.append(f"  missing from plan: '{sid}'")
            lines.append(
                "  Existing progress is not a prefix of the current plan. "
                "Restore stage_plan.json, or restart Phase 3 by deleting "
                "works/{work_id}/analysis/progress/phase3_stages.json.")
            print("\n".join(lines))
            sys.exit(1)

        current_count = len(phase3.stages)
        effective_max = max_stages if (max_stages is not None
                                        and max_stages > 0) else 0
        added = phase3.expand_stages(full_stages,
                                      max_stages=effective_max)
        if added > 0:
            phase3.save(self.project_root)
            print(f"  [EXPAND] Added {added} new stages from stage plan "
                  f"({current_count} → {len(phase3.stages)})")

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run_full(
        self,
        *,
        preset_characters: list[str] | None = None,
        preset_end_stage: int | None = None,
        auto_resume: bool = False,
    ) -> None:
        """Run the complete pipeline: analysis → confirm → extract.

        ``auto_resume`` (decision #51): when True, silence the
        ``Resume from existing progress? [Y/n]`` interactive prompt and
        proceed as if the user answered "yes". Phase-level skip /
        self-heal logic in ``run_summarization`` /
        ``Phase3Progress.reconcile_with_disk`` / etc. is unchanged —
        ``--resume`` only mutes this single confirmation.
        """
        pipeline: PipelineProgress | None
        phase3: Phase3Progress | None
        # Check for legacy progress and migrate if needed
        legacy_result = migrate_legacy_progress(
            self.project_root, self.work_id)
        if legacy_result:
            pipeline, phase3 = legacy_result
            print(f"[MIGRATE] Migrated legacy progress for {self.work_id}.")
        else:
            # Try loading new-format progress
            pipeline = PipelineProgress.load(
                self.project_root, self.work_id)
            phase3 = Phase3Progress.load(
                self.project_root, self.work_id)

        # Self-heal: if Phase 1.5 is done and stage_plan exists but
        # phase3_stages.json was deleted/corrupted, rebuild from stage_plan
        # rather than falling through to the fresh-start path (which would
        # re-prompt for characters and overwrite pipeline.json).
        if (pipeline and pipeline.is_done("phase_1_5") and phase3 is None):
            stage_plan_path = (self.project_root / "works" / self.work_id
                               / "analysis" / "stage_plan.json")
            if stage_plan_path.exists():
                stage_plan_data = _load_json(stage_plan_path) or {}
                phase3 = Phase3Progress(
                    work_id=self.work_id,
                    stages=[
                        StageEntry(
                            stage_id=b["stage_id"],
                            chapters=b["chapters"],
                            chapter_count=b.get("chapter_count", 10),
                            stage_title=b.get("stage_title", ""),
                        )
                        for b in stage_plan_data.get("stages", [])
                    ],
                )
                phase3.save(self.project_root)
                print(f"[REBUILT] phase3_stages.json from stage_plan.json "
                      f"({len(phase3.stages)} stages, all pending).")

        if pipeline is not None and phase3 is not None:
            rec = phase3.reconcile_with_disk(
                self.project_root, pipeline.target_characters)
            if rec["reverted"] or rec["purged_files"]:
                print(f"[RECONCILE] Phase 3: reverted {rec['reverted']} "
                      f"stage(s), purged {rec['purged_files']} stale "
                      f"artifact(s), {rec['sha_missing']} committed_sha "
                      f"missing from git")
                phase3.save(self.project_root)

        if pipeline and phase3 and pipeline.is_done("phase_1_5"):
            print(f"Found existing progress for {self.work_id}.")
            print(f"  Completed: {phase3.completed_stage_count()}"
                  f"/{len(phase3.stages)}")
            # Non-interactive paths: preset characters or auto_resume signal
            # both skip the [Y/n] prompt and continue into the extraction loop.
            if preset_characters or auto_resume:
                if auto_resume:
                    print("  Auto-resuming (--resume passed).")
                else:
                    print("  Auto-resuming (preset characters provided).")
                self.pipeline = pipeline
                self.phase3 = phase3
                self.run_extraction_loop(
                    pipeline, phase3,
                    max_stages=preset_end_stage)
                return
            try:
                resume = input("Resume from existing progress? [Y/n]: ").strip()
            except EOFError:
                # Daemon path with stdin=DEVNULL — CLI background validator
                # should have intercepted, but defend in depth: treat empty
                # stdin as "yes resume" (the [Y/n] default) so we don't crash.
                resume = ""
            if resume.lower() != "n":
                self.pipeline = pipeline
                self.phase3 = phase3
                self.run_extraction_loop(
                    pipeline, phase3,
                    max_stages=preset_end_stage)
                return

        # Fresh start: summarize → analyze → confirm → baseline → extract.
        # Create pipeline early so Phase 0/1 can track their status, and
        # fill ``extraction_branch`` at run_full entry (not lazily inside
        # confirm_with_user) so the outer try block below can switch
        # branches before the very first LLM call.
        expected_branch = (
            f"{get_config().git.extraction_branch_prefix}{self.work_id}")
        if not pipeline:
            pipeline = PipelineProgress(
                work_id=self.work_id,
                extraction_branch=expected_branch)
            pipeline.save(self.project_root)
        elif not pipeline.extraction_branch:
            # Load-from-disk pipeline written by an older run that did not
            # fill the field — patch in place so the branch switch below
            # has a target. Idempotent for already-filled values.
            pipeline.extraction_branch = expected_branch
            pipeline.save(self.project_root)
        self.pipeline = pipeline

        # Switch to the extraction branch BEFORE the first LLM call so
        # all five phases (0 chunk summaries / 1 analysis fan-out /
        # 1.5 user confirmation + works manifest write / 2 baseline /
        # 3+ stage extraction) run on the extraction branch. ``finally``
        # returns to ``main`` on any exit path. See
        # ai_context/architecture.md §Git Branch Model + decision #26a.
        try:
            if pipeline.extraction_branch:
                if not create_extraction_branch(self.project_root,
                                                pipeline.extraction_branch):
                    print("[ERROR] Cannot create extraction branch.")
                    sys.exit(1)

            self.run_summarization()
            analysis = self.run_analysis()
            pipeline, phase3 = self.confirm_with_user(
                analysis,
                preset_characters=preset_characters,
                preset_end_stage=preset_end_stage,
            )

            self.pipeline = pipeline
            self.phase3 = phase3

            self.run_baseline_production(pipeline.target_characters)

            # Commit baseline output so Phase 3 starts with a clean tree.
            # Treat a None sha as fatal (decision #58 / M3) — moving phase_2
            # mark_done out of run_baseline_production into the post-commit
            # path means an empty / failed commit must not silently fall
            # through to Phase 3 on a dirty / uncommitted baseline.
            sha = commit_stage(self.project_root, "baseline",
                               work_id=pipeline.work_id,
                               message="Phase 0-2 baseline")
            if sha is None:
                print(
                    "\n[ERROR] Baseline commit produced no SHA (commit "
                    "failed or empty status). Refusing to proceed to "
                    "Phase 3 with a dirty / uncommitted baseline "
                    "(decision #58 / M3).")
                sys.exit(1)
            print(f"  [OK] Baseline committed as {sha}")
            pipeline.mark_done("phase_2")
            pipeline.save(self.project_root)

            self.run_extraction_loop(pipeline, phase3,
                                     max_stages=preset_end_stage)
        finally:
            if pipeline and pipeline.extraction_branch:
                checkout_main(
                    self.project_root,
                    scope_paths=[f"works/{pipeline.work_id}/"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_stage_plan_limits(
    stage_plan: dict[str, Any],
    *,
    max_stage_size: int = 15,
    min_stage_size: int = 8,
) -> list[dict[str, Any]]:
    """Check stage chapter counts against limits.

    Returns a list of violating stage dicts (empty = all OK).
    Prints a report either way.
    """
    stages = stage_plan.get("stages", [])
    if not stages:
        return []

    violating = [b for b in stages
                 if (b.get("chapter_count", 0) > max_stage_size
                     or b.get("chapter_count", 0) < min_stage_size)]

    if not violating:
        print(f"  [OK] Stage plan: {len(stages)} stages, "
              f"all within {min_stage_size}-{max_stage_size} chapter limit.")
        return []

    print(f"\n  [FAIL] {len(violating)}/{len(stages)} stage(es) outside "
          f"{min_stage_size}-{max_stage_size} chapter limit:")
    for b in violating:
        count = b.get("chapter_count", "?")
        tag = "over" if isinstance(count, int) and count > max_stage_size else "under"
        print(f"    {b.get('stage_id', '?')}: {b.get('stage_id', '?')} "
              f"— {count} chapters ({tag})")

    return violating


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
