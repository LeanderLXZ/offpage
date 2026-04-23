"""Main orchestrator — drives the full extraction pipeline.

Flow:
  1. Analysis phase (LLM)  → stage plan + candidate characters
  2. User confirmation      → select characters, confirm stage plan, set range
  3. Extraction loop        → for each stage (1+2N parallel):
       a. Git preflight
       b. World + char_snapshot + char_support extraction (1+2N LLM calls)
       c. Programmatic post-processing (memory_digest + stage_catalog)
       d. Repair agent (L0–L3 check → T0–T3 fix loop → final verify)
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .config import get_config
from .consistency_checker import run_consistency_check, save_report
from .failed_lane_log import write_failed_lane_log
from .git_utils import (
    checkout_master,
    commit_stage,
    create_extraction_branch,
    preflight_check,
    reset_paths,
    squash_merge_to,
)
from .lane_output import (
    baseline_paths,
    expected_lane_dirty_paths,
    expected_lane_names,
    verify_lane_output,
)
from .manifests import write_works_manifest, write_world_manifest
from .llm_backend import LLMBackend, LLMResult, run_with_retry
from .post_processing import run_stage_post_processing
from .process_guard import PidLock, fmt_memory, get_rss_mb
from .progress import (
    StageEntry,
    StageState,
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
    build_char_snapshot_prompt,
    build_char_support_prompt,
    build_summarization_prompt,
    build_world_extraction_prompt,
)
from .json_repair import try_repair_json_file
from .rate_limit import (
    RateLimitController,
    get_active as get_active_rl,
    set_active as set_active_rl,
)
from .scene_archive import run_scene_archive
from .validator import load_importance_map, validate_baseline
from ..repair_agent import (
    FileEntry as RepairFileEntry,
    RepairConfig,
    RepairResult,
    RetryPolicy,
    SourceContext,
    run as run_repair,
    validate_only as repair_validate_only,
)
from ..repair_agent.recorder import RepairRecorder

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
        print(f"  Extraction Summary")
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

        # Per-work rate-limit controller (§11.13). Installed as the
        # process-wide singleton so deeply-nested run_with_retry calls
        # (json_repair, scene_archive, repair_agent) find it.
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

        result = run_with_retry(
            self.backend, prompt,
            timeout_seconds=get_config().phase3.review_timeout_s,
            lane_name=f"summarize[chunk_{idx:03d}]",
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

        Digest files (memory_digest.jsonl, world_event_digest.jsonl) are
        accumulated across all stages. For per-stage repair we load the
        file and filter entries whose ID segment matches this stage's
        S{stage_num:03d} marker, then pass the filtered list as pre-loaded
        content — keeping the repair scope limited to the current stage.
        """
        import json as _json
        import re as _re
        schema_dir = self.project_root / "schemas"
        files: list[RepairFileEntry] = []

        def _load_schema(schema_name: str) -> dict | None:
            schema_path = schema_dir / schema_name
            if not schema_path.exists():
                return None
            try:
                return _json.loads(
                    schema_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return None

        def _entry(path: Path, schema_name: str) -> RepairFileEntry | None:
            if not path.exists():
                return None
            return RepairFileEntry(
                path=str(path), schema=_load_schema(schema_name))

        stage_pat = _re.compile(rf"-S{stage_num:03d}-")

        def _jsonl_stage_entry(
            path: Path, schema_name: str, id_fields: tuple[str, ...],
        ) -> RepairFileEntry | None:
            """Load accumulated jsonl; keep only entries whose id belongs
            to the current stage; return FileEntry with the current-stage
            slice as ``content`` plus the full accumulated list in
            ``jsonl_full_content``. ``write_file_entry`` merges the
            patched slice back into the full list at write time, so
            prior-stage entries are never truncated by a slice write-back.
            """
            if not path.exists():
                return None
            full: list[dict] = []
            kept: list[dict] = []
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                return None
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = _json.loads(line)
                except _json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                full.append(obj)
                for f_key in id_fields:
                    val = obj.get(f_key)
                    if isinstance(val, str) and stage_pat.search(val):
                        kept.append(obj)
                        break
            if not kept:
                return None
            return RepairFileEntry(
                path=str(path),
                schema=_load_schema(schema_name),
                content=kept,
                is_jsonl_slice=True,
                jsonl_full_content=full,
                jsonl_key_field=id_fields[0],
            )

        # World stage snapshot
        world_ss = work_dir / "world" / "stage_snapshots" / f"{stage_id}.json"
        e = _entry(world_ss, "world/world_stage_snapshot.schema.json")
        if e:
            files.append(e)

        # World event digest (accumulated; filter to this stage)
        world_ed = work_dir / "world" / "world_event_digest.jsonl"
        e = _jsonl_stage_entry(
            world_ed, "world/world_event_digest_entry.schema.json",
            id_fields=("event_id",))
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

            # Memory digest (accumulated; filter to this stage)
            e = _jsonl_stage_entry(
                char_dir / "memory_digest.jsonl",
                "character/memory_digest_entry.schema.json",
                id_fields=("memory_id",))
            if e:
                files.append(e)

            # Stage catalog
            e = _entry(
                char_dir / "stage_catalog.json",
                "work/stage_catalog.schema.json")
            if e:
                files.append(e)

        return files

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
        """Run analysis phase: identity merge + world overview + stage plan + candidates.

        If the produced stage plan contains oversized stages (>15 chapters),
        the plan file is deleted and the LLM is re-run with corrective
        feedback (up to MAX_ANALYSIS_RETRIES times).
        """
        cfg = get_config()
        MAX_ANALYSIS_RETRIES = cfg.phase1.exit_validation_max_retry
        STAGE_MIN = cfg.stage.min_chapter_count
        STAGE_MAX = cfg.stage.max_chapter_count
        work_dir = self.project_root / "works" / self.work_id
        inc_dir = work_dir / "analysis"
        correction_feedback = ""

        for attempt in range(1, MAX_ANALYSIS_RETRIES + 2):
            print("\n" + "=" * 60)
            if attempt == 1:
                print("  Phase 1: Analysis (from chapter summaries)")
            else:
                print(f"  Phase 1: Analysis — retry {attempt - 1}"
                      f" (correcting stage plan)")
            print("=" * 60 + "\n")

            prompt = build_analysis_prompt(
                self.project_root, self.work_id,
                correction_feedback=correction_feedback)
            result = run_with_retry(
                self.backend, prompt,
                timeout_seconds=get_config().phase3.extraction_timeout_s,
                lane_name="phase1_analysis",
            )

            if not result.success:
                print(f"[ERROR] Analysis failed: {result.error}")
                sys.exit(1)

            print("[OK] Analysis complete.")

            stage_plan = _load_json(inc_dir / "stage_plan.json")
            candidates = _load_json(inc_dir / "candidate_characters.json")
            world_overview = _load_json(inc_dir / "world_overview.json")

            if world_overview:
                print("  [OK] World overview produced.")
            else:
                print("  [WARN] World overview not found.")

            # Phase 1 exit validation: check stage chapter_count limits
            if stage_plan:
                violating = _check_stage_plan_limits(
                    stage_plan,
                    max_stage_size=STAGE_MAX,
                    min_stage_size=STAGE_MIN,
                )
                if not violating:
                    break  # all good

                if attempt <= MAX_ANALYSIS_RETRIES:
                    # Build correction feedback for next attempt
                    details = "; ".join(
                        f"{b.get('stage_id', '?')}={b.get('chapter_count')}章"
                        for b in violating)
                    correction_feedback = (
                        f"上次产出的 stage plan 中有 {len(violating)} 个 stage "
                        f"不满足 {STAGE_MIN}-{STAGE_MAX} 章限制：{details}。\n\n"
                        "请重新生成 `stage_plan.json`，确保每个 stage "
                        f"的 chapter_count 在 {STAGE_MIN}-{STAGE_MAX} 范围内。"
                        "对于跨度大的故事弧，必须在其中寻找次级剧情节点拆分为多个 stage；"
                        "对于过短的 stage，应合并到相邻 stage。\n\n"
                        "其他已产出的文件（world_overview.json、"
                        "candidate_characters.json）如果已存在且正确，"
                        "可以保留不变，只需重写 stage plan。"
                    )
                    # Delete the bad plan so the LLM regenerates it
                    plan_path = inc_dir / "stage_plan.json"
                    if plan_path.exists():
                        plan_path.unlink()
                    print(f"  [RETRY] Will re-run Phase 1 to correct "
                          f"stage plan (attempt {attempt + 1})...")
                else:
                    print(f"  [FATAL] Stage plan still has violating stages "
                          f"after {MAX_ANALYSIS_RETRIES} retries. Aborting.")
                    sys.exit(1)
            else:
                break  # no plan produced, let downstream handle

        # Mark pipeline phase_1 done
        if self.pipeline:
            self.pipeline.mark_done("phase_1")
            self.pipeline.save(self.project_root)

        return {
            "stage_plan": stage_plan,
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
        result = run_with_retry(
            self.backend, prompt,
            timeout_seconds=get_config().phase3.extraction_timeout_s,
            lane_name="baseline",
        )

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

        # Write world manifest programmatically now that foundation exists.
        world_manifest_path = write_world_manifest(
            self.project_root, self.work_id)
        print(f"  [OK] Wrote world manifest: {world_manifest_path}")

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
        preset_end_stage: int | None = None,
    ) -> tuple[PipelineProgress, Phase3Progress]:
        """Interactive user confirmation of characters and parameters."""
        print("\n" + "=" * 60)
        print("  Phase 2: User Confirmation")
        print("=" * 60 + "\n")

        candidates = analysis.get("candidates") or {}
        stage_plan = analysis.get("stage_plan") or {}

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
        # the full stage plan (same pattern as Phase 4).
        if preset_end_stage is None:
            raw = input(f"Extract up to stage N (total {total_stages}, "
                        f"0 or empty = all): ").strip()
            preset_end_stage = int(raw) if raw else 0

        stage_size = stage_plan.get("default_stage_size", 10)

        pipeline = PipelineProgress(
            work_id=self.work_id,
            extraction_branch=(
                f"{get_config().git.extraction_branch_prefix}{self.work_id}"),
            target_characters=selected,
        )
        pipeline.mark_done("phase_1")
        pipeline.mark_done("phase_2")
        pipeline.save(self.project_root)

        # Write works manifest now that characters + stages are confirmed.
        works_manifest_path = write_works_manifest(
            self.project_root, self.work_id, selected)
        print(f"  [OK] Wrote works manifest: {works_manifest_path}")

        phase3 = Phase3Progress(
            work_id=self.work_id,
            stage_size=stage_size,
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

        run_label = (f"first {preset_end_stage}" if preset_end_stage
                     else "all")
        print(f"\n[OK] Configuration saved.")
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
        pipeline = pipeline or self.pipeline
        phase3 = phase3 or self.phase3
        if not pipeline or not phase3:
            print("[ERROR] No progress loaded. Run analysis first.")
            sys.exit(1)

        self.pipeline = pipeline
        self.phase3 = phase3

        # Expand stages from stage plan if --end-stage increased
        self._ensure_stages_from_plan(phase3, max_stages)

        # --end-stage 0 means baseline only — skip extraction loop
        if max_stages is not None and max_stages == 0:
            # Still need baseline
            force_baseline = True
        else:
            force_baseline = self.start_phase == "2.5"

        # Force baseline if --start-phase 2.5
        if force_baseline:
            pipeline.set_phase("phase_2_5", PHASE_RUNNING)
            pipeline.save(self.project_root)

        # Enter the extraction branch FIRST, then run baseline rerun +
        # loop inside ``try`` — ``finally`` below guarantees the working
        # tree returns to ``master`` on every exit path (normal completion,
        # BLOCKED, --end-stage stop, keyboard interrupt, exception, or
        # ``sys.exit`` from branch creation failure). Baseline rerun
        # commits land on the extraction branch, not master, honoring the
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
            if not pipeline.is_done("phase_2_5") or (
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
                    # Phase 2.5 exit validation before marking done. File
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
                    if not baseline_report.passed:
                        print("  [WARN] Existing baseline failed validation. "
                              "Re-running Phase 2.5 to repair.")
                        self.run_baseline_production(pipeline.target_characters)
                        sha = commit_stage(
                            self.project_root, "baseline",
                            message="Phase 2.5 baseline (validation-triggered "
                                    "recovery)")
                        if sha:
                            print(f"  [OK] Baseline committed as {sha}")
                    else:
                        pipeline.mark_done("phase_2_5")
                        pipeline.save(self.project_root)
                else:
                    print("  [WARN] Baseline not completed. Running Phase 2.5...")
                    self.run_baseline_production(pipeline.target_characters)
                    # Commit baseline so extraction starts with clean tree
                    sha = commit_stage(self.project_root, "baseline",
                                       message="Phase 2.5 baseline (recovery)")
                    if sha:
                        print(f"  [OK] Baseline committed as {sha}")

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
            print(f"  Phase 3: Extraction Loop")
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
                checkout_master(
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
                        proc_type, proc_id, result = future.result()
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

            # Determine stage order (0-based index in stages list)
            stage_order = next(
                (i for i, b in enumerate(phase3.stages)
                 if b.stage_id == stage.stage_id), 0)

            pp_errors, pp_warnings = run_stage_post_processing(
                project_root=self.project_root,
                work_id=pipeline.work_id,
                stage_id=stage.stage_id,
                stage_order=stage_order,
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
            # reach repair_agent with an incomplete file list.
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

            # LLM callable for semantic checker + T1/T2/T3 fixers
            default_timeout = get_config().phase3.review_timeout_s

            def _llm_call(prompt: str, timeout: int | None = None) -> str:
                result = run_with_retry(
                    self.reviewer_backend or self.backend,
                    prompt,
                    timeout_seconds=timeout or default_timeout,
                    lane_name=f"repair[{stage.stage_id}]",
                )
                return result.text

            importance_map = load_importance_map(
                self.project_root, pipeline.work_id)

            ra_cfg = get_config().repair_agent

            # Per-file parallel repair (E1). Each file becomes an
            # independent repair transaction with its own coordinator.run
            # invocation, recorder, and tracker. Files are dispatched to a
            # ThreadPoolExecutor sized by [repair_agent].repair_concurrency.
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
                        t3_max=ra_cfg.t3_retry,
                        t3_max_per_file=ra_cfg.t3_max_per_file,
                        max_total_rounds=ra_cfg.total_round_limit,
                    ),
                )

            def _repair_one(f: RepairFileEntry) -> tuple[
                    RepairFileEntry, RepairResult]:
                rec_path = progress_dir / (
                    f"repair_{stage.stage_id}_"
                    f"{_repair_slug(f.path)}.jsonl")
                with RepairRecorder(rec_path) as recorder:
                    result = run_repair(
                        files=[f],
                        config=_repair_cfg(),
                        source_context=source_ctx,
                        llm_call=_llm_call,
                        importance_map=importance_map,
                        relationship_history_summary_max_chars=(
                            ra_cfg.relationship_history_summary_max_chars),
                        recorder=recorder,
                    )
                return f, result

            repair_concurrency = max(1, ra_cfg.repair_concurrency)
            print(f"  [4/5] Repair agent ({len(repair_files)} files, "
                  f"up to {repair_concurrency} parallel)...")
            per_file_results: list[tuple[RepairFileEntry, RepairResult]] = []
            with ThreadPoolExecutor(
                    max_workers=repair_concurrency) as pool:
                futures = {
                    pool.submit(_repair_one, f): f for f in repair_files
                }
                for fut in as_completed(futures):
                    submitted = futures[fut]
                    try:
                        per_file_results.append(fut.result())
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

            if all_pass:
                tracker.print_step_done(
                    4, 5, "Repair agent", "PASS")
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

            stage.transition(StageState.PASSED)
            phase3.save(self.project_root)

            # Repair may have rewritten source fields that post-processing
            # already consumed (memory_timeline.digest_summary,
            # world stage_events, character stage_events). Re-run the
            # programmatic post-processing pass so
            # memory_digest.jsonl / world_event_digest.jsonl /
            # stage_catalog.json reflect the repaired source. The pass is
            # idempotent and 0-token; if repair made no substantive change
            # the re-run is a no-op. Errors here downgrade the stage to
            # ERROR so --resume retries (same contract as the first pass).
            stage_order_pp2 = next(
                (i for i, b in enumerate(phase3.stages)
                 if b.stage_id == stage.stage_id), 0)
            pp2_errors, pp2_warnings = run_stage_post_processing(
                project_root=self.project_root,
                work_id=pipeline.work_id,
                stage_id=stage.stage_id,
                stage_order=stage_order_pp2,
                character_ids=pipeline.target_characters,
                chapter_range=stage.chapters,
            )
            for w in pp2_warnings:
                print(f"    [WARN] post-repair PP: {w}")
            if pp2_errors:
                for e in pp2_errors:
                    print(f"    [ERROR] post-repair PP: {e}")
                stage.error_message = (
                    "; ".join(pp2_errors)[:2000]
                    or "post-repair post-processing failed")
                stage.transition(StageState.FAILED)
                stage.transition(StageState.ERROR)
                phase3.save(self.project_root)
                return


        # --- Step 5: Git commit ---
        if stage.state == StageState.PASSED:
            tracker.start_step()
            tracker.print_step(5, 5, "Git commit")

            # Attempt the git commit first. Only after a real SHA comes back
            # do we transition to COMMITTED. If commit_stage returns None
            # (empty diff or commit failure), treat the stage as FAILED and
            # preserve the progress file so the next resume can retry.
            # See requirements.md §11.4b "提交顺序契约".
            sha = commit_stage(self.project_root, stage.stage_id)
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
        """
        assert self.pipeline and self.phase3
        print("\n--- Phase 3.5: Cross-stage consistency check ---")
        stage_ids = [b.stage_id for b in self.phase3.stages
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
            print("  [BLOCKED] Errors found — Phase 4 blocked. "
                  "Review consistency_report.json and fix before retrying.")
            for issue in report.issues:
                if issue.severity == "error":
                    print(f"    [ERROR] [{issue.category}] {issue.location}: "
                          f"{issue.message}")
            return False

        print("  [OK] No blocking issues found.")
        return True

    def _run_scene_archive(self, *, end_stage: int = 0,
                           resume: bool = True) -> None:
        """Run Phase 4: scene archive generation."""
        run_scene_archive(
            self.project_root, self.work_id, self.backend,
            concurrency=self.concurrency,
            end_stage=end_stage,
            resume=resume,
        )

    def _offer_squash_merge(self) -> None:
        """After all stages complete, offer to squash-merge to master."""
        assert self.pipeline and self.phase3
        branch = self.pipeline.extraction_branch
        if not branch:
            return

        print(f"\n  All stages committed on branch '{branch}'.")
        print(f"  Squash-merge to master will consolidate all extraction")
        print(f"  commits into a single clean commit.")

        if get_config().git.auto_squash_merge:
            print("  [auto] [git].auto_squash_merge = true; merging.")
            answer = "y"
        else:
            try:
                answer = input("  Squash-merge to master now? [Y/n]: ").strip()
            except EOFError:
                answer = "n"

        if answer.lower() == "n":
            print(f"  Skipped. You can manually merge later:\n"
                  f"    git checkout master && "
                  f"git merge --squash {branch} && "
                  f"git commit")
            return

        chars = ", ".join(self.pipeline.target_characters)
        n = len(self.phase3.stages)
        message = (f"Extraction complete: {self.pipeline.work_id} "
                   f"({n} stages, {chars})\n\n"
                   f"Squash-merged from {branch}.\n"
                   f"Automated extraction via persona-extraction orchestrator.")

        sha = squash_merge_to(self.project_root, "master", branch, message)
        if sha:
            print(f"  [OK] Squash-merged to master as {sha}")
            print(f"  Extraction branch '{branch}' preserved. "
                  f"Delete with: git branch -d {branch}")
        else:
            print(f"  [ERROR] Squash-merge failed. "
                  f"Merge manually from '{branch}'.")

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

        # Self-heal: if Phase 2 is done and stage_plan exists but
        # phase3_stages.json was deleted/corrupted, rebuild from stage_plan
        # rather than falling through to the fresh-start path (which would
        # re-prompt for characters and overwrite pipeline.json).
        if (pipeline and pipeline.is_done("phase_2") and phase3 is None):
            stage_plan_path = (self.project_root / "works" / self.work_id
                               / "analysis" / "stage_plan.json")
            if stage_plan_path.exists():
                stage_plan_data = _load_json(stage_plan_path) or {}
                phase3 = Phase3Progress(
                    work_id=self.work_id,
                    stage_size=stage_plan_data.get(
                        "default_stage_size", 10),
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

        if phase3 is not None:
            rec = phase3.reconcile_with_disk(
                self.project_root, pipeline.target_characters)
            if rec["reverted"] or rec["purged_files"]:
                print(f"[RECONCILE] Phase 3: reverted {rec['reverted']} "
                      f"stage(s), purged {rec['purged_files']} stale "
                      f"artifact(s), {rec['sha_missing']} committed_sha "
                      f"missing from git")
                phase3.save(self.project_root)

        if pipeline and phase3 and pipeline.is_done("phase_2"):
            print(f"Found existing progress for {self.work_id}.")
            print(f"  Completed: {phase3.completed_stage_count()}"
                  f"/{len(phase3.stages)}")
            # Auto-resume when characters are preset (non-interactive mode)
            if preset_characters:
                print("  Auto-resuming (preset characters provided).")
                self.pipeline = pipeline
                self.phase3 = phase3
                self.run_extraction_loop(
                    pipeline, phase3,
                    max_stages=preset_end_stage)
                return
            resume = input("Resume from existing progress? [Y/n]: ").strip()
            if resume.lower() != "n":
                self.pipeline = pipeline
                self.phase3 = phase3
                self.run_extraction_loop(
                    pipeline, phase3,
                    max_stages=preset_end_stage)
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
            preset_end_stage=preset_end_stage,
        )

        self.pipeline = pipeline
        self.phase3 = phase3

        # Create extraction branch, run baseline + extraction. ``finally``
        # returns to ``master`` if anything raises between switching to
        # the extraction branch and ``run_extraction_loop`` completing
        # its own cleanup. See ai_context/architecture.md §Git Branch Model.
        try:
            if pipeline.extraction_branch:
                create_extraction_branch(self.project_root,
                                         pipeline.extraction_branch)

            self.run_baseline_production(pipeline.target_characters)

            # Commit baseline output so Phase 3 starts with a clean tree
            sha = commit_stage(self.project_root, "baseline",
                               message="Phase 0-2.5 baseline")
            if sha:
                print(f"  [OK] Baseline committed as {sha}")

            self.run_extraction_loop(pipeline, phase3,
                                     max_stages=preset_end_stage)
        finally:
            if pipeline and pipeline.extraction_branch:
                checkout_master(
                    self.project_root,
                    scope_paths=[f"works/{pipeline.work_id}/"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_stage_plan_limits(
    stage_plan: dict[str, Any],
    *,
    max_stage_size: int = 15,
    min_stage_size: int = 5,
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
