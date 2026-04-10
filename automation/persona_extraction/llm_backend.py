"""LLM backend abstraction — Claude CLI and Codex CLI."""

from __future__ import annotations

import glob as _glob
import json
import logging
import os
import shutil
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .process_guard import fmt_memory, get_rss_mb

logger = logging.getLogger(__name__)


def _fmt_elapsed(seconds: float) -> str:
    """Format seconds as compact human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s"


def _find_claude_binary() -> str:
    """Locate the claude CLI binary.

    Search order:
      1. CLAUDE_PATH environment variable
      2. System PATH (``shutil.which``)
      3. VS Code / Cursor extension directories (common install locations)
    """
    env_path = os.environ.get("CLAUDE_PATH")
    if env_path and Path(env_path).is_file():
        return env_path

    which_path = shutil.which("claude")
    if which_path:
        return which_path

    # Search in VS Code and Cursor extension dirs
    home = Path.home()
    patterns = [
        str(home / ".vscode" / "extensions" / "anthropic.claude-code-*" /
            "resources" / "native-binary" / "claude"),
        str(home / ".cursor-server" / "extensions" / "anthropic.claude-code-*" /
            "resources" / "native-binary" / "claude"),
        str(home / ".vscode-server" / "extensions" / "anthropic.claude-code-*" /
            "resources" / "native-binary" / "claude"),
    ]
    for pattern in patterns:
        matches = sorted(_glob.glob(pattern), reverse=True)  # newest first
        for m in matches:
            if os.path.isfile(m) and os.access(m, os.X_OK):
                logger.info("Auto-discovered claude binary: %s", m)
                return m

    raise FileNotFoundError(
        "claude CLI binary not found. Install Claude Code, add it to PATH, "
        "or set CLAUDE_PATH environment variable."
    )

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class LLMResult:
    """Unified result from any LLM backend."""
    success: bool
    text: str
    raw: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    error: str | None = None
    pid: int | None = None
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class LLMBackend(ABC):
    """Abstract interface for invoking an LLM agent."""

    def __init__(self, project_root: Path, max_turns: int = 50):
        self.project_root = project_root
        self.max_turns = max_turns

    @abstractmethod
    def run(self, prompt: str, *, allowed_tools: list[str] | None = None,
            timeout_seconds: int = 600) -> LLMResult:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


# ---------------------------------------------------------------------------
# Claude CLI backend (subscription)
# ---------------------------------------------------------------------------

CLAUDE_DEFAULT_TOOLS = [
    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
]


class ClaudeBackend(LLMBackend):
    """Invoke `claude -p` using an existing Claude Code subscription."""

    def __init__(self, project_root: Path, max_turns: int = 50,
                 model: str | None = None, effort: str | None = None):
        super().__init__(project_root, max_turns)
        self.model = model  # e.g. "opus", "sonnet"
        self.effort = effort  # e.g. "low", "medium", "high", "max"
        self._claude_bin = _find_claude_binary()

    def name(self) -> str:
        return "claude"

    def run(self, prompt: str, *, allowed_tools: list[str] | None = None,
            timeout_seconds: int = 600) -> LLMResult:
        tools = allowed_tools or CLAUDE_DEFAULT_TOOLS

        cmd: list[str] = [
            self._claude_bin, "-p", prompt,
            "--output-format", "json",
            "--max-turns", str(self.max_turns),
            "--dangerously-skip-permissions",
            "--allowedTools", ",".join(tools),
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        if self.effort:
            cmd.extend(["--effort", self.effort])

        logger.info("Running claude -p  (max_turns=%d, timeout=%ds)",
                     self.max_turns, timeout_seconds)
        logger.debug("Prompt length: %d chars", len(prompt))

        start = time.monotonic()
        proc = subprocess.Popen(
            cmd, cwd=self.project_root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

        print(f"    PID {proc.pid} started")

        # Heartbeat thread — prints elapsed + memory every 30s
        stop_event = threading.Event()
        orch_pid = os.getpid()

        def heartbeat() -> None:
            while not stop_event.wait(30):
                elapsed = time.monotonic() - start
                child_mem = fmt_memory(get_rss_mb(proc.pid))
                orch_mem = fmt_memory(get_rss_mb(orch_pid))
                print(f"    ... running [{_fmt_elapsed(elapsed)}]"
                      f"  PID {proc.pid}"
                      f"  Mem: claude={child_mem} orch={orch_mem}")

        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()

        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            duration = time.monotonic() - start
            return LLMResult(success=False, text="",
                             error="claude -p timed out",
                             pid=proc.pid, duration_seconds=duration)
        finally:
            stop_event.set()
            hb.join(timeout=2)

        duration = time.monotonic() - start
        child_mem = fmt_memory(get_rss_mb(proc.pid))
        print(f"    PID {proc.pid} finished [{_fmt_elapsed(duration)}]")

        if proc.returncode != 0:
            stderr_s = stderr.strip()
            lower = stderr_s.lower()
            # Detect token/context limit (not retryable — same prompt
            # will hit the same limit)
            token_limit_signals = [
                "context window", "context_length", "max_tokens",
                "token limit", "too many tokens", "prompt is too long",
                "maximum context length",
            ]
            if any(sig in lower for sig in token_limit_signals):
                return LLMResult(
                    success=False, text="",
                    error=f"token_limit: {stderr_s}",
                    pid=proc.pid, duration_seconds=duration)
            # Detect rate-limit (retryable)
            rate_limit_signals = ["rate limit", "rate_limit", "too many requests"]
            if any(sig in lower for sig in rate_limit_signals):
                return LLMResult(success=False, text="",
                                 error=f"rate_limit: {stderr_s}",
                                 pid=proc.pid, duration_seconds=duration)
            return LLMResult(success=False, text="",
                             error=f"exit {proc.returncode}: {stderr_s}",
                             pid=proc.pid, duration_seconds=duration)

        # Parse JSON output
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            # Fallback: treat raw stdout as text
            return LLMResult(success=True, text=stdout.strip(),
                             pid=proc.pid, duration_seconds=duration)

        result_text = data.get("result", stdout.strip())
        session_id = data.get("session_id")
        return LLMResult(success=True, text=result_text, raw=data,
                         session_id=session_id,
                         pid=proc.pid, duration_seconds=duration)


# ---------------------------------------------------------------------------
# Codex CLI backend (subscription)
# ---------------------------------------------------------------------------

class CodexBackend(LLMBackend):
    """Invoke OpenAI Codex CLI using an existing subscription."""

    def __init__(self, project_root: Path, max_turns: int = 50,
                 model: str | None = None):
        super().__init__(project_root, max_turns)
        self.model = model

    def name(self) -> str:
        return "codex"

    def run(self, prompt: str, *, allowed_tools: list[str] | None = None,
            timeout_seconds: int = 600) -> LLMResult:
        cmd: list[str] = ["codex", "--quiet", "--full-auto", prompt]
        if self.model:
            cmd.extend(["--model", self.model])

        logger.info("Running codex --full-auto  (timeout=%ds)", timeout_seconds)

        start = time.monotonic()
        proc = subprocess.Popen(
            cmd, cwd=self.project_root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

        print(f"    PID {proc.pid} started")

        stop_event = threading.Event()
        orch_pid = os.getpid()

        def heartbeat() -> None:
            while not stop_event.wait(30):
                elapsed = time.monotonic() - start
                child_mem = fmt_memory(get_rss_mb(proc.pid))
                orch_mem = fmt_memory(get_rss_mb(orch_pid))
                print(f"    ... running [{_fmt_elapsed(elapsed)}]"
                      f"  PID {proc.pid}"
                      f"  Mem: codex={child_mem} orch={orch_mem}")

        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()

        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            duration = time.monotonic() - start
            return LLMResult(success=False, text="",
                             error="codex timed out",
                             pid=proc.pid, duration_seconds=duration)
        finally:
            stop_event.set()
            hb.join(timeout=2)

        duration = time.monotonic() - start
        print(f"    PID {proc.pid} finished [{_fmt_elapsed(duration)}]")

        if proc.returncode != 0:
            return LLMResult(success=False, text="",
                             error=f"exit {proc.returncode}: {stderr.strip()}",
                             pid=proc.pid, duration_seconds=duration)

        return LLMResult(success=True, text=stdout.strip(),
                         pid=proc.pid, duration_seconds=duration)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_backend(name: str, project_root: Path, *,
                   max_turns: int = 50,
                   model: str | None = None,
                   effort: str | None = None) -> LLMBackend:
    """Create a backend by name ('claude' or 'codex')."""
    if name == "claude":
        return ClaudeBackend(project_root, max_turns, model, effort=effort)
    if name == "codex":
        return CodexBackend(project_root, max_turns, model)
    raise ValueError(f"Unknown backend: {name!r}  (choices: claude, codex)")


# ---------------------------------------------------------------------------
# Rate-limit aware wrapper
# ---------------------------------------------------------------------------

def _is_fast_empty_failure(result: LLMResult) -> bool:
    """Detect CLI launch failures: fast return + empty/generic error."""
    if result.success:
        return False
    if result.duration_seconds is not None and result.duration_seconds < 5:
        err = (result.error or "").strip()
        # "exit 1: " or "exit 1:" with empty stderr
        if err.startswith("exit") and err.rstrip(": ").replace("exit", "").strip().isdigit():
            return True
    return False


def run_with_retry(backend: LLMBackend, prompt: str, *,
                   allowed_tools: list[str] | None = None,
                   max_retries: int = 3,
                   cooldown_seconds: int = 60,
                   timeout_seconds: int = 600) -> LLMResult:
    """Run prompt with automatic retry on rate-limit and fast-fail errors."""
    for attempt in range(1, max_retries + 1):
        result = backend.run(prompt, allowed_tools=allowed_tools,
                             timeout_seconds=timeout_seconds)
        if result.success:
            return result
        # Token/context limit — same prompt will fail again, don't retry
        if result.error and "token_limit" in result.error:
            logger.error("Token limit exceeded (not retryable): %s",
                         result.error)
            return result
        # Rate limit — retryable with backoff
        if result.error and "rate_limit" in result.error:
            if attempt < max_retries:
                wait = cooldown_seconds * attempt
                logger.warning("Rate limited (attempt %d/%d). "
                               "Waiting %ds before retry...",
                               attempt, max_retries, wait)
                time.sleep(wait)
                continue
        # Fast empty failure (CLI launch error) — retryable with backoff
        if _is_fast_empty_failure(result):
            if attempt < max_retries:
                wait = 30 * (2 ** (attempt - 1))  # 30s, 60s, 120s
                logger.warning("Fast empty failure (attempt %d/%d, %.1fs). "
                               "Waiting %ds before retry...",
                               attempt, max_retries,
                               result.duration_seconds or 0, wait)
                time.sleep(wait)
                continue
        # Non-retryable error
        return result
    return result  # type: ignore[possibly-undefined]
