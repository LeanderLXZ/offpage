"""Shared validation issue type.

Used by both ``validation.shared.schema_tolerance`` and
``validation.gates.*`` so the same dataclass shape is returned across
the gate-style validation layer. Repair-framework checkers use their
own ``extraction.repair.protocol.Issue`` type — see
``validation/README.md`` for why these two coexist.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationIssue:
    severity: str   # "error" or "warning"
    file: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.file}: {self.message}"
