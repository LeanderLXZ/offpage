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

from .config import get_config
from .process_guard import fmt_memory, get_rss_mb
from .rate_limit import classify_error, get_active as get_active_rl

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
    # Diagnostic fields populated on failure (and when parseable on success).
    # raw_stdout is capped at 20KB; full stdout goes to the per-lane log file
    # written by the orchestrator.
    raw_stdout: str = ""
    raw_stderr: str = ""
    subtype: str | None = None
    num_turns: int | None = None
    total_cost_usd: float | None = None


_RAW_STDOUT_CAP = 20_000
_RAW_STDERR_CAP = 20_000


def _parse_claude_json(stdout: str) -> dict[str, Any]:
    """Extract diagnostic fields from claude --output-format json stdout.

    Returns an empty dict if stdout is not valid JSON or not a dict. Claude
    CLI emits structured JSON even on some non-zero exits (e.g. touching
    --max-turns), so this best-effort parse extracts subtype / num_turns /
    total_cost_usd whenever available.
    """
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _build_diagnostic_error(returncode: int, stderr: str,
                            parsed: dict[str, Any]) -> str:
    """Prepend parsed subtype/num_turns to the error message for visibility."""
    prefix_parts: list[str] = [f"exit {returncode}"]
    if parsed:
        tags: list[str] = []
        if parsed.get("subtype"):
            tags.append(f"subtype={parsed['subtype']}")
        if parsed.get("num_turns") is not None:
            tags.append(f"num_turns={parsed['num_turns']}")
        if tags:
            prefix_parts.append(f"[{' '.join(tags)}]")
    return f"{' '.join(prefix_parts)}: {stderr}"


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
            timeout_seconds: int = 600,
            lane_name: str | None = None) -> LLMResult:
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
            timeout_seconds: int = 600,
            lane_name: str | None = None) -> LLMResult:
        tools = allowed_tools or CLAUDE_DEFAULT_TOOLS
        lane_tag = f"[{lane_name}]" if lane_name else "[lane]"

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

        logger.info("Running claude -p  (max_turns=%d, timeout=%ds, lane=%s)",
                     self.max_turns, timeout_seconds, lane_name or "?")
        logger.debug("Prompt length: %d chars", len(prompt))

        start = time.monotonic()
        proc = subprocess.Popen(
            cmd, cwd=self.project_root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

        print(f"    PID {proc.pid} started {lane_tag}")

        # Heartbeat thread — prints elapsed + memory every 30s
        stop_event = threading.Event()
        orch_pid = os.getpid()

        def heartbeat() -> None:
            while not stop_event.wait(get_config().runtime.heartbeat_interval_s):
                elapsed = time.monotonic() - start
                child_mem = fmt_memory(get_rss_mb(proc.pid))
                orch_mem = fmt_memory(get_rss_mb(orch_pid))
                print(f"    ... running [{_fmt_elapsed(elapsed)}]"
                      f"  PID {proc.pid} {lane_tag}"
                      f"  Mem: claude={child_mem} orch={orch_mem}")

        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()

        stdout = ""
        stderr = ""
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                stdout, stderr = proc.communicate()
            except Exception:  # noqa: BLE001
                stdout, stderr = stdout or "", stderr or ""
            timed_out = True
        finally:
            stop_event.set()
            hb.join(timeout=2)

        duration = time.monotonic() - start
        print(f"    PID {proc.pid} finished {lane_tag} "
              f"[{_fmt_elapsed(duration)}]")

        parsed = _parse_claude_json(stdout)
        raw_stdout_capped = (stdout or "")[:_RAW_STDOUT_CAP]
        raw_stderr_capped = (stderr or "")[:_RAW_STDERR_CAP]

        if timed_out:
            return LLMResult(
                success=False, text="",
                error="claude -p timed out",
                pid=proc.pid, duration_seconds=duration,
                raw_stdout=raw_stdout_capped,
                raw_stderr=raw_stderr_capped,
                subtype=parsed.get("subtype"),
                num_turns=parsed.get("num_turns"),
                total_cost_usd=parsed.get("total_cost_usd"))

        if proc.returncode != 0:
            stderr_s = (stderr or "").strip()
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
                    pid=proc.pid, duration_seconds=duration,
                    raw_stdout=raw_stdout_capped,
                    raw_stderr=raw_stderr_capped,
                    subtype=parsed.get("subtype"),
                    num_turns=parsed.get("num_turns"),
                    total_cost_usd=parsed.get("total_cost_usd"))
            # Detect rate-limit (retryable)
            rate_limit_signals = ["rate limit", "rate_limit", "too many requests"]
            if any(sig in lower for sig in rate_limit_signals):
                return LLMResult(
                    success=False, text="",
                    error=f"rate_limit: {stderr_s}",
                    pid=proc.pid, duration_seconds=duration,
                    raw_stdout=raw_stdout_capped,
                    raw_stderr=raw_stderr_capped,
                    subtype=parsed.get("subtype"),
                    num_turns=parsed.get("num_turns"),
                    total_cost_usd=parsed.get("total_cost_usd"))
            return LLMResult(
                success=False, text="",
                error=_build_diagnostic_error(proc.returncode, stderr_s,
                                              parsed),
                pid=proc.pid, duration_seconds=duration,
                raw_stdout=raw_stdout_capped,
                raw_stderr=raw_stderr_capped,
                subtype=parsed.get("subtype"),
                num_turns=parsed.get("num_turns"),
                total_cost_usd=parsed.get("total_cost_usd"))

        if not parsed:
            # Fallback: treat raw stdout as text
            return LLMResult(success=True, text=(stdout or "").strip(),
                             pid=proc.pid, duration_seconds=duration,
                             raw_stdout=raw_stdout_capped)

        result_text = parsed.get("result", (stdout or "").strip())
        session_id = parsed.get("session_id")
        return LLMResult(success=True, text=result_text, raw=parsed,
                         session_id=session_id,
                         pid=proc.pid, duration_seconds=duration,
                         raw_stdout=raw_stdout_capped,
                         subtype=parsed.get("subtype"),
                         num_turns=parsed.get("num_turns"),
                         total_cost_usd=parsed.get("total_cost_usd"))


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
            timeout_seconds: int = 600,
            lane_name: str | None = None) -> LLMResult:
        cmd: list[str] = ["codex", "--quiet", "--full-auto", prompt]
        if self.model:
            cmd.extend(["--model", self.model])
        lane_tag = f"[{lane_name}]" if lane_name else "[lane]"

        logger.info("Running codex --full-auto  (timeout=%ds, lane=%s)",
                    timeout_seconds, lane_name or "?")

        start = time.monotonic()
        proc = subprocess.Popen(
            cmd, cwd=self.project_root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

        print(f"    PID {proc.pid} started {lane_tag}")

        stop_event = threading.Event()
        orch_pid = os.getpid()

        def heartbeat() -> None:
            while not stop_event.wait(get_config().runtime.heartbeat_interval_s):
                elapsed = time.monotonic() - start
                child_mem = fmt_memory(get_rss_mb(proc.pid))
                orch_mem = fmt_memory(get_rss_mb(orch_pid))
                print(f"    ... running [{_fmt_elapsed(elapsed)}]"
                      f"  PID {proc.pid} {lane_tag}"
                      f"  Mem: codex={child_mem} orch={orch_mem}")

        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()

        stdout = ""
        stderr = ""
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                stdout, stderr = proc.communicate()
            except Exception:  # noqa: BLE001
                stdout, stderr = stdout or "", stderr or ""
            timed_out = True
        finally:
            stop_event.set()
            hb.join(timeout=2)

        duration = time.monotonic() - start
        print(f"    PID {proc.pid} finished {lane_tag} "
              f"[{_fmt_elapsed(duration)}]")

        raw_stdout_capped = (stdout or "")[:_RAW_STDOUT_CAP]
        raw_stderr_capped = (stderr or "")[:_RAW_STDERR_CAP]

        if timed_out:
            return LLMResult(success=False, text="",
                             error="codex timed out",
                             pid=proc.pid, duration_seconds=duration,
                             raw_stdout=raw_stdout_capped,
                             raw_stderr=raw_stderr_capped)

        if proc.returncode != 0:
            return LLMResult(
                success=False, text="",
                error=f"exit {proc.returncode}: {(stderr or '').strip()}",
                pid=proc.pid, duration_seconds=duration,
                raw_stdout=raw_stdout_capped,
                raw_stderr=raw_stderr_capped)

        return LLMResult(success=True, text=(stdout or "").strip(),
                         pid=proc.pid, duration_seconds=duration,
                         raw_stdout=raw_stdout_capped)


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
    backoff_cfg = get_config().backoff
    threshold = float(backoff_cfg.fast_empty_failure_threshold_s)
    if result.duration_seconds is not None and result.duration_seconds < threshold:
        err = (result.error or "").strip()
        # "exit 1: " or "exit 1:" with empty stderr
        if err.startswith("exit") and err.rstrip(": ").replace("exit", "").strip().isdigit():
            return True
    return False


def _probe_fn_for(backend: LLMBackend) -> Any:
    """Build a minimal-cost probe callable for rate_limit fallback.

    Sends ``"1"`` with ``--max-turns 1`` and a 60s timeout. Returns ``True``
    iff the call succeeded *or* failed for a reason other than rate-limit.
    Used by ``RateLimitController.wait_if_paused`` when the reset time
    cannot be parsed from stderr.
    """
    def _probe() -> bool:
        try:
            r = backend.run(
                "1", allowed_tools=[], timeout_seconds=60,
                lane_name="rl_probe",
            )
        except Exception:  # noqa: BLE001
            logger.exception("rate_limit probe raised")
            return False
        if r.success:
            return True
        err = (r.error or "").lower()
        if "rate_limit" in err or classify_error(r.raw_stderr or "") != "unknown":
            return False
        # Any other error means the limit is no longer the gate.
        return True
    return _probe


def run_with_retry(backend: LLMBackend, prompt: str, *,
                   allowed_tools: list[str] | None = None,
                   max_retries: int = 3,
                   cooldown_seconds: int = 60,
                   timeout_seconds: int = 600,
                   lane_name: str | None = None,
                   on_failure: Any = None) -> LLMResult:
    """Run prompt with automatic retry on fast-fail errors.

    Rate-limit handling is **out-of-band**: when ``rate_limit`` is detected,
    we record a global pause via ``RateLimitController`` (if installed) and
    block here until the reset passes, then re-run the same prompt without
    consuming a retry slot. This keeps quality equivalent to a no-limit run.

    ``on_failure`` is called once per failed attempt with the LLMResult, so
    callers can persist per-lane diagnostic logs for every attempt (including
    intermediate retries) rather than only the final one.
    """
    backoff_cfg = get_config().backoff
    fast_backoff = backoff_cfg.fast_empty_failure_backoff_s

    attempt = 0
    while True:
        attempt += 1
        result = backend.run(prompt, allowed_tools=allowed_tools,
                             timeout_seconds=timeout_seconds,
                             lane_name=lane_name)
        if not result.success and on_failure is not None:
            try:
                on_failure(result, attempt)
            except Exception:  # noqa: BLE001
                logger.exception("on_failure callback raised")
        if result.success:
            return result
        # Token/context limit — same prompt will fail again, don't retry
        if result.error and "token_limit" in result.error:
            logger.error("Token limit exceeded (not retryable): %s",
                         result.error)
            return result
        # Rate limit — pause globally, wait for reset, then re-run without
        # consuming a retry slot (§11.13).
        if result.error and "rate_limit" in result.error:
            controller = get_active_rl()
            if controller is not None:
                controller.record_pause(
                    result.raw_stderr or result.error or "",
                    lane_name=lane_name,
                )
                controller.wait_if_paused(probe_fn=_probe_fn_for(backend))
                attempt -= 1   # pause does not consume a retry slot
                continue
            # No controller installed (e.g. ad-hoc test) → fall back to the
            # legacy linear backoff so behaviour stays defined.
            if attempt < max_retries:
                wait = cooldown_seconds * attempt
                logger.warning("Rate limited (no controller; attempt %d/%d). "
                               "Waiting %ds before retry...",
                               attempt, max_retries, wait)
                time.sleep(wait)
                continue
            return result
        # Fast empty failure (CLI launch error) — retryable with backoff
        if _is_fast_empty_failure(result):
            if attempt <= len(fast_backoff):
                wait = int(fast_backoff[attempt - 1])
                logger.warning("Fast empty failure (attempt %d/%d, %.1fs). "
                               "Waiting %ds before retry...",
                               attempt, len(fast_backoff),
                               result.duration_seconds or 0, wait)
                time.sleep(wait)
                continue
        # Non-retryable error
        return result
