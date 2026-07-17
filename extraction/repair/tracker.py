"""Issue tracking across repair rounds — fingerprint diff, convergence
and regression detection.

Since the Phase B L3 gate re-checks only the json_paths a fix touched this
round (T-GATE-SCOPED-RECHECK), the round diff below acquires a sharper
meaning than it had under the old full-file gate: an ``introduced`` semantic
issue can now only appear ON A PATH A FIX TOUCHED, so it is a genuine "my fix
broke something here", not the nondeterministic untouched-field jitter the
full-file re-review used to manufacture every round. The math is unchanged;
the interpretation is what tightened. That is why ``is_regression`` /
``is_stalled`` / ``is_l3_gate_reemerge`` remain valid without new guards.
"""

from __future__ import annotations

from .protocol import Issue, RepairAttempt, RoundReport


class IssueTracker:
    """Tracks issues across rounds and per-issue repair history."""

    def __init__(self) -> None:
        self._history: dict[str, list[RepairAttempt]] = {}
        self._prev_fingerprints: dict[str, Issue] = {}
        # Ordered log of L3 gate blocking-fingerprint sets, one entry per
        # gate invocation. Used by is_l3_gate_reemerge() to detect when
        # semantic issues refuse to converge across consecutive rounds.
        self._l3_gate_history: list[set[str]] = []

    # ------------------------------------------------------------------
    # Round diff
    # ------------------------------------------------------------------

    def diff(self, prev: list[Issue], curr: list[Issue]) -> RoundReport:
        prev_fps = {i.fingerprint: i for i in prev}
        curr_fps = {i.fingerprint: i for i in curr}
        return RoundReport(
            resolved=[prev_fps[fp] for fp in prev_fps if fp not in curr_fps],
            persisting=[curr_fps[fp] for fp in curr_fps if fp in prev_fps],
            introduced=[curr_fps[fp] for fp in curr_fps if fp not in prev_fps],
        )

    # ------------------------------------------------------------------
    # Per-issue repair history
    # ------------------------------------------------------------------

    def record_attempt(self, attempt: RepairAttempt) -> None:
        self._history.setdefault(attempt.issue_fingerprint, []).append(attempt)

    def get_history(self) -> dict[str, list[RepairAttempt]]:
        return dict(self._history)

    # ------------------------------------------------------------------
    # Safety valves
    # ------------------------------------------------------------------

    def is_regression(self, report: RoundReport) -> bool:
        """True if a round introduced strictly more issues than it resolved.

        Under the scoped L3 gate ``introduced`` counts only new problems on
        json_paths a fix touched this round, so this is now a real "the fixes
        broke more than they mended" signal rather than being tripped by
        full-file review jitter (which used to keep ``introduced`` at ~1 every
        round and slip past this valve).
        """
        return len(report.introduced) > len(report.resolved)

    def is_stalled(self, prev_report: RoundReport | None,
                   curr_report: RoundReport) -> bool:
        """True if persisting set is identical across two consecutive rounds.

        The ``len(curr_fps) > 0`` guard stays: an empty persisting set is
        convergence (issues cleared), not a stall. Reviewed under scoped-gate
        semantics — persisting is now "same issue survived a re-check of the
        very path it sits on", which is exactly the non-converging case this
        valve should catch.
        """
        if prev_report is None:
            return False
        prev_fps = {i.fingerprint for i in prev_report.persisting}
        curr_fps = {i.fingerprint for i in curr_report.persisting}
        return prev_fps == curr_fps and len(curr_fps) > 0

    # ------------------------------------------------------------------
    # L3 gate reemergence detection
    # ------------------------------------------------------------------

    def record_l3_gate(self, fingerprints: set[str]) -> None:
        """Record the blocking fingerprint set returned by one L3 gate run."""
        self._l3_gate_history.append(set(fingerprints))

    def is_l3_gate_reemerge(self) -> bool:
        """True when the two most recent non-empty L3 gate runs match.

        Means fixes changed the data but the LLM keeps flagging the same
        set of semantic issues — further fixing won't converge. Under the
        scoped gate this is sharper still: the identical set recurs on the
        same touched path(s) across rounds, so it is genuine non-convergence,
        not two independent full-file reviews happening to overlap.
        """
        if len(self._l3_gate_history) < 2:
            return False
        last = self._l3_gate_history[-1]
        prev = self._l3_gate_history[-2]
        return bool(last) and last == prev
