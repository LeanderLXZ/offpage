"""Repair Agent — unified validation and repair system.

All phases call the same interface. The agent checks files against
schemas and business rules, then repairs issues in-place using
field-level patches with escalating fixer tiers.

Public API::

    from automation.repair_agent import run, validate_only

    result = run(files=[...], config=RepairConfig(...))
    issues = validate_only(files=[...])
"""

from .coordinator import run, validate_only
from .protocol import (
    FileEntry,
    Issue,
    RepairConfig,
    RepairResult,
    RetryPolicy,
    RoundReport,
    SourceContext,
)

__all__ = [
    "FileEntry",
    "Issue",
    "RepairConfig",
    "RepairResult",
    "RetryPolicy",
    "RoundReport",
    "SourceContext",
    "run",
    "validate_only",
]
