"""Main orchestrator — drives the full extraction pipeline.

Flow:
  1. Analysis phase (LLM)  → batch plan + candidate characters
  2. User confirmation      → select characters, confirm batch plan, set range
  3. Extraction loop        → for each batch:
       a. Git preflight
       b. Build prompt
       c. Run extraction agent (LLM)
       d. Programmatic validation (Python)
       e. Semantic review (LLM)
       f. Git commit or rollback + retry
"""

from __future__ import annotations

import json
import logging
import signal
import sys
from pathlib import Path
from typing import Any

from .git_utils import (
    commit_batch,
    create_extraction_branch,
    preflight_check,
    rollback_to_head,
)
from .llm_backend import LLMBackend, LLMResult, run_with_retry
from .progress import BatchEntry, BatchState, ExtractionProgress
from .prompt_builder import (
    build_analysis_prompt,
    build_extraction_prompt,
    build_reviewer_prompt,
)
from .validator import ValidationReport, validate_batch

logger = logging.getLogger(__name__)


class ExtractionOrchestrator:
    """Drives the full automated extraction pipeline."""

    def __init__(
        self,
        project_root: Path,
        work_id: str,
        backend: LLMBackend,
        reviewer_backend: LLMBackend | None = None,
    ):
        self.project_root = project_root
        self.work_id = work_id
        self.backend = backend
        self.reviewer_backend = reviewer_backend or backend
        self.progress: ExtractionProgress | None = None
        self._interrupted = False

        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum: int, frame: Any) -> None:
        logger.warning("Interrupt received. Saving progress and exiting...")
        self._interrupted = True
        if self.progress:
            self.progress.save(self.project_root)
        sys.exit(130)

    # ------------------------------------------------------------------
    # Phase 1: Analysis
    # ------------------------------------------------------------------

    def run_analysis(self) -> dict[str, Any]:
        """Run analysis phase: overview, batch plan, candidate characters."""
        print("\n" + "=" * 60)
        print("  Phase 1: Analysis")
        print("=" * 60 + "\n")

        prompt = build_analysis_prompt(self.project_root, self.work_id)
        result = run_with_retry(self.backend, prompt)

        if not result.success:
            print(f"[ERROR] Analysis failed: {result.error}")
            sys.exit(1)

        print("[OK] Analysis complete.")

        # Try to load the generated files
        work_dir = self.project_root / "works" / self.work_id
        batch_plan = _load_json(
            work_dir / "analysis" / "incremental" / "source_batch_plan.json")
        candidates = _load_json(
            work_dir / "analysis" / "incremental" / "candidate_characters.json")

        return {
            "batch_plan": batch_plan,
            "candidates": candidates,
            "raw_output": result.text,
        }

    # ------------------------------------------------------------------
    # Phase 2: User confirmation
    # ------------------------------------------------------------------

    def confirm_with_user(
        self,
        analysis: dict[str, Any],
        *,
        preset_characters: list[str] | None = None,
        preset_end_batch: int | None = None,
    ) -> ExtractionProgress:
        """Interactive user confirmation of characters and parameters."""
        print("\n" + "=" * 60)
        print("  Phase 2: User Confirmation")
        print("=" * 60 + "\n")

        candidates = analysis.get("candidates", {})
        batch_plan = analysis.get("batch_plan", {})

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

        # End batch
        if preset_end_batch is not None:
            end_batch = preset_end_batch
        else:
            raw = input(f"Extract up to batch N (total {total_batches}, "
                        f"0 or empty = all): ").strip()
            end_batch = int(raw) if raw else 0

        if end_batch > 0:
            batches_data = batches_data[:end_batch]

        batch_size = batch_plan.get("default_batch_size", 10)

        progress = ExtractionProgress(
            work_id=self.work_id,
            target_characters=selected,
            batch_size=batch_size,
            extraction_branch=f"extraction/{self.work_id}",
            batches=[
                BatchEntry(
                    batch_id=b["batch_id"],
                    stage_id=b["stage_id"],
                    chapters=b["chapters"],
                    chapter_count=b.get("chapter_count", 10),
                )
                for b in batches_data
            ],
            analysis_done=True,
            characters_confirmed=True,
        )

        progress.save(self.project_root)
        self.progress = progress

        print(f"\n[OK] Configuration saved.")
        print(f"     Characters: {selected}")
        print(f"     Batches: {len(progress.batches)}")
        print(f"     Branch: {progress.extraction_branch}")
        return progress

    # ------------------------------------------------------------------
    # Phase 3: Extraction loop
    # ------------------------------------------------------------------

    def run_extraction_loop(self, progress: ExtractionProgress | None = None,
                            ) -> None:
        """Main extraction loop: iterate through batches."""
        progress = progress or self.progress
        if not progress:
            print("[ERROR] No progress loaded. Run analysis first.")
            sys.exit(1)

        self.progress = progress

        print("\n" + "=" * 60)
        print("  Phase 3: Extraction Loop")
        print("=" * 60)
        print(f"  Work: {progress.work_id}")
        print(f"  Characters: {progress.target_characters}")
        print(f"  Total batches: {len(progress.batches)}")
        print(f"  Completed: {progress.completed_batch_count()}")
        print("=" * 60 + "\n")

        # Create extraction branch
        if progress.extraction_branch:
            if not create_extraction_branch(self.project_root,
                                            progress.extraction_branch):
                print("[ERROR] Cannot create extraction branch.")
                sys.exit(1)

        while True:
            if self._interrupted:
                break

            batch = progress.next_pending_batch()
            if batch is None:
                if progress.all_committed():
                    print("\n[DONE] All batches completed!")
                else:
                    print("\n[BLOCKED] No actionable batches. "
                          "Check progress for blocked/error batches.")
                break

            self._process_batch(progress, batch)

    def _process_batch(self, progress: ExtractionProgress,
                       batch: BatchEntry) -> None:
        """Process a single batch through the full pipeline."""
        print(f"\n{'─' * 50}")
        print(f"  Batch: {batch.batch_id} ({batch.stage_id})")
        print(f"  Chapters: {batch.chapters}")
        print(f"  State: {batch.state.value}")
        print(f"  Retry: {batch.retry_count}/{batch.max_retries}")
        print(f"{'─' * 50}\n")

        # Handle state resumption
        if batch.state == BatchState.FAILED:
            if batch.retry_count >= batch.max_retries:
                print(f"[BLOCKED] {batch.batch_id} exceeded max retries. "
                      f"Needs manual intervention.")
                return
            batch.transition(BatchState.RETRYING)
            batch.retry_count += 1
            progress.save(self.project_root)

        if batch.state in (BatchState.RETRYING, BatchState.PENDING):
            # --- Step 1: Git preflight ---
            print("[1/5] Git preflight check...")
            problems = preflight_check(
                self.project_root, progress.extraction_branch or None)
            if problems:
                for p in problems:
                    print(f"  [PROBLEM] {p}")
                batch.transition(BatchState.ERROR)
                batch.error_message = "; ".join(problems)
                progress.save(self.project_root)
                return

            # --- Step 2: Run extraction ---
            print("[2/5] Running coordinated extraction...")
            batch.transition(BatchState.EXTRACTING)
            progress.save(self.project_root)

            prompt = build_extraction_prompt(
                self.project_root, progress, batch,
                reviewer_feedback=batch.last_reviewer_feedback)

            result = run_with_retry(self.backend, prompt,
                                    timeout_seconds=900)

            if not result.success:
                print(f"  [ERROR] Extraction failed: {result.error}")
                batch.transition(BatchState.ERROR)
                batch.error_message = result.error or "unknown"
                progress.save(self.project_root)
                return

            batch.transition(BatchState.EXTRACTED)
            progress.save(self.project_root)

        # --- Step 3: Programmatic validation ---
        if batch.state == BatchState.EXTRACTED:
            print("[3/5] Programmatic validation...")
            report = validate_batch(
                self.project_root, progress.work_id,
                batch.stage_id, progress.target_characters)

            print(report.summary())

            if not report.passed:
                print("  [FAIL] Programmatic validation failed.")
                rollback_to_head(self.project_root)
                batch.transition(BatchState.REVIEWING)
                # Treat as review failure so retry includes feedback
                batch.last_reviewer_feedback = (
                    "Programmatic validation failures:\n" +
                    "\n".join(str(i) for i in report.issues
                             if i.severity == "error"))
                batch.transition(BatchState.FAILED)
                progress.save(self.project_root)
                return

            batch.transition(BatchState.REVIEWING)
            progress.save(self.project_root)

        # --- Step 4: Semantic review ---
        if batch.state == BatchState.REVIEWING:
            print("[4/5] Semantic review...")
            # Re-run programmatic for the report text
            report = validate_batch(
                self.project_root, progress.work_id,
                batch.stage_id, progress.target_characters)

            reviewer_prompt = build_reviewer_prompt(
                self.project_root, progress, batch,
                report.summary())

            review_result = run_with_retry(
                self.reviewer_backend, reviewer_prompt,
                timeout_seconds=600)

            if not review_result.success:
                print(f"  [ERROR] Review failed: {review_result.error}")
                batch.transition(BatchState.FAILED)
                batch.last_reviewer_feedback = (
                    f"Review agent error: {review_result.error}")
                progress.save(self.project_root)
                return

            verdict = _parse_verdict(review_result.text)
            print(f"  Verdict: {verdict['verdict']}")

            if verdict["verdict"] != "PASS":
                print("  [FAIL] Semantic review failed.")
                print(f"  Findings: {verdict.get('findings', '')[:500]}")
                rollback_to_head(self.project_root)
                batch.transition(BatchState.FAILED)
                batch.last_reviewer_feedback = review_result.text
                progress.save(self.project_root)
                return

            batch.transition(BatchState.PASSED)
            progress.save(self.project_root)

        # --- Step 5: Git commit ---
        if batch.state == BatchState.PASSED:
            print("[5/5] Committing...")
            sha = commit_batch(self.project_root,
                               batch.batch_id, batch.stage_id)
            if sha:
                batch.committed_sha = sha
                batch.transition(BatchState.COMMITTED)
                print(f"  [OK] Committed as {sha}")
            else:
                print("  [WARN] Nothing to commit (no changes?)")
                batch.transition(BatchState.COMMITTED)

            progress.save(self.project_root)

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
        # Check for existing progress
        existing = ExtractionProgress.load(self.project_root, self.work_id)
        if existing and existing.characters_confirmed:
            print(f"Found existing progress for {self.work_id}.")
            print(f"  Completed: {existing.completed_batch_count()}"
                  f"/{len(existing.batches)}")
            resume = input("Resume from existing progress? [Y/n]: ").strip()
            if resume.lower() != "n":
                self.progress = existing
                self.run_extraction_loop(existing)
                return

        # Fresh start
        analysis = self.run_analysis()
        progress = self.confirm_with_user(
            analysis,
            preset_characters=preset_characters,
            preset_end_batch=preset_end_batch,
        )
        self.run_extraction_loop(progress)


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


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
