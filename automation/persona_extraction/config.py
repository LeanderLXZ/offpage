"""TOML configuration for the extraction pipeline.

Single entry point: ``load_config()``. Returns a frozen ``Config`` dataclass
that callers (orchestrator, scene_archive, llm_backend, repair_agent) read
default values from instead of hard-coding constants.

Override priority (high → low):
    CLI flag  >  config.local.toml  >  config.toml  >  code dataclass default

``config.local.toml`` (sibling of ``config.toml``) is git-ignored and lets
a single developer override individual keys without modifying the tracked
file.

See ``docs/requirements.md`` §11.12 for the full configuration contract.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sectional dataclasses (mirror config.toml structure)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StageConfig:
    target_chapter_count: int = 10
    min_chapter_count: int = 5
    max_chapter_count: int = 15


@dataclass(frozen=True)
class Phase0Config:
    concurrency: int = 10
    json_repair_l2_timeout_s: int = 600


@dataclass(frozen=True)
class Phase1Config:
    exit_validation_max_retry: int = 2


@dataclass(frozen=True)
class Phase3Config:
    extraction_timeout_s: int = 3600
    review_timeout_s: int = 600
    max_turns: int = 50


@dataclass(frozen=True)
class Phase4Config:
    concurrency: int = 10
    circuit_breaker_failure_threshold: int = 8
    circuit_breaker_window_s: int = 60
    circuit_breaker_pause_s: int = 180


@dataclass(frozen=True)
class RepairAgentConfig:
    t0_retry: int = 1
    t1_retry: int = 3
    t2_retry: int = 3
    t3_retry: int = 1
    t3_max_per_file: int = 1
    total_round_limit: int = 5
    triage_enabled: bool = True
    triage_accept_cap_per_file: int = 3


@dataclass(frozen=True)
class BackoffConfig:
    fast_empty_failure_threshold_s: int = 5
    fast_empty_failure_backoff_s: tuple[int, ...] = (30, 60, 120)


@dataclass(frozen=True)
class RateLimitConfig:
    resume_buffer_s: int = 60
    parse_fallback_strategy: str = "probe"   # "probe" | "fixed"
    parse_fallback_sleep_s: int = 1800
    weekly_max_wait_h: int = 12
    weekly_over_limit_action: str = "stop"   # "stop" | "wait"
    # Probe hard-stop (§11.13.8): maximum wall-clock hours a single
    # unknown-reason probe session may drag on before the controller
    # raises RateLimitHardStop (→ CLI exit 2). Anchored on
    # ``probe_session_started_at`` in the pause record.
    probe_max_wait_h: int = 6
    # Probe leader election (§11.13.6): only one lane per process calls
    # ``probe_fn`` per window. Claims expire after this TTL so a crashed
    # leader can't block the pool forever.
    probe_claim_ttl_s: int = 120
    # Follower poll interval: how long a non-leader lane sleeps before
    # re-reading the pause record to see the leader's verdict.
    probe_follower_poll_s: int = 30


@dataclass(frozen=True)
class RuntimeConfig:
    max_runtime_min_default: int = 360
    heartbeat_interval_s: int = 30
    default_backend: str = "claude"


@dataclass(frozen=True)
class LoggingConfig:
    failed_lanes_retention_days: int = 30


@dataclass(frozen=True)
class GitConfig:
    extraction_branch_prefix: str = "extraction/"
    auto_squash_merge: bool = False


@dataclass(frozen=True)
class Config:
    stage: StageConfig = field(default_factory=StageConfig)
    phase0: Phase0Config = field(default_factory=Phase0Config)
    phase1: Phase1Config = field(default_factory=Phase1Config)
    phase3: Phase3Config = field(default_factory=Phase3Config)
    phase4: Phase4Config = field(default_factory=Phase4Config)
    repair_agent: RepairAgentConfig = field(default_factory=RepairAgentConfig)
    backoff: BackoffConfig = field(default_factory=BackoffConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    git: GitConfig = field(default_factory=GitConfig)


# ---------------------------------------------------------------------------
# Section name → dataclass map
# ---------------------------------------------------------------------------

_SECTION_TYPES: dict[str, type] = {
    "stage": StageConfig,
    "phase0": Phase0Config,
    "phase1": Phase1Config,
    "phase3": Phase3Config,
    "phase4": Phase4Config,
    "repair_agent": RepairAgentConfig,
    "backoff": BackoffConfig,
    "rate_limit": RateLimitConfig,
    "runtime": RuntimeConfig,
    "logging": LoggingConfig,
    "git": GitConfig,
}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "config.toml"
)
_LOCAL_OVERRIDE_PATH = (
    Path(__file__).resolve().parents[1] / "config.local.toml"
)


def _coerce_to_dataclass(section_name: str, raw: dict[str, Any]) -> Any:
    """Build a section dataclass from a TOML dict.

    Unknown keys are logged and dropped (forward-compat: a config.toml
    written by a newer pipeline version stays readable). Type coercion is
    minimal — we trust TOML's native typing except for tuple-of-int lists.
    """
    cls = _SECTION_TYPES[section_name]
    valid_fields = {f.name: f for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for key, val in raw.items():
        if key not in valid_fields:
            logger.warning("config: unknown key '%s.%s' ignored",
                           section_name, key)
            continue
        target_type = valid_fields[key].type
        # Tuple-of-int normalization (TOML arrays come in as list)
        if isinstance(val, list) and "tuple" in str(target_type):
            kwargs[key] = tuple(val)
        else:
            kwargs[key] = val
    return cls(**kwargs)


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Shallow merge: override section dicts win key-by-key."""
    out: dict[str, Any] = {k: dict(v) if isinstance(v, dict) else v
                           for k, v in base.items()}
    for section, payload in override.items():
        if isinstance(payload, dict) and isinstance(out.get(section), dict):
            out[section] = {**out[section], **payload}
        else:
            out[section] = payload
    return out


def load_config(
    *,
    config_path: Path | None = None,
    local_override_path: Path | None = None,
) -> Config:
    """Load the TOML config; missing file → all defaults.

    ``config.local.toml`` (sibling) overrides individual keys when present.
    Both paths are overridable for testing.
    """
    cfg_path = config_path or _DEFAULT_CONFIG_PATH
    local_path = local_override_path or _LOCAL_OVERRIDE_PATH

    raw: dict[str, Any] = {}
    if cfg_path.exists():
        with open(cfg_path, "rb") as f:
            raw = tomllib.load(f)
    else:
        logger.info("config: %s not found, using built-in defaults",
                    cfg_path)

    if local_path.exists():
        with open(local_path, "rb") as f:
            local_raw = tomllib.load(f)
        raw = _merge_dicts(raw, local_raw)

    sections: dict[str, Any] = {}
    for name, cls in _SECTION_TYPES.items():
        section_raw = raw.get(name, {})
        if not isinstance(section_raw, dict):
            logger.warning("config: section [%s] is not a table, ignoring",
                           name)
            section_raw = {}
        sections[name] = _coerce_to_dataclass(name, section_raw)

    return Config(**sections)


# ---------------------------------------------------------------------------
# Process-level cached singleton
# ---------------------------------------------------------------------------

_active: Config | None = None


def get_config() -> Config:
    """Return the process-wide loaded config (loads on first call)."""
    global _active
    if _active is None:
        _active = load_config()
    return _active


def set_config(cfg: Config) -> None:
    """Override the cached config (for tests / explicit reloads)."""
    global _active
    _active = cfg


def reset_config() -> None:
    """Drop the cached config; next ``get_config()`` reloads from disk."""
    global _active
    _active = None
