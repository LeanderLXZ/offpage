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

        Used by the Phase C fallback L3 (whole-file semantic verdict when the
        Phase B gate never ran) to re-check the semantic layer without
        re-running L0-L2. Returns an empty list if no checker is registered
        at this layer.
        """
        issues: list[Issue] = []
        for checker in self._checkers:
            if checker.layer != layer:
                continue
            issues.extend(checker.check(files, **kwargs))
        return issues

    def run_semantic_scoped(
        self,
        files: list[FileEntry],
        paths: list[str],
        **kwargs,
    ) -> list[Issue]:
        """Re-check the semantic layer (L3) restricted to ``paths``.

        The Phase B L3 gate uses this instead of ``run_layer(..., layer=3)``:
        it re-checks ONLY the paths it is handed — the caller's per-file gate
        scope (``coordinator._gate_scope``: what a fix touched this round plus
        the paths of semantic issues still open on that file) — and the
        semantic checker filters its output down to those paths (a program
        guarantee, not the soft prompt hint). This is what makes the gate a
        "did my fix land + is the known problem still there" verdict rather
        than a full-file re-audit — the latter re-flags nondeterministic
        untouched-field nits every round and never converges. Checkers at L3
        without ``check_scoped`` fall back to the full ``check``. Empty if no
        L3 checker is registered.
        """
        issues: list[Issue] = []
        for checker in self._checkers:
            if checker.layer != 3:
                continue
            scoped = getattr(checker, "check_scoped", None)
            if callable(scoped):
                issues.extend(scoped(files, paths, **kwargs))
            else:
                issues.extend(checker.check(files, **kwargs))
        return issues
