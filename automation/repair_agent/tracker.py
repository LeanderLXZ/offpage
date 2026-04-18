"""Issue tracking across repair rounds — fingerprint diff, convergence
and regression detection."""

from __future__ import annotations

from .protocol import Issue, RepairAttempt, RoundReport


class IssueTracker:
    """Tracks issues across rounds and per-issue repair history."""

    def __init__(self) -> None:
        self._history: dict[str, list[RepairAttempt]] = {}
        self._prev_fingerprints: dict[str, Issue] = {}
        # Global per-file tier-usage counters. Currently read by the
        # coordinator to enforce `RetryPolicy.t3_max_per_file`, but the
        # shape is general (tier -> count) so other tiers can opt in.
        self._tier_uses_per_file: dict[str, dict[int, int]] = {}
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

    def attempts_at_tier(self, fingerprint: str, tier: int) -> int:
        return sum(
            1 for a in self._history.get(fingerprint, [])
            if a.tier == tier
        )

    def get_history(self) -> dict[str, list[RepairAttempt]]:
        return dict(self._history)

    # ------------------------------------------------------------------
    # Safety valves
    # ------------------------------------------------------------------

    def is_regression(self, report: RoundReport) -> bool:
        """True if a round introduced strictly more issues than it resolved."""
        return len(report.introduced) > len(report.resolved)

    def is_stalled(self, prev_report: RoundReport | None,
                   curr_report: RoundReport) -> bool:
        """True if persisting set is identical across two consecutive rounds."""
        if prev_report is None:
            return False
        prev_fps = {i.fingerprint for i in prev_report.persisting}
        curr_fps = {i.fingerprint for i in curr_report.persisting}
        return prev_fps == curr_fps and len(curr_fps) > 0

    # ------------------------------------------------------------------
    # Per-file tier usage (T3 global cap enforcement)
    # ------------------------------------------------------------------

    def record_tier_use_on_file(self, file_path: str, tier: int) -> None:
        """Increment the tier-use counter for a file."""
        per_tier = self._tier_uses_per_file.setdefault(file_path, {})
        per_tier[tier] = per_tier.get(tier, 0) + 1

    def tier_uses_on_file(self, file_path: str, tier: int) -> int:
        """Return how many times ``tier`` has been applied to this file."""
        return self._tier_uses_per_file.get(file_path, {}).get(tier, 0)

    # ------------------------------------------------------------------
    # L3 gate reemergence detection
    # ------------------------------------------------------------------

    def record_l3_gate(self, fingerprints: set[str]) -> None:
        """Record the blocking fingerprint set returned by one L3 gate run."""
        self._l3_gate_history.append(set(fingerprints))

    def is_l3_gate_reemerge(self) -> bool:
        """True when the two most recent non-empty L3 gate runs match.

        Means fixes changed the data but the LLM keeps flagging the same
        set of semantic issues — further fixing won't converge.
        """
        if len(self._l3_gate_history) < 2:
            return False
        last = self._l3_gate_history[-1]
        prev = self._l3_gate_history[-2]
        return bool(last) and last == prev
