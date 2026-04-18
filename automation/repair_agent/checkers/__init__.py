"""Checker registry and pipeline.

Checkers are executed in layer order (L0 → L1 → L2 → L3).  Files with
errors at a lower layer are skipped by subsequent layers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..protocol import FileEntry, Issue


class BaseChecker(ABC):
    """Interface for all checker layers."""

    layer: int = 0  # 0=json_syntax, 1=schema, 2=structural, 3=semantic

    @abstractmethod
    def check(self, files: list[FileEntry], **kwargs) -> list[Issue]:
        ...


class CheckerPipeline:
    """Runs checkers in layer order, skipping files with prior errors."""

    def __init__(self) -> None:
        self._checkers: list[BaseChecker] = []

    def register(self, checker: BaseChecker) -> None:
        self._checkers.append(checker)
        self._checkers.sort(key=lambda c: c.layer)

    def run(
        self,
        files: list[FileEntry],
        max_layer: int = 3,
        run_semantic: bool = True,
        **kwargs,
    ) -> list[Issue]:
        all_issues: list[Issue] = []
        error_files: set[str] = set()

        for checker in self._checkers:
            if checker.layer > max_layer:
                break
            if checker.layer == 3 and not run_semantic:
                continue

            clean_files = [f for f in files if f.path not in error_files]
            if not clean_files:
                break

            issues = checker.check(clean_files, **kwargs)
            for issue in issues:
                all_issues.append(issue)
                if issue.severity == "error":
                    error_files.add(issue.file)

        return all_issues

    def run_scoped(
        self,
        files: list[FileEntry],
        patched_paths: list[str],
        max_layer: int = 2,
        **kwargs,
    ) -> list[Issue]:
        """Run L0–L2 checkers during fix loop (no semantic).

        All files are re-checked (not just patched ones) because a fix
        can introduce new issues or uncover previously-masked ones.
        ``patched_paths`` is passed as a hint for checkers that support
        optimized re-validation.
        """
        return self.run(
            files,
            max_layer=min(max_layer, 2),
            run_semantic=False,
            patched_paths=patched_paths,
            **kwargs,
        )

    def run_layer(
        self,
        files: list[FileEntry],
        layer: int,
        **kwargs,
    ) -> list[Issue]:
        """Run exactly one checker layer, bypassing the prior-error skip.

        Used by the Phase B L3 gate to re-check semantic layer on files
        that have been patched this round, without re-running L0-L2.
        Returns an empty list if no checker is registered at this layer.
        """
        issues: list[Issue] = []
        for checker in self._checkers:
            if checker.layer != layer:
                continue
            issues.extend(checker.check(files, **kwargs))
        return issues
