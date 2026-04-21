"""Git safety utilities — preflight checks, commit, rollback."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


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
    """Run preflight checks before a stage. Returns list of problems.

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


def checkout_master(project_root: Path) -> bool:
    """Return working tree to ``master``. Idempotent and non-destructive.

    Returns ``True`` when the tree is on ``master`` after the call (either
    already there or switched successfully). Returns ``False`` when the
    switch is skipped (dirty tree) or the underlying ``git checkout``
    fails. Callers treat this as best-effort cleanup and should not raise
    on failure.

    A dirty working tree is refused: untracked / modified files could
    leak onto ``master`` when switching from an extraction branch (e.g.
    SIGINT mid-stage leaves ``works/.../阶段XX_*.json`` untracked). When
    dirty, we log + stay on the current branch so the user can inspect
    and clean up manually before re-trying.
    """
    gs = git_status(project_root)
    if gs.branch == "master":
        return True
    if not gs.clean:
        logger.warning(
            "Working tree dirty on '%s' — staying put instead of "
            "switching to master. Inspect and clean up manually, then "
            "run 'git checkout master'.", gs.branch)
        return False
    result = _git(["checkout", "master"], project_root)
    if result.returncode != 0:
        logger.error("Failed to checkout master: %s", result.stderr)
        return False
    logger.info("Returned to master branch")
    return True


def commit_stage(project_root: Path, stage_id: str,
                 *, message: str | None = None,
                 files: list[str] | None = None) -> str | None:
    """Commit current changes for a stage. Returns commit SHA or None.

    ``stage_id`` is the human-readable stage identifier (e.g.
    ``阶段XX_<slug>`` or ``baseline`` for pre-Phase-3 commits). When
    ``message`` is omitted, a default template is used for extraction
    commits.
    """
    if files:
        for f in files:
            _git(["add", f], project_root)
    else:
        _git(["add", "-A", "works/"], project_root)

    status = _git(["status", "--porcelain"], project_root)
    if not status.stdout.strip():
        logger.warning("Nothing to commit for stage %s", stage_id)
        return None

    if message is None:
        message = (f"{stage_id}: 分层提取完成\n\n"
                   f"Automated extraction via persona-extraction orchestrator.")

    result = _git(["commit", "-m", message], project_root)
    if result.returncode != 0:
        logger.error("Commit failed: %s", result.stderr)
        return None

    sha_proc = _git(["rev-parse", "--short", "HEAD"], project_root)
    sha = sha_proc.stdout.strip()
    logger.info("Committed %s as %s", stage_id, sha)
    return sha


def reset_paths(project_root: Path, paths: list[Path]) -> bool:
    """Restore the given paths to their HEAD state.

    For each path:

    - If tracked at HEAD: ``git checkout HEAD -- <path>`` restores the
      HEAD contents, undoing any partial uncommitted edits.
    - If path is not tracked at HEAD (untracked or never committed):
      remove the file from the working tree, if it exists. This keeps
      "reset to the state before the current stage touched this file"
      semantics consistent regardless of whether the file predates HEAD.

    Used by the Phase 3 partial-resume flow to surgically reset
    char_support baseline files before re-running an incomplete lane.

    Returns True on success, False if any git operation failed.
    """
    ok = True
    for p in paths:
        rel = p.relative_to(project_root) if p.is_absolute() else p
        rel_str = str(rel)
        # Check whether the path is tracked at HEAD. `cat-file -e` exits 0
        # iff the object exists; this does not read the blob's contents.
        probe = _git(["cat-file", "-e", f"HEAD:{rel_str}"], project_root)
        if probe.returncode == 0:
            co = _git(["checkout", "HEAD", "--", rel_str], project_root)
            if co.returncode != 0:
                logger.error("reset_paths checkout failed for %s: %s",
                             rel_str, co.stderr)
                ok = False
        else:
            # Not in HEAD — best we can do is remove any working-tree copy.
            abs_path = (project_root / rel_str).resolve()
            try:
                if abs_path.exists():
                    abs_path.unlink()
            except OSError as exc:
                logger.error("reset_paths unlink failed for %s: %s",
                             rel_str, exc)
                ok = False
    return ok


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
