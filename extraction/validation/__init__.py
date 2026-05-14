"""Validation primitives + phase-boundary gates.

Top-level home for data-correctness logic shared by the orchestrator
(phase-boundary gates) and the repair framework (L0–L3 checkers).

Layout::

    validation/
    ├── gates/   — phase-boundary validators called by the orchestrator
    │              (e.g. Phase 2 baseline, Phase 3.5 consistency).
    │              Returns ``ValidationReport`` — no fixer loop.
    └── shared/  — pure-function primitives reused by both gates above
                   and ``extraction.repair.checkers.*`` framework layers.
"""
