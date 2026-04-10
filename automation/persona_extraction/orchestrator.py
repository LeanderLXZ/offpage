"""Main orchestrator — drives the full extraction pipeline.

Flow:
  1. Analysis phase (LLM)  → batch plan + candidate characters
  2. User confirmation      → select characters, confirm batch plan, set range
  3. Extraction loop        → for each batch (1+N parallel):
       a. Git preflight
       b. World + character extraction (1+N LLM calls, all parallel)
       c. Programmatic post-processing (memory_digest + stage_catalog)
       d. Parallel review lanes (world + each character: V+R+F)
       e. Commit gate (programmatic cross-consistency)
       f. Git commit or rollback + retry
  3.5 Cross-batch consistency check (programmatic, zero tokens)
  4. Scene archive (per-chapter parallel, programmatic validation only)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Any

from .consistency_checker import run_consistency_check, save_report
from .git_utils import (
    commit_batch,
    create_extraction_branch,
    preflight_check,
    rollback_to_head,
    squash_merge_to,
)
from .json_repair import try_repair_json_file
from .llm_backend import LLMBackend, LLMResult, run_with_retry
from .post_processing import run_batch_post_processing
from .process_guard import PidLock, fmt_memory, get_rss_mb
from .progress import (
    BatchEntry,
    BatchState,
    ChunkEntry,
    Phase0Progress,
    Phase3Progress,
    PipelineProgress,
    migrate_legacy_progress,
    PHASE_DONE,
    PHASE_RUNNING,
)
from .prompt_builder import (
    build_analysis_prompt,
    build_baseline_prompt,
    build_character_extraction_prompt,
    build_reviewer_prompt,
    build_summarization_prompt,
    build_targeted_fix_prompt,
    build_world_extraction_prompt,
)
from .review_lanes import run_commit_gate, run_parallel_review
from .scene_archive import run_scene_archive
from .validator import validate_baseline, validate_lane

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


class ProgressTracker:
    """Tracks timing and progress across the extraction loop."""

    # Step names used as keys for per-step duration tracking
    STEP_EXTRACTION = "extraction"
    STEP_VALIDATION = "validation"
    STEP_REVIEW = "review"
    STEP_FIX = "fix"
    STEP_COMMIT = "commit"

    def __init__(self, total_batches: int, completed_before: int):
        self.total = total_batches
        self.completed_before = completed_before
        self.completed_this_run = 0
        self.loop_start = time.monotonic()
        self.batch_start: float = 0.0
        self.step_start: float = 0.0
        self.batch_durations: list[float] = []
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
    def avg_batch_seconds(self) -> float:
        if not self.batch_durations:
            return 0.0
        return sum(self.batch_durations) / len(self.batch_durations)

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

    def start_batch(self) -> None:
        self.batch_start = time.monotonic()

    def finish_batch(self) -> None:
        duration = time.monotonic() - self.batch_start
        self.batch_durations.append(duration)
        self.completed_this_run += 1

    def start_step(self) -> None:
        self.step_start = time.monotonic()

    def step_elapsed(self) -> str:
        return _fmt_duration(time.monotonic() - self.step_start)

    def print_batch_header(self, batch: Any) -> None:
        """Print batch header with overall and step-level progress."""
        n = self.completed + 1
        elapsed_total = time.monotonic() - self.loop_start
        avg = self.avg_batch_seconds

        print(f"\n{'━' * 60}")
        print(f"  [{n}/{self.total}] {batch.batch_id} ({batch.stage_id})")
        print(f"  Chapters: {batch.chapters}  |  "
              f"State: {batch.state.value}  |  "
              f"Retry: {batch.retry_count}/{batch.max_retries}")

        parts = [f"Elapsed: {_fmt_duration(elapsed_total)}"]
        if avg > 0:
            parts.append(f"Avg: {_fmt_duration(avg)}/batch")
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
        print(f"  Extraction Summary")
        print(f"{'=' * 60}")
        print(f"  Completed this run: {self.completed_this_run}")
        print(f"  Total completed: {self.completed}/{self.total}")
        print(f"  Total elapsed: {_fmt_duration(elapsed)}")
        if self.batch_durations:
            print(f"  Avg per batch: "
                  f"{_fmt_duration(self.avg_batch_seconds)}")
            fastest = min(self.batch_durations)
            slowest = max(self.batch_durations)
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
        chunk_size: int = 25,
        max_runtime_minutes: int = 0,
        start_phase: str = "auto",
        concurrency: int = 10,
    ):
        self.project_root = project_root
        self.work_id = work_id
        self.backend = backend
        self.reviewer_backend = reviewer_backend or backend
        self.chunk_size = chunk_size
        self.max_runtime_minutes = max_runtime_minutes
        self.start_phase = start_phase
        self.concurrency = concurrency
        self.pipeline: PipelineProgress | None = None
        self.phase3: Phase3Progress | None = None
        self._interrupted = False
        self._start_time = time.monotonic()
        self._lock = PidLock(project_root, work_id)

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
        """Return True if max runtime exceeded."""
        if self.max_runtime_minutes <= 0:
            return False
        elapsed_min = (time.monotonic() - self._start_time) / 60
        if elapsed_min >= self.max_runtime_minutes:
            print(f"\n[TIMEOUT] Max runtime ({self.max_runtime_minutes}min) "
                  f"exceeded after {elapsed_min:.0f}min. Stopping gracefully.")
            return True
        return False

    def acquire_lock(self) -> bool:
        """Acquire PID lock. Prints error and returns False if held."""
        existing = self._lock.is_held()
        if existing:
            pid = existing.get("pid", "?")
            started = existing.get("started", "?")
            mem = fmt_memory(get_rss_mb(pid)) if isinstance(pid, int) else "?"
            print(f"[ERROR] Another extraction is already running:")
            print(f"  PID: {pid}  Started: {started}  Mem: {mem}")
            print(f"  If the process is dead, remove the lock:")
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

    def _summarize_chunk(
        self,
        idx: int,
        total_chunks: int,
        start: int,
        end: int,
        summaries_dir: Path,
        *,
        _is_l3_retry: bool = False,
    ) -> tuple[int, bool, str]:
        """Process a single summarization chunk.

        Returns (chunk_index, success, message).

        If L1+L2 JSON repair both fail and this is not already an L3 retry,
        the chunk is automatically re-run once from scratch (L3).
        """
        output_path = summaries_dir / f"chunk_{idx:03d}.json"

        prompt = build_summarization_prompt(
            self.project_root, self.work_id,
            idx, total_chunks, start, end)

        result = run_with_retry(self.backend, prompt,
                                timeout_seconds=600)

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
                # L3: full re-run (once)
                if not _is_l3_retry:
                    logger.info("L3 full re-run for chunk_%03d", idx)
                    return self._summarize_chunk(
                        idx, total_chunks, start, end, summaries_dir,
                        _is_l3_retry=True,
                    )
                return idx, False, f"JSON repair failed (L3 also failed): {desc}"

        count = len(data.get("summaries", [])) if data else 0
        expected = end - start + 1
        if count < expected:
            return idx, True, f"{count}/{expected} summaries (partial)"

        return idx, True, ""

    def _extraction_output_exists(
        self,
        target_characters: list[str],
        batch: BatchEntry,
    ) -> bool:
        """Check if extraction output already exists on disk for a batch.

        Returns True if world stage_snapshot AND all target character
        stage_snapshots exist, indicating the extraction step can be
        skipped (smart resume).
        """
        work_dir = self.project_root / "works" / self.work_id
        stage_id = batch.stage_id

        # World snapshot must exist
        world_ss = (work_dir / "world" / "stage_snapshots"
                    / f"{stage_id}.json")
        if not world_ss.exists():
            return False

        # All target character snapshots must exist
        for char_id in target_characters:
            char_ss = (work_dir / "characters" / char_id / "canon"
                       / "stage_snapshots" / f"{stage_id}.json")
            if not char_ss.exists():
                return False

        return True

    def run_summarization(self) -> Path:
        """Summarize all chapters in chunks, return summaries directory."""
        print("\n" + "=" * 60)
        print("  Phase 0: Chapter Summarization")
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

        # Build chunk list: (idx, start, end) all 1-based
        chunks: list[tuple[int, int, int]] = []
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
        # Ensure all chunks are tracked
        for idx, start, end in chunks:
            chunk_id = f"chunk_{idx:03d}"
            if chunk_id not in phase0.chunks:
                phase0.chunks[chunk_id] = ChunkEntry(
                    chunk_id=chunk_id,
                    chapters=f"{start:04d}-{end:04d}",
                )
        phase0.save(self.project_root)

        print(f"  Total chapters: {total_chapters}")
        print(f"  Chunk size: {self.chunk_size}")
        print(f"  Total chunks: {total_chunks}")

        # Filter out already-completed chunks
        pending: list[tuple[int, int, int]] = []
        for idx, start, end in chunks:
            chunk_id = f"chunk_{idx:03d}"
            entry = phase0.chunks.get(chunk_id)
            output_path = summaries_dir / f"{chunk_id}.json"

            # Check progress + file existence
            if entry and entry.state == "done" and output_path.exists():
                print(f"  [{idx}/{total_chunks}] {chunk_id} "
                      f"({start:04d}-{end:04d}) — already done, skipping")
                continue

            if output_path.exists():
                existing = _load_json(output_path)
                if existing is None:
                    ok, desc = try_repair_json_file(
                        output_path,
                        backend=self.backend,
                        expected_key="summaries",
                    )
                    if ok:
                        existing = _load_json(output_path)
                        print(f"  [{idx}/{total_chunks}] {chunk_id} "
                              f"({start:04d}-{end:04d}) — repaired ({desc}), "
                              f"skipping")
                if existing and existing.get("summaries"):
                    # File exists but progress not marked — fix it
                    if entry:
                        entry.state = "done"
                        phase0.save(self.project_root)
                    print(f"  [{idx}/{total_chunks}] {chunk_id} "
                          f"({start:04d}-{end:04d}) — already done, skipping")
                    continue
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
                    chunk_idx, success, msg = future.result()
                except Exception as exc:
                    chunk_idx, success, msg = idx, False, str(exc)

                entry = phase0.chunks.get(chunk_id)
                if success:
                    completed += 1
                    if entry:
                        entry.state = "done"
                        entry.last_updated = ""  # save() updates timestamp
                    phase0.save(self.project_root)
                    if msg:  # partial
                        print(f"    [WARN] {chunk_id} "
                              f"({start:04d}-{end:04d}): {msg}  "
                              f"({completed}/{total_pending})")
                    else:
                        print(f"    [OK] {chunk_id} "
                              f"({start:04d}-{end:04d})  "
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

        # Verify all chunks completed — gate for Phase 1
        all_done = sum(1 for i in range(1, total_chunks + 1)
                       if (summaries_dir / f"chunk_{i:03d}.json").exists())

        if all_done < total_chunks:
            missing = [f"chunk_{i:03d}" for i in range(1, total_chunks + 1)
                       if not (summaries_dir / f"chunk_{i:03d}.json").exists()]
            print(f"\n[ERROR] Summarization: {all_done}/{total_chunks} chunks")
            print(f"  Missing: {missing}")
            print("  Re-run to fill gaps (completed chunks will be skipped).")
            sys.exit(1)

        print(f"\n[OK] Summarization: {all_done}/{total_chunks} chunks")

        # Mark pipeline phase_0 done
        if self.pipeline:
            self.pipeline.mark_done("phase_0")
            self.pipeline.save(self.project_root)

        return summaries_dir

    # ------------------------------------------------------------------
    # Phase 1: Analysis (from summaries)
    # ------------------------------------------------------------------

    def run_analysis(self) -> dict[str, Any]:
        """Run analysis phase: identity merge + world overview + batch plan + candidates.

        If the produced batch plan contains oversized batches (>15 chapters),
        the plan file is deleted and the LLM is re-run with corrective
        feedback (up to MAX_ANALYSIS_RETRIES times).
        """
        MAX_ANALYSIS_RETRIES = 2
        work_dir = self.project_root / "works" / self.work_id
        inc_dir = work_dir / "analysis"
        correction_feedback = ""

        for attempt in range(1, MAX_ANALYSIS_RETRIES + 2):
            print("\n" + "=" * 60)
            if attempt == 1:
                print("  Phase 1: Analysis (from chapter summaries)")
            else:
                print(f"  Phase 1: Analysis — retry {attempt - 1}"
                      f" (correcting batch plan)")
            print("=" * 60 + "\n")

            prompt = build_analysis_prompt(
                self.project_root, self.work_id,
                correction_feedback=correction_feedback)
            result = run_with_retry(self.backend, prompt,
                                    timeout_seconds=1800)

            if not result.success:
                print(f"[ERROR] Analysis failed: {result.error}")
                sys.exit(1)

            print("[OK] Analysis complete.")

            batch_plan = _load_json(inc_dir / "source_batch_plan.json")
            candidates = _load_json(inc_dir / "candidate_characters.json")
            world_overview = _load_json(inc_dir / "world_overview.json")

            if world_overview:
                print("  [OK] World overview produced.")
            else:
                print("  [WARN] World overview not found.")

            # Phase 1 exit validation: check batch chapter_count limits
            if batch_plan:
                violating = _check_batch_plan_limits(batch_plan)
                if not violating:
                    break  # all good

                if attempt <= MAX_ANALYSIS_RETRIES:
                    # Build correction feedback for next attempt
                    details = "; ".join(
                        f"{b.get('stage_id', '?')}={b.get('chapter_count')}章"
                        for b in violating)
                    correction_feedback = (
                        f"上次产出的 batch plan 中有 {len(violating)} 个 batch "
                        f"不满足 5-15 章限制：{details}。\n\n"
                        "请重新生成 `source_batch_plan.json`，确保每个 batch "
                        "的 chapter_count 在 5-15 范围内。对于跨度大的故事弧，"
                        "必须在其中寻找次级剧情节点拆分为多个 batch；"
                        "对于过短的 batch，应合并到相邻 batch。\n\n"
                        "其他已产出的文件（world_overview.json、"
                        "candidate_characters.json）如果已存在且正确，"
                        "可以保留不变，只需重写 batch plan。"
                    )
                    # Delete the bad plan so the LLM regenerates it
                    plan_path = inc_dir / "source_batch_plan.json"
                    if plan_path.exists():
                        plan_path.unlink()
                    print(f"  [RETRY] Will re-run Phase 1 to correct "
                          f"batch plan (attempt {attempt + 1})...")
                else:
                    print(f"  [FATAL] Batch plan still has violating batches "
                          f"after {MAX_ANALYSIS_RETRIES} retries. Aborting.")
                    sys.exit(1)
            else:
                break  # no plan produced, let downstream handle

        # Mark pipeline phase_1 done
        if self.pipeline:
            self.pipeline.mark_done("phase_1")
            self.pipeline.save(self.project_root)

        return {
            "batch_plan": batch_plan,
            "candidates": candidates,
            "world_overview": world_overview,
            "raw_output": result.text,
        }

    # ------------------------------------------------------------------
    # Phase 2.5: Baseline production
    # ------------------------------------------------------------------

    def run_baseline_production(
        self, target_characters: list[str]
    ) -> None:
        """Produce world foundation + character identity baselines."""
        print("\n" + "=" * 60)
        print("  Phase 2.5: Baseline Production")
        print("=" * 60 + "\n")

        print(f"  Characters: {target_characters}")
        print("  Producing: world/foundation + character identity baselines\n")

        prompt = build_baseline_prompt(
            self.project_root, self.work_id, target_characters)
        result = run_with_retry(self.backend, prompt, timeout_seconds=1800)

        if not result.success:
            print(f"[ERROR] Baseline production failed: {result.error}")
            sys.exit(1)

        # Verify outputs — these are critical for extraction
        work_dir = self.project_root / "works" / self.work_id
        missing_critical: list[str] = []

        foundation = work_dir / "world" / "foundation" / "foundation.json"
        if foundation.exists():
            print("  [OK] World foundation produced.")
        else:
            missing_critical.append("world/foundation/foundation.json")
            print("  [MISS] World foundation not found.")

        fixed_rel = (work_dir / "world" / "foundation"
                     / "fixed_relationships.json")
        if fixed_rel.exists():
            print("  [OK] World fixed_relationships produced.")
        else:
            print("  [WARN] World fixed_relationships.json not found "
                  "(Phase 2.5 should create).")

        for char_id in target_characters:
            canon_dir = work_dir / "characters" / char_id / "canon"
            identity = canon_dir / "identity.json"
            if identity.exists():
                print(f"  [OK] {char_id}/identity.json produced.")
            else:
                missing_critical.append(f"{char_id}/identity.json")
                print(f"  [MISS] {char_id}/identity.json not found.")

            # Check skeleton baseline files (non-critical — warn only)
            for fname in ("voice_rules.json", "behavior_rules.json",
                          "boundaries.json", "failure_modes.json"):
                if (canon_dir / fname).exists():
                    print(f"  [OK] {char_id}/{fname} produced.")
                else:
                    print(f"  [WARN] {char_id}/{fname} not found "
                          f"(Phase 2.5 should create).")

        if missing_critical:
            print(f"\n[ERROR] Missing critical baseline files: "
                  f"{', '.join(missing_critical)}")
            print("  Cannot proceed to extraction without these files.")
            print("  Re-run with --resume to retry baseline production.")
            sys.exit(1)

        # Phase 2.5 exit validation — catch schema/field errors early
        print("\n--- Phase 2.5 Validation ---")
        baseline_report = validate_baseline(
            self.project_root, self.work_id, target_characters)
        print(baseline_report.summary())
        if not baseline_report.passed:
            print("\n[ERROR] Baseline validation failed. "
                  "Fix the errors above before proceeding.")
            sys.exit(1)

        # Mark baseline as done in pipeline so resume skips it
        if self.pipeline:
            self.pipeline.mark_done("phase_2_5")
            self.pipeline.save(self.project_root)

        print("\n[OK] Baseline production complete.")

    # ------------------------------------------------------------------
    # Phase 2: User confirmation
    # ------------------------------------------------------------------

    def confirm_with_user(
        self,
        analysis: dict[str, Any],
        *,
        preset_characters: list[str] | None = None,
        preset_end_batch: int | None = None,
    ) -> tuple[PipelineProgress, Phase3Progress]:
        """Interactive user confirmation of characters and parameters."""
        print("\n" + "=" * 60)
        print("  Phase 2: User Confirmation")
        print("=" * 60 + "\n")

        candidates = analysis.get("candidates") or {}
        batch_plan = analysis.get("batch_plan") or {}

        # Show candidates
        if candidates and candidates.get("candidates"):
            print("Candidate characters:\n")
            for i, c in enumerate(candidates["candidates"], 1):
                rec = "RECOMMENDED" if c.get("recommended") else ""
                print(f"  {i}. {c['character_id']} — {c.get('description', '')}")
                print(f"     Frequency: {c.get('frequency', '?')}, "
                      f"Importance: {c.get('importance', '?')} {rec}")
            print()

        # Select characters
        if preset_characters:
            selected = preset_characters
            print(f"Pre-selected characters: {selected}")
        else:
            raw = input("Enter character IDs to extract (comma-separated): ")
            selected = [c.strip() for c in raw.split(",") if c.strip()]

        if not selected:
            print("[ERROR] No characters selected.")
            sys.exit(1)

        # Show batch plan summary
        batches_data = batch_plan.get("batches", [])
        total_batches = len(batches_data)
        if batches_data:
            print(f"\nBatch plan ({total_batches} batches, "
                  f"split by story boundaries):\n")
            for b in batches_data:
                print(f"  {b['batch_id']}: {b.get('stage_id', '?')} "
                      f"({b['chapters']}, {b.get('chapter_count', '?')} ch) "
                      f"— {b.get('boundary_reason', '')}")
            print()

        # --end-batch is a runtime limit only; progress always contains
        # the full batch plan (same pattern as Phase 4).
        if preset_end_batch is None:
            raw = input(f"Extract up to batch N (total {total_batches}, "
                        f"0 or empty = all): ").strip()
            preset_end_batch = int(raw) if raw else 0

        batch_size = batch_plan.get("default_batch_size", 10)

        pipeline = PipelineProgress(
            work_id=self.work_id,
            extraction_branch=f"extraction/{self.work_id}",
            target_characters=selected,
        )
        pipeline.mark_done("phase_1")
        pipeline.mark_done("phase_2")
        pipeline.save(self.project_root)

        phase3 = Phase3Progress(
            work_id=self.work_id,
            batch_size=batch_size,
            batches=[
                BatchEntry(
                    batch_id=b["batch_id"],
                    stage_id=b["stage_id"],
                    chapters=b["chapters"],
                    chapter_count=b.get("chapter_count", 10),
                )
                for b in batches_data  # full plan, not truncated
            ],
        )
        phase3.save(self.project_root)

        self.pipeline = pipeline
        self.phase3 = phase3

        run_label = (f"first {preset_end_batch}" if preset_end_batch
                     else "all")
        print(f"\n[OK] Configuration saved.")
        print(f"     Characters: {selected}")
        print(f"     Batches: {len(phase3.batches)} total "
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
        max_batches: int | None = None,
    ) -> None:
        """Main extraction loop: iterate through batches.

        Args:
            pipeline: Pipeline progress (uses self.pipeline if None).
            phase3: Phase 3 batch progress (uses self.phase3 if None).
            max_batches: Stop after this many batches complete.
                         None = all, 0 = baseline only.
        """
        pipeline = pipeline or self.pipeline
        phase3 = phase3 or self.phase3
        if not pipeline or not phase3:
            print("[ERROR] No progress loaded. Run analysis first.")
            sys.exit(1)

        self.pipeline = pipeline
        self.phase3 = phase3

        # Expand batches from batch plan if --end-batch increased
        self._ensure_batches_from_plan(phase3, max_batches)

        # --end-batch 0 means baseline only — skip extraction loop
        if max_batches is not None and max_batches == 0:
            # Still need baseline
            force_baseline = True
        else:
            force_baseline = self.start_phase == "2.5"

        # Force baseline if --start-phase 2.5
        if force_baseline:
            pipeline.set_phase("phase_2_5", PHASE_RUNNING)
            pipeline.save(self.project_root)

        # Check if baseline production was completed — if not, run it now
        work_dir = self.project_root / "works" / pipeline.work_id
        fixed_rel = (work_dir / "world" / "foundation"
                     / "fixed_relationships.json")
        if not pipeline.is_done("phase_2_5") or (
                force_baseline and not fixed_rel.exists()):
            foundation = work_dir / "world" / "foundation" / "foundation.json"
            identities_ok = all(
                (work_dir / "characters" / c / "canon" / "identity.json"
                 ).exists()
                for c in pipeline.target_characters
            )
            if (foundation.exists() and identities_ok
                    and fixed_rel.exists() and not force_baseline):
                # Files exist from a prior partial run — mark done
                print("  [OK] Baseline files already present, marking done.")
                pipeline.mark_done("phase_2_5")
                pipeline.save(self.project_root)
            else:
                print("  [WARN] Baseline not completed. Running Phase 2.5...")
                self.run_baseline_production(pipeline.target_characters)
                # Commit baseline so extraction starts with clean tree
                sha = commit_batch(self.project_root,
                                   "baseline", "Phase 2.5 baseline (recovery)")
                if sha:
                    print(f"  [OK] Baseline committed as {sha}")

        # --end-batch 0: baseline only, stop here
        if max_batches is not None and max_batches == 0:
            print("\n[STOP] --end-batch 0: baseline only, skipping "
                  "extraction loop.")
            return

        # Auto-reset blocked batches on resume — user chose to retry
        for b in phase3.batches:
            if b.state in (BatchState.FAILED, BatchState.ERROR):
                if b.retry_count >= b.max_retries:
                    print(f"  [RESET] {b.batch_id} was blocked "
                          f"(retry {b.retry_count}/{b.max_retries}), "
                          f"resetting to pending.")
                    b.state = BatchState.PENDING
                    b.retry_count = 0
                    b.error_message = ""
                    phase3.save(self.project_root)

        completed_before = phase3.completed_batch_count()
        tracker = ProgressTracker(len(phase3.batches), completed_before)

        print(f"\n{'=' * 60}")
        print(f"  Phase 3: Extraction Loop")
        print(f"{'=' * 60}")
        print(f"  Work: {pipeline.work_id}")
        print(f"  Characters: {pipeline.target_characters}")
        print(f"  Total batches: {tracker.total}")
        print(f"  Completed: {completed_before}")
        if max_batches is not None and max_batches > 0:
            to_run = max(0, max_batches - completed_before)
            print(f"  Target: {max_batches} (up to {to_run} this run)")
        else:
            print(f"  Target: all ({tracker.remaining} remaining)")
        print(f"{'=' * 60}")

        # Create extraction branch
        if pipeline.extraction_branch:
            if not create_extraction_branch(self.project_root,
                                            pipeline.extraction_branch):
                print("[ERROR] Cannot create extraction branch.")
                sys.exit(1)

        reached_limit = False

        while True:
            if self._interrupted:
                break

            if self._check_runtime_limit():
                break

            if (max_batches is not None and max_batches > 0
                    and tracker.completed >= max_batches):
                print(f"\n[STOP] Reached max_batches limit "
                      f"({tracker.completed}/{max_batches}).")
                reached_limit = True
                break

            batch = phase3.next_pending_batch()
            if batch is None:
                if phase3.all_committed():
                    print("\n[DONE] All batches completed!")
                    reached_limit = True
                else:
                    print("\n[BLOCKED] No actionable batches. "
                          "Check progress for blocked/error batches.")
                break

            self._process_batch(phase3, pipeline, batch, tracker)

        # Post-loop: run Phase 3.5/4 when target was reached
        if reached_limit:
            self._run_consistency_check()
            self._offer_squash_merge()
            self._run_scene_archive(
                end_batch=max_batches or 0, resume=True)

        tracker.print_summary()

    def _process_batch(self, phase3: Phase3Progress,
                       pipeline: PipelineProgress,
                       batch: BatchEntry,
                       tracker: ProgressTracker) -> None:
        """Process a single batch through the full pipeline."""
        tracker.start_batch()
        tracker.print_batch_header(batch)

        # Handle state resumption — reset interrupted states
        if batch.state == BatchState.FAILED:
            if batch.retry_count >= batch.max_retries:
                print(f"  [BLOCKED] {batch.batch_id} exceeded max retries. "
                      f"Needs manual intervention.")
                return
            batch.transition(BatchState.RETRYING)
            batch.retry_count += 1
            phase3.save(self.project_root)

        if batch.state == BatchState.ERROR:
            if batch.retry_count >= batch.max_retries:
                print(f"  [BLOCKED] {batch.batch_id} exceeded max retries. "
                      f"Needs manual intervention.")
                return
            print(f"  [RETRY] {batch.batch_id} in error state, retrying...")
            rollback_to_head(self.project_root)
            batch.retry_count += 1
            batch.transition(BatchState.PENDING)
            phase3.save(self.project_root)

        if batch.state == BatchState.EXTRACTING:
            print("  [RESUME] Interrupted during extraction, "
                  "rolling back and restarting...")
            rollback_to_head(self.project_root)
            batch.state = BatchState.PENDING
            phase3.save(self.project_root)

        if batch.state == BatchState.FIXING:
            # Interrupted during targeted fix — the fix may be partial.
            # Re-enter the FIXING step and let it re-run the fix agent.
            print("  [RESUME] Interrupted during targeted fix, "
                  "will retry fix...")

        if batch.state in (BatchState.RETRYING, BatchState.PENDING):
            # --- Step 1: Git preflight ---
            tracker.start_step()
            tracker.print_step(1, 6, "Git preflight")
            problems = preflight_check(
                self.project_root, pipeline.extraction_branch or None,
                ignore_patterns=["extraction_progress.json",
                                 "pipeline.json", "phase3_batches.json",
                                 "__pycache__"])
            if problems:
                for p in problems:
                    print(f"    [PROBLEM] {p}")
                batch.transition(BatchState.ERROR)
                batch.error_message = "; ".join(problems)
                phase3.save(self.project_root)
                return
            tracker.print_step_done(1, 6, "Git preflight")

            # --- Smart skip: if extraction output already on disk ---
            if self._extraction_output_exists(
                    pipeline.target_characters, batch):
                print(f"  [SKIP] Extraction output already on disk for "
                      f"{batch.batch_id}, jumping to post-processing")
                batch.transition(BatchState.EXTRACTED)
                phase3.save(self.project_root)
            else:
                # --- Step 2: World + Character extraction (1+N parallel) ---
                tracker.start_step()
                n_chars = len(pipeline.target_characters)
                tracker.print_step(2, 6,
                                   f"Extraction (1 world + "
                                   f"{n_chars} characters parallel)")
                batch.transition(BatchState.EXTRACTING)
                phase3.save(self.project_root)

                extraction_errors: list[str] = []

                def _extract_world() -> tuple[str, LLMResult]:
                    prompt = build_world_extraction_prompt(
                        self.project_root, pipeline, batch,
                        batches=phase3.batches,
                        reviewer_feedback=batch.last_reviewer_feedback)
                    result = run_with_retry(
                        self.backend, prompt, timeout_seconds=3600)
                    return "world", result

                def _extract_character(
                    char_id: str,
                ) -> tuple[str, LLMResult]:
                    char_prompt = build_character_extraction_prompt(
                        self.project_root, pipeline, batch, char_id,
                        batches=phase3.batches,
                        reviewer_feedback=batch.last_reviewer_feedback)
                    result = run_with_retry(
                        self.backend, char_prompt,
                        timeout_seconds=3600)
                    return char_id, result

                with ThreadPoolExecutor(
                        max_workers=1 + n_chars) as executor:
                    futures = [executor.submit(_extract_world)]
                    futures.extend(
                        executor.submit(_extract_character, c)
                        for c in pipeline.target_characters
                    )
                    for future in as_completed(futures):
                        entity_id, result = future.result()
                        if not result.success:
                            extraction_errors.append(
                                f"{entity_id}: "
                                f"{result.error or 'unknown'}")
                            print(f"    [ERROR] {entity_id} extraction "
                                  f"failed: {result.error}")

                if extraction_errors:
                    print("    Rolling back uncommitted changes...")
                    rollback_to_head(self.project_root)
                    batch.transition(BatchState.ERROR)
                    batch.error_message = "; ".join(extraction_errors)
                    phase3.save(self.project_root)
                    return

                tracker.record_step(ProgressTracker.STEP_EXTRACTION)
                tracker.print_step_done(2, 6,
                                        f"Extraction "
                                        f"(1+{n_chars} parallel)")

                batch.transition(BatchState.EXTRACTED)
                phase3.save(self.project_root)

        # --- Step 3: Programmatic post-processing ---
        if batch.state in (BatchState.EXTRACTED, BatchState.POST_PROCESSING):
            if batch.state == BatchState.EXTRACTED:
                batch.transition(BatchState.POST_PROCESSING)
                phase3.save(self.project_root)

            tracker.start_step()
            tracker.print_step(3, 6, "Post-processing (digest + catalog)")

            # Determine batch order (0-based index in batches list)
            batch_order = next(
                (i for i, b in enumerate(phase3.batches)
                 if b.batch_id == batch.batch_id), 0)

            pp_issues = run_batch_post_processing(
                project_root=self.project_root,
                work_id=pipeline.work_id,
                stage_id=batch.stage_id,
                batch_order=batch_order,
                character_ids=pipeline.target_characters,
                chapter_range=batch.chapters,
            )

            if pp_issues:
                for issue in pp_issues:
                    print(f"    [WARN] {issue}")
                # Post-processing warnings don't block — files may still
                # be validated by the review lanes below.

            tracker.record_step(ProgressTracker.STEP_VALIDATION)
            tracker.print_step_done(3, 6, "Post-processing",
                                    f"{len(pp_issues)} issues")

            batch.transition(BatchState.REVIEWING)
            phase3.save(self.project_root)

        # --- Step 4: Parallel review lanes (V+R+F per entity) ---
        if batch.state == BatchState.REVIEWING:
            # Safety check: verify extraction output still exists on disk
            work_dir = self.project_root / "works" / pipeline.work_id
            has_output = any(
                (work_dir / "characters" / c / "canon" / "stage_snapshots")
                .exists()
                for c in pipeline.target_characters
            )
            if not has_output:
                print("  [RESUME] Extraction output missing for REVIEWING "
                      "batch, rolling back and restarting...")
                rollback_to_head(self.project_root)
                batch.state = BatchState.PENDING
                phase3.save(self.project_root)
                return

            tracker.start_step()
            n_lanes = 1 + len(pipeline.target_characters)
            tracker.print_step(4, 6,
                               f"Parallel review lanes ({n_lanes} lanes)")

            lane_results = run_parallel_review(
                project_root=self.project_root,
                progress=pipeline,
                batch=batch,
                backend=self.backend,
                reviewer_backend=self.reviewer_backend,
                validate_fn=validate_lane,
                build_reviewer_fn=partial(
                    build_reviewer_prompt, batches=phase3.batches),
                build_fix_fn=partial(
                    build_targeted_fix_prompt, batches=phase3.batches),
                parse_verdict_fn=_parse_verdict,
                is_fixable_fn=_is_fixable,
                run_with_retry_fn=run_with_retry,
            )

            # Print lane results
            passed_lanes = sum(1 for r in lane_results if r.passed)
            failed_lanes = [r for r in lane_results if not r.passed]
            for r in lane_results:
                status = "PASS" if r.passed else "FAIL"
                detail = r.error or r.findings[:200] if not r.passed else ""
                print(f"    [{r.lane_type}:{r.lane_id}] {status}"
                      f"{' — ' + detail if detail else ''}")

            if failed_lanes:
                tracker.print_step_done(
                    4, 6, "Parallel review lanes",
                    f"{passed_lanes}/{n_lanes} passed")

                # Collect failure feedback for retry
                feedback_parts = []
                for r in failed_lanes:
                    feedback_parts.append(
                        f"[{r.lane_type}:{r.lane_id}] "
                        f"{r.error or r.findings[:500]}")
                batch.last_reviewer_feedback = "\n".join(feedback_parts)

                print("    [FAIL] Rolling back for retry...")
                rollback_to_head(self.project_root)
                batch.transition(BatchState.FAILED)
                phase3.save(self.project_root)
                return

            tracker.record_step(ProgressTracker.STEP_REVIEW)
            tracker.print_step_done(4, 6, "Parallel review lanes",
                                    f"{n_lanes}/{n_lanes} passed")

            # --- Step 5: Commit gate (programmatic, 0 token) ---
            tracker.start_step()
            tracker.print_step(5, 6, "Commit gate")

            gate_passed, gate_issues = run_commit_gate(
                project_root=self.project_root,
                work_id=pipeline.work_id,
                stage_id=batch.stage_id,
                character_ids=pipeline.target_characters,
                lane_results=lane_results,
            )

            if not gate_passed:
                for issue in gate_issues:
                    print(f"    [GATE] {issue}")
                print("    [FAIL] Commit gate failed, rolling back...")
                rollback_to_head(self.project_root)
                batch.last_reviewer_feedback = "\n".join(gate_issues)
                batch.transition(BatchState.FAILED)
                phase3.save(self.project_root)
                return

            tracker.print_step_done(5, 6, "Commit gate", "PASS")
            batch.transition(BatchState.PASSED)
            phase3.save(self.project_root)

        # --- Step 6: Git commit ---
        if batch.state == BatchState.PASSED:
            tracker.start_step()
            tracker.print_step(6, 6, "Git commit")

            # Clear feedback/error fields on successful commit
            batch.last_reviewer_feedback = ""
            batch.error_message = ""
            batch.fail_source = ""

            # Transition and save BEFORE git commit so the committed
            # progress file is included in the same commit.
            batch.transition(BatchState.COMMITTED)
            phase3.save(self.project_root)

            sha = commit_batch(self.project_root,
                               batch.batch_id, batch.stage_id)
            tracker.record_step(ProgressTracker.STEP_COMMIT)
            if sha:
                batch.committed_sha = sha
                # Save again with the SHA (this will be uncommitted
                # on disk but consistent on next resume)
                phase3.save(self.project_root)
                tracker.print_step_done(6, 6, "Git commit", sha)
            else:
                tracker.print_step_done(6, 6, "Git commit",
                                        "no changes")

            tracker.finish_batch()

    def _run_consistency_check(self) -> None:
        """Run Phase 3.5 cross-batch consistency check."""
        assert self.pipeline and self.phase3
        print("\n--- Phase 3.5: Cross-batch consistency check ---")
        stage_ids = [b.stage_id for b in self.phase3.batches
                     if b.state.value == "committed"]
        char_ids = self.pipeline.target_characters or []

        report = run_consistency_check(
            self.project_root, self.pipeline.work_id, char_ids, stage_ids)

        # Save report
        save_report(report, self.project_root, self.pipeline.work_id)

        # Print summary
        errors = sum(1 for i in report.issues if i.severity == "error")
        warnings = sum(1 for i in report.issues if i.severity == "warning")
        print(f"  Results: {errors} errors, {warnings} warnings, "
              f"{len(report.issues) - errors - warnings} info")

        if errors > 0:
            print("  [WARNING] Errors found — review consistency_report.json "
                  "before proceeding to Phase 4.")
            for issue in report.issues:
                if issue.severity == "error":
                    print(f"    [ERROR] [{issue.category}] {issue.location}: "
                          f"{issue.message}")
        else:
            print("  [OK] No blocking issues found.")

    def _run_scene_archive(self, *, end_batch: int = 0,
                           resume: bool = True) -> None:
        """Run Phase 4: scene archive generation."""
        run_scene_archive(
            self.project_root, self.work_id, self.backend,
            concurrency=self.concurrency,
            end_batch=end_batch,
            resume=resume,
        )

    def _offer_squash_merge(self) -> None:
        """After all batches complete, offer to squash-merge to main."""
        assert self.pipeline and self.phase3
        branch = self.pipeline.extraction_branch
        if not branch:
            return

        print(f"\n  All batches committed on branch '{branch}'.")
        print(f"  Squash-merge to main will consolidate all extraction")
        print(f"  commits into a single clean commit.")

        try:
            answer = input("  Squash-merge to main now? [Y/n]: ").strip()
        except EOFError:
            answer = "n"

        if answer.lower() == "n":
            print(f"  Skipped. You can manually merge later:\n"
                  f"    git checkout main && "
                  f"git merge --squash {branch} && "
                  f"git commit")
            return

        chars = ", ".join(self.pipeline.target_characters)
        n = len(self.phase3.batches)
        message = (f"Extraction complete: {self.pipeline.work_id} "
                   f"({n} stages, {chars})\n\n"
                   f"Squash-merged from {branch}.\n"
                   f"Automated extraction via persona-extraction orchestrator.")

        sha = squash_merge_to(self.project_root, "main", branch, message)
        if sha:
            print(f"  [OK] Squash-merged to main as {sha}")
            print(f"  Extraction branch '{branch}' preserved. "
                  f"Delete with: git branch -d {branch}")
        else:
            print(f"  [ERROR] Squash-merge failed. "
                  f"Merge manually from '{branch}'.")

    # ------------------------------------------------------------------
    # Batch expansion (like Phase 4: always derive targets from plan)
    # ------------------------------------------------------------------

    def _ensure_batches_from_plan(
        self,
        phase3: Phase3Progress,
        max_batches: int | None = None,
    ) -> None:
        """Ensure progress contains all target batches from the batch plan.

        Like Phase 4's chapter expansion pattern: every run re-reads the
        batch plan and appends any batches not yet tracked.  Existing
        batch states are preserved.
        """
        plan_path = (self.project_root / "works" / self.work_id
                     / "analysis" / "source_batch_plan.json")
        if not plan_path.exists():
            return

        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        full_batches = plan.get("batches", [])

        current_count = len(phase3.batches)
        effective_max = max_batches if (max_batches is not None
                                        and max_batches > 0) else 0
        added = phase3.expand_batches(full_batches,
                                      max_batches=effective_max)
        if added > 0:
            phase3.save(self.project_root)
            print(f"  [EXPAND] Added {added} new batches from batch plan "
                  f"({current_count} → {len(phase3.batches)})")

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run_full(
        self,
        *,
        preset_characters: list[str] | None = None,
        preset_end_batch: int | None = None,
    ) -> None:
        """Run the complete pipeline: analysis → confirm → extract."""
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

        if pipeline and phase3 and pipeline.is_done("phase_2"):
            print(f"Found existing progress for {self.work_id}.")
            print(f"  Completed: {phase3.completed_batch_count()}"
                  f"/{len(phase3.batches)}")
            # Auto-resume when characters are preset (non-interactive mode)
            if preset_characters:
                print("  Auto-resuming (preset characters provided).")
                self.pipeline = pipeline
                self.phase3 = phase3
                self.run_extraction_loop(
                    pipeline, phase3,
                    max_batches=preset_end_batch)
                return
            resume = input("Resume from existing progress? [Y/n]: ").strip()
            if resume.lower() != "n":
                self.pipeline = pipeline
                self.phase3 = phase3
                self.run_extraction_loop(
                    pipeline, phase3,
                    max_batches=preset_end_batch)
                return

        # Fresh start: summarize → analyze → confirm → baseline → extract
        # Create pipeline early so Phase 0/1 can track their status
        if not pipeline:
            pipeline = PipelineProgress(work_id=self.work_id)
            pipeline.save(self.project_root)
        self.pipeline = pipeline

        self.run_summarization()
        analysis = self.run_analysis()
        pipeline, phase3 = self.confirm_with_user(
            analysis,
            preset_characters=preset_characters,
            preset_end_batch=preset_end_batch,
        )

        self.pipeline = pipeline
        self.phase3 = phase3

        # Create extraction branch and commit pre-extraction output
        if pipeline.extraction_branch:
            create_extraction_branch(self.project_root,
                                     pipeline.extraction_branch)

        self.run_baseline_production(pipeline.target_characters)

        # Commit baseline output so Phase 3 starts with a clean working tree
        sha = commit_batch(self.project_root,
                           "baseline", "Phase 0-2.5 baseline")
        if sha:
            print(f"  [OK] Baseline committed as {sha}")

        self.run_extraction_loop(pipeline, phase3,
                                 max_batches=preset_end_batch)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_verdict(text: str) -> dict[str, str]:
    """Extract PASS/FAIL verdict from reviewer output."""
    verdict = "UNKNOWN"
    findings = ""

    for line in text.split("\n"):
        stripped = line.strip().upper()
        if stripped.startswith("VERDICT:"):
            v = stripped.replace("VERDICT:", "").strip()
            if "PASS" in v:
                verdict = "PASS"
            elif "FAIL" in v:
                verdict = "FAIL"

    # Extract findings section
    in_findings = False
    finding_lines: list[str] = []
    for line in text.split("\n"):
        if line.strip().upper().startswith("FINDINGS:"):
            in_findings = True
            continue
        if in_findings:
            if line.strip().upper().startswith(
                    ("STYLE_CONSISTENCY:", "SUMMARY:", "VERDICT:")):
                break
            finding_lines.append(line)

    findings = "\n".join(finding_lines).strip()

    return {"verdict": verdict, "findings": findings}


def _is_fixable(verdict: dict[str, str]) -> bool:
    """Determine if reviewer findings are fixable with targeted edits.

    Fixable: all error-level findings point to specific fields/values.
    Systemic (not fixable): file missing, large sections empty, structural
    errors, or understanding-level mistakes.
    """
    findings = verdict.get("findings", "")
    if not findings:
        return False

    # Systemic signals — these require full re-extraction
    systemic_signals = [
        "文件缺失", "file missing", "file not found",
        "整体", "全部为空", "completely empty",
        "结构错误", "structural error", "schema",
        "理解偏差", "方向错误", "misunderstand",
        "大段缺失", "大量缺失", "missing entire",
        "voice_map 为空", "behavior_state 为空",
        "未生成", "not generated", "not produced",
    ]
    lower = findings.lower()
    for signal in systemic_signals:
        if signal.lower() in lower:
            return False

    # Count error-level findings
    error_count = 0
    for line in findings.split("\n"):
        if "severity: error" in line.lower():
            error_count += 1

    # Too many errors → systemic, not worth patching
    if error_count > 5:
        return False

    return True


def _check_batch_plan_limits(
    batch_plan: dict[str, Any],
    *,
    max_batch_size: int = 15,
    min_batch_size: int = 5,
) -> list[dict[str, Any]]:
    """Check batch chapter counts against limits.

    Returns a list of violating batch dicts (empty = all OK).
    Prints a report either way.
    """
    batches = batch_plan.get("batches", [])
    if not batches:
        return []

    violating = [b for b in batches
                 if (b.get("chapter_count", 0) > max_batch_size
                     or b.get("chapter_count", 0) < min_batch_size)]

    if not violating:
        print(f"  [OK] Batch plan: {len(batches)} batches, "
              f"all within {min_batch_size}-{max_batch_size} chapter limit.")
        return []

    print(f"\n  [FAIL] {len(violating)}/{len(batches)} batch(es) outside "
          f"{min_batch_size}-{max_batch_size} chapter limit:")
    for b in violating:
        count = b.get("chapter_count", "?")
        tag = "over" if isinstance(count, int) and count > max_batch_size else "under"
        print(f"    {b.get('batch_id', '?')}: {b.get('stage_id', '?')} "
              f"— {count} chapters ({tag})")

    return violating


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
