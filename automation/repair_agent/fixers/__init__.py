"""Fixer registry — T0 through T3, escalating cost."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..protocol import FileEntry, FixResult, Issue, SourceContext


class BaseFixer(ABC):
    """Interface for all fixer tiers."""

    tier: int = 0

    @abstractmethod
    def fix(
        self,
        files: list[FileEntry],
        issues: list[Issue],
        strategy: str = "standard",
        source_context: SourceContext | None = None,
        attempt_num: int = 0,
        max_attempts: int = 1,
    ) -> FixResult:
        ...
