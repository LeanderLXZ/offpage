"""Phase 4 — Scene archive: split chapters into scenes.

Each chapter is processed independently by a single LLM call that outputs
scene boundary annotations (start/end line numbers + metadata).  The program
then extracts full_text from the original chapter file using those line
numbers.  Multiple chapters run in parallel via ThreadPoolExecutor.

Progress is tracked in:
  works/{work_id}/analysis/progress/phase4_scenes.json

Intermediate per-chapter results are stored in:
  works/{work_id}/analysis/scene_splits/{chapter}.json

Final output:
  works/{work_id}/retrieval/scene_archive.jsonl
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

from .config import get_config
from .llm_backend import LLMBackend, run_with_retry
from .json_repair import programmatic_repair
from .process_guard import PidLock
from .prompt_builder import build_scene_split_prompt
from .rate_limit import RateLimitController, get_active as get_active_rl, set_active as set_active_rl


@lru_cache(maxsize=1)
def _scene_split_validator() -> jsonschema.Draft202012Validator:
    """Lazy-load schemas/analysis/scene_split.schema.json once per process."""
    schema_path = (Path(__file__).resolve().parents[2]
                   / "schemas/analysis/scene_split.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

class ChapterState:
    PENDING = "pending"
    SPLITTING = "splitting"
    SPLIT = "split"
    VALIDATING = "validating"
    PASSED = "passed"
    FAILED = "failed"
    RETRYING = "retrying"
    ERROR = "error"


@dataclass
class ChapterEntry:
    chapter_id: str
    state: str = ChapterState.PENDING
    retry_count: int = 0
    max_retries: int = 2
    error_message: str = ""
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, chapter_id: str, d: dict[str, Any]) -> ChapterEntry:
        return cls(
            chapter_id=chapter_id,
            state=d.get("state", ChapterState.PENDING),
            retry_count=d.get("retry_count", 0),
            max_retries=d.get("max_retries", 2),
            error_message=d.get("error_message", ""),
            last_updated=d.get("last_updated", ""),
        )


@dataclass
class SceneArchiveProgress:
    work_id: str
    total_chapters: int = 0
    chapters: dict[str, ChapterEntry] = field(default_factory=dict)
    merged: bool = False
    last_updated: str = ""

    def progress_path(self, project_root: Path) -> Path:
        return (project_root / "works" / self.work_id
                / "analysis" / "progress" / "phase4_scenes.json")

    def splits_dir(self, project_root: Path) -> Path:
        return (project_root / "works" / self.work_id
                / "analysis" / "scene_splits")

    def save(self, project_root: Path) -> Path:
        path = self.progress_path(project_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.last_updated = _now_iso()
        data = {
            "phase": "scene_archive",
            "work_id": self.work_id,
            "total_chapters": self.total_chapters,
            "chapters": {
                cid: entry.to_dict()
                for cid, entry in self.chapters.items()
            },
            "merged": self.merged,
            "last_updated": self.last_updated,
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return path

    @classmethod
    def load(cls, project_root: Path, work_id: str,
             ) -> SceneArchiveProgress | None:
        path = (project_root / "works" / work_id / "analysis"
                / "progress" / "phase4_scenes.json")
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            prog = cls(
                work_id=data["work_id"],
                total_chapters=data.get("total_chapters", 0),
                merged=data.get("merged", False),
                last_updated=data.get("last_updated", ""),
            )
            for cid, entry_data in data.get("chapters", {}).items():
                prog.chapters[cid] = ChapterEntry.from_dict(cid, entry_data)
            return prog
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.warning("Failed to load scene archive progress: %s", exc)
            return None

    def pending_chapters(self) -> list[str]:
        """Return chapter IDs that need processing."""
        actionable = {ChapterState.PENDING, ChapterState.SPLITTING,
                      ChapterState.SPLIT, ChapterState.VALIDATING,
                      ChapterState.RETRYING, ChapterState.FAILED}
        return [cid for cid, e in sorted(self.chapters.items())
                if e.state in actionable]

    def failed_chapters(self) -> list[str]:
        return [cid for cid, e in sorted(self.chapters.items())
                if e.state in (ChapterState.FAILED, ChapterState.ERROR)]

    def all_passed(self) -> bool:
        return all(e.state == ChapterState.PASSED
                   for e in self.chapters.values())

    def reset_failed(self) -> int:
        """Reset blocked (ERROR) chapters to pending (for --resume).

        FAILED chapters auto-retry within the same run, so only ERROR
        (exceeded max_retries) needs reset here.  Resets retry_count to 0
        so the user gets a fresh set of retries — matches Phase 3 behavior.
        """
        count = 0
        for entry in self.chapters.values():
            if entry.state == ChapterState.ERROR:
                entry.state = ChapterState.PENDING
                entry.retry_count = 0
                entry.error_message = ""
                count += 1
        return count

    def reconcile_with_disk(self, project_root: Path) -> dict[str, int]:
        """Reconcile chapter states against on-disk split files.

        Rules:
          - state == PASSED but split file missing → revert to PENDING
          - state == PENDING but split file present → delete (partial run)
          - state in any intermediate state (SPLITTING, SPLIT, VALIDATING,
            FAILED, RETRYING, ERROR) → delete any split file, revert to
            PENDING

        Returns counts: {"reverted": N, "purged": M}.
        """
        splits = self.splits_dir(project_root)
        reverted = 0
        purged = 0
        for entry in self.chapters.values():
            split_path = splits / f"{entry.chapter_id}.json"
            on_disk = split_path.exists()

            if entry.state == ChapterState.PASSED:
                if not on_disk:
                    entry.state = ChapterState.PENDING
                    entry.retry_count = 0
                    entry.error_message = ""
                    reverted += 1
                continue

            if entry.state == ChapterState.PENDING:
                if on_disk:
                    split_path.unlink()
                    purged += 1
                continue

            if on_disk:
                split_path.unlink()
                purged += 1
            entry.state = ChapterState.PENDING
            entry.retry_count = 0
            entry.error_message = ""
            reverted += 1
        return {"reverted": reverted, "purged": purged}

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.chapters.values():
            counts[entry.state] = counts.get(entry.state, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_scene_split(
    scenes: list[dict[str, Any]],
    total_lines: int,
    known_aliases: set[str] | None = None,
) -> list[str]:
    """Validate a chapter's scene split output.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    if not scenes:
        errors.append("No scenes produced")
        return errors

    required_fields = {"scene_start_line", "scene_end_line",
                       "time", "location",
                       "characters_present", "summary"}

    prev_end = 0
    for i, scene in enumerate(scenes):
        prefix = f"Scene {i + 1}"

        # Check required fields
        missing = required_fields - set(scene.keys())
        if missing:
            errors.append(f"{prefix}: missing fields: {missing}")
            continue

        start = scene.get("scene_start_line")
        end = scene.get("scene_end_line")

        if not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"{prefix}: start/end line must be integers")
            continue

        # Line number validity
        if start < 1:
            errors.append(f"{prefix}: start_line {start} < 1")
        if end > total_lines:
            errors.append(f"{prefix}: end_line {end} > total lines {total_lines}")
        if start > end:
            errors.append(f"{prefix}: start_line {start} > end_line {end}")

        # No overlap, no gap
        expected_start = prev_end + 1
        if start != expected_start:
            if start < expected_start:
                errors.append(
                    f"{prefix}: overlap — start_line {start}, "
                    f"previous scene ended at {prev_end}")
            else:
                errors.append(
                    f"{prefix}: gap — lines {expected_start}-{start - 1} "
                    f"not covered")
        prev_end = end

        # Empty fields
        for fld in ("time", "location", "summary"):
            if not scene.get(fld):
                errors.append(f"{prefix}: {fld} is empty")

        if not scene.get("characters_present"):
            errors.append(f"{prefix}: characters_present is empty")

        # Alias matching (soft check)
        if known_aliases:
            for char in scene.get("characters_present", []):
                if char not in known_aliases:
                    errors.append(
                        f"{prefix}: unknown character '{char}' "
                        f"(not in known aliases)")

    # Check full coverage
    if prev_end != total_lines:
        errors.append(
            f"Incomplete coverage: last scene ends at line {prev_end}, "
            f"but chapter has {total_lines} lines")

    # JSON Schema gate (schemas/analysis/scene_split.schema.json)
    # Schema enforces all bounds (time/location, summary, maxItems,
    # additionalProperties=false); exact numbers live in the schema.
    # Fail messages are appended to the same errors list so the existing
    # retry-with-prior-error path picks them up.
    for err in _scene_split_validator().iter_errors(scenes):
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"schema {path}: {err.message[:80]}")

    return errors


# ---------------------------------------------------------------------------
# Single chapter processing
# ---------------------------------------------------------------------------

def _mark_failed(entry: ChapterEntry, msg: str) -> str:
    """Increment retry_count and set FAILED or ERROR. Returns msg."""
    entry.retry_count += 1
    if entry.retry_count > entry.max_retries:
        entry.state = ChapterState.ERROR
    else:
        entry.state = ChapterState.FAILED
    entry.error_message = msg
    entry.last_updated = _now_iso()
    return msg


def _process_chapter(
    project_root: Path,
    work_id: str,
    chapter_id: str,
    backend: LLMBackend,
    progress: SceneArchiveProgress,
    known_aliases: set[str] | None = None,
) -> tuple[str, bool, str]:
    """Process a single chapter.  Returns (chapter_id, success, error_msg)."""
    entry = progress.chapters[chapter_id]
    chapter_path = (project_root / "sources" / "works" / work_id
                    / "chapters" / f"{chapter_id}.txt")

    if not chapter_path.exists():
        return chapter_id, False, f"Chapter file not found: {chapter_path}"

    lines = chapter_path.read_text(encoding="utf-8").splitlines()
    total_lines = len(lines)

    if total_lines == 0:
        return chapter_id, False, "Chapter file is empty"

    # Build prompt (inject prior error if retrying)
    prior_error = entry.error_message if entry.retry_count > 0 else ""
    prompt = build_scene_split_prompt(
        project_root, work_id, chapter_id, lines,
        prior_error=prior_error)

    # Update state
    entry.state = ChapterState.SPLITTING
    entry.last_updated = _now_iso()

    # Run LLM
    cfg = get_config()
    result = run_with_retry(
        backend, prompt,
        timeout_seconds=cfg.phase3.review_timeout_s,
        lane_name=f"scene[{chapter_id}]",
    )

    if not result.success:
        msg = result.error or "LLM call failed"
        return chapter_id, False, _mark_failed(entry, msg)

    entry.state = ChapterState.SPLIT
    entry.last_updated = _now_iso()

    # Parse output
    scenes = _parse_scene_output(result.text)
    if scenes is None:
        # Try L1 programmatic JSON repair
        repaired = programmatic_repair(result.text)
        scenes = _parse_scene_output(repaired)

    if scenes is None:
        msg = "Failed to parse LLM output as JSON array"
        return chapter_id, False, _mark_failed(entry, msg)

    # Validate
    entry.state = ChapterState.VALIDATING
    entry.last_updated = _now_iso()

    errors = validate_scene_split(scenes, total_lines, known_aliases)

    if errors:
        msg = "; ".join(errors)
        return chapter_id, False, _mark_failed(entry, msg)

    # Save intermediate result
    splits_dir = progress.splits_dir(project_root)
    splits_dir.mkdir(parents=True, exist_ok=True)
    split_path = splits_dir / f"{chapter_id}.json"
    split_path.write_text(
        json.dumps(scenes, ensure_ascii=False, indent=2),
        encoding="utf-8")

    entry.state = ChapterState.PASSED
    entry.error_message = ""
    entry.last_updated = _now_iso()

    return chapter_id, True, ""


def _parse_scene_output(text: str) -> list[dict[str, Any]] | None:
    """Extract JSON array from LLM output."""
    text = text.strip()

    # Try direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    import re
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Try finding first [ ... ] block
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def _build_chapter_to_stage_map(
    project_root: Path, work_id: str,
) -> dict[str, str]:
    """Build chapter_id → stage_id mapping from stage_plan.json."""
    plan_path = (project_root / "works" / work_id / "analysis"
                 / "stage_plan.json")
    if not plan_path.exists():
        return {}

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}

    for stage in plan.get("stages", []):
        stage_id = stage.get("stage_id", "")
        ch_range = stage.get("chapters", "")
        if "-" in ch_range:
            parts = ch_range.split("-")
            ch_start = int(parts[0])
            ch_end = int(parts[1])
            for ch in range(ch_start, ch_end + 1):
                mapping[f"{ch:04d}"] = stage_id

    return mapping


_STAGE_NUM_RE = re.compile(r"(\d+)")


def _stage_number(stage_id: str) -> int:
    """Extract the leading numeric stage index from ``S###`` style IDs."""
    m = _STAGE_NUM_RE.search(stage_id or "")
    return int(m.group(1)) if m else 0


def merge_scene_archive(
    project_root: Path,
    work_id: str,
    progress: SceneArchiveProgress,
) -> tuple[bool, str]:
    """Merge all per-chapter splits into scene_archive.jsonl.

    ``stage_plan.json`` is the **single source of truth** for
    ``stage_id``: any pre-existing ``scene_archive.jsonl`` is entirely
    overwritten so stale stage names (e.g. from an earlier Phase 1 run)
    cannot leak through. ``scene_id`` is assigned as
    ``SC-S{stage:03d}-{seq:02d}`` with ``seq`` growing monotonically within
    a stage following chapter order + intra-chapter scene order.

    Returns (success, error_message).
    """
    if not progress.all_passed():
        return False, "Not all chapters have passed"

    chapter_to_stage = _build_chapter_to_stage_map(project_root, work_id)
    if not chapter_to_stage:
        return False, "stage_plan.json not found or empty"

    known_stage_ids = set(chapter_to_stage.values())

    splits_dir = progress.splits_dir(project_root)
    retrieval_dir = project_root / "works" / work_id / "retrieval"
    retrieval_dir.mkdir(parents=True, exist_ok=True)
    output_path = retrieval_dir / "scene_archive.jsonl"

    all_scenes: list[dict[str, Any]] = []
    scene_ids_seen: set[str] = set()
    stage_seq_counter: dict[str, int] = {}

    for chapter_id in sorted(progress.chapters.keys()):
        split_path = splits_dir / f"{chapter_id}.json"
        if not split_path.exists():
            return False, f"Split file missing for chapter {chapter_id}"

        scenes = json.loads(split_path.read_text(encoding="utf-8"))
        chapter_path = (project_root / "sources" / "works" / work_id
                        / "chapters" / f"{chapter_id}.txt")
        lines = chapter_path.read_text(encoding="utf-8").splitlines()

        stage_id = chapter_to_stage.get(chapter_id, "")
        if not stage_id:
            return False, (
                f"Chapter {chapter_id} has no stage_id in "
                f"stage_plan.json (stage plan is authoritative)")
        if stage_id not in known_stage_ids:
            return False, (
                f"Chapter {chapter_id} mapped to unknown stage_id "
                f"'{stage_id}' (stage plan mismatch)")

        stage_num = _stage_number(stage_id)
        if stage_num <= 0 or stage_num > 999:
            return False, (
                f"stage_id '{stage_id}' yields invalid stage number "
                f"{stage_num} (must be 1..999)")

        for scene in scenes:
            seq = stage_seq_counter.get(stage_id, 0) + 1
            stage_seq_counter[stage_id] = seq
            if seq > 99:
                return False, (
                    f"stage '{stage_id}' exceeds 99 scenes — ID format "
                    f"SC-S###-## supports max 99 per stage; split the "
                    f"stage or regenerate stage plan")

            scene_id = f"SC-S{stage_num:03d}-{seq:02d}"
            if scene_id in scene_ids_seen:
                return False, f"Duplicate scene_id: {scene_id}"
            scene_ids_seen.add(scene_id)

            start = scene.get("scene_start_line", 1) - 1  # 0-indexed
            end = scene.get("scene_end_line", len(lines))
            full_text = "\n".join(lines[start:end])

            entry = {
                "scene_id": scene_id,
                "stage_id": stage_id,
                "chapter": chapter_id,
                "time": scene.get("time", ""),
                "location": scene.get("location", ""),
                "characters_present": scene.get("characters_present", []),
                "summary": scene.get("summary", ""),
                "full_text": full_text,
            }
            all_scenes.append(entry)

    # Fully rewrite scene_archive.jsonl — stage_plan is the truth source
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in all_scenes:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    chapters_covered = {s["chapter"] for s in all_scenes}
    expected = set(progress.chapters.keys())
    missing = expected - chapters_covered
    if missing:
        return False, f"Chapters missing from output: {sorted(missing)}"

    return True, ""


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def _load_known_aliases(
    project_root: Path, work_id: str,
) -> set[str] | None:
    """Load character aliases from identity.json files if available."""
    chars_dir = project_root / "works" / work_id / "characters"
    if not chars_dir.exists():
        return None

    aliases: set[str] = set()
    for identity_path in chars_dir.glob("*/canon/identity.json"):
        try:
            data = json.loads(identity_path.read_text(encoding="utf-8"))
            # Add canonical name
            if data.get("canonical_name"):
                aliases.add(data["canonical_name"])
            # Add aliases
            for alias in data.get("aliases", []):
                if isinstance(alias, dict) and alias.get("name"):
                    aliases.add(alias["name"])
                elif isinstance(alias, str):
                    aliases.add(alias)
        except (json.JSONDecodeError, OSError):
            continue

    return aliases if aliases else None


def run_scene_archive(
    project_root: Path,
    work_id: str,
    backend: LLMBackend,
    *,
    concurrency: int = 10,
    end_stage: int = 0,
    resume: bool = False,
) -> bool:
    """Run Phase 4: scene archive generation.

    Args:
        concurrency: Max parallel chapter workers.
        end_stage: Only process chapters from stages 1..N (0 = all).
        resume: If True, load existing progress and continue.

    Returns True if completed successfully.
    """
    print("\n" + "=" * 60)
    print("  Phase 4: Scene Archive")
    print("=" * 60)

    # Independent PID lock — allows Phase 4 to run parallel with Phase 3
    lock = PidLock(project_root, work_id,
                   lock_name=".scene_archive.lock")
    existing = lock.is_held()
    if existing:
        pid = existing.get("pid", "?")
        started = existing.get("started", "?")
        print(f"[ERROR] Another Phase 4 process is already running:")
        print(f"  PID: {pid}  Started: {started}")
        print(f"  If the process is dead, remove the lock:")
        print(f"  rm \"{lock.lock_path}\"")
        return False
    if not lock.acquire():
        print("[ERROR] Failed to acquire scene archive lock.")
        return False

    # Install rate-limit controller so run_with_retry can pause/resume
    # against the per-work pause file. If one is already installed (e.g.
    # by the orchestrator running Phase 0-3.5), reuse it instead of
    # shadowing.
    work_root = project_root / "works" / work_id
    own_controller = False
    if get_active_rl() is None:
        set_active_rl(RateLimitController(work_root))
        own_controller = True

    try:
        return _run_scene_archive_inner(
            project_root, work_id, backend,
            concurrency=concurrency, end_stage=end_stage, resume=resume)
    finally:
        lock.release()
        if own_controller:
            set_active_rl(None)


def _run_scene_archive_inner(
    project_root: Path,
    work_id: str,
    backend: LLMBackend,
    *,
    concurrency: int = 10,
    end_stage: int = 0,
    resume: bool = False,
) -> bool:
    """Inner implementation after lock is acquired."""

    # Check precondition: stage_plan.json
    plan_path = (project_root / "works" / work_id / "analysis"
                 / "stage_plan.json")
    if not plan_path.exists():
        print("[ERROR] stage_plan.json not found. "
              "Phase 1 must complete first.")
        return False

    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    # Determine which chapters to process
    chapters_to_process = _collect_chapters(plan, end_stage)
    if not chapters_to_process:
        print("[ERROR] No chapters to process.")
        return False

    # Load or create progress
    progress: SceneArchiveProgress | None = None
    if resume:
        progress = SceneArchiveProgress.load(project_root, work_id)

    if progress is None:
        progress = SceneArchiveProgress(
            work_id=work_id,
            total_chapters=len(chapters_to_process),
        )

    # Ensure all target chapters have entries; refresh max_retries from
    # current config so toml bumps take effect on --resume runs.
    cfg_phase4 = get_config().phase4
    for cid in chapters_to_process:
        if cid not in progress.chapters:
            progress.chapters[cid] = ChapterEntry(
                chapter_id=cid,
                max_retries=cfg_phase4.max_retries_per_chapter,
            )
        else:
            progress.chapters[cid].max_retries = (
                cfg_phase4.max_retries_per_chapter)

    # Reconcile in-memory state against on-disk artifacts, every run.
    # Drift can come from manual edits, interrupted writes, or git resets.
    rec = progress.reconcile_with_disk(project_root)
    if rec["reverted"] or rec["purged"]:
        print(f"  Reconciled with disk: reverted {rec['reverted']} chapter(s) "
              f"to pending, purged {rec['purged']} stale split file(s)")
    if resume:
        reset_count = progress.reset_failed()
        if reset_count > 0:
            print(f"  Reset {reset_count} blocked (ERROR) chapters to pending")

    # Filter to chapters that need work
    pending = [cid for cid in chapters_to_process
               if progress.chapters[cid].state != ChapterState.PASSED]

    if not pending:
        if progress.merged:
            print("  Phase 4 already complete.")
            return True
        print("  All chapters already passed. Proceeding to merge.")
    else:
        stats = progress.stats()
        print(f"  Work: {work_id}")
        print(f"  Total chapters: {len(chapters_to_process)}")
        print(f"  Already passed: {stats.get(ChapterState.PASSED, 0)}")
        print(f"  To process: {len(pending)}")
        print(f"  Concurrency: {concurrency}")
        print("=" * 60)

        # Save initial progress
        progress.save(project_root)

        # Scene archive is work-level (all characters), so skip
        # character name validation — it would reject valid names
        # that aren't in the extracted character set.

        # Run parallel processing
        _run_parallel(
            project_root, work_id, backend, progress,
            pending, concurrency, None)

    # Check if all passed
    not_passed = [cid for cid in chapters_to_process
                  if progress.chapters[cid].state != ChapterState.PASSED]
    if not_passed:
        stats = progress.stats()
        print(f"\n[INCOMPLETE] {len(not_passed)} chapters not passed:")
        for state, count in sorted(stats.items()):
            if state != ChapterState.PASSED:
                print(f"  {state}: {count}")
        progress.save(project_root)
        return False

    # Merge
    print("\n--- Merging scene archive ---")
    success, error = merge_scene_archive(project_root, work_id, progress)
    if not success:
        print(f"[ERROR] Merge failed: {error}")
        progress.save(project_root)
        return False

    progress.merged = True
    progress.save(project_root)

    total_scenes = _count_jsonl_lines(
        project_root / "works" / work_id / "retrieval" / "scene_archive.jsonl")
    print(f"  [OK] scene_archive.jsonl written "
          f"({total_scenes} scenes, {len(chapters_to_process)} chapters)")
    return True


def _collect_chapters(
    plan: dict[str, Any], end_stage: int,
) -> list[str]:
    """Collect chapter IDs from stage plan, respecting end_stage limit.

    Parses the 'chapters' field (format: "0001-0011") from each stage.
    """
    chapters: list[str] = []
    stages = plan.get("stages", [])

    for i, stage in enumerate(stages):
        if end_stage > 0 and (i + 1) > end_stage:
            break
        ch_range = stage.get("chapters", "")
        if "-" in ch_range:
            parts = ch_range.split("-")
            ch_start = int(parts[0])
            ch_end = int(parts[1])
            for ch in range(ch_start, ch_end + 1):
                chapters.append(f"{ch:04d}")

    return chapters


def _run_parallel(
    project_root: Path,
    work_id: str,
    backend: LLMBackend,
    progress: SceneArchiveProgress,
    pending: list[str],
    concurrency: int,
    known_aliases: set[str] | None,
) -> None:
    """Run chapter processing in parallel with circuit breaker."""
    start_time = time.monotonic()
    completed = 0
    failed = 0
    total = len(pending)

    # Circuit breaker: if recent_failures >= threshold within the window,
    # pause all workers before submitting new tasks. Tunable via
    # [phase4] in automation/config.toml. Independent of §11.13's token-
    # limit pause: this guards short-burst failures, that one guards quota.
    cfg = get_config()
    recent_failures: list[float] = []  # timestamps of recent failures
    BREAKER_WINDOW = float(cfg.phase4.circuit_breaker_window_s)
    BREAKER_THRESHOLD = int(cfg.phase4.circuit_breaker_failure_threshold)
    BREAKER_PAUSE = int(cfg.phase4.circuit_breaker_pause_s)

    rl_controller = get_active_rl()

    def _gate() -> None:
        if rl_controller is not None:
            rl_controller.wait_if_paused()

    print(f"\n  Processing {total} chapters with {concurrency} workers...\n")

    pending_iter = iter(pending)
    # FAILED chapters (state == FAILED, retry budget remaining) are
    # appended here and pulled before the main pending_iter so they get
    # a fresh attempt within the same run, with prior_error injected
    # into the prompt by _process_chapter.
    retry_queue: list[str] = []
    retried = 0

    def _next_chapter() -> str | None:
        if retry_queue:
            return retry_queue.pop(0)
        return next(pending_iter, None)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures: dict = {}

        # Seed initial stage
        for _ in range(concurrency):
            chapter_id = _next_chapter()
            if chapter_id is None:
                break
            _gate()
            future = executor.submit(
                _process_chapter,
                project_root, work_id, chapter_id,
                backend, progress, known_aliases,
            )
            futures[future] = chapter_id

        while futures:
            done, _ = wait(futures, return_when=FIRST_COMPLETED)

            for future in done:
                chapter_id = futures.pop(future)
                try:
                    cid, success, error_msg = future.result()
                except Exception as exc:
                    cid = chapter_id
                    success = False
                    error_msg = str(exc)
                    entry = progress.chapters[cid]
                    entry.state = ChapterState.ERROR
                    entry.error_message = error_msg
                    entry.last_updated = _now_iso()

                if success:
                    completed += 1
                    print(f"    [OK] {cid}  ({completed}/{total})")
                else:
                    entry = progress.chapters[cid]
                    if (entry.state == ChapterState.FAILED
                            and entry.retry_count <= entry.max_retries):
                        attempt = entry.retry_count + 1
                        max_attempts = entry.max_retries + 1
                        print(f"    [RETRY] {cid} attempt "
                              f"{attempt}/{max_attempts}: "
                              f"{error_msg[:80]}")
                        # Reset to PENDING so the requeued attempt can
                        # transition through SPLITTING/VALIDATING again.
                        entry.state = ChapterState.PENDING
                        entry.last_updated = _now_iso()
                        retry_queue.append(cid)
                        retried += 1
                    else:
                        failed += 1
                        print(f"    [FAIL] {cid}: {error_msg[:100]}")
                        recent_failures.append(time.monotonic())

                # Periodic save
                if (completed + failed) % 10 == 0:
                    progress.save(project_root)

            # Circuit breaker check before submitting new tasks
            now = time.monotonic()
            recent_failures = [t for t in recent_failures
                               if now - t < BREAKER_WINDOW]
            if len(recent_failures) >= BREAKER_THRESHOLD:
                print(f"\n  [BREAKER] {len(recent_failures)} failures in "
                      f"{BREAKER_WINDOW:.0f}s. Pausing {BREAKER_PAUSE}s...")
                progress.save(project_root)
                time.sleep(BREAKER_PAUSE)
                recent_failures.clear()
                print("  [BREAKER] Resuming...")

            # Submit new tasks to fill vacant slots; pulls retry_queue first.
            while len(futures) < concurrency:
                next_chapter = _next_chapter()
                if next_chapter is None:
                    break
                _gate()
                future = executor.submit(
                    _process_chapter,
                    project_root, work_id, next_chapter,
                    backend, progress, known_aliases,
                )
                futures[future] = next_chapter

    # Final save
    progress.save(project_root)

    elapsed = time.monotonic() - start_time
    print(f"\n  Completed: {completed}/{total}  "
          f"Failed: {failed}  "
          f"Retried: {retried}  "
          f"Elapsed: {_fmt_duration(elapsed)}")
    if completed > 0:
        print(f"  Avg: {_fmt_duration(elapsed / completed)}/chapter")


def _count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
