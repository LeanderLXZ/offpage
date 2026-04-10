"""Git safety utilities — preflight checks, commit, rollback."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


ROLLBACK_CLEAN_EXCLUDES = [
    "__pycache__",
    "*.pyc",
    # Preserve Phase 4 scene archive progress and split artifacts even when
    # Phase 3 performs a repo-wide rollback.
    "works/*/analysis/incremental/.scene_archive.lock",
    "works/*/analysis/incremental/scene_archive/",
]


@dataclass
class GitStatus:
    clean: bool
    branch: str
    head_sha: str
    in_rebase: bool
    in_merge: bool
    error: str = ""


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args, cwd=cwd,
        capture_output=True, text=True, timeout=30,
    )


def git_status(project_root: Path) -> GitStatus:
    """Gather current git state."""
    try:
        # Check for clean working tree
        status_proc = _git(["status", "--porcelain"], project_root)
        clean = status_proc.stdout.strip() == ""

        # Current branch
        branch_proc = _git(["branch", "--show-current"], project_root)
        branch = branch_proc.stdout.strip()

        # HEAD sha
        head_proc = _git(["rev-parse", "--short", "HEAD"], project_root)
        head_sha = head_proc.stdout.strip()

        # In rebase or merge?
        git_dir = project_root / ".git"
        in_rebase = (git_dir / "rebase-merge").exists() or \
                    (git_dir / "rebase-apply").exists()
        in_merge = (git_dir / "MERGE_HEAD").exists()

        return GitStatus(clean=clean, branch=branch, head_sha=head_sha,
                         in_rebase=in_rebase, in_merge=in_merge)
    except Exception as e:
        return GitStatus(clean=False, branch="", head_sha="",
                         in_rebase=False, in_merge=False, error=str(e))


def preflight_check(project_root: Path,
                    expected_branch: str | None = None,
                    ignore_patterns: list[str] | None = None) -> list[str]:
    """Run preflight checks before a batch. Returns list of problems.

    ``ignore_patterns`` — file path substrings to tolerate in dirty status
    (e.g. ``["extraction_progress.json", "__pycache__"]``).
    """
    problems: list[str] = []
    gs = git_status(project_root)

    if gs.error:
        problems.append(f"Git error: {gs.error}")
        return problems

    if not gs.clean:
        # Check if all dirty files match ignore patterns
        ignore = ignore_patterns or []
        status_proc = _git(["status", "--porcelain"], project_root)
        dirty_lines = [l for l in status_proc.stdout.strip().splitlines()
                       if l.strip()]
        significant = []
        for line in dirty_lines:
            # porcelain format: XY filename  (filename starts at col 3)
            fname = line[3:].strip().strip('"')
            if not any(pat in fname for pat in ignore):
                significant.append(fname)
        if significant:
            problems.append("Working tree has uncommitted changes. "
                            "Commit or stash before extraction.")

    if gs.in_rebase:
        problems.append("A rebase is in progress. Resolve it first.")

    if gs.in_merge:
        problems.append("A merge is in progress. Resolve it first.")

    if expected_branch and gs.branch != expected_branch:
        problems.append(f"Expected branch '{expected_branch}', "
                        f"but on '{gs.branch}'.")

    return problems


def create_extraction_branch(project_root: Path,
                             branch_name: str) -> bool:
    """Create and checkout extraction branch if not already on it."""
    gs = git_status(project_root)
    if gs.branch == branch_name:
        logger.info("Already on branch %s", branch_name)
        return True

    # Check if branch exists
    check = _git(["branch", "--list", branch_name], project_root)
    if check.stdout.strip():
        # Branch exists, checkout
        result = _git(["checkout", branch_name], project_root)
    else:
        # Create new branch
        result = _git(["checkout", "-b", branch_name], project_root)

    if result.returncode != 0:
        logger.error("Failed to checkout branch %s: %s",
                     branch_name, result.stderr)
        return False

    logger.info("On extraction branch: %s", branch_name)
    return True


def commit_batch(project_root: Path, batch_id: str, stage_id: str,
                 files: list[str] | None = None) -> str | None:
    """Commit current changes for a batch. Returns commit SHA or None."""
    if files:
        for f in files:
            _git(["add", f], project_root)
    else:
        # Stage all changes under works/ and analysis/
        _git(["add", "works/"], project_root)

    # Also stage progress file
    _git(["add", "-A", "works/"], project_root)

    # Check if there's anything to commit
    status = _git(["status", "--porcelain"], project_root)
    if not status.stdout.strip():
        logger.warning("Nothing to commit for batch %s", batch_id)
        return None

    message = (f"{batch_id}: 分层提取完成 ({stage_id})\n\n"
               f"Automated extraction via persona-extraction orchestrator.")

    result = _git(["commit", "-m", message], project_root)
    if result.returncode != 0:
        logger.error("Commit failed: %s", result.stderr)
        return None

    sha_proc = _git(["rev-parse", "--short", "HEAD"], project_root)
    sha = sha_proc.stdout.strip()
    logger.info("Committed %s as %s", batch_id, sha)
    return sha


def rollback_to_head(project_root: Path) -> bool:
    """Discard all uncommitted changes (hard reset to HEAD).

    Restores tracked files and removes untracked files across the whole
    repo (not just works/). Excludes caches plus Phase 4 scene archive
    lock/progress artefacts so independent scene splitting state survives
    a Phase 3 rollback.
    """
    result = _git(["checkout", "--", "."], project_root)
    clean_args = ["clean", "-fd"]
    for pattern in ROLLBACK_CLEAN_EXCLUDES:
        clean_args.append(f"--exclude={pattern}")
    clean = _git(clean_args, project_root)
    success = result.returncode == 0 and clean.returncode == 0
    if success:
        logger.info("Rolled back to HEAD (full-repo clean, scene_archive preserved)")
    else:
        logger.error("Rollback failed: checkout=%s clean=%s",
                     result.stderr, clean.stderr)
    return success


def rollback_last_commit(project_root: Path) -> bool:
    """Undo the last commit (keep files as uncommitted changes, then discard)."""
    result = _git(["reset", "--hard", "HEAD~1"], project_root)
    success = result.returncode == 0
    if success:
        logger.info("Rolled back last commit")
    else:
        logger.error("Rollback of last commit failed: %s", result.stderr)
    return success


def squash_merge_to(project_root: Path, target_branch: str,
                    source_branch: str, message: str) -> str | None:
    """Squash-merge *source_branch* into *target_branch*.

    Returns the new commit SHA on *target_branch*, or None on failure.
    The source branch is **not** deleted — caller decides.
    """
    # Switch to target branch
    result = _git(["checkout", target_branch], project_root)
    if result.returncode != 0:
        logger.error("Cannot checkout %s: %s", target_branch, result.stderr)
        return None

    # Squash merge
    result = _git(["merge", "--squash", source_branch], project_root)
    if result.returncode != 0:
        logger.error("Squash merge failed: %s", result.stderr)
        _git(["checkout", source_branch], project_root)
        return None

    # Commit
    result = _git(["commit", "-m", message], project_root)
    if result.returncode != 0:
        logger.error("Squash commit failed: %s", result.stderr)
        _git(["reset", "--hard", "HEAD"], project_root)
        _git(["checkout", source_branch], project_root)
        return None

    sha_proc = _git(["rev-parse", "--short", "HEAD"], project_root)
    sha = sha_proc.stdout.strip()
    logger.info("Squash-merged %s into %s as %s", source_branch,
                target_branch, sha)
    return sha
