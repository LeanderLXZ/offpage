"""Issue tracking across repair rounds — fingerprint diff, convergence
and regression detection."""

from __future__ import annotations

from .protocol import Issue, RepairAttempt, RoundReport


class IssueTracker:
    """Tracks issues across rounds and per-issue repair history."""

    def __init__(self) -> None:
        self._history: dict[str, list[RepairAttempt]] = {}
        self._prev_fingerprints: dict[str, Issue] = {}

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
