"""LLM backend abstraction — Claude CLI and Codex CLI."""

from __future__ import annotations

import collections
import glob as _glob
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .config import get_config
from .process_guard import fmt_memory, get_rss_mb
from .rate_limit import classify_error, get_active as get_active_rl
from .run_metrics import record as _record_run_metrics

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


# Keywords that indicate the underlying request hit a rate-limit / quota
# surface (case-insensitive). Matches the contract in
# docs/requirements.md §11.13.4 — keep this list in sync with that table.
_RATE_LIMIT_SIGNALS = (
    "rate limit",
    "rate_limit",
    "too many requests",
    "429",
)


def _classify_rate_limit(text: str) -> bool:
    """Return True iff *text* looks like a rate-limit / quota error."""
    if not text:
        return False
    lower = text.lower()
    return any(sig in lower for sig in _RATE_LIMIT_SIGNALS)


_HB_RING_MAXLEN = 20

# How long to wait for the pipes to drain after killing a timed-out child.
# Bounded on purpose: the kill below should make EOF immediate, so this only
# ever fires if something escaped the process group. Never wait forever here —
# an unattended run would deadlock the lane thread until someone notices.
_REAP_TIMEOUT_S = 30


# Live LLM children, so a signal handler can take them down before the
# orchestrator lets go of its PID lock. Without this the handler releases the
# lock and calls sys.exit, but the lane threads are non-daemon and still blocked
# in communicate() — the interpreter waits for them, the children (now immune to
# the terminal's SIGINT) run to their full timeout, and for that whole window the
# lock file says "nobody is running" while lanes are still writing. See #63.
_live_children: set[subprocess.Popen] = set()
_live_children_lock = threading.Lock()


def _register_child(proc: subprocess.Popen) -> None:
    with _live_children_lock:
        _live_children.add(proc)


def _unregister_child(proc: subprocess.Popen) -> None:
    with _live_children_lock:
        _live_children.discard(proc)


def terminate_all_children() -> int:
    """Kill every in-flight LLM child tree. Returns how many were signalled.

    Called from the orchestrator's SIGINT / SIGTERM handler BEFORE it releases
    the PID lock, so the blocked lane threads unblock promptly and the shutdown
    window stays short instead of stretching to the child timeout (up to
    ``[phase3].extraction_timeout_s``).
    """
    with _live_children_lock:
        procs = list(_live_children)
    for proc in procs:
        try:
            _terminate_process_tree(proc)
        except Exception as exc:  # noqa: BLE001 — best effort during shutdown
            logger.warning("failed to terminate child %s: %s", proc.pid, exc)
    if procs:
        logger.warning("Terminated %d in-flight LLM child process tree(s).",
                       len(procs))
    return len(procs)


def _terminate_process_tree(proc: subprocess.Popen) -> None:
    """SIGKILL a timed-out child *and everything it spawned*.

    The CLI backends spawn grandchildren (their own Bash tool) which inherit our
    stdout/stderr pipes. Killing only the direct child leaves those grandchildren
    holding the write end, so a subsequent ``communicate()`` waits for an EOF that
    never arrives and the lane thread deadlocks — and ``--max-runtime`` is not
    preemptive, so nothing breaks the deadlock. Since the child is started with
    ``start_new_session=True`` it leads its own process group, and one ``killpg``
    takes the whole tree down.

    That pairing is load-bearing: without ``start_new_session=True`` the child
    stays in the orchestrator's OWN process group, and ``killpg`` would SIGKILL
    the orchestrator along with it. The guard below refuses that case rather
    than trusting every future ``Popen`` site to remember the flag.
    """
    try:
        pgid = os.getpgid(proc.pid)
    except OSError as exc:  # already reaped — nothing to kill
        logger.warning("getpgid failed for PID %s (%s) — child already gone?",
                       proc.pid, exc)
        return
    if pgid != os.getpgid(0):
        try:
            os.killpg(pgid, signal.SIGKILL)
            return
        except OSError as exc:
            logger.warning("killpg failed for PID %s (%s) — killing child only",
                           proc.pid, exc)
    else:
        # Same group as us: the Popen that made this child forgot
        # start_new_session=True. Killing the group would take the whole
        # orchestrator down, so degrade to the (deadlock-prone) child-only kill
        # and make the misconfiguration loud.
        logger.error(
            "PID %s shares the orchestrator's process group (%s) — refusing "
            "killpg. Its Popen is missing start_new_session=True; grandchildren "
            "may survive and block the pipes.", proc.pid, pgid)
    try:
        proc.kill()
    except OSError:
        pass


def _heartbeat_visible() -> bool:
    """Heartbeats print to the terminal only when stderr is a tty.

    In ``--background`` mode stderr is redirected to ``extraction.log``
    (``process_guard.launch_background`` merges stderr into the log), so
    live heartbeats would pollute the log — mute them instead. In the
    failure path, the in-memory ring buffer is flushed via ``logger``
    so diagnostics aren't lost.
    """
    try:
        return sys.stderr.isatty()
    except (AttributeError, ValueError):
        return False


def _flush_heartbeats(ring: "collections.deque[str]", lane_tag: str) -> None:
    """Dump the last captured heartbeats to the log on failure."""
    if not ring:
        return
    logger.warning(
        "claude -p failed %s — last %d heartbeat(s):\n%s",
        lane_tag, len(ring), "\n".join(ring))


@contextmanager
def _prompt_tempfile(prompt: str, *, backend_tag: str,
                     lane_name: str | None = None) -> Iterator[Path]:
    """Write ``prompt`` to a unique tempfile and yield its path.

    Avoids Linux ARG_MAX (~128 KiB per argv entry, MAX_ARG_STRLEN) by
    routing long prompts via a file handle instead of the command line.
    ``tempfile.mkstemp`` generates a process- / thread-unique path
    atomically, so concurrent lanes never collide. The file is deleted
    in ``finally`` even on timeout / exception.
    """
    safe_lane = "".join(c if c.isalnum() or c in "_-" else "_"
                        for c in (lane_name or "nolane"))[:40]
    prefix = f"persona_{backend_tag}_{os.getpid()}_{safe_lane}_"
    fd, path_str = tempfile.mkstemp(prefix=prefix, suffix=".txt")
    path = Path(path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        yield path
    finally:
        try:
            path.unlink()
        except OSError:
            pass


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
            lane_name: str | None = None,
            effort: str | None = None) -> LLMResult:
        """Run one LLM call. ``effort`` is a per-call override of the
        backend instance's default effort (low/medium/high/max); ``None``
        falls back to the instance default. Used by Phase 0 recovery
        sweep to downgrade max → high without a separate backend
        instance. See decision #49."""
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
            lane_name: str | None = None,
            effort: str | None = None) -> LLMResult:
        tools = allowed_tools or CLAUDE_DEFAULT_TOOLS
        lane_tag = f"[{lane_name}]" if lane_name else "[lane]"

        # Per-call effort override (decision #49) takes precedence over
        # the backend instance default. ``None`` keeps instance default.
        active_effort = effort if effort is not None else self.effort

        # Prompt is fed via stdin from a unique tempfile to bypass Linux
        # ARG_MAX (~128 KiB per argv entry). T3 repair prompts carry full
        # chapter text and routinely exceed that limit.
        cmd: list[str] = [
            self._claude_bin, "-p",
            "--output-format", "json",
            "--max-turns", str(self.max_turns),
            "--dangerously-skip-permissions",
            "--allowedTools", ",".join(tools),
            "--append-system-prompt", "[extraction_worker_mode]",
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        if active_effort:
            cmd.extend(["--effort", active_effort])

        logger.info("Running claude -p  (max_turns=%d, timeout=%ds, lane=%s)",
                     self.max_turns, timeout_seconds, lane_name or "?")
        logger.debug("Prompt length: %d chars", len(prompt))

        start = time.monotonic()
        stdout = ""
        stderr = ""
        timed_out = False
        proc: subprocess.Popen[str] | None = None
        with _prompt_tempfile(prompt, backend_tag="claude",
                              lane_name=lane_name) as prompt_path:
            with open(prompt_path, "r", encoding="utf-8") as prompt_fh:
                proc = subprocess.Popen(
                    cmd, cwd=self.project_root,
                    stdin=prompt_fh,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    # Own process group so a timeout can kill the whole tree
                    # (see _terminate_process_tree). Side effect: the child no
                    # longer receives the terminal's Ctrl+C — the orchestrator's
                    # own KeyboardInterrupt handling is what stops a run.
                    start_new_session=True,
                )
            _register_child(proc)

            print(f"    PID {proc.pid} started {lane_tag}")

            # Heartbeat thread — ring-buffers the last N samples and, when
            # running in a terminal, also prints them live on stderr. In
            # ``--background`` mode stderr is merged into extraction.log,
            # so live prints are muted; the ring buffer still captures
            # samples and gets flushed on failure so the final log has
            # the tail of memory/elapsed data needed for diagnosis.
            stop_event = threading.Event()
            orch_pid = os.getpid()
            hb_ring: collections.deque[str] = collections.deque(
                maxlen=_HB_RING_MAXLEN)
            live_hb = _heartbeat_visible()

            def heartbeat() -> None:
                while not stop_event.wait(
                        get_config().runtime.heartbeat_interval_s):
                    elapsed = time.monotonic() - start
                    child_mem = fmt_memory(get_rss_mb(proc.pid))
                    orch_mem = fmt_memory(get_rss_mb(orch_pid))
                    line = (f"    ... running [{_fmt_elapsed(elapsed)}]"
                            f"  PID {proc.pid} {lane_tag}"
                            f"  Mem: claude={child_mem} orch={orch_mem}")
                    hb_ring.append(line)
                    if live_hb:
                        print(line, file=sys.stderr, flush=True)

            hb = threading.Thread(target=heartbeat, daemon=True)
            hb.start()

            try:
                stdout, stderr = proc.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _terminate_process_tree(proc)
                try:
                    stdout, stderr = proc.communicate(
                        timeout=_REAP_TIMEOUT_S)
                except Exception:  # noqa: BLE001
                    stdout, stderr = stdout or "", stderr or ""
                timed_out = True
            finally:
                _unregister_child(proc)
                stop_event.set()
                hb.join(timeout=2)

        duration = time.monotonic() - start
        print(f"    PID {proc.pid} finished {lane_tag} "
              f"[{_fmt_elapsed(duration)}]")

        if timed_out or proc.returncode != 0:
            _flush_heartbeats(hb_ring, lane_tag)

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
            # Detect rate-limit (retryable). Signals (incl. HTTP 429) are
            # centralised in `_classify_rate_limit` so requirements.md
            # §11.13.4 is the single source of truth across backends.
            if (_classify_rate_limit(stderr_s)
                    or _classify_rate_limit(raw_stdout_capped or "")):
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
            lane_name: str | None = None,
            effort: str | None = None) -> LLMResult:
        # ``effort`` kwarg accepted for interface parity with
        # ClaudeBackend.run (decision #49). codex CLI does not currently
        # expose an effort flag; the kwarg is silently ignored.
        # NOTE: codex CLI still receives the prompt via argv (not stdin).
        # Large prompts (> ~128 KiB) will fail with ARG_MAX; switch this to
        # the stdin+tempfile pattern used in ClaudeBackend once the codex
        # CLI's stdin interface is verified on the target machine.
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
            # Own process group — see the Claude backend above.
            start_new_session=True,
        )
        _register_child(proc)

        print(f"    PID {proc.pid} started {lane_tag}")

        stop_event = threading.Event()
        orch_pid = os.getpid()
        hb_ring: collections.deque[str] = collections.deque(
            maxlen=_HB_RING_MAXLEN)
        live_hb = _heartbeat_visible()

        def heartbeat() -> None:
            while not stop_event.wait(get_config().runtime.heartbeat_interval_s):
                elapsed = time.monotonic() - start
                child_mem = fmt_memory(get_rss_mb(proc.pid))
                orch_mem = fmt_memory(get_rss_mb(orch_pid))
                line = (f"    ... running [{_fmt_elapsed(elapsed)}]"
                        f"  PID {proc.pid} {lane_tag}"
                        f"  Mem: codex={child_mem} orch={orch_mem}")
                hb_ring.append(line)
                if live_hb:
                    print(line, file=sys.stderr, flush=True)

        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()

        stdout = ""
        stderr = ""
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_process_tree(proc)
            try:
                stdout, stderr = proc.communicate(timeout=_REAP_TIMEOUT_S)
            except Exception:  # noqa: BLE001
                stdout, stderr = stdout or "", stderr or ""
            timed_out = True
        finally:
            _unregister_child(proc)
            stop_event.set()
            hb.join(timeout=2)

        duration = time.monotonic() - start
        print(f"    PID {proc.pid} finished {lane_tag} "
              f"[{_fmt_elapsed(duration)}]")

        if timed_out or proc.returncode != 0:
            _flush_heartbeats(hb_ring, lane_tag)

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
                   on_failure: Any = None,
                   effort: str | None = None) -> LLMResult:
    """Run prompt with automatic retry on fast-fail errors.

    Rate-limit handling is **out-of-band**: when ``rate_limit`` is detected,
    we record a global pause via ``RateLimitController`` (if installed) and
    block here until the reset passes, then re-run the same prompt without
    consuming a retry slot. This keeps quality equivalent to a no-limit run.

    ``on_failure`` is called once per failed attempt with the LLMResult, so
    callers can persist per-lane diagnostic logs for every attempt (including
    intermediate retries) rather than only the final one.

    ``effort`` per-call override (decision #49) — passed through to
    ``backend.run``. ``None`` falls back to backend instance default.
    """
    backoff_cfg = get_config().backoff
    fast_backoff = backoff_cfg.fast_empty_failure_backoff_s

    attempt = 0
    while True:
        attempt += 1
        result = backend.run(prompt, allowed_tools=allowed_tools,
                             timeout_seconds=timeout_seconds,
                             lane_name=lane_name,
                             effort=effort)
        # Record per-call time / token / cost to the run ledger (no-op when
        # uninitialised; every attempt — incl. retries — is a real subprocess
        # that spent tokens, so record each one).
        _record_run_metrics(lane_name, result)
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
